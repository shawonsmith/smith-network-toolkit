"""Common port connectivity and firewall reachability tester."""

import socket
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from src.utils.logger import log_event

STANDARD_PORTS = [
    {"port": 80, "service": "HTTP (Web)", "category": "Web"},
    {"port": 443, "service": "HTTPS (Secure Web)", "category": "Web"},
    {"port": 53, "service": "DNS (Name Resolution)", "category": "Infrastructure"},
    {"port": 22, "service": "SSH (Secure Shell)", "category": "Remote Access"},
    {"port": 3389, "service": "RDP (Remote Desktop)", "category": "Remote Access"},
    {"port": 587, "service": "SMTP Submission (Email)", "category": "Mail"},
    {"port": 993, "service": "IMAP SSL (Email)", "category": "Mail"},
    {"port": 8080, "service": "HTTP Alternate (Proxy/App)", "category": "Web"},
]


def probe_port(target_host: str, port_info: Dict[str, Any], timeout_sec: float = 1.5) -> Dict[str, Any]:
    """Test TCP socket connection to a specific port on target."""
    port = port_info["port"]
    start = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)

    try:
        sock.connect((target_host, port))
        sock.close()
        elapsed = (time.perf_counter() - start) * 1000.0
        return {
            "port": port,
            "service": port_info["service"],
            "category": port_info["category"],
            "status": "OPEN",
            "latency_ms": round(elapsed, 1),
            "message": "Connection established"
        }
    except socket.timeout:
        return {
            "port": port,
            "service": port_info["service"],
            "category": port_info["category"],
            "status": "FILTERED",
            "latency_ms": None,
            "message": "Filtered (Firewall / Timeout)"
        }
    except ConnectionRefusedError:
        return {
            "port": port,
            "service": port_info["service"],
            "category": port_info["category"],
            "status": "CLOSED",
            "latency_ms": None,
            "message": "Host replied (Port closed / No listener)"
        }
    except Exception as e:
        return {
            "port": port,
            "service": port_info["service"],
            "category": port_info["category"],
            "status": "FAILED",
            "latency_ms": None,
            "message": str(e)
        }


def scan_ports(target_host: str = "1.1.1.1", ports: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run concurrent port sweep on a target host."""
    port_list = ports or STANDARD_PORTS
    log_event(f"Starting port scan on {target_host} ({len(port_list)} ports)...")

    results = []
    with ThreadPoolExecutor(max_workers=min(len(port_list), 10)) as executor:
        futures = [executor.submit(probe_port, target_host, p) for p in port_list]
        for f in futures:
            results.append(f.result())

    # Sort results by port number
    results.sort(key=lambda x: x["port"])

    open_count = sum(1 for r in results if r["status"] == "OPEN")
    filtered_count = sum(1 for r in results if r["status"] == "FILTERED")
    closed_count = sum(1 for r in results if r["status"] == "CLOSED")

    log_event(f"Port scan completed on {target_host}: {open_count} open, {filtered_count} filtered, {closed_count} closed.")
    return {
        "target": target_host,
        "results": results,
        "open_count": open_count,
        "filtered_count": filtered_count,
        "closed_count": closed_count
    }
