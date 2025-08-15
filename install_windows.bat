@echo off
REM FSS-Mini-RAG Windows Installer - Beautiful & Comprehensive
setlocal enabledelayedexpansion

REM Enable colors and unicode for modern Windows
chcp 65001 >nul 2>&1

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║            FSS-Mini-RAG Windows Installer       ║
echo ║         Fast Semantic Search for Code           ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo 🚀 Comprehensive installation process:
echo   • Python environment setup and validation
echo   • Smart dependency management 
echo   • Optional AI model downloads (with your consent)
echo   • System testing and verification
echo   • Interactive tutorial (optional)
echo.
echo 💡 Note: You'll be asked before downloading any models
echo.

set /p "continue=Begin installation? [Y/n]: "
if /i "!continue!"=="n" (
    echo Installation cancelled.
    pause
    exit /b 0
)

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo.
echo ══════════════════════════════════════════════════
echo [1/5] Checking Python Environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python not found!
    echo.
    echo 📦 Please install Python from: https://python.org/downloads
    echo 🔧 Installation requirements:
    echo    • Python 3.8 or higher
    echo    • Make sure to check "Add Python to PATH" during installation
    echo    • Restart your command prompt after installation
    echo.
    echo 💡 Quick install options:
    echo    • Download from python.org (recommended)
    echo    • Or use: winget install Python.Python.3.11
    echo    • Or use: choco install python311
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo ✅ Found Python !PYTHON_VERSION!

REM Check Python version (basic check for 3.x)
for /f "tokens=1 delims=." %%a in ("!PYTHON_VERSION!") do set "MAJOR_VERSION=%%a"
if !MAJOR_VERSION! LSS 3 (
    echo ❌ ERROR: Python !PYTHON_VERSION! found, but Python 3.8+ required
    echo 📦 Please upgrade Python to 3.8 or higher
    pause
    exit /b 1
)

echo.
echo ══════════════════════════════════════════════════
echo [2/5] Creating Python Virtual Environment...
if exist "%SCRIPT_DIR%\.venv" (
    echo 🔄 Found existing virtual environment, checking if it works...
    call "%SCRIPT_DIR%\.venv\Scripts\activate.bat" >nul 2>&1
    if not errorlevel 1 (
        "%SCRIPT_DIR%\.venv\Scripts\python.exe" -c "import sys; print('✅ Existing environment works')" >nul 2>&1
        if not errorlevel 1 (
            echo ✅ Using existing virtual environment
            goto skip_venv_creation
        )
    )
    echo 🔄 Removing problematic virtual environment...
    rmdir /s /q "%SCRIPT_DIR%\.venv" 2>nul
    if exist "%SCRIPT_DIR%\.venv" (
        echo ⚠️ Could not remove old environment, will try to work with it...
    )
)

echo 📁 Creating fresh virtual environment...
python -m venv "%SCRIPT_DIR%\.venv"
if errorlevel 1 (
    echo ❌ ERROR: Failed to create virtual environment
    echo.
    echo 🔧 This might be because:
    echo    • Python venv module is not installed
    echo    • Insufficient permissions
    echo    • Path contains special characters
    echo.
    echo 💡 Try: python -m pip install --user virtualenv
    pause
    exit /b 1
)
echo ✅ Virtual environment created successfully

:skip_venv_creation
echo.
echo ══════════════════════════════════════════════════
echo [3/5] Installing Python Dependencies...
echo 📦 This may take 2-3 minutes depending on your internet speed...
echo.

call "%SCRIPT_DIR%\.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ❌ ERROR: Could not activate virtual environment
    pause
    exit /b 1
)

echo 🔧 Upgrading pip...
"%SCRIPT_DIR%\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo ⚠️ Warning: Could not upgrade pip, continuing anyway...
)

