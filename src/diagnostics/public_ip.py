"""Public IP address detection (informational check)."""

import urllib.request
import re
from typing import Dict, Any
from src.utils.platform_utils import is_valid_ipv4
from src.utils.logger import log_event


PUBLIC_IP_SERVICES = [
    ("api.ipify.org", "https://api.ipify.org"),
    ("ifconfig.me", "https://ifconfig.me/ip"),
    ("icanhazip.com", "https://icanhazip.com")
]


def detect_public_ip(timeout_sec: float = 2.5) -> Dict[str, Any]:
    """
    Detect external public IP address.
    Informational only - failure never penalizes the network health score.
    """
    log_event("Querying public IP from external API providers...")

    for service_name, url in PUBLIC_IP_SERVICES:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "curl/7.68.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                if resp.status == 200:
                    raw_ip = resp.read().decode("utf-8", errors="ignore").strip()
                    # Validate IPv4 format
                    if is_valid_ipv4(raw_ip):
                        log_event(f"Public IP detected: {raw_ip} (via {service_name})")
                        return {
                            "ip": raw_ip,
                            "status": "Detected",
                            "service": service_name
                        }
        except Exception as e:
            continue

    log_event("Public IP lookup unavailable (external API timeout/unreachable)", "warning")
    return {
        "ip": "Unavailable",
        "status": "Unavailable",
        "service": "None"
    }
