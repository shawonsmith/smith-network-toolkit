"""VoIP, Video Call (Zoom/Teams), and Gaming Stability / Jitter Analyzer (RFC 3550-style estimation)."""

import math
import statistics
import time
from typing import Dict, Any, List, Optional

from src.utils.logger import log_event
from src.utils.platform_utils import ping_host, tcp_ping


def calculate_rfc3550_jitter(latencies: List[float]) -> float:
    """
    Calculate RFC 3550-style interarrival jitter estimation.
    Formula: J(i) = J(i-1) + (|D(i-1, i)| - J(i-1)) / 16
    Note: Computed over sequential active ICMP/TCP round-trip time samples rather than
    in-band passive RTP packet headers.
    """
    if len(latencies) < 2:
        return 0.0

    jitter = 0.0
    for i in range(1, len(latencies)):
        d = abs(latencies[i] - latencies[i - 1])
        jitter += (d - jitter) / 16.0

    return round(jitter, 2)


def estimate_mos_score(avg_latency: float, jitter: float, packet_loss_pct: float) -> float:
    """
    Estimate Mean Opinion Score (MOS) based on ITU-T G.107 E-model approximation.
    Estimates perceived conversational call quality based on synthetic delay and
    packet drop impairments. Score ranges from 1.0 (Unusable) to 4.5 (Crystal Clear HD).
    """
    # Effective latency including buffer jitter compensation
    effective_latency = avg_latency + (jitter * 2.0)

    # Delay impairment factor (Id)
    if effective_latency < 160:
        delay_impairment = effective_latency / 40.0
    else:
        delay_impairment = (effective_latency - 120) / 10.0

    # Equipment/Packet loss impairment factor (Ie-eff)
    loss_impairment = packet_loss_pct * 2.5

    r_factor = 94.0 - delay_impairment - loss_impairment
    r_factor = max(0.0, min(100.0, r_factor))

    # Convert R-factor to MOS (1.0 - 4.5)
    if r_factor <= 0:
        mos = 1.0
    elif r_factor >= 100:
        mos = 4.5
    else:
        mos = 1.0 + (0.035 * r_factor) + (r_factor * (r_factor - 60.0) * (100.0 - r_factor) * 0.000007)
        mos = max(1.0, min(4.5, mos))

    return round(mos, 2)


def run_jitter_stability_test(
    target_host: str = "8.8.8.8",
    packet_count: int = 20,
    interval_sec: float = 0.2,
    progress_callback=None
) -> Dict[str, Any]:
    """
    Execute an empirical jitter and packet-drop stability test.
    Returns latency distribution, RFC 3550 jitter, MOS score, and suitability for VoIP/Gaming.
    """
    log_event(f"Starting stability & jitter test targeting {target_host} ({packet_count} packets)...")

    latencies: List[float] = []
    lost_count = 0

    for i in range(packet_count):
        # Prefer ICMP, fallback to TCP
        p_res = ping_host(target_host, count=1, timeout_sec=1.5)
        lat = p_res["avg_ms"] if p_res.get("success") else None
        if lat is None:
            t_res = tcp_ping(target_host, port=53, timeout_sec=1.5)
            lat = t_res["latency_ms"] if t_res.get("success") else None

        if lat is not None:
            latencies.append(round(lat, 2))
        else:
            lost_count += 1

        if progress_callback:
            progress_callback(i + 1, packet_count, lat)

        if i < packet_count - 1 and interval_sec > 0:
            time.sleep(interval_sec)

    received_count = len(latencies)
    loss_pct = round((lost_count / packet_count) * 100.0, 1) if packet_count > 0 else 0.0

    if latencies:
        min_lat = round(min(latencies), 2)
        max_lat = round(max(latencies), 2)
        avg_lat = round(statistics.mean(latencies), 2)
        med_lat = round(statistics.median(latencies), 2)
        std_dev = round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0.0
        rfc_jitter = calculate_rfc3550_jitter(latencies)
    else:
        min_lat = max_lat = avg_lat = med_lat = std_dev = rfc_jitter = 0.0

    mos = estimate_mos_score(avg_lat, rfc_jitter, loss_pct)

    # Determine Quality Ratings
    if loss_pct == 0.0 and rfc_jitter < 5.0 and avg_lat < 50.0:
        grade = "EXCELLENT"
        zoom_status = "Flawless HD Audio & Video (Zero distortion)"
        gaming_status = "Competitive Esports Grade (No noticeable lag)"
    elif loss_pct <= 1.0 and rfc_jitter < 15.0 and avg_lat < 100.0:
        grade = "GOOD"
        zoom_status = "High Quality (Smooth business video calls)"
        gaming_status = "Smooth Gameplay (Minor casual latency)"
    elif loss_pct <= 3.0 and rfc_jitter < 30.0:
        grade = "FAIR"
        zoom_status = "Fair (Occasional robotic voice or stutter)"
        gaming_status = "Noticeable Jitter (Occasional rubberbanding)"
    else:
        grade = "POOR"
        zoom_status = "Poor (Frequent audio cutouts and video freezing)"
        gaming_status = "High Packet Loss & Lag (Severe gaming stutter)"

    advice = []
    if loss_pct > 0:
        advice.append(f"Packet loss detected ({loss_pct}%). Check Wi-Fi interference, router bufferbloat, or ISP line.")
    if rfc_jitter > 15.0:
        advice.append(f"High jitter ({rfc_jitter} ms). High variance in ping indicates channel congestion or background downloads.")
    if avg_lat > 100.0:
        advice.append(f"High base latency ({avg_lat} ms). Consider switching DNS or connecting to a closer ISP gateway.")
    if not advice:
        advice.append("Connection shows exceptional timing consistency and zero packet drop.")

    return {
        "target": target_host,
        "packets_sent": packet_count,
        "packets_received": received_count,
        "packets_lost": lost_count,
        "packet_loss_pct": loss_pct,
        "min_ms": min_lat,
        "max_ms": max_lat,
        "avg_ms": avg_lat,
        "median_ms": med_lat,
        "std_dev_ms": std_dev,
        "rfc3550_jitter_ms": rfc_jitter,
        "mos_score": mos,
        "grade": grade,
        "zoom_status": zoom_status,
        "gaming_status": gaming_status,
        "latencies": latencies,
        "advice": advice
    }
