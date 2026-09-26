#!/usr/bin/env bash
# 运行已有本地参考示例，无外部依赖。
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR/python"
exec python3 -m agent "$@"
