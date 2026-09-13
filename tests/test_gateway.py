"""Unit tests for Gateway diagnostics."""

import pytest
from unittest.mock import patch
from src.diagnostics.gateway import test_gateway as run_test_gateway


def test_gateway_not_configured():
    res = run_test_gateway("Unknown")
    assert res.status == "FAIL"
    assert res.value == "Not Configured"
    assert res.details["reachable"] is False


def test_gateway_reachable_icmp():
    mock_ping = {
        "success": True,
        "sent": 3,
        "received": 3,
        "lost": 0,
        "loss_percent": 0.0,
        "avg_ms": 3.0,
        "raw": ""
    }
    with patch("src.diagnostics.gateway.ping_host", return_value=mock_ping):
        res = run_test_gateway("192.168.1.1")
        assert res.status == "PASS"
        assert res.value == "3 ms"
        assert res.details["reachable"] is True
        assert res.details["method"] == "icmp"


def test_gateway_unreachable():
    mock_ping = {
        "success": False,
        "sent": 3,
        "received": 0,
        "lost": 3,
        "loss_percent": 100.0,
        "avg_ms": None,
        "raw": ""
    }
    mock_tcp = {
        "success": False,
        "latency_ms": None,
        "port": 80,
        "error": "Timeout",
        "method": "tcp"
    }
    with patch("src.diagnostics.gateway.ping_host", return_value=mock_ping), \
         patch("src.diagnostics.gateway.tcp_ping", return_value=mock_tcp):
        res = run_test_gateway("192.168.1.1")
        assert res.status == "FAIL"
        assert res.value == "Unreachable"
        assert res.details["reachable"] is False


def test_gateway_icmp_blocked_tcp_fallback():
    mock_ping = {
        "success": False,
        "sent": 3,
        "received": 0,
        "lost": 3,
        "loss_percent": 100.0,
        "avg_ms": None,
        "raw": ""
    }
    mock_tcp = {
        "success": True,
        "latency_ms": 4.0,
        "port": 80,
        "method": "tcp"
    }
    with patch("src.diagnostics.gateway.ping_host", return_value=mock_ping), \
         patch("src.diagnostics.gateway.tcp_ping", return_value=mock_tcp):
        res = run_test_gateway("192.168.1.1")
        assert res.status == "PASS"
        assert "TCP" in res.value
        assert res.details["reachable"] is True
