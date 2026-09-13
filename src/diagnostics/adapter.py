"""Network adapter and local host configuration detection."""

import os
import platform
import re
import socket
import subprocess
from typing import Dict, Any, List, Optional
import psutil

from src.models.result import AdapterInfo
from src.utils.platform_utils import (
    get_hostname,
    get_os_name,
    is_valid_ipv4,
    is_apipa_ip
)
from src.utils.logger import log_event


def get_windows_ipconfig_data() -> Dict[str, Dict[str, Any]]:
    """Parse ipconfig /all on Windows to extract adapter properties."""
    adapters: Dict[str, Dict[str, Any]] = {}
    try:
        out = subprocess.check_output("ipconfig /all", text=True, errors="ignore", shell=True)
    except Exception as e:
        log_event(f"Error executing ipconfig: {e}", "warning")
        return adapters

    current_adapter: Optional[str] = None
    for line in out.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue

        if not line.startswith(" ") and ":" in line:
            # Header line like 'Ethernet adapter Ethernet:'
            current_adapter = line.split(":")[0].strip()
            # Clean header name
            clean_name = current_adapter
            for prefix in ["Ethernet adapter ", "Wireless LAN adapter ", "Adapter "]:
                if clean_name.startswith(prefix):
                    clean_name = clean_name[len(prefix):]
            adapters[clean_name] = {
                "raw_name": current_adapter,
                "mac": None,
                "ipv4": None,
                "mask": None,
                "gateway": None,
                "dns": [],
            }
        elif current_adapter:
            clean_name = current_adapter
            for prefix in ["Ethernet adapter ", "Wireless LAN adapter ", "Adapter "]:
                if clean_name.startswith(prefix):
                    clean_name = clean_name[len(prefix):]

            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip().replace(".", "").strip().lower()
                val = parts[1].strip()

                if "physical address" in key:
                    adapters[clean_name]["mac"] = val
                elif "ipv4 address" in key or "ip address" in key:
                    val = re.sub(r"\(.*?\)", "", val).strip()
                    adapters[clean_name]["ipv4"] = val
                elif "subnet mask" in key:
                    adapters[clean_name]["mask"] = val
                elif "default gateway" in key and is_valid_ipv4(val):
                    adapters[clean_name]["gateway"] = val
                elif "dns servers" in key and is_valid_ipv4(val):
                    if val not in adapters[clean_name]["dns"]:
                        adapters[clean_name]["dns"].append(val)
            elif line.startswith(" " * 20) and is_valid_ipv4(trimmed):
                if trimmed not in adapters[clean_name]["dns"]:
                    adapters[clean_name]["dns"].append(trimmed)

    return adapters


def get_unix_gateway() -> Optional[str]:
    """Retrieve default gateway on Linux or macOS."""
    system = platform.system()
    try:
        if system == "Darwin":
            cmd = ["route", "-n", "get", "default"]
            out = subprocess.check_output(cmd, text=True, errors="ignore")
            for line in out.splitlines():
                if "gateway:" in line:
                    return line.split(":", 1)[1].strip()
        else:
            # Linux: check /proc/net/route or ip route
            if os.path.exists("/proc/net/route"):
                with open("/proc/net/route", "r") as f:
                    for line in f.readlines()[1:]:
                        fields = line.strip().split()
                        if len(fields) >= 3 and fields[1] == "00000000":
                            gw_hex = fields[2]
                            # Convert hex to IP
                            octets = [str(int(gw_hex[i:i+2], 16)) for i in (6, 4, 2, 0)]
                            return ".".join(octets)
            # Fallback to ip route
            cmd = ["ip", "route", "show", "default"]
            out = subprocess.check_output(cmd, text=True, errors="ignore")
            m = re.search(r"default via ([\d\.]+)", out)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def get_unix_dns_servers() -> List[str]:
    """Retrieve configured DNS servers on Linux or macOS."""
    dns_servers = []
    try:
        if os.path.exists("/etc/resolv.conf"):
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    if line.strip().startswith("nameserver"):
                        parts = line.strip().split()
                        if len(parts) >= 2 and is_valid_ipv4(parts[1]):
                            dns_servers.append(parts[1])
    except Exception:
        pass
    return dns_servers


