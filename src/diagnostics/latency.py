"""Dual-tier latency measurement across local gateway and public internet."""

from typing import Dict, Any, Optional, List
from src.models.result import DiagnosticResult
from src.utils.platform_utils import ping_host, is_valid_ipv4
from src.utils.logger import log_event


LATENCY_TARGETS = {
    "Cloudflare": "1.1.1.1",
    "Google": "8.8.8.8"
}


def measure_latency(
    gateway_ip: Optional[str] = None,
    quick: bool = False
) -> DiagnosticResult:
    """
    Measure local gateway latency and public internet latency.
    Dual-tier scoring to prevent regional internet distance from penalizing LAN health.
    """
    count = 2 if quick else 4
    log_event("Starting latency measurements across Gateway and Internet...")

    destinations: Dict[str, Any] = {}
    internet_latencies: List[float] = []

    # 1. Local Gateway Latency
    gw_latency = None
    if gateway_ip and is_valid_ipv4(gateway_ip):
        res = ping_host(gateway_ip, count=count, timeout_sec=1.5)
        if res["success"] and res["avg_ms"] is not None:
            gw_latency = res["avg_ms"]
            destinations["Gateway"] = {
                "ip": gateway_ip,
                "latency_ms": gw_latency,
                "min_ms": res.get("min_ms"),
                "max_ms": res.get("max_ms"),
                "status": "Reachable"
            }
        else:
            destinations["Gateway"] = {
                "ip": gateway_ip,
                "latency_ms": None,
                "status": "Unreachable"
            }

    # 2. Public Internet Targets
    for name, ip in LATENCY_TARGETS.items():
        res = ping_host(ip, count=count, timeout_sec=1.5)
        if res["success"] and res["avg_ms"] is not None:
            destinations[name] = {
                "ip": ip,
                "latency_ms": res["avg_ms"],
                "min_ms": res.get("min_ms"),
                "max_ms": res.get("max_ms"),
                "status": "Reachable"
            }
            internet_latencies.append(res["avg_ms"])
        else:
            destinations[name] = {
                "ip": ip,
                "latency_ms": None,
                "status": "Unreachable"
            }

    avg_internet = (
        round(sum(internet_latencies) / len(internet_latencies), 1)
        if internet_latencies else None
    )

    details = {
        "gateway_latency_ms": gw_latency,
        "internet_avg_ms": avg_internet,
        "destinations": destinations
    }

    if avg_internet is None:
        log_event("Latency test FAIL: Could not reach internet hosts", "error")
        return DiagnosticResult(
            name="Latency",
            status="FAIL",
            value="Unreachable",
            severity="error",
            message="Internet latency could not be measured.",
            details=details
        )

    # Status classification (fair for regional distance):
    # <80ms: Good/Fast
    # 80-200ms: Normal/Acceptable
    # >200ms: High/Slow
    if avg_internet <= 80.0:
        log_event(f"Latency test PASS: {avg_internet} ms (Fast)")
        return DiagnosticResult(
            name="Latency",
            status="PASS",
            value=f"{avg_internet:.0f} ms",
            severity="info",
            message="Low latency connection.",
            details=details
        )
    elif avg_internet <= 200.0:
        log_event(f"Latency test PASS: {avg_internet} ms (Moderate)")
        return DiagnosticResult(
            name="Latency",
            status="PASS",
            value=f"{avg_internet:.0f} ms",
            severity="info",
            message="Moderate latency connection.",
            details=details
        )
    else:
        log_event(f"Latency test WARN: {avg_internet} ms (High)", "warning")
        return DiagnosticResult(
            name="Latency",
            status="WARN",
            value=f"{avg_internet:.0f} ms (High)",
            severity="warning",
            message="High round-trip latency detected.",
            details=details
        )
