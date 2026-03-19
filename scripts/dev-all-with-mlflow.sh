#!/bin/bash
# Start backend (AgentOS), frontend (agent-ui), and MLflow server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Starting Case Chat with MLflow Tracing ===${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping all services...${NC}"
    pkill -f "case_chat_agentos_deploy.py" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "mlflow server" 2>/dev/null || true
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup SIGINT SIGTERM

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file with required configuration:"
    echo "  - z_api_key (your Zhipu AI API key)"
    echo "  - MLFLOW_TRACKING_URI=http://localhost:5000"
    echo "  - MLFLOW_EXPERIMENT_NAME=case-chat-agent"
    exit 1
fi

# Create necessary directories
mkdir -p tmp
mkdir -p mlflow-artifacts

# Start MLflow server
echo -e "${GREEN}[1/3] Starting MLflow server...${NC}"
echo "  MLflow UI: http://localhost:5000"
uv run mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlflow-artifacts --host localhost --port 5000 > /tmp/mlflow.log 2>&1 &
MLFLOW_PID=$!

# Wait for MLflow to start
echo "  Waiting for MLflow to be ready..."
sleep 3

if ! ps -p $MLFLOW_PID > /dev/null; then
    echo -e "${RED}Error: MLflow server failed to start${NC}"
    echo "Check /tmp/mlflow.log for details"
    exit 1
fi

echo -e "${GREEN}  MLflow server started (PID: $MLFLOW_PID)${NC}"
echo ""

# Start backend
echo -e "${GREEN}[2/3] Starting backend (AgentOS Control Plane)...${NC}"
echo "  Backend API: http://localhost:7777"
echo "  API Docs: http://localhost:7777/docs"
uv run python examples/case_chat_agentos_deploy.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "  Waiting for backend to be ready..."
sleep 5

if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${RED}Error: Backend failed to start${NC}"
    echo "Check /tmp/backend.log for details"
    kill $MLFLOW_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}  Backend started (PID: $BACKEND_PID)${NC}"
echo ""

# Start frontend
echo -e "${GREEN}[3/3] Starting frontend (agent-ui)...${NC}"
echo "  Frontend: http://localhost:3000"
cd agent-ui && pnpm dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "  Waiting for frontend to be ready..."
sleep 5

if ! ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${RED}Error: Frontend failed to start${NC}"
    echo "Check /tmp/frontend.log for details"
    kill $BACKEND_PID 2>/dev/null || true
    kill $MLFLOW_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}  Frontend started (PID: $FRONTEND_PID)${NC}"
echo ""

# All services started
echo -e "${BLUE}=== All Services Started ===${NC}"
echo ""
echo -e "${GREEN}Services:${NC}"
echo "  - Frontend:     http://localhost:3000"
echo "  - Backend API:  http://localhost:7777"
echo "  - API Docs:     http://localhost:7777/docs"
echo "  - MLflow UI:    http://localhost:5000"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo "  - Backend:  tail -f /tmp/backend.log"
echo "  - Frontend: tail -f /tmp/frontend.log"
echo "  - MLflow:   tail -f /tmp/mlflow.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep script running
wait
