# USAP installer for Windows (Windows PowerShell 5.1 and PowerShell 7):
#   irm https://github.com/michael-berardi/ultraterm-subagent-protocol/releases/latest/download/install.ps1 | iex
# Downloads the latest release (usap.zip), checks its SHA-256 against SHA256SUMS, and installs the skill folder to
# %USERPROFILE%\.config\agents\skills\ultraterm-subagent-protocol. USAP is text, so it needs no runtime. Re-running upgrades
# in place. A git checkout is never replaced: if clean it is updated with git pull --ff-only, otherwise it is left alone. Nothing is added to PATH and no profile is edited.
# Environment: USAP_SKILLS_DIR (default <home>\.config\agents\skills), USAP_VERSION (pin, e.g. 1.4.1),
# USAP_RELEASE_BASE (override the download base URL, used by tests).
# The work runs inside a function so that $ErrorActionPreference is not left changed in the caller's session when run with iex.
function Install-Usap {
  $ErrorActionPreference = 'Stop'
  $ProgressPreference = 'SilentlyContinue'
  $repo = 'michael-berardi/ultraterm-subagent-protocol'
  $name = 'ultraterm-subagent-protocol'

  # Walks a folder without descending into reparse points (junctions, symlinks); returns the first reparse point or .git found.
  function Find-UnsafeEntry([string]$root) {
    $pending = New-Object 'System.Collections.Generic.Stack[string]'
    $pending.Push($root)
    while ($pending.Count -gt 0) {
      $dir = $pending.Pop()
      foreach ($child in @(Get-ChildItem -LiteralPath $dir -Force)) {
        if ($child.Name -eq '.git' -or ($child.Attributes -band [IO.FileAttributes]::ReparsePoint)) { return $child.FullName }
        if ($child.PSIsContainer) { $pending.Push($child.FullName) }
      }
    }
    return $null
  }

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
  $skillsDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($skillsDir)
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

    # Unpack straight into a staging folder under the skills folder (a move from %TEMP% can fail across drives on 5.1).
    New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
    $stage = Join-Path $skillsDir (".$name.new." + [guid]::NewGuid().ToString('N'))
    $src = $stage
    try { Expand-Archive -LiteralPath (Join-Path $tmp 'usap.zip') -DestinationPath $stage -Force }
    catch { throw "cannot unpack the download ($($_.Exception.Message)); nothing was installed." }
    $skillFile = Join-Path $src 'SKILL.md'
    if (-not (Test-Path -LiteralPath $skillFile)) { throw 'the download is not a USAP release (no SKILL.md inside); nothing was installed.' }
    $gotName = Get-SkillField $skillFile 'name'
    if ($gotName -ne $name) { throw "the download is for '$gotName', not $name; nothing was installed." }
    $version = Get-SkillField $skillFile 'version'
    if (-not $version) { throw 'cannot read the version from SKILL.md in the download; nothing was installed.' }

    $target = Join-Path $skillsDir $name
    # A symlinked or junctioned skill folder is never replaced: removing it could delete what it points at.
    if (Test-Path -LiteralPath $target) {
      $item = Get-Item -LiteralPath $target -Force
      if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "$target is a symbolic link or junction (to $($item.Target)); it was not changed. Remove the link yourself if you want the installer to manage this folder, then run this again."
      }
    }
    # A git checkout is never swapped: commits, stashes, branches and ignored files would be lost with its .git folder.
    # A clean checkout is fast-forwarded in place; anything else is left alone.
    if (Test-Path -LiteralPath (Join-Path $target '.git')) {
      if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "$target is a git checkout, and git is not installed to update it; nothing was changed." }
      $prevEAP = $ErrorActionPreference
      $ErrorActionPreference = 'Continue'
      try { $changes = & git -C $target status --porcelain 2>&1; $code = $LASTEXITCODE }
      finally { $ErrorActionPreference = $prevEAP }
      if ($code -ne 0) { throw "cannot read the git status of $target; nothing was changed." }
      if ($changes) { throw "$target is a git checkout with local changes; it was not changed. Commit, stash or move those changes aside, then run this again." }
      if ($env:USAP_VERSION) {
        throw "$target is a git checkout, and USAP_VERSION asks for a pinned release, so it was not pulled or changed. Pin it yourself with git: git -C `"$target`" fetch --tags; git -C `"$target`" checkout v$($env:USAP_VERSION.TrimStart('v'))"
      }
      Write-Host "$target is a git checkout; updating it with git pull --ff-only..."
      $prevPrompt = $env:GIT_TERMINAL_PROMPT
      $env:GIT_TERMINAL_PROMPT = '0'
      $ErrorActionPreference = 'Continue'
      try { $pulled = (& git -C $target pull --ff-only 2>&1 | Out-String); $code = $LASTEXITCODE }
      finally { $ErrorActionPreference = $prevEAP; $env:GIT_TERMINAL_PROMPT = $prevPrompt }
      if ($code -ne 0) {
        throw "git pull --ff-only failed in $target; it was not changed. $pulled Update it yourself with git (for a pinned tag: git -C `"$target`" fetch --tags, then git -C `"$target`" checkout v$version), or move it aside, then run this again."
      }
      $now = Get-SkillField (Join-Path $target 'SKILL.md') 'version'
      Write-Host "Updated the git checkout at $target; it now declares USAP $now."
      if ($now -ne $version) { Write-Host "Note: the latest release is USAP $version; the checkout's branch declares $now." }
      Write-Host "Installed at: $target"
      return
    }
    # The old copy must hold no reparse point and no .git at any depth: deleting it could follow a junction out of the folder.
    if (Test-Path -LiteralPath $target) {
      $unsafe = Find-UnsafeEntry $target
      if ($unsafe) { throw "$target contains a link or a .git folder ($unsafe); it was not changed. Move that aside or remove it yourself, then run this again." }
    }
    $previous = ''
    if (Test-Path -LiteralPath (Join-Path $target 'SKILL.md')) { $previous = Get-SkillField (Join-Path $target 'SKILL.md') 'version' }

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
      [IO.Directory]::Delete($backup, $true)
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
