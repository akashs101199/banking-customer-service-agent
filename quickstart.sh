#!/bin/bash
# Quick Start Script for Banking AI

echo "🏦 Banking Customer Service Agentic AI - Quick Start"
echo "=================================================="
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not found. Please install it first:"
    echo "   brew install ollama"
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running. Starting Ollama..."
    echo "   Please run 'ollama serve' in another terminal"
    echo "   Then run this script again"
    exit 1
fi

# Check if model is available
echo "📥 Checking for Llama 3.1 model..."
if ! ollama list | grep -q "llama3.1"; then
    echo "📥 Pulling Llama 3.1 model (this may take a few minutes)..."
    ollama pull llama3.1:8b
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found. Please install it first:"
    echo "   brew install postgresql@14"
    exit 1
fi

# Check if database exists
if ! psql -lqt | cut -d \| -f 1 | grep -qw banking_ai; then
    echo "📊 Creating database..."
    createdb banking_ai
    psql -d banking_ai -c "CREATE USER bankingai WITH PASSWORD 'bankingai123';" 2>/dev/null || true
    psql -d banking_ai -c "GRANT ALL PRIVILEGES ON DATABASE banking_ai TO bankingai;"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
fi

# Initialize database
echo "🗄️  Initializing database..."
python -c "from database.connection import init_database; init_database()" 2>/dev/null || echo "Database already initialized"

echo ""
echo "✅ Setup complete!"
echo ""
echo "You can now:"
echo "  1. Run the demo:        python demo.py"
echo "  2. Start the API:       python api/main.py"
echo "  3. View API docs:       http://localhost:8000/docs"
echo ""
echo "Happy banking! 🎉"
