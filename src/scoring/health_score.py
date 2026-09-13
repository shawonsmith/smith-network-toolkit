"""Network Health Scoring Engine (100-point rubric)."""

from typing import List, Dict, Any
from src.models.result import (
    DiagnosticResult,
    AdapterInfo,
    HealthScoreResult
)
from src.utils.logger import log_event


def calculate_health_score(
    adapter_info: AdapterInfo,
    results: List[DiagnosticResult]
) -> HealthScoreResult:
    """
    Calculate 100-point weighted network health score based on empirical checks.
    Public IP availability is purely informational and does not affect the score.
    """
    results_map: Dict[str, DiagnosticResult] = {r.name: r for r in results}

    breakdown: Dict[str, int] = {}
    max_breakdown: Dict[str, int] = {
        "valid_ip": 15,
        "gateway_detected": 10,
        "gateway_reachable": 15,
        "internet_reachable": 20,
        "dns_working": 15,
        "packet_loss": 10,
        "latency": 10,
        "adapter_healthy": 5
    }

    # 1. Valid IP Configuration (15 pts)
    if adapter_info.ipv4_address and adapter_info.ipv4_address != "Unknown" and not adapter_info.is_apipa:
        breakdown["valid_ip"] = 15
    else:
        breakdown["valid_ip"] = 0

    # 2. Gateway Detected (10 pts)
    if adapter_info.default_gateway and adapter_info.default_gateway != "Unknown":
        breakdown["gateway_detected"] = 10
    else:
        breakdown["gateway_detected"] = 0

    # 3. Gateway Reachable (15 pts) - Local LAN evaluation
    gw_res = results_map.get("Gateway")
    if gw_res and gw_res.status == "PASS":
        gw_lat = gw_res.details.get("latency_ms", 1.0)
        if gw_lat is not None and gw_lat <= 5.0:
            breakdown["gateway_reachable"] = 15
        elif gw_lat is not None and gw_lat <= 15.0:
            breakdown["gateway_reachable"] = 12
        else:
            breakdown["gateway_reachable"] = 8
    else:
        breakdown["gateway_reachable"] = 0

    # 4. Internet Reachable (20 pts)
    internet_res = results_map.get("Internet")
    if internet_res and internet_res.status == "PASS":
        breakdown["internet_reachable"] = 20
    elif internet_res and internet_res.status == "WARN":
        # Direct IP ping works, but HTTPS failed (Limited)
        breakdown["internet_reachable"] = 10
    else:
        breakdown["internet_reachable"] = 0

    # 5. DNS Working (15 pts) - Isolated DNS evaluation
    dns_res = results_map.get("DNS")
    if dns_res:
        if dns_res.status == "PASS":
            avg_ms = dns_res.details.get("avg_ms", 50.0)
            if avg_ms is not None and avg_ms <= 80.0:
                breakdown["dns_working"] = 15
            else:
                breakdown["dns_working"] = 13
        elif dns_res.status == "WARN":
            breakdown["dns_working"] = 8
        else:
            breakdown["dns_working"] = 0
    else:
        breakdown["dns_working"] = 0

    # 6. Packet Loss Acceptable (10 pts)
    loss_res = results_map.get("Packet Loss")
    if loss_res:
        loss_pct = loss_res.details.get("loss_percent", 0.0)
        if loss_pct == 0.0:
            breakdown["packet_loss"] = 10
        elif loss_pct <= 2.0:
            breakdown["packet_loss"] = 9
        elif loss_pct <= 5.0:
            breakdown["packet_loss"] = 5
        else:
            breakdown["packet_loss"] = 0
    else:
        breakdown["packet_loss"] = 0

    # 7. Latency Acceptable (10 pts) - Internet latency evaluation
    lat_res = results_map.get("Latency")
    if lat_res and lat_res.status != "FAIL":
        avg_lat = lat_res.details.get("internet_avg_ms")
        if avg_lat is not None:
            if avg_lat <= 80.0:
                breakdown["latency"] = 10
            elif avg_lat <= 150.0:
                breakdown["latency"] = 8
            elif avg_lat <= 250.0:
                breakdown["latency"] = 5
            else:
                breakdown["latency"] = 2
        else:
            breakdown["latency"] = 5
    else:
        breakdown["latency"] = 0

    # 8. Adapter Healthy (5 pts)
    if adapter_info.is_connected:
        breakdown["adapter_healthy"] = 5
    else:
        breakdown["adapter_healthy"] = 0

    total_score = sum(breakdown.values())
    total_score = max(0, min(100, total_score))

    # Grade classification
    if total_score >= 90:
        grade = "Excellent"
    elif total_score >= 75:
        grade = "Good"
    elif total_score >= 60:
        grade = "Needs Attention"
    else:
        grade = "Poor"

    log_event(f"Health Score calculated: {total_score}/100 ({grade})")
    return HealthScoreResult(
        total_score=total_score,
        grade=grade,
        breakdown=breakdown,
        max_breakdown=max_breakdown
    )
