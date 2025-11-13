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
echo Activating virtual environment...
echo.

REM Activate virtual environment and run app
call venv\Scripts\activate.bat

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
