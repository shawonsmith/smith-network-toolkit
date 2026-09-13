"""Default Gateway reachability diagnostics."""

from typing import Optional, Dict, Any
from src.models.result import DiagnosticResult
from src.utils.platform_utils import ping_host, tcp_ping, is_valid_ipv4
from src.utils.logger import log_event


def test_gateway(
    gateway_ip: Optional[str],
    count: int = 3,
    quick: bool = False
) -> DiagnosticResult:
    """Test default gateway presence and reachability."""
    ping_count = 1 if quick else count

    if not gateway_ip or gateway_ip in ("Unknown", "None", "") or not is_valid_ipv4(gateway_ip):
        log_event("Gateway test FAIL: No default gateway configured", "warning")
        return DiagnosticResult(
            name="Gateway",
            status="FAIL",
            value="Not Configured",
            severity="error",
            message="No default gateway detected on active adapter.",
            details={"gateway": "None", "latency_ms": None, "reachable": False}
        )

    log_event(f"Pinging default gateway {gateway_ip} (count={ping_count})...")
    ping_res = ping_host(gateway_ip, count=ping_count, timeout_sec=1.5)

    if ping_res["success"] and ping_res["avg_ms"] is not None:
        latency = ping_res["avg_ms"]
        log_event(f"Gateway test PASS: {gateway_ip} is reachable ({latency} ms)")
        return DiagnosticResult(
            name="Gateway",
            status="PASS",
            value=f"{latency:.0f} ms" if latency >= 1 else "<1 ms",
            severity="info",
            message="Gateway reachable",
            details={
                "gateway": gateway_ip,
                "latency_ms": latency,
                "loss_percent": ping_res["loss_percent"],
                "reachable": True,
                "method": "icmp"
            }
        )

    # Fallback to TCP in case router blocks ICMP
    for test_port in [80, 53, 443]:
        tcp_res = tcp_ping(gateway_ip, port=test_port, timeout_sec=1.0)
        if tcp_res["success"] and tcp_res["latency_ms"] is not None:
            latency = tcp_res["latency_ms"]
            log_event(f"Gateway test PASS (TCP fallback port {test_port}): {gateway_ip} is reachable ({latency} ms)")
            return DiagnosticResult(
                name="Gateway",
                status="PASS",
                value=f"{latency:.0f} ms (TCP)",
                severity="info",
                message="Gateway reachable (via TCP handshake)",
                details={
                    "gateway": gateway_ip,
                    "latency_ms": latency,
                    "loss_percent": 0.0,
                    "reachable": True,
                    "method": "tcp"
                }
            )

    log_event(f"Gateway test FAIL: {gateway_ip} is unreachable", "error")
    return DiagnosticResult(
        name="Gateway",
        status="FAIL",
        value="Unreachable",
        severity="error",
        message="Device cannot communicate with local gateway / router.",
        details={
            "gateway": gateway_ip,
            "latency_ms": None,
            "loss_percent": 100.0,
            "reachable": False,
            "method": "icmp+tcp"
        }
    )
