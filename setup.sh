#!/bin/bash

# PhonicFlow Setup Script
# Installs dependencies and configures the environment

set -e

echo "🚀 Setting up PhonicFlow..."
echo "================================"

# Check Python version
echo "✓ Checking Python version..."
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    echo "  Python $PYTHON_VERSION ✓"
else
    echo "❌ Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "✓ Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "✓ Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "✓ Creating .env file from template..."
    cp .env.example .env
    echo "  ⚠️  Please review and update .env file as needed"
fi

# Create directories if needed
echo "✓ Creating necessary directories..."
mkdir -p app/feedback_storage
mkdir -p logs

echo ""
echo "================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Ensure Ollama is running: ollama serve"
echo "2. Pull a model: ollama pull llama3"
echo "3. In a new terminal, run the backend:"
echo "   source venv/bin/activate"
echo "   python -m uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000"
echo "4. In another terminal, run the frontend:"
echo "   source venv/bin/activate"
echo "   streamlit run app/frontend/streamlit_app.py"
echo "5. Open browser to http://localhost:8501"
echo ""
