"""Lightweight internet download speed test module using reliable CDN streams."""

import time
import requests
from typing import Dict, Any, Optional
from src.utils.logger import log_event

SPEED_TEST_ENDPOINTS = [
    ("Cloudflare CDN", "https://speed.cloudflare.com/__down?bytes=10000000"),
    ("Google Public CDN", "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"),
]


def test_download_speed(progress_callback=None) -> Dict[str, Any]:
    """Measure real-world download throughput using reliable global CDN endpoints."""
    log_event("Starting download speed test...")

    best_result = None

    for provider_name, url in SPEED_TEST_ENDPOINTS:
        try:
            if progress_callback:
                progress_callback(f"Testing download throughput via {provider_name}...")

            start_time = time.perf_counter()
            resp = requests.get(url, stream=True, timeout=12.0)
            if resp.status_code != 200:
                continue

            total_bytes = 0
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if chunk:
                    total_bytes += len(chunk)

            elapsed_sec = max(time.perf_counter() - start_time, 0.001)
            if total_bytes < 1000:
                continue

            mbps = (total_bytes * 8.0) / (elapsed_sec * 1_000_000.0)
            size_mb = round(total_bytes / (1024.0 * 1024.0), 2)

            if mbps >= 50.0:
                grade = "Excellent (High Speed Fiber / Broadband)"
            elif mbps >= 25.0:
                grade = "Good (Fast HD Streaming / Multi-device)"
            elif mbps >= 10.0:
                grade = "Moderate (Standard Web & Video Calls)"
            else:
                grade = "Slow (Basic Browsing)"

            best_result = {
                "success": True,
                "provider": provider_name,
                "speed_mbps": round(mbps, 2),
                "data_mb": size_mb,
                "duration_sec": round(elapsed_sec, 2),
                "rating": grade
            }
            log_event(f"Speed test completed: {mbps:.2f} Mbps via {provider_name}")
            break

        except Exception as e:
            log_event(f"Speed test error on {provider_name}: {e}", "warning")
            continue

    if not best_result:
        return {
            "success": False,
            "provider": "None",
            "speed_mbps": 0.0,
            "data_mb": 0.0,
            "duration_sec": 0.0,
            "rating": "Failed to connect to speed test servers",
            "error": "Timeout or connection reset"
        }

    return best_result