def detect_adapter_info() -> AdapterInfo:
    """Detect and return information about primary active network adapter."""
    hostname = get_hostname()
    os_name = get_os_name()
    log_event(f"Detecting network adapter on {os_name} (Host: {hostname})")

    info = AdapterInfo(
        hostname=hostname,
        os_name=os_name,
        adapter_name="Unknown",
        mac_address="Unknown",
        ipv4_address="Unknown",
        subnet_mask="Unknown",
        default_gateway="Unknown",
        dns_servers=[],
        is_apipa=False,
        is_connected=False
    )

    system = platform.system()
    win_data = get_windows_ipconfig_data() if system == "Windows" else {}

    # Query all network interfaces via psutil
    net_addrs = psutil.net_if_addrs()
    net_stats = psutil.net_if_stats()

    best_candidate: Optional[str] = None
    candidate_ipv4: Optional[str] = None
    candidate_mask: Optional[str] = None
    candidate_mac: Optional[str] = None

    # Priority 1: An interface that is UP, not loopback, has valid non-APIPA IPv4
    for iface_name, addrs in net_addrs.items():
        if "loopback" in iface_name.lower():
            continue

        stats = net_stats.get(iface_name)
        is_up = stats.isup if stats else False

        current_ipv4 = None
        current_mask = None
        current_mac = None

        for addr in addrs:
            # IPv4 address
            if addr.family == socket.AF_INET:
                current_ipv4 = addr.address
                current_mask = addr.netmask
            # MAC Address: AF_LINK on Unix or -1 on Windows
            elif addr.family == psutil.AF_LINK or addr.family == -1:
                current_mac = addr.address

        if current_ipv4 and is_valid_ipv4(current_ipv4):
            # Check if this interface has a default gateway in win_data
            has_gateway = False
            if iface_name in win_data and win_data[iface_name].get("gateway"):
                has_gateway = True

            # If it's UP and not APIPA, choose it
            if is_up and not is_apipa_ip(current_ipv4):
                best_candidate = iface_name
                candidate_ipv4 = current_ipv4
                candidate_mask = current_mask
                candidate_mac = current_mac
                if has_gateway:
                    break  # Found best active adapter with gateway
            elif not best_candidate:
                best_candidate = iface_name
                candidate_ipv4 = current_ipv4
                candidate_mask = current_mask
                candidate_mac = current_mac

    if best_candidate:
        info.adapter_name = best_candidate
        info.ipv4_address = candidate_ipv4 or "Unknown"
        info.subnet_mask = candidate_mask or "Unknown"
        info.mac_address = candidate_mac or "Unknown"
        info.is_connected = True
        info.is_apipa = is_apipa_ip(info.ipv4_address)

        # Pull gateway and DNS
        if system == "Windows":
            # Match with win_data
            data = win_data.get(best_candidate)
            if not data:
                # Try partial match
                for name, d in win_data.items():
                    if name in best_candidate or best_candidate in name:
                        data = d
                        break
            if data:
                info.default_gateway = data.get("gateway") or "Unknown"
                info.dns_servers = data.get("dns") or []
                if not info.mac_address or info.mac_address == "Unknown":
                    info.mac_address = data.get("mac") or "Unknown"
                if not info.subnet_mask or info.subnet_mask == "Unknown":
                    info.subnet_mask = data.get("mask") or "Unknown"
        else:
            info.default_gateway = get_unix_gateway() or "Unknown"
            info.dns_servers = get_unix_dns_servers()

    log_event(f"Adapter detected: {info.adapter_name} | IPv4: {info.ipv4_address} | Gateway: {info.default_gateway}")
    return info
