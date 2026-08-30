# AURA Backend - Build a Fully Self-Contained Python Runtime.
#
# Downloads the official python.org "embeddable" Python build and turns
# it into a self-contained runtime at backend/python-portable/, with
# every package from requirements.txt installed into it. Unlike a normal
# venv, this does NOT reference any Python installed on your machine -
# it is a fully standalone folder that runs on ANY Windows 10/11 x64 PC,
# even one with no Python installed at all.
#
# Run this ONCE before every "npm run electron:build".
#
# Usage (from backend/ folder, in PowerShell):
#     .\scripts\build_portable_python.ps1

# IMPORTANT: deliberately NOT setting $ErrorActionPreference = "Stop" here.
# PowerShell merges a native exe's stderr (via 2>&1) into "error record"
# objects, and if ErrorActionPreference is "Stop", the FIRST such record
# halts the whole script immediately as an uncaught exception - even
# when we're about to check $LASTEXITCODE ourselves right after. That is
# exactly what was cutting off the real Python traceback and aborting
# mid-install. All real failure detection below is done manually via
# $LASTEXITCODE (see Invoke-Checked) instead, which is the reliable way
# to detect native command failures in PowerShell.
$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

$PY_VERSION = "3.11.9"
$ZIP_URL = "https://www.python.org/ftp/python/$PY_VERSION/python-$PY_VERSION-embed-amd64.zip"
$GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

$BackendDir = Split-Path -Parent $PSScriptRoot
$TargetDir = Join-Path $BackendDir "python-portable"
$TmpZip = Join-Path $env:TEMP "python-embed.zip"
$TmpGetPip = Join-Path $env:TEMP "get-pip.py"

# Runs a native exe, streaming its output LIVE (so you can see progress
# instead of a blank screen until it finishes), and stops the script
# with a clear message if it actually failed (non-zero exit code).
function Invoke-Checked {
    param(
        [string]$Description,
        [string]$Exe,
        [string[]]$Arguments
    )
    Write-Host $Description -ForegroundColor Cyan
    & $Exe @Arguments 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "== FAILED: $Description (exit code $LASTEXITCODE) ==" -ForegroundColor Red
        exit 1
    }
}

