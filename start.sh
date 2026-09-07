#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "============================================================"
echo "  CyberDrishti AI — Starting Full Stack (macOS/Linux)"
echo "============================================================"

# 1. Check Backend
if lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "✓ Backend is already running on http://localhost:8000"
else
    echo "→ Starting Backend (FastAPI)..."
    cd "$DIR/backend"
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        source venv/bin/activate
    fi
    uvicorn main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    echo "✓ Backend started (PID: $BACKEND_PID)"
fi

# 2. Check & Start Frontend
echo "→ Starting Frontend (Vite)..."
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "============================================================"
echo "  CyberDrishti AI is Running!"
echo "============================================================"
echo "  Frontend UI:  http://localhost:5173"
echo "  Backend API: http://localhost:8000"
echo "  API Docs:    http://localhost:8000/api/docs"
echo "  Health:      http://localhost:8000/health"
echo "============================================================"
echo "Press Ctrl+C to stop services."

trap 'echo "Stopping services..."; kill $FRONTEND_PID 2>/dev/null || true; [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null || true; exit 0' INT TERM EXIT

wait
