@echo off
title Launch Both Projects
cd /d "%~dp0"
echo ============================================================
echo Starting both services in separate windows...
echo ============================================================
start "Smart Travel Planner (:8000)" cmd /k "cd /d %~dp0 && python -m uvicorn app.main:app --port 8000 --reload"
timeout /t 2 /nobreak >nul
start "Explorely Experience Finder (:8001)" cmd /k "cd /d %~dp0..\EXPLORER_FINAL_SEND\EXPLORER && python -m uvicorn app.main:app --port 8001 --reload"
echo Both services launched!
echo - Smart Travel Planner          : http://localhost:8000
echo - Explorely (Experience Finder) : http://localhost:8001
pause
