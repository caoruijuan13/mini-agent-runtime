#!/usr/bin/env bash
# Build a forced-Mock server and run the repeatable baseline benchmark.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BENCHMARK_PORT="${BENCHMARK_PORT:-3100}"
ARTIFACT_DIR="$PROJECT_DIR/artifacts"

mkdir -p "$ARTIFACT_DIR"
cd "$PROJECT_DIR"
cargo build --release --quiet

HOST=127.0.0.1 \
PORT="$BENCHMARK_PORT" \
LLM_PROVIDER=mock \
MODEL=mock-baseline \
RUST_LOG=warn \
"$PROJECT_DIR/target/release/mini-agent-server" \
    >"$ARTIFACT_DIR/benchmark-server.log" 2>&1 &
SERVER_PID=$!

cleanup() {
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 100); do
    if curl -fsS "http://127.0.0.1:$BENCHMARK_PORT/health" >/dev/null 2>&1; then
        break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "Benchmark server exited before becoming healthy."
        exit 1
    fi
    sleep 0.1
done

if ! curl -fsS "http://127.0.0.1:$BENCHMARK_PORT/health" >/dev/null; then
    echo "Benchmark server did not become healthy."
    exit 1
fi

python3 -u "$SCRIPT_DIR/benchmark.py" \
    --base-url "http://127.0.0.1:$BENCHMARK_PORT" \
    --server-pid "$SERVER_PID" \
    "$@"
