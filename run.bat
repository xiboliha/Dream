@echo off
REM Run script for AI Girlfriend Agent on Windows

echo ========================================
echo AI Girlfriend Agent - Startup Script
echo ========================================

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if dependencies are installed
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements\base.txt
)

REM Check for .env file
if not exist ".env" (
    echo .env file not found!
    echo Please copy .env.example to .env and configure your API keys.
    echo.
    copy .env.example .env
    echo Created .env from .env.example - please edit it with your API keys.
    pause
    exit /b 1
)

REM Parse command line arguments
set MODE=%1
if "%MODE%"=="" set MODE=wechat

echo.
echo Starting in %MODE% mode...
echo.

if "%MODE%"=="wechat" (
    echo Starting WeChat mode...
    python src\main.py
) else if "%MODE%"=="cli" (
    echo Starting CLI mode...
    python src\interfaces\cli\shell.py
) else if "%MODE%"=="api" (
    echo Starting API server mode...
    python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
) else if "%MODE%"=="setup" (
    echo Running setup...
    python src\scripts\setup.py
) else (
    echo Unknown mode: %MODE%
    echo.
    echo Available modes:
    echo   wechat - Start WeChat bot (default)
    echo   cli    - Start CLI chat interface
    echo   api    - Start REST API server
    echo   setup  - Run initial setup
)
