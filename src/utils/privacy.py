"""Privacy masking engine for Smith Network Diagnostic Toolkit."""

import re
from copy import deepcopy
from typing import Optional, Any
from src.models.result import ScanReport, AdapterInfo, DiagnosticResult


# Match IPv4 addresses: 4 octets separated by dots
IPV4_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Match MAC addresses (colon or hyphen separated)
MAC_REGEX = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")


def is_private_ip(ip: str) -> bool:
    """Check if an IPv4 address belongs to private/local ranges."""
    if not ip or ip in ("Unknown", "None", ""):
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        first, second = int(parts[0]), int(parts[1])
        if first == 10:
            return True
        if first == 172 and 16 <= second <= 31:
            return True
        if first == 192 and second == 168:
            return True
        if first == 127:
            return True
        if first == 169 and second == 254:
            return True
    except ValueError:
        return False
    return False


def mask_ipv4(ip: Optional[str]) -> str:
    """
    Mask an IPv4 address.
    Private IP: 192.168.0.105 -> 192.168.0.xxx
    Public IP: 103.14.25.68 -> 103.xxx.xxx.68
    """
    if not ip or ip in ("Unknown", "None", "N/A", ""):
        return ip or "Unknown"
    parts = ip.split(".")
    if len(parts) != 4:
        return ip

    if is_private_ip(ip):
        return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
    else:
        return f"{parts[0]}.xxx.xxx.{parts[3]}"


def mask_mac(mac: Optional[str]) -> str:
    """
    Mask a MAC address:
    A4:83:E7:45:91:2B -> A4:xx:xx:xx:91:xx
    """
    if not mac or mac in ("Unknown", "None", "N/A", ""):
        return mac or "Unknown"
    sep = ":" if ":" in mac else "-"
    parts = mac.split(sep)
    if len(parts) == 6:
        return f"{parts[0]}{sep}xx{sep}xx{sep}xx{sep}{parts[4]}{sep}xx"
    return "xx:xx:xx:xx:xx:xx"


def mask_text(text: str) -> str:
    """Mask any IPv4 and MAC addresses found inside arbitrary text."""
    if not text:
        return text

    def _replace_mac(match):
        return mask_mac(match.group(0))

    def _replace_ip(match):
        ip = match.group(0)
        # Avoid masking netmasks like 255.255.255.0 if desired, or mask all
        if ip == "255.255.255.0" or ip == "0.0.0.0":
            return ip
        # Avoid masking standard DNS like 1.1.1.1 or 8.8.8.8
        if ip in ("1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9"):
            return ip
        return mask_ipv4(ip)

    text = MAC_REGEX.sub(_replace_mac, text)
    text = IPV4_REGEX.sub(_replace_ip, text)
    return text


def mask_scan_report(report: ScanReport) -> ScanReport:
    """Return a new ScanReport with all sensitive fields masked."""
    new_report = deepcopy(report)
    new_report.is_privacy_masked = True

    # Mask AdapterInfo
    adapter = new_report.adapter_info
    adapter.ipv4_address = mask_ipv4(adapter.ipv4_address)
    adapter.mac_address = mask_mac(adapter.mac_address)
    if adapter.default_gateway and adapter.default_gateway != "Unknown":
        adapter.default_gateway = mask_ipv4(adapter.default_gateway)
    # DNS servers: mask if local router IP
    masked_dns = []
    for s in adapter.dns_servers:
        if is_private_ip(s):
            masked_dns.append(mask_ipv4(s))
        else:
            masked_dns.append(s)
    adapter.dns_servers = masked_dns

    # Mask Diagnostic Results
    for r in new_report.results:
        r.value = mask_text(r.value)
        r.message = mask_text(r.message)
        # details
        if "gateway" in r.details and r.details["gateway"]:
            r.details["gateway"] = mask_ipv4(r.details["gateway"])
        if "ip" in r.details and r.details["ip"]:
            r.details["ip"] = mask_ipv4(r.details["ip"])
        if "public_ip" in r.details and r.details["public_ip"]:
            r.details["public_ip"] = mask_ipv4(r.details["public_ip"])

    # Mask Public IP info
    if "ip" in new_report.public_ip_info:
        new_report.public_ip_info["ip"] = mask_ipv4(str(new_report.public_ip_info["ip"]))

    # Mask Diagnosed Issues & Recommendations
    for issue in new_report.diagnosed_issues:
        issue.description = mask_text(issue.description)
        issue.recommendations = [mask_text(rec) for rec in issue.recommendations]

    new_report.recommendations = [mask_text(rec) for rec in new_report.recommendations]

    return new_report
