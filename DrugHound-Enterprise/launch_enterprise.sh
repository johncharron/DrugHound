#!/bin/bash
# DrugHound Enterprise Launch Script

echo "🐕 DrugHound Enterprise - Launching..."
echo "========================================="

# Activate environment
source venv/bin/activate

# Install enterprise dependencies
pip install -r requirements-enterprise.txt

# Initialize database
python -c "from src.core.database import init_database; init_database()"

# Start Elasticsearch (if available)
if command -v elasticsearch &> /dev/null; then
    echo "Starting Elasticsearch..."
    elasticsearch -d
fi

# Start Redis (if available)
if command -v redis-server &> /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
fi

# Start the web interface
echo ""
echo "🌐 Starting Web Interface..."
echo "   Access at: http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""

python src/web/app.py
