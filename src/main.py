"""Command Line Interface and Orchestration for Smith IT Company Network Diagnostic Toolkit."""

import os
import sys
import json
import argparse
import subprocess
import webbrowser
from pathlib import Path
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
from src.diagnostics.dns_benchmark import run_dns_benchmark
from src.diagnostics.ports import scan_ports
from src.diagnostics.traceroute import run_traceroute
from src.diagnostics.speedtest import test_download_speed
from src.diagnostics.live_monitor import run_live_monitor
from src.diagnostics.lan_scanner import scan_local_network
from src.diagnostics.wifi_analyzer import analyze_wifi_status
from src.diagnostics.jitter import run_jitter_stability_test
from src.scoring.health_score import calculate_health_score
from src.diagnosis.diagnosis_engine import run_diagnosis, extract_all_recommendations
from src.reporting.report_generator import generate_html_report
from src.utils.privacy import mask_scan_report, mask_text
from src.utils.logger import setup_logger, log_event, LOG_FILE

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


def play_completion_sound() -> None:
    """Play subtle notification chime on scan completion (Windows)."""
    if sys.platform == "win32":
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass


def open_report_in_browser(report_path: str) -> None:
    """Automatically open generated HTML report in default web browser."""
    try:
        uri = Path(report_path).resolve().as_uri()
        webbrowser.open(uri)
    except Exception:
        pass


def execute_full_scan(quick: bool = False) -> ScanReport:
    """Run all diagnostic modules with live progress feedback."""
    log_event("Starting full network diagnostic scan...")

    if RICH_AVAILABLE and console:
        with console.status("[bold cyan]Analyzing network stack...[/bold cyan]", spinner="dots") as status:
            status.update("[bold cyan]Step 1/7: Detecting network adapter & IP configuration...[/bold cyan]")
            adapter = detect_adapter_info()

            status.update(f"[bold cyan]Step 2/7: Pinging default gateway ({adapter.default_gateway})...[/bold cyan]")
            gw_res = test_gateway(adapter.default_gateway, quick=quick)

            status.update("[bold cyan]Step 3/7: Testing multi-stage internet reachability...[/bold cyan]")
            internet_res = test_internet_connectivity(
                gateway_reachable=(gw_res.status == "PASS"),
                quick=quick
            )

            status.update("[bold cyan]Step 4/7: Benchmarking DNS resolution speed...[/bold cyan]")
            dns_res = test_dns(timeout_sec=2.0 if quick else 3.0)

            status.update("[bold cyan]Step 5/7: Measuring packet loss and link stability...[/bold cyan]")
            loss_res = test_packet_loss(count=5 if quick else 20, quick=quick)

            status.update("[bold cyan]Step 6/7: Measuring dual-tier round-trip latency...[/bold cyan]")
            latency_res = measure_latency(gateway_ip=adapter.default_gateway, quick=quick)

            status.update("[bold cyan]Step 7/7: Checking external public IP...[/bold cyan]")
            pub_ip_info = detect_public_ip(timeout_sec=2.0)
    else:
        print("  -> Step 1/7: Detecting network adapter & IP configuration...")
        adapter = detect_adapter_info()

        print(f"  -> Step 2/7: Pinging default gateway ({adapter.default_gateway})...")
        gw_res = test_gateway(adapter.default_gateway, quick=quick)

        print("  -> Step 3/7: Testing multi-stage internet reachability...")
        internet_res = test_internet_connectivity(
            gateway_reachable=(gw_res.status == "PASS"),
            quick=quick
        )

        print("  -> Step 4/7: Benchmarking DNS resolution speed...")
        dns_res = test_dns(timeout_sec=2.0 if quick else 3.0)

        print("  -> Step 5/7: Measuring packet loss and link stability...")
        loss_res = test_packet_loss(count=5 if quick else 20, quick=quick)

        print("  -> Step 6/7: Measuring dual-tier round-trip latency...")
        latency_res = measure_latency(gateway_ip=adapter.default_gateway, quick=quick)

        print("  -> Step 7/7: Checking external public IP...")
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
    play_completion_sound()
    return report


