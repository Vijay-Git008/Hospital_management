@echo off
echo =======================================================
echo    Emergency Resource Platform Command Center Startup
echo =======================================================
echo.

echo [1/3] Resetting database and seeding inventory...
cd backend
python -m app.db.seed
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Database seed failed. Verify python is installed and dependencies are met.
    pause
    exit /b %errorlevel%
)

echo [2/3] Starting backend FastAPI service on port 8080...
start "EOC Backend Service" cmd /k "python -m uvicorn app.main:app --host 127.0.0.1 --port 8080"

echo [3/3] Starting frontend Vite dashboard on port 3000...
cd ../frontend
start "EOC Frontend Dashboard" cmd /k "npm.cmd run dev"

echo.
echo =======================================================
echo    Services spawned!
echo    - API Docs: http://127.0.0.1:8080/docs
echo    - Dashboard: http://localhost:3000
echo =======================================================
echo.
pause
