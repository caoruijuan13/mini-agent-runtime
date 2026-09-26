#!/usr/bin/env bash
# 运行当前 Python 核心的全部测试，不启动服务。
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
exec python3 -m pytest tests -q "$@"