# Runs a PowerShell cmdlet (not a native exe) and stops with a clear
# message if it throws - used for the download/extract steps.
function Invoke-Step {
    param(
        [string]$Description,
        [scriptblock]$Action
    )
    Write-Host $Description -ForegroundColor Cyan
    try {
        & $Action
    } catch {
        Write-Host ""
        Write-Host "== FAILED: $Description ==" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
}

Write-Host "== AURA: building portable Python $PY_VERSION at $TargetDir ==" -ForegroundColor Cyan

if (Test-Path $TargetDir) {
    Write-Host "Removing existing python-portable folder..."
    Remove-Item -Recurse -Force $TargetDir
}
New-Item -ItemType Directory -Path $TargetDir | Out-Null

# 1. Download and extract the official embeddable Python
Invoke-Step -Description "Downloading embeddable Python from python.org..." -Action {
    Invoke-WebRequest -Uri $ZIP_URL -OutFile $TmpZip -ErrorAction Stop
}
Invoke-Step -Description "Extracting..." -Action {
    Expand-Archive -Path $TmpZip -DestinationPath $TargetDir -Force -ErrorAction Stop
}
Remove-Item $TmpZip

# 2. Enable site-packages (disabled by default in embeddable builds,
#    required so pip-installed packages are importable), AND add the
#    backend/ folder (parent of python-portable/) to sys.path.
#
#    Why: embeddable Python's ._pth file controls sys.path EXACTLY -
#    unlike a normal install, the current working directory is NOT
#    added automatically for -c/module execution. Without this, neither
#    "python -c 'import app.main'" nor "python -m uvicorn app.main:app"
#    can find AURA's own "app" package, no matter what directory you
#    run it from. Adding ".." (relative to this pth file's own folder,
#    i.e. python-portable/..  =  backend/) fixes this permanently and
#    works wherever the whole bundle ends up installed.
$PthFile = Get-ChildItem -Path $TargetDir -Filter "python*._pth" | Select-Object -First 1
if (-not $PthFile) {
    Write-Host "ERROR: could not find python*._pth in the embeddable package." -ForegroundColor Red
    exit 1
}
Write-Host "Enabling site-packages and backend/ import path in $($PthFile.Name)..."
$content = Get-Content $PthFile.FullName
$content = $content -replace "#import site", "import site"
if ($content -notcontains "..") {
    $content += ".."
}
Set-Content -Path $PthFile.FullName -Value $content

# 3. Bootstrap pip (embeddable Python does not include it)
Invoke-Step -Description "Downloading get-pip.py..." -Action {
    Invoke-WebRequest -Uri $GET_PIP_URL -OutFile $TmpGetPip -ErrorAction Stop
}
Invoke-Checked -Description "Installing pip..." -Exe "$TargetDir\python.exe" -Arguments @($TmpGetPip, "--no-warn-script-location")
Remove-Item $TmpGetPip

# 3b. setuptools/wheel - modern pip/get-pip.py no longer bundles these.
#     Several packages (e.g. webrtcvad) `import pkg_resources` at import
#     time, which lives in setuptools. IMPORTANT: setuptools v82.0.0
#     (Feb 2026) REMOVED pkg_resources entirely - installing the latest
#     setuptools (which "--upgrade" would do) breaks this again even
#     though setuptools itself installs "successfully". Pin below 82.
Invoke-Checked -Description "Installing setuptools<82 + wheel (provides pkg_resources)..." `
    -Exe "$TargetDir\python.exe" `
    -Arguments @("-m", "pip", "install", "--no-warn-script-location", "setuptools<82", "wheel")

# 4. Install torch CPU-only FIRST (plain "pip install torch" from PyPI
#    pulls the ~2GB CUDA build by default, which AURA doesn't need -
#    it's CPU-only ONNX export). Installing this first means the
#    requirements.txt line below is already satisfied and gets skipped.
Invoke-Checked -Description "Installing torch (CPU-only build, much smaller than default)..." `
    -Exe "$TargetDir\python.exe" `
    -Arguments @("-m", "pip", "install", "--no-warn-script-location", "torch", "--index-url", "https://download.pytorch.org/whl/cpu")

# 5. Install every AURA dependency straight into this portable Python
$RequirementsPath = Join-Path $BackendDir "requirements.txt"
Invoke-Checked -Description "Installing requirements.txt into python-portable (this can take several minutes)..." `
    -Exe "$TargetDir\python.exe" `
    -Arguments @("-m", "pip", "install", "--no-warn-script-location", "-r", $RequirementsPath)

# 6. Verify the backend actually imports cleanly RIGHT NOW - before you
#    spend 10+ minutes running electron:build and reinstalling the app
#    only to hit the same ModuleNotFoundError again. This runs the exact
#    same import chain app.main.py triggers on startup.
Write-Host ""
Write-Host "Verifying backend imports cleanly..." -ForegroundColor Cyan
Push-Location $BackendDir
$env:PYTHONPATH = $BackendDir
$importLines = & "$TargetDir\python.exe" -c "import app.main; import accelerate; import torch; from optimum.onnxruntime import ORTStableDiffusionPipeline; print('IMPORT_OK')" 2>&1
$importExitCode = $LASTEXITCODE
Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
Pop-Location

$importLines | ForEach-Object { Write-Host $_ }
$importOutput = $importLines | Out-String

if ($importExitCode -ne 0 -or ($importOutput -notmatch "IMPORT_OK")) {
    Write-Host ""
    Write-Host "== FAILED: app.main did not import cleanly (see traceback above). ==" -ForegroundColor Red
    Write-Host "Usually the fix is: add the missing package name shown above to" -ForegroundColor Yellow
    Write-Host "requirements.txt, then re-run this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "Backend imports cleanly - safe to build the installer now." -ForegroundColor Green
Write-Host ""
Write-Host "== Done. backend/python-portable is self-contained. ==" -ForegroundColor Green
Write-Host "This folder needs no Python installed on the target PC."
Write-Host "Now run: npm run electron:build (from frontend/)"