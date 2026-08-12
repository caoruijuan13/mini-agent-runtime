#!/usr/bin/env bash
# test.sh — Run all tests (Rust + Python).
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "═══════════════════════════════════════════════════"
echo "  mini-agent-runtime — Test Suite"
echo "═══════════════════════════════════════════════════"
echo ""

PASS=0
FAIL=0

# ─── Rust unit tests ─────────────────────────────────────────────────────────

echo "🦀 Running Rust unit tests..."
cd "$PROJECT_DIR"
if cargo test 2>&1; then
    echo "   ✅ Rust tests passed"
    PASS=$((PASS + 1))
else
    echo "   ❌ Rust tests failed"
    FAIL=$((FAIL + 1))
fi
echo ""

# ─── Python tool tests ───────────────────────────────────────────────────────

echo "🐍 Running Python tool tests..."
cd "$PROJECT_DIR"
if python3 -m pytest tests/test_tools.py -v 2>&1; then
    echo "   ✅ Python tool tests passed"
    PASS=$((PASS + 1))
else
    echo "   ❌ Python tool tests failed"
    FAIL=$((FAIL + 1))
fi
echo ""

# ─── Python integration tests (optional — needs server) ──────────────────────

echo "🔗 Running Python integration tests..."
cd "$PROJECT_DIR"
if python3 -m pytest tests/test_integration.py -v 2>&1; then
    echo "   ✅ Integration tests passed"
    PASS=$((PASS + 1))
else
    echo "   ⚠️  Integration tests skipped or failed (server may not be running)"
fi
echo ""

# ─── Summary ──────────────────────────────────────────────────────────────────

echo "═══════════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════════════"

if [ $FAIL -gt 0 ]; then
    exit 1
fi
