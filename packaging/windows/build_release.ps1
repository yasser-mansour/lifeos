# Builds the Windows LIFEOS-Setup-<version>.exe. Must run on Windows (no
# cross-compilation) — see .github/workflows/release.yml's windows-latest
# job, which is the primary way this actually gets exercised, since there
# is no Windows machine to test this on directly during development.
#
# Usage: pwsh packaging/windows/build_release.ps1 -Version 0.1.0
param(
    [string]$Version = "0.1.0"
)
$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path "$PSScriptRoot/../..").Path
$PackagingDir = "$RootDir/packaging/windows"
$DistDir = "$PackagingDir/dist"

Write-Host "==> [1/5] Installing backend + Windows-wrapper dependencies"
& "$RootDir/.venv/Scripts/pip.exe" install -r "$RootDir/backend/requirements-windows.txt"
& "$RootDir/.venv/Scripts/pip.exe" install pyinstaller

Write-Host "==> [2/5] Bundling with PyInstaller (Python + Django + pywebview, single LIFEOS.exe)"
if (Test-Path "$DistDir") { Remove-Item -Recurse -Force "$DistDir" }
& "$RootDir/.venv/Scripts/pyinstaller.exe" "$PackagingDir/lifeos.spec" `
  --noconfirm `
  --distpath "$DistDir" `
  --workpath "$PackagingDir/build"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

Write-Host "==> [3/5] Downloading the WebView2 Runtime bootstrapper (bundled into the installer, not silently required)"
$WebView2Url = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
Invoke-WebRequest -Uri $WebView2Url -OutFile "$PackagingDir/MicrosoftEdgeWebview2Setup.exe"

Write-Host "==> [4/5] Building the installer with Inno Setup"
$Iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $Iscc) {
    Write-Host "    iscc not found — installing Inno Setup via Chocolatey"
    choco install innosetup -y --no-progress
    $Iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
}
if (-not $Iscc) { throw "Inno Setup (iscc.exe) could not be found or installed" }

$env:LIFEOS_VERSION = $Version
& $Iscc.Source "$PackagingDir/installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }

Write-Host "==> [5/5] Checksum"
$InstallerPath = "$DistDir/LIFEOS-Setup-$Version.exe"
if (-not (Test-Path $InstallerPath)) { throw "Expected installer not found at $InstallerPath" }
$Hash = Get-FileHash -Algorithm SHA256 $InstallerPath
"$($Hash.Hash.ToLower())  LIFEOS-Setup-$Version.exe" | Out-File -Encoding ascii "$DistDir/SHA256SUMS.txt"

Write-Host ""
Write-Host "Built: $InstallerPath"
Get-Content "$DistDir/SHA256SUMS.txt"
