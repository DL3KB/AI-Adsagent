#!/bin/bash
# ============================================================
# AdsAgent - Start backend + frontend
# ============================================================

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'

# ---- Pre-flight checks ----
if [ ! -d "$ROOT_DIR/backend/venv" ]; then
    echo -e "${RED}Backend venv not found. Run ./setup.sh first.${NC}"
    exit 1
fi

if [ ! -f "$ROOT_DIR/backend/.env" ]; then
    echo -e "${RED}backend/.env not found. Run ./setup.sh first.${NC}"
    exit 1
fi

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
    echo -e "${RED}Frontend node_modules not found. Run ./setup.sh first.${NC}"
    exit 1
fi

# ---- Kill any existing processes on our ports ----
lsof -ti :8000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti :5173 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# ---- Start backend ----
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AdsAgent — Starting${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Starting backend (port 8000)...${NC}"
cd "$ROOT_DIR/backend"
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# ---- Start frontend ----
echo -e "${YELLOW}Starting frontend (port 5173)...${NC}"
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# ---- Wait for backend to be ready ----
echo -e "\n${YELLOW}Waiting for backend...${NC}"
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}Backend ready!${NC}"
        break
    fi
    sleep 1
done

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  AdsAgent is running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "  Frontend:  http://localhost:5173"
echo "  Backend:   http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop both servers."
echo ""

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
