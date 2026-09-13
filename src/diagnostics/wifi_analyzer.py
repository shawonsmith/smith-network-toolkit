"""Advanced Wi-Fi Signal, Channel, Frequency, and Wireless Protocol Analyzer."""

import platform
import re
import subprocess
from typing import Dict, Any, Optional
import psutil

from src.utils.logger import log_event


def get_wifi_generation(radio_type: str) -> str:
    """Map 802.11 radio protocol to standard consumer Wi-Fi generation name."""
    radio_lower = radio_type.lower()
    if "802.11be" in radio_lower:
        return "Wi-Fi 7 (802.11be)"
    elif "802.11ax" in radio_lower:
        return "Wi-Fi 6 / 6E (802.11ax)"
    elif "802.11ac" in radio_lower:
        return "Wi-Fi 5 (802.11ac)"
    elif "802.11n" in radio_lower:
        return "Wi-Fi 4 (802.11n)"
    elif "802.11g" in radio_lower:
        return "Legacy 802.11g"
    elif "802.11b" in radio_lower:
        return "Legacy 802.11b"
    elif "802.11a" in radio_lower:
        return "Legacy 802.11a"
    return radio_type or "Unknown"


def determine_wifi_band(channel: Optional[int]) -> str:
    """Determine wireless frequency band (2.4 GHz vs 5 GHz vs 6 GHz) based on channel number."""
    if not channel:
        return "Unknown"
    if 1 <= channel <= 14:
        return "2.4 GHz"
    elif 32 <= channel <= 177:
        return "5.0 GHz"
    elif channel >= 180:
        return "6.0 GHz"
    return "Unknown"


def estimate_rssi_dbm(signal_pct: Optional[int]) -> Optional[int]:
    """Estimate received signal strength indicator (RSSI in dBm) from percentage (0-100%)."""
    if signal_pct is None:
        return None
    # Common Windows conversion approximation: dBm = (quality / 2) - 100
    # e.g., 100% -> -50 dBm (Excellent), 60% -> -70 dBm (Good), 20% -> -90 dBm (Poor)
    return round((signal_pct / 2.0) - 100.0)


def analyze_wifi_status() -> Dict[str, Any]:
    """
    Perform deep inspection of wireless adapter, connection health, and RF environment.
    Falls back gracefully to Ethernet/Wired status if Wi-Fi is inactive or not present.
    """
    system = platform.system()
    res: Dict[str, Any] = {
        "is_wifi": False,
        "state": "Disconnected / Inactive",
        "interface_name": "Unknown",
        "ssid": None,
        "bssid": None,
        "signal_pct": None,
        "rssi_dbm": None,
        "channel": None,
        "band": None,
        "radio_type": None,
        "wifi_generation": None,
        "auth": None,
        "cipher": None,
        "rx_rate_mbps": None,
        "tx_rate_mbps": None,
        "advice": [],
        "raw_status": ""
    }

    if system != "Windows":
        res["raw_status"] = f"Advanced Wi-Fi parsing not supported on {system}"
        return res

    try:
        cmd = "netsh wlan show interfaces"
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        res["raw_status"] = out

        if proc.returncode != 0 or "There is no wireless interface" in out or "wlansvc" in out:
            # Check wired Ethernet adapters instead
            stats = psutil.net_if_stats()
            for iface, s in stats.items():
                if s.isup and "loopback" not in iface.lower():
                    res["interface_name"] = iface
                    res["state"] = "Connected via Wired Ethernet"
                    res["rx_rate_mbps"] = s.speed if s.speed > 0 else None
                    res["tx_rate_mbps"] = s.speed if s.speed > 0 else None
                    res["advice"].append("Active connection is wired Ethernet, providing maximum stability and zero RF interference.")
                    return res
            res["state"] = "No active wireless or wired network interface found."
            return res

        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip()

                if "name" == k:
                    res["interface_name"] = v
                elif "state" == k:
                    res["state"] = v
                    if v.lower() == "connected":
                        res["is_wifi"] = True
                elif "ssid" == k and "bssid" not in k:
                    res["ssid"] = v
                elif "bssid" == k:
                    res["bssid"] = v
                elif "radio type" in k:
                    res["radio_type"] = v
                    res["wifi_generation"] = get_wifi_generation(v)
                elif "authentication" in k:
                    res["auth"] = v
                elif "cipher" in k:
                    res["cipher"] = v
                elif "channel" in k:
                    try:
                        res["channel"] = int(v)
                        res["band"] = determine_wifi_band(res["channel"])
                    except ValueError:
                        pass
                elif "receive rate" in k:
                    m = re.search(r"(\d+(?:\.\d+)?)", v)
                    if m:
                        res["rx_rate_mbps"] = float(m.group(1))
                elif "transmit rate" in k:
                    m = re.search(r"(\d+(?:\.\d+)?)", v)
                    if m:
                        res["tx_rate_mbps"] = float(m.group(1))
                elif "signal" in k:
                    m = re.search(r"(\d+)%", v)
                    if m:
                        res["signal_pct"] = int(m.group(1))
                        res["rssi_dbm"] = estimate_rssi_dbm(res["signal_pct"])

    except Exception as e:
        log_event(f"Error querying netsh wlan interfaces: {e}", "warning")
        res["raw_status"] = str(e)

    # If connected to Wi-Fi, generate intelligent actionable advice
    if res["is_wifi"]:
        sig = res.get("signal_pct")
        band = res.get("band")

        if sig is not None:
            if sig >= 80:
                res["advice"].append(f"Excellent wireless signal ({sig}% / ~{res.get('rssi_dbm')} dBm). Ideal for high throughput.")
            elif sig >= 60:
                res["advice"].append(f"Good wireless signal ({sig}% / ~{res.get('rssi_dbm')} dBm). Sufficient for HD streaming and calls.")
            elif sig >= 40:
                res["advice"].append(f"Fair wireless signal ({sig}% / ~{res.get('rssi_dbm')} dBm). Consider moving closer to the AP to avoid micro-drops.")
            else:
                res["advice"].append(f"Weak wireless signal ({sig}% / ~{res.get('rssi_dbm')} dBm). High risk of packet loss and bufferbloat.")

        if band == "2.4 GHz":
            res["advice"].append("Connected to 2.4 GHz band. If your access point broadcasts a 5 GHz or 6 GHz network, connect to it for lower latency and less channel congestion.")
        elif band in ("5.0 GHz", "6.0 GHz"):
            res["advice"].append(f"Connected to high-bandwidth {band} band.")

        if res.get("auth") and "wpa3" not in res.get("auth", "").lower() and "wpa2" in res.get("auth", "").lower():
            res["advice"].append("Security: WPA2-Personal active. WPA3 is recommended for enhanced cryptographic security if supported by your router.")

    return res
