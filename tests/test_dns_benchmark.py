"""Unit tests for DNS benchmark module."""

import pytest
from unittest.mock import patch
from src.diagnostics.dns_benchmark import benchmark_single_resolver, run_dns_benchmark


def test_benchmark_single_resolver_mocked():
    with patch("dns.resolver.Resolver.resolve", return_value=["1.2.3.4"]):
        res = benchmark_single_resolver("1.1.1.1", domains=["google.com"])
        assert res["ip"] == "1.1.1.1"
        assert res["success"] is True
        assert res["avg_ms"] is not None


def test_run_dns_benchmark_ranking():
    mock_single = lambda ip, domains=None, timeout_sec=2.0: {
        "ip": ip,
        "success": True,
        "success_rate": "3/3",
        "avg_ms": 15.0 if ip == "1.1.1.1" else (25.0 if ip == "8.8.8.8" else 40.0),
        "latencies": [15.0]
    }
    with patch("src.diagnostics.dns_benchmark.benchmark_single_resolver", side_effect=mock_single):
        res = run_dns_benchmark(local_dns="192.168.0.1")
        assert res["fastest"] is not None
        assert res["fastest"]["ip"] == "1.1.1.1"
        assert len(res["results"]) >= 4