echo 📚 Installing core dependencies (lancedb, pandas, numpy, etc.)...
echo    This provides semantic search capabilities
"%SCRIPT_DIR%\.venv\Scripts\pip.exe" install -r "%SCRIPT_DIR%\requirements.txt"
if errorlevel 1 (
    echo ❌ ERROR: Failed to install dependencies
    echo.
    echo 🔧 Possible solutions:
    echo    • Check internet connection
    echo    • Try running as administrator
    echo    • Check if antivirus is blocking pip
    echo    • Manually run: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo ✅ Dependencies installed successfully

echo.
echo ══════════════════════════════════════════════════
echo [4/5] Testing Installation...
echo 🧪 Verifying Python imports...
echo Attempting import test...
"%SCRIPT_DIR%\.venv\Scripts\python.exe" -c "from mini_rag import CodeEmbedder, ProjectIndexer, CodeSearcher; print('✅ Core imports successful')" 2>import_error.txt
if errorlevel 1 (
    echo ❌ ERROR: Installation test failed
    echo.
    echo 🔍 Import error details:
    type import_error.txt
    echo.
    echo 🔧 This usually means:
    echo    • Dependencies didn't install correctly
    echo    • Virtual environment is corrupted  
    echo    • Python path issues
    echo    • Module conflicts with existing installations
    echo.
    echo 💡 Troubleshooting options:
    echo    • Try: "%SCRIPT_DIR%\.venv\Scripts\pip.exe" install -r requirements.txt --force-reinstall
    echo    • Or delete .venv folder and run installer again
    echo    • Or check import_error.txt for specific error details
    del import_error.txt >nul 2>&1
    pause
    exit /b 1
)
del import_error.txt >nul 2>&1

echo 🔍 Testing embedding system...
"%SCRIPT_DIR%\.venv\Scripts\python.exe" -c "from mini_rag import CodeEmbedder; embedder = CodeEmbedder(); info = embedder.get_embedding_info(); print(f'✅ Embedding method: {info[\"method\"]}')" 2>nul
if errorlevel 1 (
    echo ⚠️ Warning: Embedding test inconclusive, but core system is ready
)

echo.
echo ══════════════════════════════════════════════════
echo [5/6] Setting Up Desktop Integration...
call :setup_windows_icon

echo.
echo ══════════════════════════════════════════════════
echo [6/6] Checking AI Features (Optional)...
call :check_ollama_enhanced

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║             INSTALLATION SUCCESSFUL!            ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo 🎯 Quick Start Options:
echo.
echo 🎨 For Beginners (Recommended):
echo    rag.bat                 - Interactive interface with guided setup
echo.
echo 💻 For Developers:
echo    rag.bat index C:\myproject      - Index a project
echo    rag.bat search C:\myproject "authentication"  - Search project  
echo    rag.bat help            - Show all commands
echo.

REM Offer interactive tutorial
echo 🧪 Quick Test Available:
echo    Test FSS-Mini-RAG with a small sample project (takes ~30 seconds)
echo.
set /p "run_test=Run interactive tutorial now? [Y/n]: "
if /i "!run_test!" NEQ "n" (
    call :run_tutorial
) else (
    echo 📚 You can run the tutorial anytime with: rag.bat
)

echo.
echo 🎉 Setup complete! FSS-Mini-RAG is ready to use.
echo 💡 Pro tip: Try indexing any folder with text files - code, docs, notes!
echo.
pause
exit /b 0

:check_ollama_enhanced
echo 🤖 Checking for AI capabilities...
echo.

REM Check if Ollama is installed
where ollama >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Ollama not installed - using basic search mode
    echo.
    echo 🎯 For Enhanced AI Features:
    echo    • 📥 Install Ollama: https://ollama.com/download
    echo    • 🔄 Run: ollama serve  
    echo    • 🧠 Download model: ollama pull qwen3:1.7b
    echo.
    echo 💡 Benefits of AI features:
    echo    • Smart query expansion for better search results
    echo    • Interactive exploration mode with conversation memory
    echo    • AI-powered synthesis of search results  
    echo    • Natural language understanding of your questions
    echo.
    goto :eof
)

REM Check if Ollama server is running
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo 🟡 Ollama installed but not running
    echo.
    set /p "start_ollama=Start Ollama server now? [Y/n]: "
    if /i "!start_ollama!" NEQ "n" (
        echo 🚀 Starting Ollama server...
        start /b ollama serve
        timeout /t 3 /nobreak >nul
        curl -s http://localhost:11434/api/version >nul 2>&1
        if errorlevel 1 (
            echo ⚠️ Could not start Ollama automatically
            echo 💡 Please run: ollama serve
        ) else (
            echo ✅ Ollama server started successfully!
        )
    )
) else (
    echo ✅ Ollama server is running!
)

