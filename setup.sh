#!/bin/bash

# Setup Script for Apple Health Dashboard

echo "🍎 Setting up Apple Health Dashboard..."

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

echo "✅ Python 3 found."

# 2. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment found."
fi

# 3. Install Dependencies
if [ -f "requirements.txt" ]; then
    echo "⬇️  Installing dependencies..."
    ./venv/bin/pip install -r requirements.txt
else
    echo "⚠️  requirements.txt not found. Scanning for dependencies..."
    # Fallback or create? Assuming it exists now.
    echo "❌ Error: requirements.txt missing."
    exit 1
fi

# 4. Configuration Check
echo "⚙️  Configuration..."
if [ -f "config.py" ]; then
    echo "✅ config.py exists."
    echo "IMPORTANT: Please ensure 'DATA_DIR' in 'config.py' points to your 'apple_health_export' folder."
else
    echo "⚠️  config.py not found. Creating default..."
    # Basic creation if missing (though user already has it)
    echo "DATA_DIR = '../apple_health_export'" > config.py
    echo "Created config.py. Please edit it to point to your data."
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "To run the dashboard:"
echo "  ./venv/bin/python app.py"
echo ""
