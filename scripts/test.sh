#!/usr/bin/env bash
# test.sh — Run deterministic Rust + Python QA and write a JSON report.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/qa.py" "$@"
