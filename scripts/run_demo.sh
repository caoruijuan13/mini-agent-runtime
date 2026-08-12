#!/usr/bin/env bash
# run_demo.sh — Start the Rust server and Python agent for a demo session.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "═══════════════════════════════════════════════════"
echo "  mini-agent-runtime — Demo"
echo "═══════════════════════════════════════════════════"
echo ""

# ─── Check prerequisites ──────────────────────────────────────────────────────

command -v cargo >/dev/null 2>&1 || { echo "❌ Rust/Cargo not found. Install: https://rustup.rs"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python3 not found."; exit 1; }

# ─── Configuration ────────────────────────────────────────────────────────────

export LLM_PROVIDER="${LLM_PROVIDER:-mock}"
export RUST_LOG="${RUST_LOG:-mini_agent_server=info}"

echo "📦 Configuration:"
echo "   LLM Provider: $LLM_PROVIDER"
echo "   Rust Log:     $RUST_LOG"
echo ""

# ─── Build Rust server ────────────────────────────────────────────────────────

echo "🔨 Building Rust server..."
cd "$PROJECT_DIR"
cargo build --release 2>&1 | tail -3
echo "   ✅ Build complete"
echo ""

# ─── Install Python dependencies ──────────────────────────────────────────────

echo "📦 Installing Python dependencies..."
pip install -q -r "$PROJECT_DIR/python/requirements.txt" 2>/dev/null || pip3 install -q -r "$PROJECT_DIR/python/requirements.txt" 2>/dev/null
echo "   ✅ Dependencies installed"
echo ""

# ─── Start Rust server in background ─────────────────────────────────────────

echo "🚀 Starting Rust server on port 3000..."
cd "$PROJECT_DIR"
./target/release/mini-agent-server &
SERVER_PID=$!

# Wait for server to be ready
echo "   Waiting for server..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:3000/health >/dev/null 2>&1; then
        echo "   ✅ Server ready (PID: $SERVER_PID)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "   ❌ Server failed to start"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    sleep 0.5
done
echo ""

# ─── Cleanup function ─────────────────────────────────────────────────────────

cleanup() {
    echo ""
    echo "🛑 Stopping server (PID: $SERVER_PID)..."
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo "   ✅ Server stopped"
}
trap cleanup EXIT INT TERM

# ─── Start Python agent ──────────────────────────────────────────────────────

echo "🤖 Starting Python agent..."
echo ""
cd "$PROJECT_DIR/python"
python3 -m agent "$@"
