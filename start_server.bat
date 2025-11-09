@echo off
REM Meal Planner - Start Server
REM This script activates the virtual environment and starts the Flask server

cd /d "%~dp0"
echo Starting Meal Planner...
echo.

REM Activate virtual environment and run app
call venv\Scripts\activate.bat
python app.py

REM Keep window open if there's an error
pause
