.PHONY: help install test lint format clean test-agents serve-ui dev-frontend dev-backend dev-all stop-all

# Default target
help:
	@echo "Case Chat - Makefile Commands"
	@echo ""
	@echo "Development (Recommended):"
	@echo "  make dev-all          Start both backend and frontend"
	@echo "                       Backend: http://localhost:7777"
	@echo "                       Frontend: http://localhost:3000"
	@echo "  make dev-backend      Start backend API only (AgentOS)"
	@echo "  make dev-frontend     Start Next.js frontend only"
	@echo "  make stop-all         Stop all running services"
	@echo ""
	@echo "Legacy (Old Frontend):"
	@echo "  make test-agents      Run Case Chat agents locally for testing"
	@echo "                       Control Plane: http://localhost:7777"
	@echo "  make serve-ui         Open local web UI in browser (file://)"
	@echo "  make serve-ui-http    Serve local web UI on http://localhost:8080"
	@echo ""
	@echo "Installation:"
	@echo "  make install          Install all dependencies"
	@echo "  make install-frontend Install frontend dependencies (pnpm)"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             Run backend tests"
	@echo "  make test-frontend    Run frontend tests"
	@echo "  make lint             Lint backend code with ruff"
	@echo "  make format           Format backend code with ruff"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            Clean cache and build files"

# Installation
install:
	@echo "Installing dependencies..."
	uv sync --all-extras --dev

# Testing
test:
	@echo "Running tests..."
	uv run pytest

# Linting
lint:
	@echo "Linting code..."
	uv run ruff check --fix .

# Formatting
format:
	@echo "Formatting code..."
	uv run ruff format .

# Clean
clean:
	@echo "Cleaning cache and build files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"

# Test Agents Locally with AgentOS
test-agents:
	@echo "Starting Case Chat Agents for local testing..."
	@echo ""
	@echo "Control Plane: http://localhost:7777"
	@echo "API Docs: http://localhost:7777/docs"
	@echo ""
	@echo "Available Agents:"
	@echo "  - Tax Law Assistant (case-chat-assistant)"
	@echo ""
	@mkdir -p tmp
	uv run python examples/case_chat_agentos_deploy.py

# Serve Local Web UI
serve-ui:
	@echo "Starting local web UI..."
	@echo ""
	@echo "Note: Make sure 'make test-agents' is running first!"
	@echo ""
	@echo "Opening frontend/index.html in your browser..."
	@echo ""
	@if command -v xdg-open >/dev/null 2>&1; then \
		xdg-open frontend/index.html; \
	elif command -v open >/dev/null 2>&1; then \
		open frontend/index.html; \
	else \
		echo "Please open frontend/index.html in your browser manually"; \
	fi

# Serve Local Web UI via HTTP Server
serve-ui-http:
	@echo "Starting local web UI with HTTP server..."
	@echo ""
	@echo "Note: Make sure 'make test-agents' is running in another terminal!"
	@echo ""
	@echo "Local UI: http://localhost:8080"
	@echo "Backend API: http://localhost:7777"
	@echo ""
	@cd frontend && python3 -m http.server 8080

# =============================================================================
# New Development Commands (agent-ui + AgentOS)
# =============================================================================

# Install frontend dependencies
install-frontend:
	@echo "Installing frontend dependencies..."
	@cd agent-ui && pnpm install

# Start backend only (AgentOS Control Plane)
dev-backend:
	@echo "Starting backend (AgentOS Control Plane)..."
	@echo ""
	@echo "Backend API: http://localhost:7777"
	@echo "API Docs: http://localhost:7777/docs"
	@echo ""
	@mkdir -p tmp
	@uv run python examples/case_chat_agentos_deploy.py

# Start frontend only (agent-ui)
dev-frontend:
	@echo "Starting frontend (agent-ui)..."
	@echo ""
	@echo "Frontend: http://localhost:3000"
	@echo ""
	@echo "Note: Make sure backend is running on http://localhost:7777"
	@echo ""
	@cd agent-ui && pnpm dev

# Start both backend and frontend
dev-all:
	@echo "Starting backend and frontend..."
	@./scripts/dev-all.sh

# Stop all running services
stop-all:
	@echo "Stopping all services..."
	@pkill -f "case_chat_agentos_deploy.py" 2>/dev/null || true
	@pkill -f "next dev" 2>/dev/null || true
	@echo "All services stopped"

# Run frontend tests
test-frontend:
	@echo "Running frontend tests..."
	@cd agent-ui && pnpm test:run
