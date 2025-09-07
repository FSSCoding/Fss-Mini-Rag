# Reusable one-line installer template for Python CLI tools (Windows PowerShell)
# Copy this file and customize the marked sections

param(
    [switch]$Help,
    [switch]$Force
)

# CUSTOMIZE: Your package details
$PACKAGE_NAME = "your-package-name"
$CLI_COMMAND = "your-cli-command"
$GITHUB_REPO = "YOUR-USERNAME/YOUR-REPO"

# Colors for output (PowerShell)
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Cyan"
    White = "White"
}

# Print functions
function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Colors.Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor $Colors.Blue
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Colors.Red
}

function Write-Header {
    Write-Host "🚀 $PACKAGE_NAME Installer" -ForegroundColor $Colors.Blue
    Write-Host "==================================================" -ForegroundColor $Colors.Blue
}

# Check if command exists
function Test-Command {
    param([string]$Command)
    try {
        if (Get-Command $Command -ErrorAction Stop) {
            return $true
        }
    }
    catch {
        return $false
    }
}

# Check if package is already installed and working
function Test-ExistingInstallation {
    if (Test-Command $CLI_COMMAND) {
        Write-Info "Found existing $CLI_COMMAND installation"
        try {
            $null = & $CLI_COMMAND --version 2>$null
            Write-Success "$PACKAGE_NAME is already installed and working!"
            Write-Info "Run '$CLI_COMMAND --help' to get started"
            exit 0
        }
        catch {
            try {
                $null = & $CLI_COMMAND --help 2>$null
                Write-Success "$PACKAGE_NAME is already installed and working!"
                Write-Info "Run '$CLI_COMMAND --help' to get started"
                exit 0
            }
            catch {
                Write-Warning "Existing installation appears broken, proceeding with reinstallation"
            }
        }
    }
}

# Install with uv (fastest method)
function Install-WithUv {
    Write-Info "Attempting installation with uv (fastest method)..."
    
    if (!(Test-Command "uv")) {
        Write-Info "Installing uv package manager..."
        try {
            powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
            # Refresh PATH
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
            Write-Success "uv installed successfully"
        }
        catch {
            Write-Warning "Failed to install uv, trying next method..."
            return $false
        }
    }
    
    try {
        uv tool install $PACKAGE_NAME
        Write-Success "Installed $PACKAGE_NAME with uv"
        return $true
    }
    catch {
        Write-Warning "uv installation failed, trying next method..."
        return $false
    }
}

# Install with pipx (isolated environment)
function Install-WithPipx {
    Write-Info "Attempting installation with pipx (isolated environment)..."
    
    if (!(Test-Command "pipx")) {
        Write-Info "Installing pipx..."
        try {
            if (Test-Command "pip3") {
                pip3 install --user pipx
            }
            elseif (Test-Command "pip") {
                pip install --user pipx
            }
            else {
                Write-Warning "No pip found, trying next method..."
                return $false
            }
            
            # Refresh PATH
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
            
            if (Test-Command "pipx") {
                pipx ensurepath
                Write-Success "pipx installed successfully"
            }
            else {
                Write-Warning "pipx installation failed, trying next method..."
                return $false
            }
        }
        catch {
            Write-Warning "pipx installation failed, trying next method..."
            return $false
        }
    }
    
    try {
        pipx install $PACKAGE_NAME
        Write-Success "Installed $PACKAGE_NAME with pipx"
        return $true
    }
    catch {
        Write-Warning "pipx installation failed, trying next method..."
        return $false
    }
}

# Install with pip (fallback method)
function Install-WithPip {
    Write-Info "Attempting installation with pip (user install)..."
    
    $pipCmd = $null
    if (Test-Command "pip3") {
        $pipCmd = "pip3"
    }
    elseif (Test-Command "pip") {
        $pipCmd = "pip"
    }
    else {
        Write-Error "No pip found. Please install Python and pip first."
        return $false
    }
    
    try {
        & $pipCmd install --user $PACKAGE_NAME
        Write-Success "Installed $PACKAGE_NAME with pip"
        Write-Info "Make sure Python Scripts directory is in your PATH"
        return $true
    }
    catch {
        Write-Error "pip installation failed"
        return $false
    }
}

# Verify installation
function Test-Installation {
    # Refresh PATH to include newly installed tools
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    
    if (Test-Command $CLI_COMMAND) {
        Write-Success "Installation successful!"
        Write-Info "Testing $CLI_COMMAND..."
        
        try {
            $null = & $CLI_COMMAND --version 2>$null
            Write-Success "$CLI_COMMAND is working correctly!"
        }
        catch {
            try {
                $null = & $CLI_COMMAND --help 2>$null
                Write-Success "$CLI_COMMAND is working correctly!"
            }
            catch {
                Write-Warning "$CLI_COMMAND installed but not working properly"
                return $false
            }
        }
        
        Write-Info ""
        Write-Success "🎉 $PACKAGE_NAME is now installed!"
        Write-Info "Run '$CLI_COMMAND --help' to get started"
        
        # CUSTOMIZE: Add usage examples specific to your tool
        Write-Info ""
        Write-Info "Quick start examples:"
        Write-Info "  $CLI_COMMAND --help        # Show help"
        Write-Info "  $CLI_COMMAND init          # Initialize (if applicable)"
        Write-Info "  $CLI_COMMAND status        # Check status (if applicable)"
        
        return $true
    }
    else {
        Write-Error "Installation completed but $CLI_COMMAND not found in PATH"
        Write-Info "You may need to restart your PowerShell session or add Python Scripts to PATH"
        return $false
    }
}

# Show help
function Show-Help {
    Write-Header
    Write-Info "This script installs $PACKAGE_NAME using the best available method"
    Write-Info ""
    Write-Info "USAGE:"
    Write-Info "  iwr https://raw.githubusercontent.com/$GITHUB_REPO/main/install.ps1 -UseBasicParsing | iex"
    Write-Info ""
    Write-Info "OPTIONS:"
    Write-Info "  -Help    Show this help message"
    Write-Info "  -Force   Force reinstallation even if already installed"
    Write-Info ""
    Write-Info "METHODS (tried in order):"
    Write-Info "  1. uv (fastest)"
    Write-Info "  2. pipx (isolated)"
    Write-Info "  3. pip (fallback)"
}

# Main installation function
function Start-Installation {
    Write-Header
    Write-Info "This script will install $PACKAGE_NAME using the best available method"
    Write-Info "Trying: uv (fastest) → pipx (isolated) → pip (fallback)"
    Write-Info ""
    
    if (!$Force) {
        Test-ExistingInstallation
    }
    
    # Try installation methods in order of preference
    $success = $false
    if (Install-WithUv) { $success = $true }
    elseif (Install-WithPipx) { $success = $true }
    elseif (Install-WithPip) { $success = $true }
    
    if ($success) {
        Write-Info ""
        if (Test-Installation) {
            exit 0
        }
        else {
            exit 1
        }
    }
    else {
        Write-Info ""
        Write-Error "All installation methods failed!"
        Write-Info ""
        Write-Info "Manual installation options:"
        Write-Info "1. Install Python 3.8+ and pip, then run:"
        Write-Info "   pip install --user $PACKAGE_NAME"
        Write-Info ""
        Write-Info "2. Visit our GitHub for more options:"
        Write-Info "   https://github.com/$GITHUB_REPO"
        exit 1
    }
}

# Main execution
if ($Help) {
    Show-Help
}
else {
    Start-Installation
}