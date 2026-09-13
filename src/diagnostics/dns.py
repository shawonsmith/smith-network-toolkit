"""DNS resolution diagnostics and performance benchmark."""

import socket
import time
from typing import Dict, Any, List
from src.models.result import DiagnosticResult
from src.utils.logger import log_event

TEST_DOMAINS = ["google.com", "cloudflare.com", "github.com"]


def resolve_domain(domain: str, timeout_sec: float = 3.0) -> Dict[str, Any]:
    """Perform a pure DNS resolution for a domain and measure resolution latency."""
    start = time.perf_counter()
    original_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout_sec)
        # Query getaddrinfo for socket AF_INET
        addr_info = socket.getaddrinfo(domain, 80, socket.AF_INET, socket.SOCK_STREAM)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        resolved_ips = list(set([item[4][0] for item in addr_info if item[4]]))
        return {
            "domain": domain,
            "success": True,
            "latency_ms": round(elapsed_ms, 1),
            "ips": resolved_ips,
            "error": None
        }
    except socket.gaierror as e:
        return {
            "domain": domain,
            "success": False,
            "latency_ms": None,
            "ips": [],
            "error": f"Resolution failed: {e.strerror}"
        }
    except Exception as e:
        return {
            "domain": domain,
            "success": False,
            "latency_ms": None,
            "ips": [],
            "error": str(e)
        }
    finally:
        socket.setdefaulttimeout(original_timeout)


def test_dns(domains: List[str] = None, timeout_sec: float = 3.0) -> DiagnosticResult:
    """
    Test DNS resolution across standard domains.
    Strictly isolated from HTTP/HTTPS connectivity.
    """
    target_domains = domains or TEST_DOMAINS
    log_event(f"Starting DNS diagnostics for: {', '.join(target_domains)}")

    results = []
    latencies = []
    success_count = 0

    for domain in target_domains:
        res = resolve_domain(domain, timeout_sec=timeout_sec)
        results.append(res)
        if res["success"]:
            success_count += 1
            if res["latency_ms"] is not None:
                latencies.append(res["latency_ms"])

    total = len(target_domains)
    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else None

    details: Dict[str, Any] = {
        "domains": results,
        "total_tested": total,
        "resolved_count": success_count,
        "avg_ms": avg_latency
    }

    if success_count == 0:
        log_event("DNS test FAIL: 0 domains could be resolved", "error")
        return DiagnosticResult(
            name="DNS",
            status="FAIL",
            value="Failed",
            severity="error",
            message="Domain Name Resolution failed for all test domains.",
            details=details
        )

    if success_count < total:
        log_event(f"DNS test WARN: Only {success_count}/{total} domains resolved", "warning")
        return DiagnosticResult(
            name="DNS",
            status="WARN",
            value=f"Inconsistent ({success_count}/{total})",
            severity="warning",
            message=f"Only {success_count} of {total} test domains resolved successfully.",
            details=details
        )

    # All resolved - check response time threshold
    if avg_latency is not None and avg_latency > 200.0:
        log_event(f"DNS test WARN: Resolution is slow ({avg_latency} ms)", "warning")
        return DiagnosticResult(
            name="DNS",
            status="WARN",
            value=f"{avg_latency:.0f} ms (Slow)",
            severity="warning",
            message=f"DNS resolution is slow (Average: {avg_latency} ms).",
            details=details
        )

    log_event(f"DNS test PASS: Average resolution time {avg_latency} ms")
    return DiagnosticResult(
        name="DNS",
        status="PASS",
        value=f"{avg_latency:.0f} ms" if avg_latency is not None else "OK",
        severity="info",
        message="DNS resolution is fast and consistent.",
        details=details
    )
