"""Platform and OS utility functions for networking, ping, and interface queries."""

import os
import platform
import re
import socket
import subprocess
import time
from typing import Dict, Any, List, Optional, Tuple


def get_os_name() -> str:
    """Return friendly OS description (e.g., Windows 11, Ubuntu 22.04, macOS Sonoma)."""
    system = platform.system()
    release = platform.release()
    if system == "Windows":
        # Check for Windows 11 detection (build >= 22000)
        try:
            ver = sys_platform_version = platform.version()
            build = int(ver.split(".")[2]) if len(ver.split(".")) > 2 else 0
            if build >= 22000 and release == "10":
                return "Windows 11"
        except Exception:
            pass
        return f"Windows {release}"
    elif system == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"
    elif system == "Linux":
        try:
            import distro
            return distro.name(pretty=True)
        except Exception:
            return f"Linux {release}"
    return f"{system} {release}"


def get_hostname() -> str:
    """Return local device hostname."""
    return socket.gethostname()


def is_valid_ipv4(ip: str) -> bool:
    """Validate IPv4 address format."""
    if not ip or not isinstance(ip, str):
        return False
    parts = ip.strip().split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit() or not (0 <= int(p) <= 255):
            return False
    return True


def is_apipa_ip(ip: str) -> bool:
    """Check if address is an APIPA address (169.254.x.x)."""
    if not is_valid_ipv4(ip):
        return False
    parts = ip.split(".")
    return parts[0] == "169" and parts[1] == "254"


def parse_ping_output(output: str, system: str) -> Dict[str, Any]:
    """Parse output from system ping command across Windows, Linux, and macOS."""
    result = {
        "success": False,
        "sent": 0,
        "received": 0,
        "lost": 0,
        "loss_percent": 100.0,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "raw": output
    }

    if not output:
        return result

    # 1. Parse packet transmission statistics
    # Windows format: Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)
    win_match = re.search(
        r"Packets:\s*Sent\s*=\s*(\d+),\s*Received\s*=\s*(\d+),\s*Lost\s*=\s*(\d+)\s*\(([\d\.]+)%\s*loss\)",
        output, re.IGNORECASE
    )
    if win_match:
        result["sent"] = int(win_match.group(1))
        result["received"] = int(win_match.group(2))
        result["lost"] = int(win_match.group(3))
        result["loss_percent"] = float(win_match.group(4))
    else:
        # Unix/macOS format: 4 packets transmitted, 4 received, 0% packet loss
        unix_match = re.search(
            r"(\d+)\s+(?:packets\s+)?transmitted,\s+(\d+)\s+(?:packets\s+)?received,\s+([\d\.]+)%\s*packet\s*loss",
            output, re.IGNORECASE
        )
        if unix_match:
            result["sent"] = int(unix_match.group(1))
            result["received"] = int(unix_match.group(2))
            result["lost"] = result["sent"] - result["received"]
            result["loss_percent"] = float(unix_match.group(3))

    # 2. Parse Round-Trip Times (RTT)
    # Windows: Minimum = 1ms, Maximum = 2ms, Average = 1ms
    win_rtt = re.search(
        r"Minimum\s*=\s*(\d+)ms,\s*Maximum\s*=\s*(\d+)ms,\s*Average\s*=\s*(\d+)ms",
        output, re.IGNORECASE
    )
    if win_rtt:
        result["min_ms"] = float(win_rtt.group(1))
        result["max_ms"] = float(win_rtt.group(2))
        result["avg_ms"] = float(win_rtt.group(3))
    else:
        # Check for single ping individual reply e.g. time=4ms or time<1ms
        single_times = re.findall(r"time(?:=|<)\s*(\d+(?:\.\d+)?)ms", output, re.IGNORECASE)
        if single_times:
            times = [float(t) for t in single_times]
            result["min_ms"] = round(min(times), 2)
            result["max_ms"] = round(max(times), 2)
            result["avg_ms"] = round(sum(times) / len(times), 2)
        else:
            # Unix/macOS: rtt min/avg/max/mdev = 12.1/14.5/18.2/1.5 ms
            unix_rtt = re.search(
                r"(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*([\d\.]+)/([\d\.]+)/([\d\.]+)",
                output, re.IGNORECASE
            )
            if unix_rtt:
                result["min_ms"] = float(unix_rtt.group(1))
                result["avg_ms"] = float(unix_rtt.group(2))
                result["max_ms"] = float(unix_rtt.group(3))

    if result["received"] > 0:
        result["success"] = True
        if result["avg_ms"] is None and result["min_ms"] is not None:
            result["avg_ms"] = result["min_ms"]
        elif result["avg_ms"] is None:
            result["avg_ms"] = 1.0  # default minimum if response arrived

    return result


def ping_host(host: str, count: int = 4, timeout_sec: float = 2.0) -> Dict[str, Any]:
    """Execute ICMP ping with platform-appropriate arguments."""
    system = platform.system()
    cmd: List[str] = []

    if system == "Windows":
        timeout_ms = int(timeout_sec * 1000)
        cmd = ["ping", "-n", str(count), "-w", str(timeout_ms), host]
    elif system == "Darwin":
        timeout_ms = int(timeout_sec * 1000)
        cmd = ["ping", "-c", str(count), "-W", str(timeout_ms), host]
    else:  # Linux and other Unix
        cmd = ["ping", "-c", str(count), "-W", str(int(timeout_sec)), host]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=(count * timeout_sec) + 4.0,
            check=False
        )
        return parse_ping_output(proc.stdout, system)
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "sent": count,
            "received": 0,
            "lost": count,
            "loss_percent": 100.0,
            "min_ms": None,
            "avg_ms": None,
            "max_ms": None,
            "raw": "Ping command timed out."
        }
    except Exception as e:
        return {
            "success": False,
            "sent": count,
            "received": 0,
            "lost": count,
            "loss_percent": 100.0,
            "min_ms": None,
            "avg_ms": None,
            "max_ms": None,
            "raw": f"Error running ping: {str(e)}"
        }


def tcp_ping(host: str, port: int = 53, timeout_sec: float = 2.0) -> Dict[str, Any]:
    """
    TCP Handshake ping for environments where ICMP is blocked.
    Connects to target host and measures round-trip handshake time.
    """
    start_time = time.perf_counter()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        sock.connect((host, port))
        sock.close()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "success": True,
            "latency_ms": round(elapsed_ms, 2),
            "port": port,
            "method": "tcp"
        }
    except Exception as e:
        return {
            "success": False,
            "latency_ms": None,
            "port": port,
            "error": str(e),
            "method": "tcp"
        }
