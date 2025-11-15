@echo off
REM Meal Planner - Start Server
REM This script activates the virtual environment and starts the Flask server

cd /d "%~dp0"
cls
echo.
echo ========================================
echo     MEAL PLANNER SERVER
echo ========================================
echo.
echo Current directory: %cd%
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Virtual environment activated successfully!
echo.
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo Server is starting...
echo.
echo Open your browser and go to:
echo   Desktop:  http://localhost:5000
echo   Mobile:   http://192.168.1.242:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python app.py

REM Keep window open if there's an error
pause
