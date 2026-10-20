@echo off
title Experience Finder (:8001)
cd /d "%~dp0..\EXPLORER_FINAL_SEND\EXPLORER"
echo ============================================================
echo Starting Explorely Experience Finder on http://localhost:8001
echo ============================================================
python -m uvicorn app.main:app --port 8001 --reload
pause
