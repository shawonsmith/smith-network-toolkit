"""Unit tests for Internet connectivity tiering."""

import pytest
from unittest.mock import patch
from src.diagnostics.connectivity import test_internet_connectivity as run_test_connectivity


def test_situation_a_healthy():
    # Gateway works, External IP works, HTTPS works
    with patch("src.diagnostics.connectivity.check_external_ip_reachability", return_value={"reachable": True, "target": "1.1.1.1", "method": "icmp", "latency_ms": 15.0}), \
         patch("src.diagnostics.connectivity.check_https_connectivity", return_value={"success": True, "url": "https://www.cloudflare.com", "status_code": 200}):
        
        res = run_test_connectivity(gateway_reachable=True)
        assert res.status == "PASS"
        assert res.value == "Connected"


def test_situation_b_dns_or_web_limited():
    # Gateway works, External IP works, HTTPS fails
    with patch("src.diagnostics.connectivity.check_external_ip_reachability", return_value={"reachable": True, "target": "1.1.1.1", "method": "icmp", "latency_ms": 15.0}), \
         patch("src.diagnostics.connectivity.check_https_connectivity", return_value={"success": False, "url": None, "error": "Timeout"}):
        
        res = run_test_connectivity(gateway_reachable=True)
        assert res.status == "WARN"
        assert res.value == "Limited"


def test_situation_c_isp_outage():
    # Gateway works, External IP fails
    with patch("src.diagnostics.connectivity.check_external_ip_reachability", return_value={"reachable": False, "target": None, "method": "icmp", "latency_ms": None}), \
         patch("src.diagnostics.connectivity.check_https_connectivity", return_value={"success": False, "url": None, "error": "Timeout"}):
        
        res = run_test_connectivity(gateway_reachable=True)
        assert res.status == "FAIL"
        assert res.value == "No Internet"


def test_situation_d_gateway_unreachable():
    # Gateway fails
    with patch("src.diagnostics.connectivity.check_external_ip_reachability", return_value={"reachable": False, "target": None, "method": "icmp", "latency_ms": None}), \
         patch("src.diagnostics.connectivity.check_https_connectivity", return_value={"success": False, "url": None, "error": "Timeout"}):
        
        res = run_test_connectivity(gateway_reachable=False)
        assert res.status == "FAIL"
        assert res.value == "Disconnected"
