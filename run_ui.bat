@echo off
SETLOCAL

:: Set your virtual environment folder name
SET VENV_DIR=.venv

:: Check if .venv folder exists
IF NOT EXIST "%VENV_DIR%\" (
    echo [INFO] Creating virtual environment...
    python -m venv %VENV_DIR%
    :: Activate virtual environment
    call %VENV_DIR%\Scripts\activate.bat

    :: Install required packages
    echo [INFO] Installing requirements...
    pip install -r requirements.txt
)

:: Activate virtual environment
call %VENV_DIR%\Scripts\activate.bat

:: Run Flask application
echo [INFO] Launching Pakaneo Billing Automation Web Interface...
python app.py

:: Pause so the window stays open
pause