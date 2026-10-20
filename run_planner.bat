@echo off
title Smart Travel Planner (:8000)
cd /d "%~dp0"
echo ============================================================
echo Starting Smart Travel Planner on http://localhost:8000
echo ============================================================
python -m uvicorn app.main:app --port 8000 --reload
pause
