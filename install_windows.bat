@echo off
REM FSS-Mini-RAG Windows Installer - Simple & Reliable

echo.
echo ===================================================
echo          FSS-Mini-RAG Windows Setup
echo ===================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo.
    echo Please install Python from: https://python.org/downloads
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo Found Python %PYTHON_VERSION%

echo.
echo [2/4] Creating virtual environment...
if exist "%SCRIPT_DIR%\.venv" (
    echo Removing old virtual environment...
    rmdir /s /q "%SCRIPT_DIR%\.venv" 2>nul
)

python -m venv "%SCRIPT_DIR%\.venv"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo Virtual environment created successfully

echo.
echo [3/4] Installing dependencies...
echo This may take a few minutes...
call "%SCRIPT_DIR%\.venv\Scripts\activate.bat"
"%SCRIPT_DIR%\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"%SCRIPT_DIR%\.venv\Scripts\pip.exe" install -r "%SCRIPT_DIR%\requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully

echo.
echo [4/4] Testing installation...
"%SCRIPT_DIR%\.venv\Scripts\python.exe" -c "from mini_rag import CodeEmbedder; print('Import test: OK')" 2>nul
if errorlevel 1 (
    echo ERROR: Installation test failed
    pause
    exit /b 1
)

echo.
echo ===================================================
echo          INSTALLATION SUCCESSFUL!
echo ===================================================
echo.
echo Quick start:
echo   rag.bat          - Interactive interface
echo   rag.bat help     - Show all commands
echo.

REM Check for Ollama and offer model setup
call :check_ollama

echo.
echo Setup complete! FSS-Mini-RAG is ready to use.
set /p choice="Press Enter to continue or 'test' to run quick test: "
if /i "%choice%"=="test" (
    echo.
    echo Running quick test...
    call "%SCRIPT_DIR%\.venv\Scripts\activate.bat"
    "%SCRIPT_DIR%\.venv\Scripts\python.exe" rag-mini.py index . --force
    if not errorlevel 1 (
        "%SCRIPT_DIR%\.venv\Scripts\python.exe" rag-mini.py search . "embedding" --top-k 3
    )
)

echo.
pause
exit /b 0

:check_ollama
echo.
echo Checking for AI features...

REM Simple Ollama check
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo Ollama not detected - basic search mode available
    echo.
    echo For AI features (synthesis, exploration):
    echo   1. Install Ollama: https://ollama.com/download
    echo   2. Run: ollama serve
    echo   3. Run: ollama pull qwen3:1.7b
    return
)

echo Ollama detected!

REM Check for any LLM models
ollama list 2>nul | findstr /v "NAME" | findstr /v "^$" >nul
if errorlevel 1 (
    echo No LLM models found
    echo.
    echo Recommended: ollama pull qwen3:1.7b
    echo This enables AI synthesis and exploration features
) else (
    echo LLM models found - AI features available!
)
return