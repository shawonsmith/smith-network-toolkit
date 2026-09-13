"""Packet loss diagnostic module."""

from typing import Dict, Any, Optional
from src.models.result import DiagnosticResult
from src.utils.platform_utils import ping_host
from src.utils.logger import log_event


def test_packet_loss(
    target: str = "1.1.1.1",
    count: int = 20,
    quick: bool = False
) -> DiagnosticResult:
    """
    Measure packet loss percentage against a reliable target.
    Standard: 20 packets.
    Quick mode: 5 packets.
    """
    packet_count = 5 if quick else count
    log_event(f"Starting packet loss test to {target} ({packet_count} packets)...")

    ping_res = ping_host(target, count=packet_count, timeout_sec=1.5)
    loss = ping_res["loss_percent"]
    sent = ping_res["sent"]
    received = ping_res["received"]
    lost = ping_res["lost"]

    details: Dict[str, Any] = {
        "target": target,
        "sent": sent,
        "received": received,
        "lost": lost,
        "loss_percent": loss,
        "avg_ms": ping_res.get("avg_ms")
    }

    # Classification:
    # 0%      Excellent
    # 1–2%    Acceptable
    # 3–5%    Warning
    # >5%     Poor
    if loss == 0.0:
        log_event(f"Packet loss test PASS: 0% loss ({sent}/{sent})")
        return DiagnosticResult(
            name="Packet Loss",
            status="PASS",
            value="0%",
            severity="info",
            message="No packet loss detected.",
            details=details
        )
    elif loss <= 2.0:
        log_event(f"Packet loss test PASS: {loss:.1f}% loss (Acceptable)")
        return DiagnosticResult(
            name="Packet Loss",
            status="PASS",
            value=f"{loss:.1f}%",
            severity="info",
            message="Acceptable minimal packet loss.",
            details=details
        )
    elif loss <= 5.0:
        log_event(f"Packet loss test WARN: {loss:.1f}% loss (Warning)", "warning")
        return DiagnosticResult(
            name="Packet Loss",
            status="WARN",
            value=f"{loss:.1f}%",
            severity="warning",
            message="Minor packet loss detected on connection.",
            details=details
        )
    else:
        log_event(f"Packet loss test FAIL: {loss:.1f}% loss (Poor)", "error")
        return DiagnosticResult(
            name="Packet Loss",
            status="FAIL",
            value=f"{loss:.1f}%",
            severity="error",
            message="High packet loss detected (connection unstable).",
            details=details
        )
