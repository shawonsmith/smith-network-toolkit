"""Unit tests for DNS diagnostics."""

import pytest
from unittest.mock import patch
from src.diagnostics.dns import test_dns as run_test_dns


def test_dns_success_fast():
    mock_resolve = lambda domain, timeout_sec: {
        "domain": domain,
        "success": True,
        "latency_ms": 35.0,
        "ips": ["1.2.3.4"],
        "error": None
    }
    with patch("src.diagnostics.dns.resolve_domain", side_effect=mock_resolve):
        res = run_test_dns()
        assert res.status == "PASS"
        assert res.details["resolved_count"] == 3
        assert "35 ms" in res.value


def test_dns_slow():
    mock_resolve = lambda domain, timeout_sec: {
        "domain": domain,
        "success": True,
        "latency_ms": 280.0,
        "ips": ["1.2.3.4"],
        "error": None
    }
    with patch("src.diagnostics.dns.resolve_domain", side_effect=mock_resolve):
        res = run_test_dns()
        assert res.status == "WARN"
        assert "Slow" in res.value


def test_dns_partial_inconsistent():
    def mock_resolve(domain, timeout_sec):
        if domain == "google.com":
            return {"domain": domain, "success": True, "latency_ms": 30.0, "ips": ["1.2.3.4"], "error": None}
        return {"domain": domain, "success": False, "latency_ms": None, "ips": [], "error": "Timeout"}

    with patch("src.diagnostics.dns.resolve_domain", side_effect=mock_resolve):
        res = run_test_dns()
        assert res.status == "WARN"
        assert "Inconsistent" in res.value


def test_dns_total_failure():
    mock_resolve = lambda domain, timeout_sec: {
        "domain": domain,
        "success": False,
        "latency_ms": None,
        "ips": [],
        "error": "Timeout"
    }
    with patch("src.diagnostics.dns.resolve_domain", side_effect=mock_resolve):
        res = run_test_dns()
        assert res.status == "FAIL"
        assert res.value == "Failed"
