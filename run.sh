#!/bin/bash
# =========================================================================
#  NEXUS & EOC Command Center - Unified Linux/Codespaces Startup Script
# =========================================================================

# Clean up background jobs on exit
trap "kill 0" EXIT

echo "======================================================="
echo "   Emergency Resource Platform Command Center Startup"
echo "======================================================="
echo ""

# 1. Activate python virtual environment if present
if [ -d "venv" ]; then
    echo "[1/4] Activating virtual environment..."
    source venv/bin/activate
    pip install -r backend/requirements.txt
else
    echo "[1/4] No virtual environment found, installing dependencies on system Python..."
    pip install -r backend/requirements.txt
fi

# 2. Seed database
echo "[2/4] Resetting database and seeding inventory..."
cd backend
python -m app.db.seed
if [ $? -ne 0 ]; then
    echo "ERROR: Database seed failed. Verify python is installed and dependencies are met."
    exit 1
fi
cd ..

# 3. Start Backend
echo "[3/4] Starting backend FastAPI service on port 8080..."
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 &
cd ..

# 4. Start Frontend
echo "[4/4] Resolving frontend dependencies and starting Vite..."
cd frontend
npm install
npm run dev -- --host 0.0.0.0 &
cd ..

echo ""
echo "======================================================="
echo "   Services spawned successfully!"
echo "   - API Docs / Swagger: http://localhost:8080/docs"
echo "   - Hospital Management: http://localhost:8080/ (Served by FastAPI)"
echo "   - EOC Command Center: http://localhost:3000/"
echo "======================================================="
echo ""
echo "Press Ctrl+C to shut down all processes."

# Keep script running to preserve background processes
wait
