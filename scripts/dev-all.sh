#!/bin/bash
# Start both backend and frontend for Case Chat development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Case Chat - Development Environment${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${GREEN}Starting services...${NC}"
echo ""
echo -e "${YELLOW}Backend API:${NC}   http://localhost:7777"
echo -e "${YELLOW}Frontend UI:${NC}   http://localhost:3000"
echo -e "${YELLOW}API Docs:${NC}      http://localhost:7777/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both services${NC}"
echo ""

# Create tmp directory
mkdir -p tmp

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${RED}Stopping services...${NC}"
    pkill -f "case_chat_agentos_deploy.py" || true
    pkill -f "next dev" || true
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}[1/2]${NC} Starting backend..."
uv run python examples/case_chat_agentos_deploy.py &
BACKEND_PID=$!
echo -e "${GREEN}[OK]${NC} Backend started (PID: $BACKEND_PID)"

# Wait a bit for backend to initialize
sleep 3

# Check if backend is responding
if curl -s http://localhost:7777/health > /dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC} Backend is responding at http://localhost:7777"
else
    echo -e "${YELLOW}[WARN]${NC} Backend not yet responding, may need more time..."
fi

echo ""

# Start frontend
echo -e "${GREEN}[2/2]${NC} Starting frontend..."
cd agent-ui && pnpm dev &
FRONTEND_PID=$!
echo -e "${GREEN}[OK]${NC} Frontend started (PID: $FRONTEND_PID)"

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}All services running!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${YELLOW}Backend:${NC}  http://localhost:7777"
echo -e "${YELLOW}Frontend:${NC} http://localhost:3000"
echo ""
echo -e "Logs are being written to terminal output"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
