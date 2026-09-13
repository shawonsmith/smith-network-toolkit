"""Unit tests for dual latency measurement."""

import pytest
from unittest.mock import patch
from src.diagnostics.latency import measure_latency


def test_measure_latency_healthy():
    def mock_ping(host, count=4, timeout_sec=1.5):
        if host == "192.168.1.1":
            return {"success": True, "avg_ms": 2.0, "min_ms": 1.0, "max_ms": 3.0}
        elif host == "1.1.1.1":
            return {"success": True, "avg_ms": 30.0, "min_ms": 28.0, "max_ms": 32.0}
        else:
            return {"success": True, "avg_ms": 34.0, "min_ms": 33.0, "max_ms": 35.0}

    with patch("src.diagnostics.latency.ping_host", side_effect=mock_ping):
        res = measure_latency(gateway_ip="192.168.1.1")
        assert res.status == "PASS"
        assert res.details["gateway_latency_ms"] == 2.0
        assert res.details["internet_avg_ms"] == 32.0


def test_measure_latency_internet_unreachable():
    def mock_ping(host, count=4, timeout_sec=1.5):
        if host == "192.168.1.1":
            return {"success": True, "avg_ms": 2.0}
        return {"success": False, "avg_ms": None}

    with patch("src.diagnostics.latency.ping_host", side_effect=mock_ping):
        res = measure_latency(gateway_ip="192.168.1.1")
        assert res.status == "FAIL"
        assert res.value == "Unreachable"
