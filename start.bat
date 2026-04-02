@echo off
title SharePoint Rename App

echo Starting SharePoint Rename App...

:: Create venv if needed
if not exist "venv\Scripts\python.exe" (
    echo Setting up environment for first time...
    py -3 -m venv venv
    venv\Scripts\pip install -r requirements.txt --quiet
)

:: Start server and open browser
start "" "http://localhost:8000"
venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
