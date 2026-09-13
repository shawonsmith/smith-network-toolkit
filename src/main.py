"""Command Line Interface and Orchestration for Smith Network Diagnostic Toolkit."""

import os
import sys
import json
import argparse
from typing import Optional

# Ensure UTF-8 output on Windows consoles if possible
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.result import ScanReport, DiagnosticResult
from src.diagnostics.adapter import detect_adapter_info
from src.diagnostics.gateway import test_gateway
from src.diagnostics.connectivity import test_internet_connectivity
from src.diagnostics.dns import test_dns
from src.diagnostics.packet_loss import test_packet_loss
from src.diagnostics.latency import measure_latency
from src.diagnostics.public_ip import detect_public_ip
from src.scoring.health_score import calculate_health_score
from src.diagnosis.diagnosis_engine import run_diagnosis, extract_all_recommendations
from src.reporting.report_generator import generate_html_report
from src.utils.privacy import mask_scan_report, mask_text
from src.utils.logger import setup_logger, log_event

# Optional Rich CLI imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
    console = Console(highlight=False)
except ImportError:
    RICH_AVAILABLE = False
    console = None


def execute_full_scan(quick: bool = False) -> ScanReport:
    """Run all diagnostic modules and synthesize a unified ScanReport."""
    log_event("Starting full network diagnostic scan...")

    # 1. Adapter Info
    adapter = detect_adapter_info()

    # 2. Gateway Reachability
    gw_res = test_gateway(adapter.default_gateway, quick=quick)

    # 3. Internet Connectivity
    internet_res = test_internet_connectivity(
        gateway_reachable=(gw_res.status == "PASS"),
        quick=quick
    )

    # 4. DNS Diagnostics (isolated from web requests)
    dns_res = test_dns(timeout_sec=2.0 if quick else 3.0)

    # 5. Packet Loss
    loss_res = test_packet_loss(count=5 if quick else 20, quick=quick)

    # 6. Latency (Dual-tier Gateway & Internet)
    latency_res = measure_latency(gateway_ip=adapter.default_gateway, quick=quick)

    # 7. Public IP (Informational)
    pub_ip_info = detect_public_ip(timeout_sec=2.0)

    results = [gw_res, internet_res, dns_res, loss_res, latency_res]

    # 8. Health Score
    health = calculate_health_score(adapter, results)

    # 9. Diagnosis Engine & Recommendations
    issues = run_diagnosis(adapter, results)
    recs = extract_all_recommendations(issues)

    report = ScanReport(
        version="1.0.0",
        adapter_info=adapter,
        results=results,
        health_score=health,
        diagnosed_issues=issues,
        recommendations=recs,
        public_ip_info=pub_ip_info,
        is_privacy_masked=False
    )
    log_event(f"Scan complete. Health Score: {health.total_score}/100")
    return report


def render_rich_terminal(report: ScanReport) -> None:
    """Render polished CLI interface using Rich."""
    adapter = report.adapter_info
    score = report.health_score

    # Header Panel
    header_text = Text()
    header_text.append("SMITH NETWORK DIAGNOSTIC TOOLKIT\n", style="bold cyan")
    header_text.append("Automated Network Troubleshooting & Health Score", style="dim white")
    if report.is_privacy_masked:
        header_text.append("  [Privacy Mode Active]", style="bold blue")
    console.print(Panel(header_text, box=box.ROUNDED, expand=False))

    # Device & Adapter Table
    info_table = Table(title="Device & Network Adapter", box=box.SIMPLE_HEAVY, show_header=False)
    info_table.add_column("Property", style="bold white")
    info_table.add_column("Value", style="cyan")

    info_table.add_row("Hostname", adapter.hostname)
    info_table.add_row("Operating System", adapter.os_name)
    info_table.add_row("Adapter Name", adapter.adapter_name)
    info_table.add_row("MAC Address", adapter.mac_address)
    info_table.add_row("IPv4 Address", adapter.ipv4_address)
    info_table.add_row("Subnet Mask", adapter.subnet_mask)
    info_table.add_row("Default Gateway", adapter.default_gateway)
    dns_display = ", ".join(adapter.dns_servers) if adapter.dns_servers else "None"
    info_table.add_row("DNS Servers", dns_display)
    pub_ip = report.public_ip_info.get("ip", "Unavailable")
    info_table.add_row("Public IP", pub_ip)
    console.print(info_table)

    # Diagnostics Table
    diag_table = Table(title="Diagnostic Checks", box=box.ROUNDED)
    diag_table.add_column("Target Check", style="bold")
    diag_table.add_column("Status", justify="center")
    diag_table.add_column("Measured Metric", style="yellow")
    diag_table.add_column("Summary Message", style="dim")

    for r in report.results:
        if r.status == "PASS":
            status_style = "[bold green][PASS][/bold green]"
        elif r.status == "WARN":
            status_style = "[bold yellow][WARN][/bold yellow]"
        else:
            status_style = "[bold red][FAIL][/bold red]"
        diag_table.add_row(r.name, status_style, r.value, r.message)

    console.print(diag_table)

    # Health Score Panel
    if score.total_score >= 90:
        score_color = "bold green"
    elif score.total_score >= 75:
        score_color = "bold cyan"
    elif score.total_score >= 60:
        score_color = "bold yellow"
    else:
        score_color = "bold red"

    score_panel = Panel(
        f"[{score_color}]Network Health Score: {score.total_score}/100 ({score.grade})[/{score_color}]",
        box=box.DOUBLE,
        expand=False
    )
    console.print(score_panel)

    # Diagnosed Issues & Recommendations
    if report.diagnosed_issues:
        console.print("\n[bold red]Likely Issues Identified:[/bold red]")
        for issue in report.diagnosed_issues:
            tag = "[bold yellow]WARNING[/bold yellow]" if issue.severity == "warning" else "[bold red]CRITICAL[/bold red]"
            console.print(f" • {tag} [bold]{issue.title}[/bold]: {issue.description}")

        console.print("\n[bold green]Recommended Actions:[/bold green]")
        for idx, rec in enumerate(report.recommendations, 1):
            console.print(f" {idx}. {rec}")
    else:
        console.print("\n[bold green][PASS] No network connectivity or DNS issues identified.[/bold green]")


