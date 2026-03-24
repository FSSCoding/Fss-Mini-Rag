@echo off
REM FSS-Mini-RAG Windows Launcher - Simple and Reliable

setlocal
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "VENV_PYTHON=%SCRIPT_DIR%\.venv\Scripts\python.exe"

REM Check if virtual environment exists
if not exist "%VENV_PYTHON%" (
    echo Virtual environment not found!
    echo.
    echo Run this first: install_windows.bat
    echo.
    pause
    exit /b 1
)

REM Route commands
if "%1"=="" goto :interactive
if "%1"=="help" goto :help
if "%1"=="--help" goto :help
if "%1"=="-h" goto :help

REM Pass all arguments to Python script
"%VENV_PYTHON%" "%SCRIPT_DIR%\rag-mini.py" %*
goto :end

:interactive
echo Starting interactive interface...
"%VENV_PYTHON%" "%SCRIPT_DIR%\rag-tui.py"
goto :end

:help
echo FSS-Mini-RAG - Semantic Code Search
echo.
echo Usage:
echo   rag.bat                           - Interactive interface
echo   rag.bat index ^<folder^>             - Index a project
echo   rag.bat search ^<folder^> ^<query^>     - Search project
echo   rag.bat status ^<folder^>            - Check status
echo.
echo Examples:
echo   rag.bat index C:\myproject
echo   rag.bat search C:\myproject "authentication"
echo   rag.bat search . "error handling"
echo.
pause

:end
endlocal