@echo off
echo Starting CyberSaathi services...

echo Starting Backend API on http://localhost:8000 ...
start "CyberSaathi Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Starting Frontend Dev Server on http://localhost:5173 ...
start "CyberSaathi Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo All services launched!
echo - Frontend: http://localhost:5173
echo - Backend API Docs: http://localhost:8000/api/docs
