#!/bin/bash
set -e # Exit immediately if a command fails

# Check for Python 3
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    # Try to create venv, capture error if it fails
    if ! $PYTHON_CMD -m venv venv; then
        echo ""
        echo "❌ Error: Failed to create virtual environment."
        echo "Please ensure you have python3-venv installed or a full Python installation."
        exit 1
    fi
fi

# Activate venv
# Use . instead of source for POSIX compatibility (works in sh and bash)
if [ -f "venv/bin/activate" ]; then
    . venv/bin/activate
else
    echo "Error: venv/bin/activate not found!"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the bot
echo "Starting Kingshot Assistant..."
# Use python (which is now the venv python)
python main.py