def render_plain_terminal(report: ScanReport) -> None:
    """Plain ANSI terminal fallback when Rich is unavailable."""
    adapter = report.adapter_info
    score = report.health_score

    print("=" * 50)
    print("       SMITH NETWORK DIAGNOSTIC TOOLKIT")
    if report.is_privacy_masked:
        print("              [Privacy Mode]")
    print("=" * 50)
    print(f"Hostname:        {adapter.hostname}")
    print(f"OS:              {adapter.os_name}")
    print(f"Adapter:         {adapter.adapter_name}")
    print(f"MAC:             {adapter.mac_address}")
    print(f"IPv4:            {adapter.ipv4_address}")
    print(f"Subnet:          {adapter.subnet_mask}")
    print(f"Gateway:         {adapter.default_gateway}")
    print(f"DNS:             {', '.join(adapter.dns_servers)}")
    print(f"Public IP:       {report.public_ip_info.get('ip', 'Unavailable')}\n")

    print("DIAGNOSTIC CHECKS:")
    print("-" * 50)
    for r in report.results:
        symbol = "[PASS]" if r.status == "PASS" else ("[WARN]" if r.status == "WARN" else "[FAIL]")
        print(f"{symbol:<8} {r.name:<15} : {r.value:<12} ({r.message})")
    print("-" * 50)
    print(f"\nNetwork Health Score: {score.total_score}/100 ({score.grade})\n")

    if report.diagnosed_issues:
        print("Likely Issues:")
        for issue in report.diagnosed_issues:
            print(f" • {issue.title}: {issue.description}")
        print("\nRecommendations:")
        for idx, rec in enumerate(report.recommendations, 1):
            print(f" {idx}. {rec}")
    else:
        print("[PASS] All network checks healthy.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smith Network Diagnostic Toolkit - Automated network troubleshooting and health scoring."
    )
    parser.add_argument("--quick", action="store_true", help="Perform a rapid diagnostic scan with fewer samples")
    parser.add_argument("--privacy", action="store_true", help="Mask sensitive IP and MAC addresses across CLI, JSON, HTML, and logs")
    parser.add_argument("--report", action="store_true", help="Generate a modern HTML report in reports/ directory")
    parser.add_argument("--output", type=str, default=None, help="Custom output filepath for HTML report")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON to stdout")
    parser.add_argument("--dns", action="store_true", help="Run DNS diagnostics only")
    parser.add_argument("--gateway", action="store_true", help="Run Gateway diagnostics only")

    args = parser.parse_args()

    # Configure logger with privacy setting
    setup_logger(privacy=args.privacy)

    # Handle single check: DNS only
    if args.dns:
        dns_res = test_dns()
        if args.json:
            print(json.dumps(dns_res.to_dict(), indent=2))
        else:
            print(f"DNS Status: {dns_res.status} ({dns_res.value})")
            for d in dns_res.details.get("domains", []):
                print(f"  {d['domain']}: {d.get('latency_ms', 'FAIL')} ms - {d.get('ips')}")
        return

    # Handle single check: Gateway only
    if args.gateway:
        adapter = detect_adapter_info()
        gw_res = test_gateway(adapter.default_gateway, quick=args.quick)
        if args.json:
            print(json.dumps(gw_res.to_dict(), indent=2))
        else:
            print(f"Gateway ({adapter.default_gateway}): {gw_res.status} ({gw_res.value})")
        return

    # Full Scan
    report = execute_full_scan(quick=args.quick)

    # Apply privacy masking if requested
    if args.privacy:
        report = mask_scan_report(report)

    # Handle JSON output
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        if args.report or args.output:
            report_path = generate_html_report(report, output_path=args.output)
        return

    # Render terminal UI
    if RICH_AVAILABLE:
        render_rich_terminal(report)
    else:
        render_plain_terminal(report)

    # Generate HTML report if requested
    if args.report or args.output:
        report_path = generate_html_report(report, output_path=args.output)
        if RICH_AVAILABLE:
            console.print(f"\n[bold green]Report generated successfully:[/bold green] [underline]{report_path}[/underline]")
        else:
            print(f"\nReport generated successfully: {report_path}")


if __name__ == "__main__":
    main()
