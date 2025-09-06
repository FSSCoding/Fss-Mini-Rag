# FSS-Mini-RAG Installation Script for Windows PowerShell
# Usage: iwr https://raw.githubusercontent.com/fsscoding/fss-mini-rag/main/install.ps1 -UseBasicParsing | iex

# Requires -Version 5.1
param(
    [switch]$Force = $false,
    [switch]$Quiet = $false
)

# Configuration
$PackageName = "fss-mini-rag"
$CommandName = "rag-mini"
$ErrorActionPreference = "Stop"

# Colors for output
$Red = [System.ConsoleColor]::Red
$Green = [System.ConsoleColor]::Green
$Yellow = [System.ConsoleColor]::Yellow
$Blue = [System.ConsoleColor]::Blue
$Cyan = [System.ConsoleColor]::Cyan

function Write-ColoredOutput {
    param(
        [string]$Message,
        [System.ConsoleColor]$Color = [System.ConsoleColor]::White,
        [string]$Prefix = ""
    )
    
    if (-not $Quiet) {
        $originalColor = $Host.UI.RawUI.ForegroundColor
        $Host.UI.RawUI.ForegroundColor = $Color
        Write-Host "$Prefix$Message"
        $Host.UI.RawUI.ForegroundColor = $originalColor
    }
}

function Write-Header {
    if ($Quiet) { return }
    
    Write-ColoredOutput "████████╗██╗   ██╗██████╗ " -Color $Cyan
    Write-ColoredOutput "██╔══██║██║   ██║██╔══██╗" -Color $Cyan
    Write-ColoredOutput "██████╔╝██║   ██║██████╔╝" -Color $Cyan
    Write-ColoredOutput "██╔══██╗██║   ██║██╔══██╗" -Color $Cyan
    Write-ColoredOutput "██║  ██║╚██████╔╝██║  ██║" -Color $Cyan
    Write-ColoredOutput "╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝" -Color $Cyan
    Write-Host ""
    Write-ColoredOutput "FSS-Mini-RAG Installation Script" -Color $Blue
    Write-ColoredOutput "Educational RAG that actually works!" -Color $Yellow
    Write-Host ""
}

function Write-Log {
    param([string]$Message)
    Write-ColoredOutput $Message -Color $Green -Prefix "[INFO] "
}

function Write-Warning {
    param([string]$Message)
    Write-ColoredOutput $Message -Color $Yellow -Prefix "[WARN] "
}

function Write-Error {
    param([string]$Message)
    Write-ColoredOutput $Message -Color $Red -Prefix "[ERROR] "
    exit 1
}

function Test-SystemRequirements {
    Write-Log "Checking system requirements..."
    
    # Check PowerShell version
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -lt 5) {
        Write-Error "PowerShell 5.1 or later is required. Found version: $($psVersion.ToString())"
    }
    Write-Log "PowerShell $($psVersion.ToString()) detected ✓"
    
    # Check if Python 3.8+ is available
    try {
        $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $pythonPath) {
            $pythonPath = (Get-Command python3 -ErrorAction SilentlyContinue).Source
        }
        
        if (-not $pythonPath) {
            Write-Error "Python 3 is required but not found. Please install Python 3.8 or later from python.org"
        }
        
        # Check Python version
        $pythonVersionOutput = & python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        if (-not $pythonVersionOutput) {
            $pythonVersionOutput = & python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        }
        
        if (-not $pythonVersionOutput) {
            Write-Error "Unable to determine Python version"
        }
        
        # Parse version and check if >= 3.8
        $versionParts = $pythonVersionOutput.Split('.')
        $majorVersion = [int]$versionParts[0]
        $minorVersion = [int]$versionParts[1]
        
        if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
            Write-Error "Python $pythonVersionOutput detected, but Python 3.8+ is required"
        }
        
        Write-Log "Python $pythonVersionOutput detected ✓"
        
        # Store python command for later use
        $script:PythonCommand = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
        
    } catch {
        Write-Error "Failed to check Python installation: $($_.Exception.Message)"
    }
}

function Install-UV {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Log "uv is already installed ✓"
        return $true
    }
    
    Write-Log "Installing uv (fast Python package manager)..."
    
    try {
        # Install uv using the official Windows installer
        $uvInstaller = Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing
        Invoke-Expression $uvInstaller.Content
        
        # Refresh environment to pick up new PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            Write-Log "uv installed successfully ✓"
            return $true
        } else {
            Write-Warning "uv installation may not be in PATH. Falling back to pip method."
            return $false
        }
    } catch {
        Write-Warning "uv installation failed: $($_.Exception.Message). Falling back to pip method."
        return $false
    }
}

