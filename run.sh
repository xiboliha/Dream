#!/bin/bash
# Run script for AI Girlfriend Agent on Linux/Mac

echo "========================================"
echo "AI Girlfriend Agent - Startup Script"
echo "========================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Check if dependencies are installed
if ! pip show fastapi > /dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install -r requirements/base.txt
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo ".env file not found!"
    echo "Please copy .env.example to .env and configure your API keys."
    echo ""
    cp .env.example .env
    echo "Created .env from .env.example - please edit it with your API keys."
    exit 1
fi

# Parse command line arguments
MODE=${1:-wechat}

echo ""
echo "Starting in $MODE mode..."
echo ""

case $MODE in
    wechat)
        echo "Starting WeChat mode..."
        python src/main.py
        ;;
    cli)
        echo "Starting CLI mode..."
        python src/interfaces/cli/shell.py
        ;;
    api)
        echo "Starting API server mode..."
        uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
        ;;
    setup)
        echo "Running setup..."
        python src/scripts/setup.py
        ;;
    test)
        echo "Running tests..."
        pytest tests/ -v
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo ""
        echo "Available modes:"
        echo "  wechat - Start WeChat bot (default)"
        echo "  cli    - Start CLI chat interface"
        echo "  api    - Start REST API server"
        echo "  setup  - Run initial setup"
        echo "  test   - Run tests"
        ;;
esac