def render_rich_terminal(report: ScanReport) -> None:
    """Render polished CLI interface using Rich."""
    adapter = report.adapter_info
    score = report.health_score

    # Header Panel
    header_text = Text()
    header_text.append("SMITH IT COMPANY NETWORK DIAGNOSTIC TOOLKIT\n", style="bold cyan")
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

    if adapter.wifi_info.get("ssid"):
        info_table.add_row("Wi-Fi SSID", adapter.wifi_info["ssid"])
        if adapter.wifi_info.get("signal"):
            info_table.add_row("Wi-Fi Signal", adapter.wifi_info["signal"])

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
    print("   SMITH IT COMPANY NETWORK DIAGNOSTIC TOOLKIT")
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


def render_output(report: ScanReport) -> None:
    """Render report to terminal using Rich or Plain text."""
    if RICH_AVAILABLE:
        render_rich_terminal(report)
    else:
        render_plain_terminal(report)


def run_quick_network_repair() -> None:
    """Execute standard network repair operations: flush DNS and renew IP."""
    print("\n" + "=" * 55)
    print("      QUICK NETWORK REPAIR & DNS FLUSH WIZARD")
    print("=" * 55)

    if sys.platform == "win32":
        print("\n[1/3] Flushing Windows DNS Resolver Cache...")
        try:
            res = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, check=False)
            print(res.stdout.strip())
        except Exception as e:
            print(f"Error flushing DNS: {e}")

        print("\n[2/3] Registering DNS connections...")
        try:
            res = subprocess.run(["ipconfig", "/registerdns"], capture_output=True, text=True, check=False)
            print(res.stdout.strip() or "DNS registration initiated.")
        except Exception as e:
            print(f"Error: {e}")

        try:
            ans = input("\n[3/3] Do you also want to Release & Renew DHCP IP address? (y/n): ").strip().lower()
            if ans == "y":
                print("Releasing IP...")
                subprocess.run(["ipconfig", "/release"], capture_output=True, text=True, check=False)
                print("Requesting new IP from DHCP router...")
                r = subprocess.run(["ipconfig", "/renew"], capture_output=True, text=True, check=False)
                print(r.stdout.strip())
                print("DHCP renewal finished.")
            else:
                print("Skipping DHCP renewal.")
        except Exception:
            pass
    else:
        print("Flushing local DNS resolver...")
        try:
            subprocess.run(["resolvectl", "flush-caches"], check=False)
            print("resolvectl cache cleared.")
        except Exception:
            try:
                subprocess.run(["systemd-resolve", "--flush-caches"], check=False)
                print("systemd-resolve cache cleared.")
            except Exception as e:
                print(f"Could not flush DNS automatically on this platform: {e}")

    print("\n✓ Repair tasks completed successfully!")


