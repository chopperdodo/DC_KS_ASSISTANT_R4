@echo off
echo Checking for Python...
if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found!
    echo Please run "python -m venv venv" first.
    pause
    exit /b
)

echo Installing dependencies...
.\venv\Scripts\python.exe -m pip install -r requirements.txt

echo Starting Kingshot Assistant...
.\venv\Scripts\python.exe main.py
pause