REM Check for available models
echo 🔍 Checking for AI models...
ollama list 2>nul | findstr /v "NAME" | findstr /v "^$" >nul
if errorlevel 1 (
    echo 📦 No AI models found
    echo.
    echo 🧠 Recommended Models (choose one):
    echo    • qwen3:1.7b    - Excellent for RAG (1.4GB, recommended)
    echo    • qwen3:0.6b    - Lightweight and fast (~500MB)  
    echo    • qwen3:4b      - Higher quality but slower (~2.5GB)
    echo.
    set /p "install_model=Download qwen3:1.7b model now? [Y/n]: "
    if /i "!install_model!" NEQ "n" (
        echo 📥 Downloading qwen3:1.7b model...
        echo    This may take 5-10 minutes depending on your internet speed
        ollama pull qwen3:1.7b
        if errorlevel 1 (
            echo ⚠️ Download failed - you can try again later with: ollama pull qwen3:1.7b
        ) else (
            echo ✅ Model downloaded successfully! AI features are now available.
        )
    )
) else (
    echo ✅ AI models found - full AI features available!
    echo 🎉 Your system supports query expansion, exploration mode, and synthesis!
)
goto :eof

:run_tutorial
echo.
echo ═══════════════════════════════════════════════════
echo 🧪 Running Interactive Tutorial
echo ═══════════════════════════════════════════════════
echo.
echo 📚 This tutorial will:
echo    • Index the FSS-Mini-RAG documentation
echo    • Show you how to search effectively
echo    • Demonstrate AI features (if available)
echo.

call "%SCRIPT_DIR%\.venv\Scripts\activate.bat"

echo 📁 Indexing project for demonstration...
"%SCRIPT_DIR%\.venv\Scripts\python.exe" rag-mini.py index "%SCRIPT_DIR%" >nul 2>&1
if errorlevel 1 (
    echo ❌ Indexing failed - please check the installation
    goto :eof
)

echo ✅ Indexing complete! 
echo.
echo 🔍 Example search: "embedding"
"%SCRIPT_DIR%\.venv\Scripts\python.exe" rag-mini.py search "%SCRIPT_DIR%" "embedding" --top-k 3
echo.
echo 🎯 Try the interactive interface:
echo    rag.bat
echo.
echo 💡 You can now search any project by indexing it first!
goto :eof

:setup_windows_icon
echo 🎨 Setting up application icon and shortcuts...

REM Check if icon exists
if not exist "%SCRIPT_DIR%\assets\Fss_Mini_Rag.png" (
    echo ⚠️ Icon file not found - skipping desktop integration
    goto :eof
)

REM Create desktop shortcut
echo 📱 Creating desktop shortcut...
set "desktop=%USERPROFILE%\Desktop"
set "shortcut=%desktop%\FSS-Mini-RAG.lnk"

REM Use PowerShell to create shortcut with icon
powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%shortcut%'); $Shortcut.TargetPath = '%SCRIPT_DIR%\rag.bat'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.Description = 'FSS-Mini-RAG - Fast Semantic Search'; $Shortcut.Save()}" >nul 2>&1

if exist "%shortcut%" (
    echo ✅ Desktop shortcut created
) else (
    echo ⚠️ Could not create desktop shortcut
)

REM Create Start Menu shortcut
echo 📂 Creating Start Menu entry...
set "startmenu=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "startshortcut=%startmenu%\FSS-Mini-RAG.lnk"

powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%startshortcut%'); $Shortcut.TargetPath = '%SCRIPT_DIR%\rag.bat'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.Description = 'FSS-Mini-RAG - Fast Semantic Search'; $Shortcut.Save()}" >nul 2>&1

if exist "%startshortcut%" (
    echo ✅ Start Menu entry created
) else (
    echo ⚠️ Could not create Start Menu entry
)

echo 💡 FSS-Mini-RAG shortcuts have been created on your Desktop and Start Menu
echo    You can now launch the application from either location
goto :eof