def interactive_menu() -> None:
    """Display interactive numbered menu for guided troubleshooting."""
    setup_logger(privacy=False)

    while True:
        if RICH_AVAILABLE:
            menu_text = Text()
            menu_text.append("SMITH IT COMPANY NETWORK DIAGNOSTIC TOOLKIT\n", style="bold cyan")
            menu_text.append("Main Menu - Select an action below", style="dim white")
            console.print("\n", Panel(menu_text, box=box.ROUNDED, expand=False))
            console.print("[bold cyan][1][/bold cyan]   Full Diagnostic Scan")
            console.print("[bold cyan][2][/bold cyan]   Quick Diagnostic Scan")
            console.print("[bold cyan][3][/bold cyan]   Full Scan + Generate HTML Report (Auto-Opens in Browser)")
            console.print("[bold cyan][4][/bold cyan]   Privacy Mode Scan (Mask IP & MAC)")
            console.print("[bold cyan][5][/bold cyan]   DNS Diagnostics Only")
            console.print("[bold cyan][6][/bold cyan]   Default Gateway Test Only")
            console.print("[bold cyan][7][/bold cyan]   DNS Speed Benchmark & Comparison (Cloudflare, Google, Quad9)")
            console.print("[bold cyan][8][/bold cyan]   Common Port & Service Connectivity Scan")
            console.print("[bold cyan][9][/bold cyan]   Live Ping & Packet Drop Monitor (Real-time Watcher)")
            console.print("[bold cyan][10][/bold cyan]  Hop-by-Hop Visual Traceroute")
            console.print("[bold cyan][11][/bold cyan]  Internet Download Speed Test (Mbps)")
            console.print("[bold cyan][12][/bold cyan]  Launch Desktop GUI Dashboard")
            console.print("[bold cyan][13][/bold cyan]  Quick Network Repair & DNS Flush Wizard")
            console.print("[bold cyan][14][/bold cyan]  View Diagnostic Logs")
            console.print("[bold cyan][15][/bold cyan]  Run Automated Unit Tests (pytest)")
            console.print("[bold cyan][16][/bold cyan]  LAN Subnet Device Discovery / IP Scanner")
            console.print("[bold cyan][17][/bold cyan]  Advanced Wi-Fi Signal & Channel Inspector")
            console.print("[bold cyan][18][/bold cyan]  VoIP / Video Call (Zoom/Teams) & Gaming Stability Test")
            console.print("[bold red][0][/bold red]   Exit\n")
        else:
            print("\n" + "=" * 55)
            print("   SMITH IT COMPANY NETWORK DIAGNOSTIC TOOLKIT")
            print("=" * 55)
            print(" [1]  Full Diagnostic Scan")
            print(" [2]  Quick Diagnostic Scan")
            print(" [3]  Full Scan + Generate HTML Report (Auto-Opens in Browser)")
            print(" [4]  Privacy Mode Scan (Mask IP & MAC)")
            print(" [5]  DNS Diagnostics Only")
            print(" [6]  Default Gateway Test Only")
            print(" [7]  DNS Speed Benchmark & Comparison (Cloudflare, Google, Quad9)")
            print(" [8]  Common Port & Service Connectivity Scan")
            print(" [9]  Live Ping & Packet Drop Monitor (Real-time Watcher)")
            print(" [10] Hop-by-Hop Visual Traceroute")
            print(" [11] Internet Download Speed Test (Mbps)")
            print(" [12] Launch Desktop GUI Dashboard")
            print(" [13] Quick Network Repair & DNS Flush Wizard")
            print(" [14] View Diagnostic Logs")
            print(" [15] Run Automated Unit Tests (pytest)")
            print(" [16] LAN Subnet Device Discovery / IP Scanner")
            print(" [17] Advanced Wi-Fi Signal & Channel Inspector")
            print(" [18] VoIP / Video Call (Zoom/Teams) & Gaming Stability Test")
            print(" [0]  Exit\n")

        try:
            choice = input("Enter your choice [0-18]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break

        print()

        if choice == "1":
            report = execute_full_scan(quick=False)
            render_output(report)

        elif choice == "2":
            report = execute_full_scan(quick=True)
            render_output(report)

        elif choice == "3":
            report = execute_full_scan(quick=False)
            render_output(report)
            report_path = generate_html_report(report)
            open_report_in_browser(report_path)
            if RICH_AVAILABLE:
                console.print(f"\n[bold green]Report generated and opened in browser:[/bold green] [underline]{report_path}[/underline]")
            else:
                print(f"\nReport generated and opened in browser: {report_path}")

        elif choice == "4":
            report = execute_full_scan(quick=True)
            report = mask_scan_report(report)
            render_output(report)

        elif choice == "5":
            print("Running DNS Resolution Diagnostics...")
            dns_res = test_dns()
            print(f"\nDNS Status: {dns_res.status} ({dns_res.value})")
            print(f"Message:    {dns_res.message}")
            for d in dns_res.details.get("domains", []):
                lat = f"{d.get('latency_ms', 'FAIL')} ms"
                ips = ", ".join(d.get("ips", [])) or "None"
                print(f"  • {d['domain']:<16} : {lat:<10} (IPs: {ips})")

        elif choice == "6":
            print("Running Gateway Diagnostics...")
            adapter = detect_adapter_info()
            gw_res = test_gateway(adapter.default_gateway)
            print(f"\nDefault Gateway: {adapter.default_gateway}")
            print(f"Status:          {gw_res.status}")
            print(f"Measured Metric: {gw_res.value}")
            print(f"Message:         {gw_res.message}")

        elif choice == "7":
            print("Benchmarking top global DNS resolvers (Cloudflare, Google, Quad9, OpenDNS)...")
            adapter = detect_adapter_info()
            res = run_dns_benchmark(local_dns=adapter.default_gateway)
            print(f"\nFastest Resolver: {res['fastest']['name']} ({res['fastest']['avg_ms']} ms)\n")
            print(f"{'Resolver':<25} {'IP':<16} {'Response Time':<15} {'Success':<10}")
            print("-" * 68)
            for r in res["results"]:
                ms_val = f"{r.get('avg_ms')} ms" if r.get('avg_ms') is not None else "TIMEOUT"
                print(f"{r['name']:<25} {r['ip']:<16} {ms_val:<15} {r['success_rate']:<10}")
            if res.get("recommendation"):
                print(f"\n* Recommendation: {res['recommendation']}")

        elif choice == "8":
            target = input("Enter target host to scan [Default 1.1.1.1]: ").strip() or "1.1.1.1"
            print(f"\nScanning common ports on {target}...")
            p_res = scan_ports(target)
            print(f"\nResults for {p_res['target']}: {p_res['open_count']} Open, {p_res['filtered_count']} Filtered, {p_res['closed_count']} Closed\n")
            print(f"{'Port':<8} {'Service':<30} {'Status':<12} {'Latency':<10}")
            print("-" * 62)
            for r in p_res["results"]:
                lat = f"{r.get('latency_ms')} ms" if r.get('latency_ms') else "-"
                print(f"{r['port']:<8} {r['service']:<30} {r['status']:<12} {lat:<10}")

        elif choice == "9":
            adapter = detect_adapter_info()
            run_live_monitor(gateway_ip=adapter.default_gateway, internet_target="1.1.1.1")

        elif choice == "10":
            target = input("Enter traceroute destination [Default 1.1.1.1]: ").strip() or "1.1.1.1"
            print(f"\nTracing hop-by-hop route to {target} (Please wait 5-10 seconds)...")
            tr_res = run_traceroute(target)
            print(f"\n{'Hop':<6} {'IP Address':<20} {'Latency':<12} {'Type':<25}")
            print("-" * 65)
            for h in tr_res["hops"]:
                lat = f"{h['avg_ms']} ms" if h['avg_ms'] is not None else "*"
                print(f"{h['hop']:<6} {h['ip']:<20} {lat:<12} {h['desc']:<25}")

        elif choice == "11":
            print("Measuring internet download speed via global CDN streaming...")
            sp_res = test_download_speed()
            print(f"\nDownload Speed:   {sp_res['speed_mbps']} Mbps")
            print(f"Data Transferred: {sp_res['data_mb']} MB in {sp_res['duration_sec']}s")
            print(f"Service Endpoint: {sp_res['provider']}")
            print(f"Classification:   {sp_res['rating']}")

        elif choice == "12":
            print("Launching Desktop Graphical Interface...")
            try:
                if getattr(sys, "frozen", False):
                    import threading
                    from src.gui.app import main as run_gui_app
                    threading.Thread(target=run_gui_app, daemon=True).start()
                    print("Desktop GUI launched in separate window.")
                else:
                    subprocess.Popen([sys.executable, "-m", "src.gui.app"])
                    print("Desktop GUI launched in a separate window.")
            except Exception as e:
                print(f"Could not open GUI: {e}")

        elif choice == "13":
            run_quick_network_repair()

        elif choice == "14":
            print("Latest Diagnostic Logs:")
            print("-" * 55)
            if LOG_FILE.exists():
                lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
                recent = lines[-20:] if len(lines) > 20 else lines
                for l in recent:
                    print(l)
            else:
                print("No log entries found yet.")
            print("-" * 55)

        elif choice == "15":
            print("Running Automated Pytest Suite...")
            subprocess.run([sys.executable, "-m", "pytest", "-v", "tests/"])

        elif choice == "16":
            subnet_in = input("Enter subnet CIDR to scan [Press Enter for auto-detect]: ").strip() or None
            print("\nScanning local network devices (using multi-threaded discovery)...")
            res = scan_local_network(subnet_cidr=subnet_in)
            print(f"\nSubnet: {res['subnet']} | Total Hosts Scanned: {res['total_hosts_scanned']} | Active Devices: {res['active_devices_count']}\n")
            print(f"{'IP Address':<18} {'MAC Address':<20} {'Hostname':<25} {'Role / Status':<25}")
            print("-" * 88)
            for d in res["devices"]:
                print(f"{d['ip']:<18} {d['mac']:<20} {d['hostname'][:24]:<25} {d['role']:<25}")

        elif choice == "17":
            print("Inspecting wireless adapter, signal health, and RF environment...")
            res = analyze_wifi_status()
            print(f"\nInterface:       {res['interface_name']}")
            print(f"Status:          {res['state']}")
            if res['is_wifi']:
                print(f"SSID:            {res['ssid']} (BSSID: {res['bssid']})")
                print(f"Signal Quality:  {res['signal_pct']}% (~{res['rssi_dbm']} dBm)")
                print(f"Band & Channel:  {res['band']} (Channel {res['channel']})")
                print(f"Protocol:        {res['wifi_generation']} ({res['radio_type']})")
                print(f"Security:        {res['auth']} / {res['cipher']}")
                rx = f"{res['rx_rate_mbps']} Mbps" if res['rx_rate_mbps'] else "N/A"
                tx = f"{res['tx_rate_mbps']} Mbps" if res['tx_rate_mbps'] else "N/A"
                print(f"Link Speeds:     Rx: {rx} | Tx: {tx}")
            elif res.get('rx_rate_mbps'):
                print(f"Link Speed:      {res['rx_rate_mbps']} Mbps (Wired)")
            if res.get('advice'):
                print("\nOptimization & Diagnostic Advice:")
                for adv in res['advice']:
                    print(f"  * {adv}")

        elif choice == "18":
            target = input("Enter target host for jitter test [Default 8.8.8.8]: ").strip() or "8.8.8.8"
            print(f"\nRunning VoIP & Gaming Jitter / Stability test against {target} (20 packets)...")
            res = run_jitter_stability_test(target_host=target, packet_count=20)
            print(f"\nTarget Host:      {res['target']}")
            print(f"Packets Sent/Rec: {res['packets_sent']} sent, {res['packets_received']} received ({res['packet_loss_pct']}% loss)")
            print(f"Latency Range:    Min: {res['min_ms']} ms | Avg: {res['avg_ms']} ms | Max: {res['max_ms']} ms | StdDev: {res['std_dev_ms']} ms")
            print(f"RFC 3550 Jitter:  {res['rfc3550_jitter_ms']} ms")
            print(f"VoIP MOS Score:   {res['mos_score']} / 4.5  [{res['grade']}]")
            print(f"Zoom / Teams:     {res['zoom_status']}")
            print(f"Gaming Rating:    {res['gaming_status']}")
            if res.get('advice'):
                print("\nDiagnostic Advice:")
                for adv in res['advice']:
                    print(f"  * {adv}")

        elif choice == "0":
            print("Thank you for using Smith IT Company Network Diagnostic Toolkit. Goodbye!\n")
            break

        else:
            print("Invalid option. Please select a number between 0 and 18.")

        try:
            input("\nPress Enter to return to main menu...")
        except (KeyboardInterrupt, EOFError):
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smith IT Company Network Diagnostic Toolkit - Automated network troubleshooting and health scoring."
    )
    parser.add_argument("--menu", action="store_true", help="Launch interactive selection menu")
    parser.add_argument("--quick", action="store_true", help="Perform a rapid diagnostic scan with fewer samples")
    parser.add_argument("--privacy", action="store_true", help="Mask sensitive IP and MAC addresses across CLI, JSON, HTML, and logs")
    parser.add_argument("--report", action="store_true", help="Generate a modern HTML report and open in browser")
    parser.add_argument("--output", type=str, default=None, help="Custom output filepath for HTML report")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON to stdout")
    parser.add_argument("--dns", action="store_true", help="Run DNS diagnostics only")
    parser.add_argument("--gateway", action="store_true", help="Run Gateway diagnostics only")
    parser.add_argument("--dns-bench", action="store_true", help="Run DNS benchmark across global providers")
    parser.add_argument("--ports", action="store_true", help="Run common port connectivity scan")
    parser.add_argument("--traceroute", action="store_true", help="Run hop-by-hop traceroute")
    parser.add_argument("--speedtest", action="store_true", help="Run download speed test")
    parser.add_argument("--monitor", action="store_true", help="Run continuous ping monitor")
    parser.add_argument("--repair", action="store_true", help="Run quick network repair (flush DNS and renew IP)")
    parser.add_argument("--gui", action="store_true", help="Launch Desktop GUI dashboard")
    parser.add_argument("--lan-scan", "--lan", action="store_true", help="Run high-speed LAN subnet device discovery")
    parser.add_argument("--wifi-info", "--wifi", action="store_true", help="Inspect Wi-Fi signal, channel, and link speed")
    parser.add_argument("--jitter", action="store_true", help="Run VoIP and gaming stability / jitter test")

    # If user ran `python run.py` without flags, open interactive menu!
    if len(sys.argv) == 1:
        interactive_menu()
        return

    args = parser.parse_args()

    if args.menu:
        interactive_menu()
        return

    if args.gui:
        subprocess.Popen([sys.executable, "-m", "src.gui.app"])
        return

    if args.repair:
        run_quick_network_repair()
        return

    if args.monitor:
        adapter = detect_adapter_info()
        run_live_monitor(gateway_ip=adapter.default_gateway, internet_target="1.1.1.1")
        return

    if args.traceroute:
        res = run_traceroute("1.1.1.1")
        for h in res["hops"]:
            print(f"Hop {h['hop']}: {h['ip']} ({h.get('avg_ms')} ms) - {h['desc']}")
        return

    if args.speedtest:
        res = test_download_speed()
        print(f"Speed: {res['speed_mbps']} Mbps ({res['rating']})")
        return

    if args.ports:
        res = scan_ports("1.1.1.1")
        print(f"Target: {res['target']} | Open: {res['open_count']} | Filtered: {res['filtered_count']}")
        for r in res["results"]:
            print(f"  Port {r['port']} ({r['service']}): {r['status']}")
        return

    if args.dns_bench:
        adapter = detect_adapter_info()
        res = run_dns_benchmark(local_dns=adapter.default_gateway)
        print(f"Fastest: {res['fastest']['name']} ({res['fastest']['avg_ms']} ms)")
        for r in res["results"]:
            print(f"  {r['name']} ({r['ip']}): {r.get('avg_ms')} ms")
        return

    if args.lan_scan:
        res = scan_local_network()
        print(f"Subnet: {res['subnet']} | Hosts Scanned: {res['total_hosts_scanned']} | Active Devices: {res['active_devices_count']}\n")
        print(f"{'IP Address':<18} {'MAC Address':<20} {'Hostname':<25} {'Role'}")
        print("-" * 75)
        for d in res["devices"]:
            print(f"{d['ip']:<18} {d['mac']:<20} {d['hostname'][:24]:<25} {d['role']}")
        return

    if args.wifi_info:
        res = analyze_wifi_status()
        print(f"Interface: {res['interface_name']} | Status: {res['state']}")
        if res['is_wifi']:
            print(f"SSID: {res['ssid']} | Signal: {res['signal_pct']}% (~{res['rssi_dbm']} dBm) | Channel: {res['channel']} ({res['band']})")
            print(f"Protocol: {res['wifi_generation']} | Security: {res['auth']} / {res['cipher']}")
        for adv in res.get('advice', []):
            print(f"  Advice: {adv}")
        return

    if args.jitter:
        res = run_jitter_stability_test()
        print(f"Target: {res['target']} | Avg Latency: {res['avg_ms']} ms | Jitter: {res['rfc3550_jitter_ms']} ms | Loss: {res['packet_loss_pct']}%")
        print(f"VoIP MOS Score: {res['mos_score']} [{res['grade']}]")
        print(f"Zoom / Teams:   {res['zoom_status']}")
        print(f"Gaming Rating:  {res['gaming_status']}")
        return

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
    render_output(report)

    # Generate HTML report if requested
    if args.report or args.output:
        report_path = generate_html_report(report, output_path=args.output)
        open_report_in_browser(report_path)
        if RICH_AVAILABLE:
            console.print(f"\n[bold green]Report generated and opened in browser:[/bold green] [underline]{report_path}[/underline]")
        else:
            print(f"\nReport generated and opened in browser: {report_path}")


if __name__ == "__main__":
    main()
