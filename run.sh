#!/bin/bash

# PhonicFlow - Run Script
# Starts all components in separate terminal windows (for development)

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Virtual environment not found!${NC}"
    echo "Please run: ./setup.sh"
    exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     PhonicFlow - Development Server       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"

# Activate virtual environment
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env created${NC}"
fi

# Function to run in background with job control
run_service() {
    local name=$1
    local command=$2
    
    echo -e "${BLUE}Starting ${name}...${NC}"
    eval "$command" &
    local pid=$!
    echo -e "${GREEN}✓ ${name} started (PID: ${pid})${NC}"
    pids[$name]=$pid
}

declare -A pids

# Check prerequisites
echo -e "\n${BLUE}Checking prerequisites...${NC}"

# Check for Ollama
if ! curl -s http://localhost:11434/tags > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Ollama is not running!${NC}"
    echo "Please start Ollama in another terminal:"
    echo -e "  ${BLUE}ollama serve${NC}"
    echo ""
    read -p "Press enter to continue..."
fi

# Start backend
echo ""
echo -e "${BLUE}═ Backend API${NC}"
run_service "Backend" \
    "python -m uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000"
sleep 2

# Start frontend
echo ""
echo -e "${BLUE}═ Frontend UI${NC}"
run_service "Frontend" \
    "streamlit run app/frontend/streamlit_app.py"
sleep 2

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     All Services Started Successfully!    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Backend API: ${BLUE}http://localhost:8000${NC}"
echo -e "  Docs:      ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "Frontend UI: ${BLUE}http://localhost:8501${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all background jobs
wait

# Cleanup on exit
trap "kill ${pids[@]} 2>/dev/null" EXIT
