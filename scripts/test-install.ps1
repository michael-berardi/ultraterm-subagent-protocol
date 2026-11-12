# Installer tests for scripts/install.ps1 (Windows PowerShell 5.1 and PowerShell 7).
# Invoke-WebRequest does not accept file:// URLs, so the release must be served over HTTP:
#   -Base     a folder URL serving the release built by scripts/build-release.sh (usap.zip, SHA256SUMS, ...)
#   -BadBase  a folder URL serving the same release with usap.zip corrupted (its SHA256SUMS line unchanged)
#   -Expected the version the release declares (SKILL.md metadata.version)
# Each run installs into a temporary skills folder through USAP_SKILLS_DIR, never the real profile.
# Covered: fresh install and health check, re-install upgrade, corrupted archive refused, unreachable release named,
# git checkout with local changes protected, clean git checkout upgraded (needs git on PATH).
# Usage: pwsh -NoProfile -File scripts/test-install.ps1 -Base <url> -BadBase <url> -Expected <version>
param(
  [Parameter(Mandatory = $true)][string]$Base,
  [Parameter(Mandatory = $true)][string]$BadBase,
  [Parameter(Mandatory = $true)][string]$Expected,
  [string]$Installer = (Join-Path $PSScriptRoot 'install.ps1')
)
$ErrorActionPreference = 'Continue'
$name = 'ultraterm-subagent-protocol'
$pwshExe = (Get-Process -Id $PID).Path
$root = Join-Path ([IO.Path]::GetTempPath()) ("usap-test-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null

function Check([bool]$ok, [string]$message) {
  if (-not $ok) { throw "FAIL - $message" }
  Write-Host "ok - $message"
}

# Runs install.ps1 in a child PowerShell with the given skills folder and base URL; returns exit code and output.
function Invoke-Installer([string]$skills, [string]$base) {
  [Environment]::SetEnvironmentVariable('USAP_SKILLS_DIR', $skills)
  [Environment]::SetEnvironmentVariable('USAP_RELEASE_BASE', $base)
  [Environment]::SetEnvironmentVariable('USAP_VERSION', $null)
  $out = (& $pwshExe -NoProfile -File $Installer 2>&1 | Out-String)
  return @{ Code = $LASTEXITCODE; Out = $out }
}

function Get-Version([string]$skillFile) {
  $m = [regex]::Match((Get-Content -LiteralPath $skillFile -Raw), '(?m)^\s*version:\s*(\S+)')
  if ($m.Success) { return $m.Groups[1].Value }
  return ''
}

function Get-FolderEntry([string]$dir) {
  # Returned with the comma operator so a single entry stays an array instead of unrolling to a string.
  return , @(Get-ChildItem -LiteralPath $dir -Force)
}

try {
  $skills = Join-Path $root 'skills'
  $target = Join-Path $skills $name
  $skillFile = Join-Path $target 'SKILL.md'

  # 1. Fresh install.
  $r = Invoke-Installer $skills $Base
  Check ($r.Code -eq 0) "fresh install exits 0 (exit $($r.Code))"
  Check ($r.Out -match "USAP $([regex]::Escape($Expected)) installed\.") "fresh install reports $Expected"
  Check ((Get-Version $skillFile) -eq $Expected) "installed SKILL.md declares $Expected"
  $entries = Get-FolderEntry $skills
  Check ($entries.Count -eq 1 -and $entries[0].Name -eq $name) 'fresh install leaves no staging or backup folders'

  # 2. Re-install upgrades in place: pretend the installed copy is older first.
  $text = Get-Content -LiteralPath $skillFile -Raw
  Set-Content -LiteralPath $skillFile -Value ($text -replace '(?m)^(\s*version:)\s*\S+', '$1 0.0.1') -NoNewline
  $r = Invoke-Installer $skills $Base
  Check ($r.Code -eq 0) "re-install exits 0 (exit $($r.Code))"
  Check ($r.Out -match "Upgraded USAP from 0\.0\.1 to $([regex]::Escape($Expected))\.") 're-install reports the upgrade from 0.0.1'
  Check ((Get-Version $skillFile) -eq $Expected) 're-install restores the release copy'

  # 3. Corrupted archive refused; the installed copy is untouched.
  Set-Content -LiteralPath $skillFile -Value ($text -replace '(?m)^(\s*version:)\s*\S+', '$1 0.0.1') -NoNewline
  $r = Invoke-Installer $skills $BadBase
  Check ($r.Code -ne 0) "corrupted archive exits non-zero (exit $($r.Code))"
  Check ($r.Out -match 'checksum mismatch for usap\.zip') 'corrupted archive is named as a checksum mismatch'
  Check ((Get-Version $skillFile) -eq '0.0.1') 'corrupted archive leaves the installed copy unchanged'
  $entries = Get-FolderEntry $skills
  Check ($entries.Count -eq 1 -and $entries[0].Name -eq $name) 'corrupted archive leaves no staging folder'
  $r = Invoke-Installer $skills $Base
  Check ($r.Code -eq 0 -and (Get-Version $skillFile) -eq $Expected) 'a good release installs again after a refused one'

  # 4. Unreachable release is named by URL and changes nothing.
  $skills4 = Join-Path $root 'skills4'
  $r = Invoke-Installer $skills4 "$Base/no-such-release"
  # PowerShell's error display may wrap the message, so the pattern allows line breaks between its parts.
  Check ($r.Code -ne 0 -and $r.Out -match '(?s)download failed:.*no-such-release/usap\.zip') 'unreachable release is named by URL'
  Check (-not (Test-Path -LiteralPath $skills4)) 'unreachable release creates no folder'

  # 5. Git checkouts are never swapped; a clean one is fast-forwarded. Each is a clone of a local origin.
  if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitc = @('-c', 'user.name=usap-test', '-c', 'user.email=usap-test@example.invalid')
    function Invoke-Git([string]$dir, [string[]]$gitArgs) { $o = (& git -C $dir @gitc @gitArgs 2>&1 | Out-String); if ($LASTEXITCODE -ne 0) { throw "git $gitArgs failed: $o" }; return $o }
    $origin = Join-Path $root 'origin.git'
    $seed = Join-Path $root 'seed'
    & git init -q --bare $origin 2>&1 | Out-Null
    New-Item -ItemType Directory -Path $seed | Out-Null
    & git init -q $seed 2>&1 | Out-Null
    Copy-Item -LiteralPath $skillFile -Destination (Join-Path $seed 'SKILL.md')
    Invoke-Git $seed @('add', 'SKILL.md') | Out-Null
    Invoke-Git $seed @('commit', '-q', '-m', 'seed') | Out-Null
    Invoke-Git $seed @('push', '-q', $origin, 'HEAD:refs/heads/main') | Out-Null
    & git -C $origin symbolic-ref HEAD refs/heads/main 2>&1 | Out-Null
    function New-Clone([string]$skillsFolder) {
      New-Item -ItemType Directory -Force -Path $skillsFolder | Out-Null
      $d = Join-Path $skillsFolder $name
      & git clone -q $origin $d 2>&1 | Out-Null
      return $d
    }

    $skills5 = Join-Path $root 'skills5'
    $t5 = New-Clone $skills5
    Add-Content -LiteralPath (Join-Path $t5 'SKILL.md') -Value 'local edit'
    $r = Invoke-Installer $skills5 $Base
    Check ($r.Code -ne 0 -and $r.Out -match 'local changes; it was not changed') 'git checkout with local changes is refused'
    Check ((Get-Content -LiteralPath (Join-Path $t5 'SKILL.md') -Raw) -match 'local edit') 'refused checkout keeps its local edit'
    Check (Test-Path -LiteralPath (Join-Path $t5 '.git')) 'refused checkout keeps its .git folder'
    Invoke-Git $t5 @('checkout', '-q', '--', 'SKILL.md') | Out-Null

    Set-Content -LiteralPath (Join-Path $t5 'notes.txt') -Value 'extra'
    Invoke-Git $t5 @('add', 'notes.txt') | Out-Null
    Invoke-Git $t5 @('commit', '-q', '-m', 'unpushed local work') | Out-Null
    $mine = (Invoke-Git $t5 @('rev-parse', 'HEAD')).Trim()
    $r = Invoke-Installer $skills5 $Base
    Check ($r.Code -eq 0 -and (Test-Path -LiteralPath (Join-Path $t5 '.git'))) 'clean checkout with an unpushed commit keeps its .git'
    Check ((Invoke-Git $t5 @('rev-parse', 'HEAD')).Trim() -eq $mine -and (Test-Path -LiteralPath (Join-Path $t5 'notes.txt'))) 'the unpushed local commit is kept'

    Add-Content -LiteralPath (Join-Path $t5 'SKILL.md') -Value 'wip'
    Invoke-Git $t5 @('stash', 'push', '-q', '-m', 'wip') | Out-Null
    $r = Invoke-Installer $skills5 $Base
    Check ($r.Code -eq 0 -and (Test-Path -LiteralPath (Join-Path $t5 '.git')) -and (Invoke-Git $t5 @('stash', 'list')).Trim()) 'checkout with a stash is not replaced and keeps the stash'

    $t6 = New-Clone (Join-Path $root 'skills6')
    Set-Content -LiteralPath (Join-Path $seed 'more.txt') -Value 'more'
    Invoke-Git $seed @('add', 'more.txt') | Out-Null
    Invoke-Git $seed @('commit', '-q', '-m', 'upstream') | Out-Null
    Invoke-Git $seed @('push', '-q', $origin, 'HEAD:refs/heads/main') | Out-Null
    $r = Invoke-Installer (Join-Path $root 'skills6') $Base
    Check ($r.Code -eq 0 -and (Test-Path -LiteralPath (Join-Path $t6 'more.txt')) -and (Test-Path -LiteralPath (Join-Path $t6 '.git'))) 'clean checkout behind origin is fast-forwarded in place'

    $t8 = New-Clone (Join-Path $root 'skills8')
    Set-Content -LiteralPath (Join-Path $t8 'mine.txt') -Value 'mine'
    Invoke-Git $t8 @('add', 'mine.txt') | Out-Null
    Invoke-Git $t8 @('commit', '-q', '-m', 'local') | Out-Null
    Set-Content -LiteralPath (Join-Path $seed 'x.txt') -Value 'x'
    Invoke-Git $seed @('add', 'x.txt') | Out-Null
    Invoke-Git $seed @('commit', '-q', '-m', 'upstream 2') | Out-Null
    Invoke-Git $seed @('push', '-q', $origin, 'HEAD:refs/heads/main') | Out-Null
    $mine = (Invoke-Git $t8 @('rev-parse', 'HEAD')).Trim()
    $r = Invoke-Installer (Join-Path $root 'skills8') $Base
    Check ($r.Code -ne 0 -and $r.Out -match 'git pull --ff-only failed' -and (Invoke-Git $t8 @('rev-parse', 'HEAD')).Trim() -eq $mine) 'checkout that cannot fast-forward is refused and unchanged'
  } else {
    Write-Host 'skip - git checkout tests: git is not on PATH'
  }

  # 6. A symlinked skill folder is refused and its target is untouched (needs symlink rights; always available on Linux).
  $skills10 = Join-Path $root 'skills10'
  $real = Join-Path $root 'real-skill'
  New-Item -ItemType Directory -Force -Path $skills10, $real | Out-Null
  Set-Content -LiteralPath (Join-Path $real 'keep.txt') -Value 'precious'
  $linked = $false
  try { New-Item -ItemType SymbolicLink -Path (Join-Path $skills10 $name) -Target $real -ErrorAction Stop | Out-Null; $linked = $true } catch { }
  if ($linked) {
    $r = Invoke-Installer $skills10 $Base
    Check ($r.Code -ne 0 -and $r.Out -match 'symbolic link or junction') 'symlinked skill folder is refused'
    Check (Test-Path -LiteralPath (Join-Path $real 'keep.txt')) 'the symlink target keeps its files'
  } else {
    Write-Host 'skip - symlink test: cannot create a symbolic link here'
  }

  # 6b. A link or .git anywhere inside the old copy is refused before anything moves.
  $skills11 = Join-Path $root 'skills11'
  $t11 = Join-Path $skills11 $name
  $out11 = Join-Path $root 'outside'
  New-Item -ItemType Directory -Force -Path (Join-Path $t11 'references/deep'), $out11 | Out-Null
  Set-Content -LiteralPath (Join-Path $out11 'keep.txt') -Value 'precious'
  Copy-Item -LiteralPath $skillFile -Destination (Join-Path $t11 'SKILL.md')
  $linked = $false
  try { New-Item -ItemType SymbolicLink -Path (Join-Path $t11 'references/deep/link') -Target $out11 -ErrorAction Stop | Out-Null; $linked = $true } catch { }
  if ($linked) {
    $r = Invoke-Installer $skills11 $Base
    Check ($r.Code -ne 0 -and $r.Out -match 'contains a link or a \.git folder') 'nested symlink in the old copy is refused'
    Check ((Test-Path -LiteralPath (Join-Path $out11 'keep.txt')) -and (Test-Path -LiteralPath (Join-Path $t11 'references/deep/link'))) 'nested symlink and its target are untouched'
    Remove-Item -LiteralPath (Join-Path $t11 'references/deep/link') -Force
  } else {
    Write-Host 'skip - nested symlink test: cannot create a symbolic link here'
  }
  New-Item -ItemType Directory -Path (Join-Path $t11 'references/deep/.git') | Out-Null
  $r = Invoke-Installer $skills11 $Base
  Check ($r.Code -ne 0 -and $r.Out -match 'contains a link or a \.git folder') 'nested .git in the old copy is refused'
  Check (Test-Path -LiteralPath (Join-Path $t11 'references/deep/.git')) 'nested .git is kept'
  $entries = Get-FolderEntry $skills11
  Check ($entries.Count -eq 1) 'refusal leaves no staging or backup folders'

  # 7. Static: bad Windows-only patterns must not return.
  $src = Get-Content -LiteralPath $Installer -Raw
  Check ($src -notmatch 'Move-Item\s+-LiteralPath\s+\$src') 'installer does not move the unpacked folder from %TEMP%'
  Check ($src -notmatch '\[IO\.Path\]::GetFullPath') 'installer does not resolve paths with [IO.Path]::GetFullPath'
  Check ($src -match 'ReparsePoint') 'installer checks for reparse points before removing a folder'
  Check ($src -match 'pull --ff-only') 'installer fast-forwards git checkouts instead of swapping them'
  Check ($src -match '\[IO\.Directory\]::Delete\(\$backup') 'old copy is deleted with [IO.Directory]::Delete, which does not follow junctions'
  Check ($src -notmatch 'Remove-Item[^\r\n]*\$backup') 'old copy is not deleted with Remove-Item -Recurse'
  Check ($src -match 'Find-UnsafeEntry \$target') 'old copy is scanned for links and .git before the swap'
  Check ($src -match '\$prevPrompt') 'GIT_TERMINAL_PROMPT is saved and restored'
  Write-Host "all installer tests passed for $Expected under $($PSVersionTable.PSEdition) $($PSVersionTable.PSVersion)"
}
finally {
  Remove-Item -Recurse -Force -LiteralPath $root -ErrorAction SilentlyContinue
  [Environment]::SetEnvironmentVariable('USAP_SKILLS_DIR', $null)
  [Environment]::SetEnvironmentVariable('USAP_RELEASE_BASE', $null)
}
