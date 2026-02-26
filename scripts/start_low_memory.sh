#!/bin/bash
# Low Memory Startup Script for SS-54
# Optimized for $5/mo VPS (1GB RAM, 25GB disk, 1 vCPU)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

MIN_MEMORY_MB=400

check_memory() {
    local total_mb=$(free -m | awk '/^Mem:/{print $2}')
    local avail_mb=$(free -m | awk '/^Mem:/{print $7}')
    
    echo "Total memory: ${total_mb}MB"
    echo "Available memory: ${avail_mb}MB"
    
    if [ "$avail_mb" -lt "$MIN_MEMORY_MB" ]; then
        echo "WARNING: Low memory detected (${avail_mb}MB available, ${MIN_MEMORY_MB}MB recommended)"
        echo "Consider restarting services or adding swap"
    fi
}

echo "=========================================="
echo "SS-54 Low Memory Mode Startup"
echo "=========================================="

check_memory

export LOW_MEMORY_MODE=true

export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

echo ""
echo "Starting uvicorn with single worker (LOW_MEMORY_MODE=true)..."
echo ""

exec uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --workers 1 \
    --no-access-log \
    --timeout-keep-alive 30
