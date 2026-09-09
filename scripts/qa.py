#!/usr/bin/env python3
"""Deterministic project QA with a machine-readable report."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_counts(output: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in ("passed", "failed", "skipped", "error", "errors"):
        matches = re.findall(rf"(\d+)\s+{label}\b", output)
        if matches:
            normalized = "errors" if label in {"error", "errors"} else label
            counts[normalized] = max(counts.get(normalized, 0), int(matches[-1]))
    return counts


def run_check(
    name: str,
    command: list[str],
    *,
    env: dict[str, str],
    reject_skips: bool = False,
) -> dict:
    print(f"\n▶ {name}")
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    duration = time.perf_counter() - started
    print(completed.stdout, end="")
    counts = test_counts(completed.stdout)
    skipped = counts.get("skipped", 0)
    passed = completed.returncode == 0 and (not reject_skips or skipped == 0)
    if completed.returncode == 0 and reject_skips and skipped:
        print(f"QA error: {name} skipped {skipped} test(s); skips are not allowed.")
    print(f"{'✓' if passed else '✗'} {name} ({duration:.2f}s)")
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "exit_code": completed.returncode,
        "duration_seconds": round(duration, 6),
        "counts": counts,
        "command": command,
        "output_tail": None if passed else completed.stdout[-4000:],
    }


def wait_until_healthy(base_url: str, process: subprocess.Popen, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"mock server exited with code {process.returncode}")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=0.5) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # server may still be binding
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"mock server did not become healthy: {last_error}")


def git_revision() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.stdout.strip() or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_DIR / "artifacts" / "qa-report.json",
        help="JSON report path",
    )
    args = parser.parse_args()
    report_path = args.report if args.report.is_absolute() else PROJECT_DIR / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Explicit values win over dotenvy's non-overwriting load behavior.
    qa_env = os.environ.copy()
    qa_env.update({
        "HOST": "127.0.0.1",
        "LLM_PROVIDER": "mock",
        "MODEL": "mock-baseline",
        "RUST_LOG": "warn",
    })

    started_at = datetime.now(timezone.utc)
    checks: list[dict] = []
    checks.append(run_check("rust_tests", ["cargo", "test", "--quiet"], env=qa_env))
    checks.append(run_check("server_build", ["cargo", "build", "--quiet"], env=qa_env))
    checks.append(
        run_check(
            "python_unit_tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_tools.py",
                "tests/test_benchmark.py",
                "tests/test_client.py",
                "tests/test_runtime.py",
                "-q",
            ],
            env=qa_env,
            reject_skips=True,
        )
    )

    server: subprocess.Popen | None = None
    server_log_path = report_path.parent / "qa-server.log"
    if checks[1]["status"] == "passed":
        with server_log_path.open("w", encoding="utf-8") as server_log:
            try:
                port = free_port()
                server_env = qa_env | {"PORT": str(port)}
                server = subprocess.Popen(
                    [str(PROJECT_DIR / "target" / "debug" / "mini-agent-server")],
                    cwd=PROJECT_DIR,
                    env=server_env,
                    stdout=server_log,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                base_url = f"http://127.0.0.1:{port}"
                wait_until_healthy(base_url, server)
                integration_env = qa_env | {"TEST_SERVER_URL": base_url}
                checks.append(
                    run_check(
                        "python_integration_tests",
                        [sys.executable, "-m", "pytest", "tests/test_integration.py", "-q"],
                        env=integration_env,
                        reject_skips=True,
                    )
                )
            except Exception as exc:
                print(f"✗ python_integration_tests: {exc}")
                checks.append({
                    "name": "python_integration_tests",
                    "status": "failed",
                    "exit_code": None,
                    "duration_seconds": 0.0,
                    "counts": {},
                    "command": [sys.executable, "-m", "pytest", "tests/test_integration.py", "-q"],
                    "output_tail": str(exc),
                })
            finally:
                if server is not None and server.poll() is None:
                    server.terminate()
                    try:
                        server.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait(timeout=5)
    else:
        checks.append({
            "name": "python_integration_tests",
            "status": "failed",
            "exit_code": None,
            "duration_seconds": 0.0,
            "counts": {},
            "command": [],
            "output_tail": "server build failed; integration tests were not run",
        })

    passed = all(check["status"] == "passed" for check in checks)
    report = {
        "schema_version": 1,
        "kind": "mini-agent-runtime-qa",
        "status": "passed" if passed else "failed",
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(),
        "environment_contract": {
            "llm_provider": "mock",
            "model": "mock-baseline",
            "integration_skips_allowed": False,
        },
        "checks": checks,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n{'PASS' if passed else 'FAIL'} — report: {report_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
