@echo off
REM FSS-Mini-RAG Windows Installer
setlocal enabledelayedexpansion

REM Enable colors and unicode for modern Windows
chcp 65001 >nul 2>&1

REM Check for command line arguments
set "HEADLESS_MODE=false"
if "%1"=="--headless" (
    set "HEADLESS_MODE=true"
    echo Running in headless mode - using defaults for automation
) else if "%1"=="--help" (
    goto show_help
) else if "%1"=="-h" (
    goto show_help
)

goto start_installation

:show_help
echo.
echo FSS-Mini-RAG Windows Installation Script
echo.
echo Usage:
echo   install_windows.bat              Interactive installation
echo   install_windows.bat --headless   Automated installation for CI
echo   install_windows.bat --help       Show this help
echo.
pause
exit /b 0

:start_installation

echo.
echo ========================================================
echo            FSS-Mini-RAG Windows Installer
echo       Self-contained research and code search
echo ========================================================
echo.
echo Installation steps:
echo   1. Check Python environment
echo   2. Create virtual environment
echo   3. Install dependencies
echo   4. Verify installation
echo.

if "!HEADLESS_MODE!"=="true" (
    echo Headless mode: Beginning installation automatically
) else (
    set /p "continue=Begin installation? [Y/n]: "
    if /i "!continue!"=="n" (
        echo Installation cancelled.
        pause
        exit /b 0
    )
)

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo.
echo ========================================================
echo [1/4] Checking Python Environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo.
    echo Please install Python from: https://python.org/downloads
    echo   - Python 3.10 or higher recommended
    echo   - Make sure to check "Add Python to PATH" during installation
    echo   - Restart your command prompt after installation
    echo.
    echo Quick install options:
    echo   winget install Python.Python.3.12
    echo   choco install python312
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo Found Python !PYTHON_VERSION!

REM Check Python version (basic check for 3.x)
for /f "tokens=1 delims=." %%a in ("!PYTHON_VERSION!") do set "MAJOR_VERSION=%%a"
if !MAJOR_VERSION! LSS 3 (
    echo ERROR: Python !PYTHON_VERSION! found, but Python 3.10+ recommended
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [2/4] Creating Python Virtual Environment...
if exist "%SCRIPT_DIR%\.venv" (
    echo Found existing virtual environment, checking if it works...
    call "%SCRIPT_DIR%\.venv\Scripts\activate.bat" >nul 2>&1
    if not errorlevel 1 (
        "%SCRIPT_DIR%\.venv\Scripts\python.exe" -c "import sys; print('OK')" >nul 2>&1
        if not errorlevel 1 (
            echo Using existing virtual environment
            goto skip_venv_creation
        )
    )
    echo Removing problematic virtual environment...
    rmdir /s /q "%SCRIPT_DIR%\.venv" 2>nul
)

echo Creating fresh virtual environment...
python -m venv "%SCRIPT_DIR%\.venv"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    echo.
    echo This might be because:
    echo   - Python venv module is not installed
    echo   - Insufficient permissions
    echo   - Path contains special characters
    echo.
    pause
    exit /b 1
)
echo Virtual environment created successfully

:skip_venv_creation
echo.
echo ========================================================
echo [3/4] Installing Python Dependencies...
echo This may take 2-5 minutes depending on your internet speed...
echo.

call "%SCRIPT_DIR%\.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment
    pause
    exit /b 1
)

echo Upgrading pip...
"%SCRIPT_DIR%\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet

echo Installing dependencies (lancedb, pandas, numpy, etc.)...
"%SCRIPT_DIR%\.venv\Scripts\pip.exe" install -r "%SCRIPT_DIR%\requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    echo.
    echo Possible solutions:
    echo   - Check internet connection
    echo   - Try running as administrator
    echo   - Check if antivirus is blocking pip
    echo.
    pause
    exit /b 1
)

echo Installing FSS-Mini-RAG...
"%SCRIPT_DIR%\.venv\Scripts\pip.exe" install -e "%SCRIPT_DIR%"
if errorlevel 1 (
    echo ERROR: Failed to install FSS-Mini-RAG
    pause
    exit /b 1
)
echo Dependencies installed successfully

echo.
echo ========================================================
echo [4/4] Verifying Installation...
echo Testing imports...
"%SCRIPT_DIR%\.venv\Scripts\python.exe" -c "from mini_rag import CodeEmbedder, ProjectIndexer, CodeSearcher; print('Core imports OK')" 2>import_error.txt
if errorlevel 1 (
    echo ERROR: Installation test failed
    echo.
    echo Import error details:
    type import_error.txt
    echo.
    del import_error.txt >nul 2>&1
    pause
    exit /b 1
)
del import_error.txt >nul 2>&1

echo Testing CLI...
"%SCRIPT_DIR%\.venv\Scripts\rag-mini.exe" --help >nul 2>&1
if errorlevel 1 (
    echo WARNING: CLI entry point not found, but core imports work
    echo You can use: python -m mini_rag.cli --help
) else (
    echo CLI entry point OK
)

echo.
echo ========================================================
echo         INSTALLATION SUCCESSFUL!
echo ========================================================
echo.
echo Quick Start:
echo.
echo   Activate the environment first:
echo     %SCRIPT_DIR%\.venv\Scripts\activate.bat
echo.
echo   Then use the CLI:
echo     rag-mini init                          Index current directory
echo     rag-mini search "your query"           Search your codebase
echo     rag-mini search "query" --synthesize   Search with AI summary
echo     rag-mini gui                           Launch desktop GUI
echo.
echo   Or launch the GUI directly:
echo     %SCRIPT_DIR%\.venv\Scripts\rag-mini-gui.exe
echo.
echo   Web research:
echo     rag-mini scrape https://example.com    Scrape a URL
echo     rag-mini research "topic" --deep       Deep research
echo.
echo Setup complete! FSS-Mini-RAG is ready to use.
echo.
pause
exit /b 0
