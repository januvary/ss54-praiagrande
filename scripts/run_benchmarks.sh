#!/bin/bash
#
# SS-54 Benchmark Suite Runner
#
# Runs all benchmarks and outputs a summary report.
#
# Usage:
#   ./scripts/run_benchmarks.sh              # Run all benchmarks
#   ./scripts/run_benchmarks.sh --memory     # Run only memory benchmarks
#   ./scripts/run_benchmarks.sh --load       # Run only load tests
#   ./scripts/run_benchmarks.sh --quick      # Quick mode (fewer iterations)
#
# Requirements:
#   pip install -r requirements-benchmark.txt
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BENCHMARK_DIR="$PROJECT_DIR/tests/benchmarks"

RUN_MEMORY=true
RUN_CPU=true
RUN_STORAGE=true
RUN_LOAD=false
QUICK_MODE=false

for arg in "$@"; do
    case $arg in
        --memory)
            RUN_CPU=false
            RUN_STORAGE=false
            RUN_LOAD=false
            ;;
        --cpu)
            RUN_MEMORY=false
            RUN_STORAGE=false
            RUN_LOAD=false
            ;;
        --storage)
            RUN_MEMORY=false
            RUN_CPU=false
            RUN_LOAD=false
            ;;
        --load)
            RUN_MEMORY=false
            RUN_CPU=false
            RUN_STORAGE=false
            RUN_LOAD=true
            ;;
        --quick)
            QUICK_MODE=true
            ;;
        --all)
            RUN_LOAD=true
            ;;
    esac
done

cd "$PROJECT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              SS-54 Resource Benchmark Suite                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if [ ! -d "$BENCHMARK_DIR" ]; then
    echo "ERROR: Benchmark directory not found at $BENCHMARK_DIR"
    exit 1
fi

generate_test_files() {
    echo ">>> Generating test files..."
    python scripts/generate_test_files.py --count $([ "$QUICK_MODE" = true ] && echo "3" || echo "10")
    echo ""
}

run_memory_benchmarks() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  MEMORY PROFILING"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [ "$QUICK_MODE" = true ]; then
        pytest tests/benchmarks/test_memory_profile.py -v --tb=short -k "baseline" 2>&1 || true
    else
        pytest tests/benchmarks/test_memory_profile.py -v --tb=short 2>&1 || true
    fi
    echo ""
}

run_cpu_benchmarks() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  CPU PROFILING"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [ "$QUICK_MODE" = true ]; then
        pytest tests/benchmarks/test_cpu_profile.py -v --tb=short -k "Throughput" 2>&1 || true
    else
        pytest tests/benchmarks/test_cpu_profile.py -v --tb=short 2>&1 || true
    fi
    echo ""
}

run_storage_benchmarks() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  STORAGE I/O BENCHMARKS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [ "$QUICK_MODE" = true ]; then
        pytest tests/benchmarks/test_storage_io.py -v --tb=short -k "Sequential" 2>&1 || true
    else
        pytest tests/benchmarks/test_storage_io.py -v --tb=short 2>&1 || true
    fi
    echo ""
}

run_load_tests() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  LOAD TESTING (Locust)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    HOST="${HOST:-http://localhost:8000}"
    USERS=$([ "$QUICK_MODE" = true ] && echo "10" || echo "50")
    RUN_TIME=$([ "$QUICK_MODE" = true ] && echo "30s" || echo "60s")

    echo "Host: $HOST"
    echo "Users: $USERS"
    echo "Duration: $RUN_TIME"
    echo ""

    if command -v locust &> /dev/null; then
        locust -f tests/benchmarks/locustfile.py \
            --host="$HOST" \
            --users "$USERS" \
            --spawn-rate 5 \
            --run-time "$RUN_TIME" \
            --headless \
            --only-summary \
            2>&1 || echo "Locust test completed (or server not available)"
    else
        echo "WARNING: locust not installed. Skipping load tests."
        echo "Install with: pip install locust"
    fi
    echo ""
}

echo ""
echo "Benchmarks complete. See results above."
echo ""

generate_test_files

START_TIME=$(date +%s)

if [ "$RUN_MEMORY" = true ]; then
    run_memory_benchmarks
fi

if [ "$RUN_CPU" = true ]; then
    run_cpu_benchmarks
fi

if [ "$RUN_STORAGE" = true ]; then
    run_storage_benchmarks
fi

if [ "$RUN_LOAD" = true ]; then
    run_load_tests
fi

echo ""
echo "Total benchmark time: ${DURATION}s"
echo ""
echo "Benchmarks complete. See results above."
echo ""
