#!/bin/bash
# Run the app locally using Docker (same image as production)
# Usage: ./run-local.sh

set -e

cd "$(dirname "$0")/.."

echo "============================================"
echo "  CFT Support Agent - Local Docker Run"
echo "============================================"

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "   Edit .env with your API keys, then re-run."
    exit 1
fi

# Build
echo ""
echo "🔨 Building Docker image..."
docker build -t cft-support-agent:local .

# Run
echo "🚀 Starting app on http://localhost:8501"
echo "   Press Ctrl+C to stop."
echo ""

docker run --rm -it \
    --env-file .env \
    -p 8501:8501 \
    --name cft-support-agent \
    cft-support-agent:local
