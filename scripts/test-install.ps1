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

  # 5 and 6. Git checkouts: local changes are protected; a clean checkout is upgraded.
  if (Get-Command git -ErrorAction SilentlyContinue) {
    $skills5 = Join-Path $root 'skills5'
    $t5 = Join-Path $skills5 $name
    New-Item -ItemType Directory -Path $t5 | Out-Null
    Copy-Item -LiteralPath $skillFile -Destination (Join-Path $t5 'SKILL.md')
    Push-Location $t5
    try {
      & git init -q 2>&1 | Out-Null
      & git add SKILL.md 2>&1 | Out-Null
      & git -c user.name=usap-test -c user.email=usap-test@example.invalid commit -q -m 'test checkout' 2>&1 | Out-Null
      Add-Content -LiteralPath (Join-Path $t5 'SKILL.md') -Value 'local edit'
      $r = Invoke-Installer $skills5 $Base
      Check ($r.Code -ne 0 -and $r.Out -match 'local changes; it was not changed') 'git checkout with local changes is refused'
      Check ((Get-Content -LiteralPath (Join-Path $t5 'SKILL.md') -Raw) -match 'local edit') 'refused checkout keeps its local edit'
      Check (Test-Path -LiteralPath (Join-Path $t5 '.git')) 'refused checkout keeps its .git folder'
      & git checkout -q -- SKILL.md 2>&1 | Out-Null
    } finally { Pop-Location }
    $r = Invoke-Installer $skills5 $Base
    Check ($r.Code -eq 0 -and -not (Test-Path -LiteralPath (Join-Path $t5 '.git'))) 'clean git checkout is upgraded to the release copy'
  } else {
    Write-Host 'skip - git checkout tests: git is not on PATH'
  }
  Write-Host "all installer tests passed for $Expected under $($PSVersionTable.PSEdition) $($PSVersionTable.PSVersion)"
}
finally {
  Remove-Item -Recurse -Force -LiteralPath $root -ErrorAction SilentlyContinue
  [Environment]::SetEnvironmentVariable('USAP_SKILLS_DIR', $null)
  [Environment]::SetEnvironmentVariable('USAP_RELEASE_BASE', $null)
}
