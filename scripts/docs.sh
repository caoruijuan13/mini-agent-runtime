#!/usr/bin/env bash
# Build or serve the MkDocs technical documentation.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ACTION="${1:-build}"

cd "$PROJECT_DIR"

if ! python3 -m mkdocs --version >/dev/null 2>&1; then
    echo "MkDocs is not installed. Run: python3 -m pip install -r requirements-docs.txt"
    exit 1
fi

case "$ACTION" in
    build)
        exec python3 -m mkdocs build --strict
        ;;
    serve)
        exec python3 -m mkdocs serve --clean
        ;;
    *)
        echo "Usage: bash scripts/docs.sh [build|serve]"
        exit 2
        ;;
esac
