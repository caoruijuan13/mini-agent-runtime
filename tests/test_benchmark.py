"""Unit tests for deterministic benchmark statistics."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from benchmark import percentile, repeatability


def test_percentile_empty():
    assert percentile([], 0.95) is None


def test_percentile_interpolates():
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.95) == 3.8499999999999996


def test_repeatability_groups_cases():
    case_a = {
        "case_id": "json-short-c1",
        "request_throughput_per_second": 100.0,
        "latency_ms": {"p95": 10.0},
        "error_count": 0,
    }
    case_b = {
        "case_id": "json-short-c1",
        "request_throughput_per_second": 110.0,
        "latency_ms": {"p95": 12.0},
        "error_count": 0,
    }
    result = repeatability([
        {"repetition": 1, "cases": [case_a]},
        {"repetition": 2, "cases": [case_b]},
    ])
    assert result == [{
        "case_id": "json-short-c1",
        "repetitions": 2,
        "throughput_mean": 105.0,
        "throughput_coefficient_of_variation": 0.047619,
        "latency_p95_mean_ms": 11.0,
        "latency_p95_min_ms": 10.0,
        "latency_p95_max_ms": 12.0,
        "all_requests_succeeded": True,
    }]
