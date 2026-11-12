# USAP installer for Windows (Windows PowerShell 5.1 and PowerShell 7):
#   irm https://github.com/michael-berardi/ultraterm-subagent-protocol/releases/latest/download/install.ps1 | iex
# Downloads the latest release (usap.zip), checks its SHA-256 against SHA256SUMS, and installs the skill folder to
# %USERPROFILE%\.config\agents\skills\ultraterm-subagent-protocol. USAP is text, so it needs no runtime. Re-running upgrades
# in place. A git checkout with local changes is never overwritten. Nothing is added to PATH and no profile is edited.
# Environment: USAP_SKILLS_DIR (default <home>\.config\agents\skills), USAP_VERSION (pin, e.g. 1.4.1),
# USAP_RELEASE_BASE (override the download base URL, used by tests).
# The work runs inside a function so that $ErrorActionPreference is not left changed in the caller's session when run with iex.
function Install-Usap {
  $ErrorActionPreference = 'Stop'
  $repo = 'michael-berardi/ultraterm-subagent-protocol'
  $name = 'ultraterm-subagent-protocol'

  function Get-SkillField([string]$path, [string]$field) {
    $text = Get-Content -LiteralPath $path -Raw
    $m = [regex]::Match($text, "(?m)^\s*$field\s*:\s*(\S+)\s*$")
    if ($m.Success) { return $m.Groups[1].Value }
    return ''
  }

  if (-not (Get-Command Expand-Archive -ErrorAction SilentlyContinue)) {
    throw 'USAP install needs the Expand-Archive command, which is missing. Use Windows PowerShell 5.0 or newer, or install PowerShell 7 from https://aka.ms/powershell, then run this again.'
  }
  # Windows PowerShell 5.1 may default to older TLS, which github.com refuses.
  if ($PSVersionTable.PSEdition -ne 'Core') {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
  }

  $userHome = [Environment]::GetFolderPath('UserProfile')
  if (-not $userHome) { throw 'USAP install: cannot find your home folder (USERPROFILE is not set).' }
  $skillsDir = if ($env:USAP_SKILLS_DIR) { $env:USAP_SKILLS_DIR } else { Join-Path (Join-Path (Join-Path $userHome '.config') 'agents') 'skills' }
  $skillsDir = [IO.Path]::GetFullPath($skillsDir)
  if ($env:USAP_RELEASE_BASE) { $base = $env:USAP_RELEASE_BASE }
  elseif ($env:USAP_VERSION) { $base = "https://github.com/$repo/releases/download/v$($env:USAP_VERSION.TrimStart('v'))" }
  else { $base = "https://github.com/$repo/releases/latest/download" }

  $tmp = Join-Path ([IO.Path]::GetTempPath()) ("usap-install-" + [guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Path $tmp | Out-Null
  $stage = $null
  try {
    Write-Host 'Downloading USAP...'
    foreach ($file in @('usap.zip', 'SHA256SUMS')) {
      try { Invoke-WebRequest "$base/$file" -OutFile (Join-Path $tmp $file) -UseBasicParsing }
      catch { throw "download failed: $base/$file ($($_.Exception.Message))" }
    }

    $line = Get-Content -LiteralPath (Join-Path $tmp 'SHA256SUMS') | Where-Object { $_ -match '\s\*?usap\.zip$' } | Select-Object -First 1
    if (-not $line) { throw 'no checksum for usap.zip in SHA256SUMS; the release is incomplete. Nothing was installed.' }
    $want = ($line.Trim() -split '\s+')[0].ToLower()
    $got = (Get-FileHash -LiteralPath (Join-Path $tmp 'usap.zip') -Algorithm SHA256).Hash.ToLower()
    if ($got -ne $want) { throw "checksum mismatch for usap.zip (expected $want, got $got); nothing was installed." }

    $src = Join-Path $tmp 'src'
    try { Expand-Archive -LiteralPath (Join-Path $tmp 'usap.zip') -DestinationPath $src -Force }
    catch { throw "cannot unpack the download ($($_.Exception.Message)); nothing was installed." }
    $skillFile = Join-Path $src 'SKILL.md'
    if (-not (Test-Path -LiteralPath $skillFile)) { throw 'the download is not a USAP release (no SKILL.md inside); nothing was installed.' }
    $gotName = Get-SkillField $skillFile 'name'
    if ($gotName -ne $name) { throw "the download is for '$gotName', not $name; nothing was installed." }
    $version = Get-SkillField $skillFile 'version'
    if (-not $version) { throw 'cannot read the version from SKILL.md in the download; nothing was installed.' }

    New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
    $target = Join-Path $skillsDir $name
    # A git checkout is upgraded only when it has no local changes.
    if (Test-Path -LiteralPath (Join-Path $target '.git')) {
      if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "$target is a git checkout, and git is not installed to check its local changes; nothing was changed." }
      $prevEAP = $ErrorActionPreference
      $ErrorActionPreference = 'Continue'
      try { $changes = & git -C $target status --porcelain 2>&1; $code = $LASTEXITCODE }
      finally { $ErrorActionPreference = $prevEAP }
      if ($code -ne 0) { throw "cannot read the git status of $target; nothing was changed." }
      if ($changes) { throw "$target is a git checkout with local changes; it was not changed. Commit, stash or move those changes aside, then run this again." }
    }
    $previous = ''
    if (Test-Path -LiteralPath (Join-Path $target 'SKILL.md')) { $previous = Get-SkillField (Join-Path $target 'SKILL.md') 'version' }

    $stage = Join-Path $skillsDir (".$name.new." + [guid]::NewGuid().ToString('N'))
    try { Move-Item -LiteralPath $src -Destination $stage }
    catch { throw "cannot stage the download in $skillsDir ($($_.Exception.Message)); nothing was changed." }

    # Swap with renames: the old copy moves aside, the new one moves in, then the old one is removed.
    if (Test-Path -LiteralPath $target) {
      $backup = Join-Path $skillsDir (".$name.old." + [guid]::NewGuid().ToString('N'))
      try { Move-Item -LiteralPath $target -Destination $backup }
      catch { throw "cannot move the previous copy aside at $target ($($_.Exception.Message)); nothing was changed." }
      try { Move-Item -LiteralPath $stage -Destination $target }
      catch {
        Move-Item -LiteralPath $backup -Destination $target
        throw "cannot put the new copy in place at $target ($($_.Exception.Message)); the previous copy was restored."
      }
      $stage = $null
      Remove-Item -Recurse -Force -LiteralPath $backup
    } else {
      Move-Item -LiteralPath $stage -Destination $target
      $stage = $null
    }

    # Health check: the installed SKILL.md must declare the version that was downloaded.
    $installed = Get-SkillField (Join-Path $target 'SKILL.md') 'version'
    if ($installed -ne $version) { throw "the installed copy at $target reports '$installed', not $version." }

    if ($previous) { Write-Host "Upgraded USAP from $previous to $version." }
    else { Write-Host "USAP $version installed." }
    Write-Host "Installed at: $target"
    Write-Host "Check: $(Join-Path $target 'SKILL.md') declares USAP $installed (ok)"
    Write-Host 'Next: in your agent, say: Use the UltraTerm Subagent Protocol for this task.'
  }
  finally {
    if ($stage -and (Test-Path -LiteralPath $stage)) { Remove-Item -Recurse -Force -LiteralPath $stage -ErrorAction SilentlyContinue }
    Remove-Item -Recurse -Force -LiteralPath $tmp -ErrorAction SilentlyContinue
  }
}

Install-Usap
