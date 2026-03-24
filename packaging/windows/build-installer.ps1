# FSS-Mini-RAG Windows Installer Build Script
# Downloads embedded Python, builds the wheel, and creates the Inno Setup installer.
#
# Prerequisites: Inno Setup 6+ installed (iscc.exe in PATH)
# Usage: powershell -ExecutionPolicy Bypass -File packaging\windows\build-installer.ps1

param(
    [string]$Version = "",
    [string]$PythonVersion = "3.11.9"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..\..").Path
$BuildDir = "$ScriptDir\build"

# Get version from package if not provided
if (-not $Version) {
    Push-Location $ProjectRoot
    $Version = python -c "import mini_rag; print(mini_rag.__version__)" 2>$null
    if (-not $Version) { $Version = "2.3.0" }
    Pop-Location
}

Write-Host "Building FSS-Mini-RAG v$Version Windows installer..." -ForegroundColor Cyan

# Clean build directory
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
New-Item -ItemType Directory -Path "$BuildDir\python" -Force | Out-Null
New-Item -ItemType Directory -Path "$BuildDir\wheel" -Force | Out-Null
New-Item -ItemType Directory -Path "$BuildDir\launchers" -Force | Out-Null

# Step 1: Download embedded Python
Write-Host "Downloading Python $PythonVersion embeddable..." -ForegroundColor Yellow
$PythonZip = "python-$PythonVersion-embed-amd64.zip"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/$PythonZip"
Invoke-WebRequest -Uri $PythonUrl -OutFile "$BuildDir\$PythonZip"
Expand-Archive -Path "$BuildDir\$PythonZip" -DestinationPath "$BuildDir\python" -Force
Remove-Item "$BuildDir\$PythonZip"

# Step 2: Enable pip in embedded Python
# The embedded Python has a ._pth file that restricts imports. We need to modify it.
$PthFile = Get-ChildItem "$BuildDir\python\python*._pth" | Select-Object -First 1
if ($PthFile) {
    $content = Get-Content $PthFile.FullName
    # Uncomment 'import site' line
    $content = $content -replace '^#\s*import site', 'import site'
    Set-Content -Path $PthFile.FullName -Value $content
}

# Download and install pip
Write-Host "Installing pip..." -ForegroundColor Yellow
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "$BuildDir\get-pip.py"
& "$BuildDir\python\python.exe" "$BuildDir\get-pip.py" --no-warn-script-location 2>&1
Remove-Item "$BuildDir\get-pip.py"

# Step 3: Build the wheel
Write-Host "Building wheel..." -ForegroundColor Yellow
Push-Location $ProjectRoot
python -m build --wheel --outdir "$BuildDir\wheel"
Pop-Location

# Step 4: Install dependencies into embedded Python
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& "$BuildDir\python\python.exe" -m pip install --no-warn-script-location `
    -r "$ProjectRoot\requirements.txt" 2>&1

# Install the wheel
$WheelFile = Get-ChildItem "$BuildDir\wheel\*.whl" | Select-Object -First 1
& "$BuildDir\python\python.exe" -m pip install --no-warn-script-location `
    $WheelFile.FullName 2>&1

# Step 5: Create launcher batch files
$CliLauncher = @'
@echo off
"%~dp0python\python.exe" -m mini_rag.cli %*
'@
Set-Content -Path "$BuildDir\launchers\rag-mini.bat" -Value $CliLauncher

$GuiLauncher = @'
@echo off
start "" "%~dp0python\pythonw.exe" -m mini_rag.gui %*
'@
Set-Content -Path "$BuildDir\launchers\rag-mini-gui.bat" -Value $GuiLauncher

# Step 6: Verify the embedded installation works
Write-Host "Verifying installation..." -ForegroundColor Yellow
$TestResult = & "$BuildDir\python\python.exe" -c "import mini_rag; print(mini_rag.__version__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Installation verification failed!" -ForegroundColor Red
    Write-Host $TestResult
    exit 1
}
Write-Host "Verified: mini_rag v$TestResult" -ForegroundColor Green

# Step 7: Build the installer with Inno Setup
Write-Host "Building installer with Inno Setup..." -ForegroundColor Yellow
$env:FSS_VERSION = $Version

# Find iscc.exe
$IsccPaths = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\iscc.exe",
    "${env:ProgramFiles}\Inno Setup 6\iscc.exe",
    "iscc.exe"
)
$Iscc = $IsccPaths | Where-Object { Test-Path $_ -ErrorAction SilentlyContinue } | Select-Object -First 1
if (-not $Iscc) {
    $Iscc = Get-Command "iscc.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path
}
if (-not $Iscc) {
    Write-Host "ERROR: Inno Setup not found. Install from https://jrsoftware.org/isinfo.php" -ForegroundColor Red
    exit 1
}

& $Iscc "$ScriptDir\installer.iss"

if ($LASTEXITCODE -eq 0) {
    $InstallerPath = "$ProjectRoot\dist\fss-mini-rag-$Version-setup.exe"
    $Size = [math]::Round((Get-Item $InstallerPath).Length / 1MB, 1)
    Write-Host ""
    Write-Host "Built: $InstallerPath ($Size MB)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Test with:" -ForegroundColor Cyan
    Write-Host "  $InstallerPath"
} else {
    Write-Host "ERROR: Inno Setup compilation failed!" -ForegroundColor Red
    exit 1
}
