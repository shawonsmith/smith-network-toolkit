"""LAN Subnet Device Discovery and IP/MAC Scanner (High Speed Multi-threaded Socket + ARP)."""

import ipaddress
import platform
import re
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Dict, Any, List, Optional

from src.utils.logger import log_event
from src.utils.platform_utils import is_valid_ipv4, ping_host


def parse_arp_table() -> Dict[str, Dict[str, str]]:
    """Parse local system ARP table to extract IP-to-MAC mappings."""
    arp_entries: Dict[str, Dict[str, str]] = {}
    system = platform.system()
    try:
        if system == "Windows":
            out = subprocess.check_output("arp -a", text=True, errors="ignore", shell=True)
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 3:
                    ip = parts[0]
                    mac = parts[1].replace("-", ":").upper()
                    entry_type = parts[2].lower()
                    if (
                        is_valid_ipv4(ip)
                        and ":" in mac
                        and not mac.startswith("FF:FF")
                        and not ip.startswith("224.")
                        and not ip.startswith("239.")
                        and not ip.endswith(".255")
                    ):
                        arp_entries[ip] = {
                            "mac": mac,
                            "type": entry_type
                        }
        else:
            out = subprocess.check_output("arp -an", text=True, errors="ignore")
            for line in out.splitlines():
                m = re.search(r"\(([\d\.]+)\)\s+at\s+([0-9a-fA-F:]{17})", line)
                if m:
                    ip = m.group(1)
                    mac = m.group(2).upper()
                    if not ip.startswith("224.") and not ip.endswith(".255"):
                        arp_entries[ip] = {"mac": mac, "type": "dynamic"}
    except Exception as e:
        log_event(f"Error parsing ARP table: {e}", "warning")

    return arp_entries


def trigger_arp_resolution(ip: str, timeout_sec: float = 0.08) -> bool:
    """
    Attempt rapid non-blocking socket connect to port 80/445.
    Even if connection is refused or filtered, the OS kernel sends an ARP request.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_sec)
            s.connect_ex((ip, 80))
            return True
    except Exception:
        pass
    return False


def resolve_hostname_fast(ip: str, timeout_sec: float = 0.25) -> str:
    """Non-blocking reverse DNS lookup with strict timeout."""
    with ThreadPoolExecutor(max_workers=1) as ex:
        f = ex.submit(socket.gethostbyaddr, ip)
        try:
            res = f.result(timeout=timeout_sec)
            return res[0]
        except (TimeoutError, Exception):
            return "Local Device"


def inspect_device(ip: str, host_ip: str, gateway_ip: str, mac: str) -> Dict[str, Any]:
    """Gather details (latency, hostname, role) for an active IP."""
    if ip == host_ip:
        role = "This Computer"
        lat = 0.1
    elif ip == gateway_ip:
        role = "Default Gateway (Router)"
        p = ping_host(ip, count=1, timeout_sec=0.4)
        lat = p["avg_ms"] if p.get("success") else None
    else:
        role = "Active LAN Device"
        p = ping_host(ip, count=1, timeout_sec=0.4)
        lat = p["avg_ms"] if p.get("success") else None

    hostname = resolve_hostname_fast(ip, timeout_sec=0.2)
    return {
        "ip": ip,
        "mac": mac,
        "hostname": hostname,
        "role": role,
        "latency_ms": lat
    }


def scan_local_network(
    subnet_cidr: Optional[str] = None,
    max_workers: int = 64,
    progress_callback=None
) -> Dict[str, Any]:
    """
    Perform a high-speed multi-threaded scan of the local subnet in seconds.
    Uses socket ARP triggers followed by ARP table inspection.
    """
    from src.diagnostics.adapter import detect_adapter_info

    adapter = detect_adapter_info()
    host_ip = adapter.ipv4_address
    gateway_ip = adapter.default_gateway

    target_network = None
    if subnet_cidr:
        try:
            target_network = ipaddress.IPv4Network(subnet_cidr, strict=False)
        except Exception:
            pass

    if not target_network:
        if is_valid_ipv4(host_ip) and not host_ip.startswith("127.") and not host_ip.startswith("169.254"):
            octets = host_ip.split(".")
            base_cidr = f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
            target_network = ipaddress.IPv4Network(base_cidr, strict=False)
        elif is_valid_ipv4(gateway_ip):
            octets = gateway_ip.split(".")
            base_cidr = f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
            target_network = ipaddress.IPv4Network(base_cidr, strict=False)
        else:
            target_network = ipaddress.IPv4Network("192.168.1.0/24", strict=False)

    log_event(f"Triggering parallel ARP probes across {target_network}...")
    all_hosts = [str(ip) for ip in target_network.hosts()]
    total_count = len(all_hosts)
    completed_count = 0

    # Rapid parallel socket triggers to populate ARP table
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(trigger_arp_resolution, ip) for ip in all_hosts]
        for f in as_completed(futures):
            completed_count += 1
            if progress_callback:
                progress_callback(completed_count, total_count)

    # Read updated ARP cache table
    arp_entries = parse_arp_table()

    # Collect all alive IP addresses
    alive_ips = set()
    for ip in arp_entries.keys():
        try:
            if ipaddress.IPv4Address(ip) in target_network:
                alive_ips.add(ip)
        except Exception:
            pass

    # Ensure host PC and gateway are included
    if is_valid_ipv4(host_ip):
        try:
            if ipaddress.IPv4Address(host_ip) in target_network:
                alive_ips.add(host_ip)
        except Exception:
            pass

    if is_valid_ipv4(gateway_ip):
        try:
            if ipaddress.IPv4Address(gateway_ip) in target_network:
                alive_ips.add(gateway_ip)
        except Exception:
            pass

    sorted_ips = sorted(alive_ips, key=lambda x: [int(p) for p in x.split(".")])

    # Parallel detail gathering for active devices
    devices: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=10) as detail_executor:
        future_map = {}
        for ip in sorted_ips:
            mac = "Unknown"
            if ip == host_ip:
                mac = adapter.mac_address or "Local Host"
            elif ip in arp_entries:
                mac = arp_entries[ip]["mac"]
            future_map[detail_executor.submit(inspect_device, ip, host_ip, gateway_ip, mac)] = ip

        for f in as_completed(future_map):
            devices.append(f.result())

    # Sort again by IP
    devices.sort(key=lambda x: [int(p) for p in x["ip"].split(".")])

    return {
        "subnet": str(target_network),
        "total_hosts_scanned": total_count,
        "active_devices_count": len(devices),
        "host_ip": host_ip,
        "gateway_ip": gateway_ip,
        "devices": devices
    }
