"""Automatic root-cause diagnosis engine and actionable recommendation generator."""

from typing import List, Dict, Any
from src.models.result import (
    DiagnosticResult,
    AdapterInfo,
    DiagnosisItem
)
from src.utils.logger import log_event


def run_diagnosis(
    adapter_info: AdapterInfo,
    results: List[DiagnosticResult]
) -> List[DiagnosisItem]:
    """
    Analyze diagnostic test outcomes against IT support troubleshooting rules
    and produce prioritized diagnosis items with remediation steps.
    """
    issues: List[DiagnosisItem] = []
    results_map: Dict[str, DiagnosticResult] = {r.name: r for r in results}

    gw_res = results_map.get("Gateway")
    internet_res = results_map.get("Internet")
    dns_res = results_map.get("DNS")
    loss_res = results_map.get("Packet Loss")
    latency_res = results_map.get("Latency")

    # Helper flags
    gateway_reachable = gw_res is not None and gw_res.status == "PASS"
    internet_connected = internet_res is not None and internet_res.status == "PASS"
    external_ip_ok = (
        internet_res is not None and
        internet_res.details.get("external_ip_reachable", False)
    )
    dns_ok = dns_res is not None and dns_res.status == "PASS"

    log_event("Evaluating automatic diagnosis rules...")

    # Rule 1: DHCP / APIPA (169.254.x.x)
    if adapter_info.is_apipa or (adapter_info.ipv4_address and adapter_info.ipv4_address.startswith("169.254.")):
        issues.append(DiagnosisItem(
            rule_id="RULE-01-APIPA",
            title="DHCP Configuration Failure (APIPA Assigned)",
            description=(
                "Your device assigned itself an Automatic Private IP Address (169.254.x.x) "
                "because it failed to receive an IP lease from a local DHCP server."
            ),
            recommendations=[
                "Check if the local router or DHCP server is powered on and operational.",
                "Verify that your network cable is plugged in or Wi-Fi is authenticated.",
                "Open Command Prompt as Administrator and run: 'ipconfig /release' followed by 'ipconfig /renew'.",
                "Check network adapter IPv4 properties to ensure 'Obtain an IP address automatically' is selected."
            ],
            severity="critical"
        ))

    # Rule 2: DNS Failure (Gateway & External IP work, but DNS fails or inconsistent)
    if gateway_reachable and external_ip_ok and (dns_res is not None and dns_res.status in ("FAIL", "WARN")):
        if dns_res.status == "FAIL":
            issues.append(DiagnosisItem(
                rule_id="RULE-02-DNS-FAIL",
                title="DNS Name Resolution Failure",
                description=(
                    "Device can communicate with external IP addresses, but domain name lookup (DNS) "
                    "completely failed. Websites cannot be reached by their domain names."
                ),
                recommendations=[
                    "Change your adapter DNS settings to public resolvers: Primary 1.1.1.1, Secondary 8.8.8.8.",
                    "Flush local DNS resolver cache: 'ipconfig /flushdns'.",
                    "Check if any third-party antivirus, VPN, or ad-blocker is intercepting DNS requests."
                ],
                severity="critical"
            ))
        elif dns_res.value and "Slow" in dns_res.value:
            issues.append(DiagnosisItem(
                rule_id="RULE-07-DNS-SLOW",
                title="Slow DNS Resolver Response",
                description=(
                    f"Domain name resolution takes {dns_res.value} on average, which slows down "
                    "webpage load times."
                ),
                recommendations=[
                    "Test switching your configured DNS servers to Cloudflare (1.1.1.1) or Google (8.8.8.8).",
                    "Clear the DNS cache using: 'ipconfig /flushdns'."
                ],
                severity="warning"
            ))

    # Rule 3: Gateway Unreachable
    if gw_res is not None and gw_res.status == "FAIL":
        issues.append(DiagnosisItem(
            rule_id="RULE-03-GATEWAY-DOWN",
            title="Local Network Gateway Unreachable",
            description=(
                "Your device is connected to an adapter, but cannot communicate with the local default router/gateway."
            ),
            recommendations=[
                "Check physical Ethernet cable connection or re-authenticate to Wi-Fi.",
                "Restart your local router or Wi-Fi access point (wait 30 seconds).",
                "Ensure your device's static IP (if configured) is within the same subnet as the gateway.",
                "Restart your network adapter."
            ],
            severity="critical"
        ))

    # Rule 4: ISP / Upstream Outage (Gateway reachable, but external IP unreachable)
    if gateway_reachable and not external_ip_ok and (internet_res is not None and internet_res.status == "FAIL"):
        issues.append(DiagnosisItem(
            rule_id="RULE-04-ISP-OUTAGE",
            title="ISP or Upstream Connection Outage",
            description=(
                "Local network communication with the router is working normally, but data cannot "
                "reach the external Internet. The issue is likely upstream at the ISP or modem level."
            ),
            recommendations=[
                "Inspect the WAN / Internet LED indicator on your broadband modem/router.",
                "Power cycle your broadband modem / Optical Network Terminal (ONT).",
                "Contact your Internet Service Provider (ISP) to report an outage or check service status."
            ],
            severity="critical"
        ))

    # Rule 5: Packet Loss > 5%
    if loss_res is not None:
        loss_pct = loss_res.details.get("loss_percent", 0.0)
        if loss_pct > 5.0:
            issues.append(DiagnosisItem(
                rule_id="RULE-05-PACKET-LOSS",
                title=f"Unstable Connection ({loss_pct:.1f}% Packet Loss)",
                description=(
                    f"High packet loss of {loss_pct:.1f}% detected. This causes dropped video calls, "
                    "gaming lag spikes, and broken downloads."
                ),
                recommendations=[
                    "If on Wi-Fi, test moving closer to the router or switch from 2.4 GHz to 5 GHz band.",
                    "If on Ethernet, inspect cables for kinks or test a known-good Cat6 patch cord.",
                    "Check if another device on the network is saturating the upload/download bandwidth.",
                    "Restart router to flush full memory/buffer tables."
                ],
                severity="critical" if loss_pct > 15.0 else "warning"
            ))

    # Rule 6: High Local Gateway Latency
    if latency_res is not None:
        gw_lat = latency_res.details.get("gateway_latency_ms")
        if gw_lat is not None and gw_lat > 15.0:
            issues.append(DiagnosisItem(
                rule_id="RULE-06-LAN-LATENCY",
                title=f"High Local Gateway Latency ({gw_lat:.1f} ms)",
                description=(
                    f"Local router ping response is {gw_lat:.1f} ms (expected <5 ms on LAN). "
                    "Indicates wireless degradation or local link saturation."
                ),
                recommendations=[
                    "Check for Wi-Fi interference from household appliances or neighbouring networks.",
                    "Connect via a wired Ethernet cable to verify if the delay is wireless-specific."
                ],
                severity="warning"
            ))

    log_event(f"Diagnosis completed: {len(issues)} issue(s) identified.")
    return issues


def extract_all_recommendations(issues: List[DiagnosisItem]) -> List[str]:
    """Collect deduplicated list of recommendations from all diagnosed issues."""
    recs: List[str] = []
    seen = set()
    for issue in issues:
        for r in issue.recommendations:
            if r not in seen:
                recs.append(r)
                seen.add(r)
    return recs