function Install-WithUV {
    Write-Log "Installing $PackageName with uv..."
    
    try {
        & uv tool install $PackageName
        if ($LASTEXITCODE -eq 0) {
            Write-Log "$PackageName installed successfully with uv ✓"
            return $true
        } else {
            Write-Warning "uv installation failed. Falling back to pip method."
            return $false
        }
    } catch {
        Write-Warning "uv installation failed: $($_.Exception.Message). Falling back to pip method."
        return $false
    }
}

function Install-WithPipx {
    # Check if pipx is available
    if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
        Write-Log "Installing pipx..."
        try {
            & $script:PythonCommand -m pip install --user pipx
            & $script:PythonCommand -m pipx ensurepath
            
            # Refresh PATH
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        } catch {
            Write-Warning "Failed to install pipx: $($_.Exception.Message). Falling back to pip method."
            return $false
        }
    }
    
    if (Get-Command pipx -ErrorAction SilentlyContinue) {
        Write-Log "Installing $PackageName with pipx..."
        try {
            & pipx install $PackageName
            if ($LASTEXITCODE -eq 0) {
                Write-Log "$PackageName installed successfully with pipx ✓"
                return $true
            } else {
                Write-Warning "pipx installation failed. Falling back to pip method."
                return $false
            }
        } catch {
            Write-Warning "pipx installation failed: $($_.Exception.Message). Falling back to pip method."
            return $false
        }
    } else {
        Write-Warning "pipx not available. Falling back to pip method."
        return $false
    }
}

function Install-WithPip {
    Write-Log "Installing $PackageName with pip..."
    
    try {
        & $script:PythonCommand -m pip install --user $PackageName
        if ($LASTEXITCODE -eq 0) {
            Write-Log "$PackageName installed successfully with pip --user ✓"
            
            # Add Scripts directory to PATH if not already there
            $scriptsPath = & $script:PythonCommand -c "import site; print(site.getusersitepackages().replace('site-packages', 'Scripts'))"
            $currentPath = $env:Path
            
            if ($currentPath -notlike "*$scriptsPath*") {
                Write-Warning "Adding $scriptsPath to PATH..."
                $newPath = "$scriptsPath;$currentPath"
                [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
                $env:Path = $newPath
            }
            
            return $true
        } else {
            Write-Error "Failed to install $PackageName with pip."
        }
    } catch {
        Write-Error "Failed to install $PackageName with pip: $($_.Exception.Message)"
    }
}

function Test-Installation {
    Write-Log "Verifying installation..."
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Check if command is available
    if (Get-Command $CommandName -ErrorAction SilentlyContinue) {
        Write-Log "$CommandName command is available ✓"
        
        # Test the command
        try {
            & $CommandName --help > $null 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Installation verified successfully! ✅"
                return $true
            } else {
                Write-Warning "Command exists but may have issues."
                return $false
            }
        } catch {
            Write-Warning "Command exists but may have issues."
            return $false
        }
    } else {
        Write-Warning "$CommandName command not found in PATH."
        Write-Warning "You may need to restart your PowerShell session or reboot."
        return $false
    }
}

function Write-Usage {
    if ($Quiet) { return }
    
    Write-Host ""
    Write-ColoredOutput "🎉 Installation complete!" -Color $Green
    Write-Host ""
    Write-ColoredOutput "Quick Start:" -Color $Blue
    Write-ColoredOutput "  # Initialize your project" -Color $Cyan
    Write-Host "  $CommandName init"
    Write-Host ""
    Write-ColoredOutput "  # Search your codebase" -Color $Cyan
    Write-Host "  $CommandName search `"authentication logic`""
    Write-Host ""
    Write-ColoredOutput "  # Get help" -Color $Cyan
    Write-Host "  $CommandName --help"
    Write-Host ""
    Write-ColoredOutput "Documentation: " -Color $Blue -NoNewline
    Write-Host "https://github.com/FSSCoding/Fss-Mini-Rag"
    Write-Host ""
    
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        Write-ColoredOutput "Note: If the command is not found, restart PowerShell or reboot Windows." -Color $Yellow
        Write-Host ""
    }
}

# Main execution
function Main {
    Write-Header
    
    # Check system requirements
    Test-SystemRequirements
    
    # Try installation methods in order of preference
    $installationMethod = ""
    
    if ((Install-UV) -and (Install-WithUV)) {
        $installationMethod = "uv ✨"
    } elseif (Install-WithPipx) {
        $installationMethod = "pipx 📦"
    } else {
        Install-WithPip
        $installationMethod = "pip 🐍"
    }
    
    Write-Log "Installation method: $installationMethod"
    
    # Verify installation
    if (Test-Installation) {
        Write-Usage
    } else {
        Write-Warning "Installation completed but verification failed. The tool may still work after restarting PowerShell."
        Write-Usage
    }
}

# Run if not being dot-sourced
if ($MyInvocation.InvocationName -ne '.') {
    Main
}