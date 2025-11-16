@echo off
REM ============================================================================
REM Tech Spec Agent - Startup Script
REM ============================================================================
REM This script starts the Tech Spec Agent API server
REM ============================================================================

echo.
echo ========================================
echo  Starting Tech Spec Agent
echo ========================================
echo.

REM Change to Tech Agent directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then run: venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/3] Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo The .env file has been auto-created. Please fill in API keys:
    echo - TAVILY_API_KEY: Get from https://tavily.com/
    pause
    exit /b 1
)

echo [2/3] Environment configured
echo.

REM Start Tech Spec Agent API server
echo [3/3] Starting Tech Spec Agent API server...
echo.
echo ========================================
echo  Tech Spec Agent is running!
echo  API: http://localhost:8001
echo  Docs: http://localhost:8001/docs
echo  Health: http://localhost:8001/health
echo  Press Ctrl+C to stop
echo ========================================
echo.

python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload

REM If server exits, pause to see error
pause
