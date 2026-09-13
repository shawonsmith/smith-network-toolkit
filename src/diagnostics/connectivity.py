"""Multi-stage Internet connectivity diagnostics."""

import urllib.request
import socket
from typing import Dict, Any, Optional
from src.models.result import DiagnosticResult
from src.utils.platform_utils import ping_host, tcp_ping
from src.utils.logger import log_event


PUBLIC_DNS_IPS = ["1.1.1.1", "8.8.8.8"]
HTTPS_TEST_ENDPOINTS = [
    "https://www.cloudflare.com",
    "https://www.google.com"
]


def check_external_ip_reachability(timeout_sec: float = 2.0, quick: bool = False) -> Dict[str, Any]:
    """Test direct external IP reachability via ICMP ping with TCP 53 fallback."""
    count = 1 if quick else 2
    for ip in PUBLIC_DNS_IPS:
        # Try ICMP ping first
        ping_res = ping_host(ip, count=count, timeout_sec=timeout_sec)
        if ping_res["success"] and ping_res["avg_ms"] is not None:
            return {
                "reachable": True,
                "target": ip,
                "method": "icmp",
                "latency_ms": ping_res["avg_ms"]
            }

        # TCP Fallback (e.g. port 53 DNS on public resolver)
        tcp_res = tcp_ping(ip, port=53, timeout_sec=timeout_sec)
        if tcp_res["success"]:
            return {
                "reachable": True,
                "target": ip,
                "method": "tcp",
                "latency_ms": tcp_res["latency_ms"]
            }

    return {
        "reachable": False,
        "target": None,
        "method": "icmp+tcp",
        "latency_ms": None
    }


def check_https_connectivity(timeout_sec: float = 3.0) -> Dict[str, Any]:
    """Test actual HTTPS web browsing connectivity."""
    for url in HTTPS_TEST_ENDPOINTS:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SmithNetworkToolkit/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                if 200 <= resp.status < 400:
                    return {"success": True, "url": url, "status_code": resp.status}
        except urllib.error.HTTPError as e:
            return {"success": True, "url": url, "status_code": e.code}
        except Exception as e:
            continue

    return {"success": False, "url": None, "error": "HTTPS requests failed or timed out"}


def test_internet_connectivity(
    gateway_reachable: bool = True,
    quick: bool = False
) -> DiagnosticResult:
    """
    Run multi-tier internet connectivity check:
    Stage 1: Gateway reachable (passed from gateway test)
    Stage 2: Direct public IP reachability (ICMP + TCP fallback)
    Stage 3: HTTPS web endpoint reachability
    """
    log_event("Starting multi-stage Internet connectivity check...")

    ext_ip_check = check_external_ip_reachability(quick=quick)
    https_check = check_https_connectivity(timeout_sec=2.0 if quick else 3.0)

    external_ip_ok = ext_ip_check["reachable"]
    https_ok = https_check["success"]

    details = {
        "gateway_reachable": gateway_reachable,
        "external_ip_reachable": external_ip_ok,
        "external_ip_target": ext_ip_check.get("target"),
        "external_ip_method": ext_ip_check.get("method"),
        "https_reachable": https_ok,
        "https_endpoint": https_check.get("url"),
    }

    # Situation A: All good
    if gateway_reachable and external_ip_ok and https_ok:
        log_event("Internet test PASS: Connection healthy")
        return DiagnosticResult(
            name="Internet",
            status="PASS",
            value="Connected",
            severity="info",
            message="Internet connection healthy.",
            details=details
        )

    # Situation B: Gateway OK, External IP OK, HTTPS fails (Domain or web port issue)
    if external_ip_ok and not https_ok:
        log_event("Internet test WARN: Direct IP reachable, but HTTPS failed", "warning")
        return DiagnosticResult(
            name="Internet",
            status="WARN",
            value="Limited",
            severity="warning",
            message="External IP reachable, but HTTPS requests failed (possible DNS or web filtering).",
            details=details
        )

    # Situation C: Gateway OK, but External IP fails
    if gateway_reachable and not external_ip_ok:
        log_event("Internet test FAIL: Gateway reachable but external IP unreachable", "error")
        return DiagnosticResult(
            name="Internet",
            status="FAIL",
            value="No Internet",
            severity="error",
            message="Connected to local gateway, but external Internet is unreachable (ISP / WAN issue).",
            details=details
        )

    # Situation D: Gateway itself is unreachable
    log_event("Internet test FAIL: Local gateway is unreachable", "error")
    return DiagnosticResult(
        name="Internet",
        status="FAIL",
        value="Disconnected",
        severity="error",
        message="Cannot reach local network gateway or external network.",
        details=details
    )
