#!/usr/bin/env python3
"""Repeatable HTTP/SSE baseline benchmark for mini-agent-runtime."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests


PROJECT_DIR = Path(__file__).resolve().parents[1]
THREAD_LOCAL = threading.local()


def percentile(values: list[float], quantile: float) -> float | None:
    """Return a linearly interpolated percentile, or None for no samples."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def rounded(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(value, digits)


def session() -> requests.Session:
    client = getattr(THREAD_LOCAL, "session", None)
    if client is None:
        client = requests.Session()
        client.headers.update({"Content-Type": "application/json"})
        THREAD_LOCAL.session = client
    return client


class ResourceSampler:
    """Best-effort CPU and RSS sampling for a local server process."""

    def __init__(self, pid: int | None):
        self.pid = pid
        self.samples: list[dict[str, float]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.pid is None:
            return
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if not self.samples:
            return {"available": False, "server_pid": self.pid}
        cpu = [sample["cpu_percent"] for sample in self.samples]
        rss = [sample["rss_bytes"] for sample in self.samples]
        return {
            "available": True,
            "server_pid": self.pid,
            "sample_count": len(self.samples),
            "cpu_percent_mean": rounded(statistics.fmean(cpu)),
            "cpu_percent_max": rounded(max(cpu)),
            "rss_bytes_mean": round(statistics.fmean(rss)),
            "rss_bytes_max": round(max(rss)),
        }

    def _sample_loop(self) -> None:
        while not self._stop.is_set():
            completed = subprocess.run(
                ["ps", "-o", "rss=,%cpu=", "-p", str(self.pid)],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
            fields = completed.stdout.strip().split()
            if len(fields) >= 2:
                try:
                    self.samples.append({
                        "rss_bytes": float(fields[0]) * 1024,
                        "cpu_percent": float(fields[1]),
                    })
                except ValueError:
                    pass
            self._stop.wait(0.1)


def json_request(base_url: str, prompt: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        response = session().post(
            f"{base_url}/chat",
            json={"messages": [{"role": "user", "content": prompt}], "stream": False},
            timeout=timeout,
        )
        elapsed = time.perf_counter() - started
        response.raise_for_status()
        payload = response.json()
        usage = payload.get("usage") or {}
        return {
            "ok": True,
            "latency_seconds": elapsed,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "response_bytes": len(response.content),
        }
    except Exception as exc:
        return {
            "ok": False,
            "latency_seconds": time.perf_counter() - started,
            "error": f"{type(exc).__name__}: {exc}",
        }


def stream_request(base_url: str, prompt: str, timeout: float) -> dict:
    started = time.perf_counter()
    first_content_at: float | None = None
    response_bytes = 0
    try:
        with session().post(
            f"{base_url}/chat",
            json={"messages": [{"role": "user", "content": prompt}], "stream": True},
            stream=True,
            timeout=timeout,
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            response.encoding = "utf-8"
            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if not line or not line.startswith("data:"):
                    continue
                payload = json.loads(line[5:].lstrip(" "))
                content = payload.get("content")
                if content:
                    if first_content_at is None:
                        first_content_at = time.perf_counter()
                    response_bytes += len(content.encode("utf-8"))
        finished = time.perf_counter()
        if first_content_at is None:
            raise RuntimeError("stream completed without a content event")
        return {
            "ok": True,
            "latency_seconds": finished - started,
            "ttft_seconds": first_content_at - started,
            "response_bytes": response_bytes,
        }
    except Exception as exc:
        return {
            "ok": False,
            "latency_seconds": time.perf_counter() - started,
            "error": f"{type(exc).__name__}: {exc}",
        }


def execute_case(
    *,
    case_id: str,
    mode: str,
    concurrency: int,
    request_count: int,
    operation: Callable[[], dict],
) -> dict:
    wall_started = time.perf_counter()
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(operation) for _ in range(request_count)]
        for future in as_completed(futures):
            results.append(future.result())
    wall_seconds = time.perf_counter() - wall_started

    successes = [result for result in results if result["ok"]]
    latencies_ms = [result["latency_seconds"] * 1000 for result in successes]
    ttft_ms = [result["ttft_seconds"] * 1000 for result in successes if "ttft_seconds" in result]
    prompt_tokens = [result["prompt_tokens"] for result in successes if result.get("prompt_tokens") is not None]
    completion_tokens = [result["completion_tokens"] for result in successes if result.get("completion_tokens") is not None]
    errors: dict[str, int] = {}
    for result in results:
        if not result["ok"]:
            error = result.get("error", "unknown")
            errors[error] = errors.get(error, 0) + 1

    return {
        "case_id": case_id,
        "mode": mode,
        "concurrency": concurrency,
        "request_count": request_count,
        "success_count": len(successes),
        "error_count": len(results) - len(successes),
        "error_rate": rounded((len(results) - len(successes)) / len(results), 6),
        "wall_seconds": rounded(wall_seconds, 6),
        "request_throughput_per_second": rounded(len(successes) / wall_seconds),
        "latency_ms": {
            "mean": rounded(statistics.fmean(latencies_ms)) if latencies_ms else None,
            "p50": rounded(percentile(latencies_ms, 0.50)),
            "p95": rounded(percentile(latencies_ms, 0.95)),
            "p99": rounded(percentile(latencies_ms, 0.99)),
            "max": rounded(max(latencies_ms)) if latencies_ms else None,
        },
        "ttft_ms": {
            "mean": rounded(statistics.fmean(ttft_ms)) if ttft_ms else None,
            "p50": rounded(percentile(ttft_ms, 0.50)),
            "p95": rounded(percentile(ttft_ms, 0.95)),
            "p99": rounded(percentile(ttft_ms, 0.99)),
        } if mode == "sse" else None,
        "tokens": {
            "prompt_total": sum(prompt_tokens) if prompt_tokens else None,
            "completion_total": sum(completion_tokens) if completion_tokens else None,
            "completion_per_second": rounded(sum(completion_tokens) / wall_seconds) if completion_tokens else None,
            "availability": "reported_by_server" if completion_tokens else "not_reported",
        },
        "response_bytes_total": sum(result.get("response_bytes", 0) for result in successes),
        "errors": errors,
    }


def repeatability(runs: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for run in runs:
        for case in run["cases"]:
            grouped.setdefault(case["case_id"], []).append(case)

    summary = []
    for case_id, cases in grouped.items():
        throughputs = [case["request_throughput_per_second"] for case in cases]
        p95_values = [case["latency_ms"]["p95"] for case in cases if case["latency_ms"]["p95"] is not None]
        mean_throughput = statistics.fmean(throughputs)
        throughput_cv = statistics.pstdev(throughputs) / mean_throughput if mean_throughput else 0.0
        summary.append({
            "case_id": case_id,
            "repetitions": len(cases),
            "throughput_mean": rounded(mean_throughput),
            "throughput_coefficient_of_variation": rounded(throughput_cv, 6),
            "latency_p95_mean_ms": rounded(statistics.fmean(p95_values)) if p95_values else None,
            "latency_p95_min_ms": rounded(min(p95_values)) if p95_values else None,
            "latency_p95_max_ms": rounded(max(p95_values)) if p95_values else None,
            "all_requests_succeeded": all(case["error_count"] == 0 for case in cases),
        })
    return sorted(summary, key=lambda item: item["case_id"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3100")
    parser.add_argument("--report", type=Path, default=PROJECT_DIR / "artifacts" / "benchmark-report.json")
    parser.add_argument("--concurrency", default="1,5,10,20,50")
    parser.add_argument("--requests-per-case", type=int, default=50)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--max-throughput-cv",
        type=float,
        default=0.20,
        help="maximum allowed throughput coefficient of variation across repetitions",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--server-pid", type=int)
    args = parser.parse_args()

    concurrencies = [int(value) for value in args.concurrency.split(",")]
    if any(value < 1 for value in concurrencies):
        parser.error("concurrency values must be positive")
    if args.requests_per_case < 1 or args.repetitions < 1:
        parser.error("requests-per-case and repetitions must be positive")
    if args.max_throughput_cv < 0:
        parser.error("max-throughput-cv must be non-negative")

    report_path = args.report if args.report.is_absolute() else PROJECT_DIR / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    base_url = args.base_url.rstrip("/")
    prompts = {
        "short": "请只回复 OK。负载：" + "甲" * 64,
        "medium": "请只回复 OK。负载：" + "乙" * 2048,
        "long": "请只回复 OK。负载：" + "丙" * 16384,
    }

    health = session().get(f"{base_url}/health", timeout=args.timeout)
    health.raise_for_status()
    server_info = health.json()

    # Warm up code paths and reusable HTTP connections outside measurements.
    for _ in range(5):
        result = json_request(base_url, prompts["short"], args.timeout)
        if not result["ok"]:
            raise RuntimeError(f"warmup failed: {result.get('error')}")

    sampler = ResourceSampler(args.server_pid)
    sampler.start()
    runs: list[dict] = []
    benchmark_started = datetime.now(timezone.utc)
    for repetition in range(1, args.repetitions + 1):
        cases = []
        print(f"Repetition {repetition}/{args.repetitions}")
        for workload_name, prompt in prompts.items():
            for concurrency in concurrencies:
                request_count = max(args.requests_per_case, concurrency * 2)
                case_id = f"json-{workload_name}-c{concurrency}"
                case = execute_case(
                    case_id=case_id,
                    mode="json",
                    concurrency=concurrency,
                    request_count=request_count,
                    operation=lambda p=prompt: json_request(base_url, p, args.timeout),
                )
                cases.append(case)
                print(
                    f"  {case_id}: {case['request_throughput_per_second']:.2f} req/s, "
                    f"p95={case['latency_ms']['p95']:.2f} ms, errors={case['error_count']}"
                )

        for concurrency in concurrencies:
            request_count = max(args.requests_per_case, concurrency * 2)
            case_id = f"sse-short-c{concurrency}"
            case = execute_case(
                case_id=case_id,
                mode="sse",
                concurrency=concurrency,
                request_count=request_count,
                operation=lambda: stream_request(base_url, prompts["short"], args.timeout),
            )
            cases.append(case)
            ttft_p95 = case["ttft_ms"]["p95"]
            ttft_display = f"{ttft_p95:.2f} ms" if ttft_p95 is not None else "unavailable"
            print(
                f"  {case_id}: TTFT p95={ttft_display}, "
                f"errors={case['error_count']}"
            )
            if case["errors"]:
                print(f"    first error: {next(iter(case['errors']))}")
        runs.append({"repetition": repetition, "cases": cases})

    resources = sampler.stop()
    comparison = repeatability(runs)
    all_succeeded = all(item["all_requests_succeeded"] for item in comparison)
    unstable_cases = [
        item["case_id"]
        for item in comparison
        if item["throughput_coefficient_of_variation"] > args.max_throughput_cv
    ]
    repeatability_stable = not unstable_cases
    passed = all_succeeded and repeatability_stable
    report = {
        "schema_version": 1,
        "kind": "mini-agent-runtime-baseline",
        "status": "passed" if passed else "failed",
        "started_at": benchmark_started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "server": server_info,
        "workload_contract": {
            "concurrency": concurrencies,
            "requests_per_case_minimum": args.requests_per_case,
            "repetitions": args.repetitions,
            "prompt_utf8_bytes": {name: len(prompt.encode("utf-8")) for name, prompt in prompts.items()},
            "warmup_requests": 5,
            "timeout_seconds": args.timeout,
        },
        "repeatability_contract": {
            "metric": "request_throughput_per_second",
            "maximum_coefficient_of_variation": args.max_throughput_cv,
            "stable": repeatability_stable,
            "unstable_cases": unstable_cases,
        },
        "metric_notes": {
            "latency": "client-observed end-to-end time",
            "ttft": "client-observed time to first SSE event with non-empty content",
            "tokens": "provider-reported usage; unavailable for the current SSE response contract",
            "resources": "best-effort local ps samples; unavailable without --server-pid",
        },
        "resources": resources,
        "runs": runs,
        "repeatability": comparison,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if unstable_cases:
        print(
            "Unstable throughput cases above "
            f"CV={args.max_throughput_cv:.3f}: {', '.join(unstable_cases)}"
        )
    print(f"\n{'PASS' if passed else 'FAIL'} — report: {report_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
