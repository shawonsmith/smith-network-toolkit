"""Autonomous Real-Time Network Self-Healing Engine (Auto-Heal Guardian)."""

import os
import sys
import time
import socket
import platform
import threading
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List

from src.utils.logger import log_event, LOG_FILE
from src.utils.platform_utils import ping_host, tcp_ping, is_valid_ipv4


class NetworkGuardian:
    """
    Continuous background network watchdog and self-healing agent.
    Detects network stalls, DNS corruption, and DHCP drops, and executes
    targeted remediations automatically in real time.
    """

    def __init__(
        self,
        probe_interval: float = 6.0,
        debounce_count: int = 2,
        cooldown_sec: float = 45.0,
        on_heartbeat: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_incident: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.probe_interval = probe_interval
        self.debounce_count = debounce_count
        self.cooldown_sec = cooldown_sec
        self.on_heartbeat = on_heartbeat
        self.on_incident = on_incident

        self._running = False
        self._thread: Optional[threading.Thread] = None

        # State tracking
        self.consecutive_dns_failures = 0
        self.consecutive_gw_failures = 0
        self.consecutive_internet_failures = 0
        self.last_heal_time: float = 0.0
        self.total_incidents_healed = 0
        self.incident_history: List[Dict[str, Any]] = []

    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the background self-healing daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="NetworkGuardianWorker")
        self._thread.start()
        log_event("Network Guardian Self-Healing Daemon STARTED", "info")

    def stop(self) -> None:
        """Gracefully stop the background daemon thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        log_event("Network Guardian Self-Healing Daemon STOPPED", "info")

    def _loop(self) -> None:
        """Main continuous observation and remediation loop."""
        while self._running:
            try:
                self._run_probe_cycle()
            except Exception as e:
                log_event(f"Unexpected error in Guardian probe cycle: {e}", "warning")

            # Sleep in short increments for responsive cancellation
            elapsed = 0.0
            while self._running and elapsed < self.probe_interval:
                time.sleep(0.5)
                elapsed += 0.5

    def _probe_dns(self, test_domain: str = "cloudflare.com") -> bool:
        """Check if DNS resolution succeeds within 2.0 seconds."""
        prev = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(2.0)
            socket.gethostbyname(test_domain)
            return True
        except Exception:
            return False
        finally:
            socket.setdefaulttimeout(prev)

    def _run_probe_cycle(self) -> None:
        """Execute a single multi-stage health check cycle."""
        from src.diagnostics.adapter import detect_adapter_info

        adapter = detect_adapter_info()
        gw_ip = adapter.default_gateway

        # Probe 1: Gateway Reachability
        gw_ok = False
        gw_lat = None
        if is_valid_ipv4(gw_ip) and gw_ip not in ("Unknown", "None"):
            p = ping_host(gw_ip, count=1, timeout_sec=1.0)
            if p.get("success"):
                gw_ok = True
                gw_lat = p.get("avg_ms")
            else:
                tcp = tcp_ping(gw_ip, port=53, timeout_sec=0.8)
                if tcp.get("success"):
                    gw_ok = True
                    gw_lat = tcp.get("latency_ms")

        # Probe 2: DNS Resolution
        dns_ok = self._probe_dns("cloudflare.com")
        if not dns_ok:
            dns_ok = self._probe_dns("google.com")

        # Probe 3: Core Internet IP (Bypasses DNS)
        net_res = ping_host("1.1.1.1", count=1, timeout_sec=1.2)
        internet_ok = net_res.get("success", False)
        net_lat = net_res.get("avg_ms")
        if not internet_ok:
            tcp_net = tcp_ping("1.1.1.1", port=53, timeout_sec=1.0)
            internet_ok = tcp_net.get("success", False)
            net_lat = tcp_net.get("latency_ms")

        # Failure Counters
        if not dns_ok and internet_ok:
            self.consecutive_dns_failures += 1
        else:
            self.consecutive_dns_failures = 0

        if not gw_ok and adapter.is_connected:
            self.consecutive_gw_failures += 1
        else:
            self.consecutive_gw_failures = 0

        if not internet_ok and gw_ok:
            self.consecutive_internet_failures += 1
        else:
            self.consecutive_internet_failures = 0

        # Emit live heartbeat update
        heartbeat = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "adapter": adapter.adapter_name,
            "gateway_ip": gw_ip,
            "gateway_ok": gw_ok,
            "gateway_latency_ms": gw_lat,
            "dns_ok": dns_ok,
            "internet_ok": internet_ok,
            "internet_latency_ms": net_lat,
            "status": "HEALTHY" if (gw_ok and dns_ok and internet_ok) else "DEGRADED",
            "is_apipa": adapter.is_apipa
        }

        if self.on_heartbeat:
            try:
                self.on_heartbeat(heartbeat)
            except Exception:
                pass

        # Check if self-healing remediation is needed
        now = time.time()
        cooldown_remaining = max(0.0, self.cooldown_sec - (now - self.last_heal_time))
        can_heal = cooldown_remaining <= 0.0

        if can_heal:
            # Case A: DNS Resolution Freeze (Internet reachable by IP, but domains fail)
            if self.consecutive_dns_failures >= self.debounce_count:
                self._execute_heal_dns(heartbeat)

            # Case B: APIPA or Stale DHCP lease (169.254.x.x)
            elif adapter.is_apipa:
                self._execute_heal_dhcp(heartbeat)

            # Case C: Gateway Unreachable while adapter UP (Stale ARP)
            elif self.consecutive_gw_failures >= self.debounce_count:
                self._execute_heal_arp(heartbeat)

    def _execute_heal_dns(self, context: Dict[str, Any]) -> None:
        """Remediation Level 1: Flush DNS resolver cache and re-register."""
        log_event("AUTO-HEAL TRIGGERED: DNS Resolution Freeze Detected! Flushing cache...", "warning")
        t_start = time.time()

        if platform.system() == "Windows":
            try:
                subprocess.run("ipconfig /flushdns", shell=True, capture_output=True, text=True, check=False)
                subprocess.run("ipconfig /registerdns", shell=True, capture_output=True, text=True, check=False)
            except Exception as e:
                log_event(f"Auto-heal error executing flushdns: {e}", "warning")

        # Verify if DNS restored
        time.sleep(1.0)
        resolved = self._probe_dns("cloudflare.com") or self._probe_dns("google.com")

        self.last_heal_time = time.time()
        self.consecutive_dns_failures = 0

        incident = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trigger": "DNS Resolution Freeze (Domain lookup failed 2x)",
            "action": "Cleared Windows DNS Cache & Triggered /registerdns",
            "verified": resolved,
            "duration_sec": round(time.time() - t_start, 2),
            "message": "DNS cache flushed. Resolution successfully restored!" if resolved else "DNS flushed. Upstream resolver may still be unresponsive."
        }

        self._record_incident(incident)

    def _execute_heal_arp(self, context: Dict[str, Any]) -> None:
        """Remediation Level 2: Refresh ARP cache table."""
        log_event("AUTO-HEAL TRIGGERED: Local Gateway Unreachable. Resetting ARP cache...", "warning")
        t_start = time.time()

        if platform.system() == "Windows":
            try:
                subprocess.run("netsh interface ip delete arpcache", shell=True, capture_output=True, text=True, check=False)
            except Exception:
                try:
                    subprocess.run("arp -d *", shell=True, capture_output=True, text=True, check=False)
                except Exception:
                    pass

        time.sleep(1.0)
        from src.diagnostics.adapter import detect_adapter_info
        adapter = detect_adapter_info()
        p = ping_host(adapter.default_gateway, count=1, timeout_sec=1.0)
        resolved = p.get("success", False)

        self.last_heal_time = time.time()
        self.consecutive_gw_failures = 0

        incident = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trigger": "Local Gateway Unreachable (Stale ARP entry suspected)",
            "action": "Flushed local ARP cache table",
            "verified": resolved,
            "duration_sec": round(time.time() - t_start, 2),
            "message": "ARP cache refreshed. Router communication restored!" if resolved else "ARP refreshed. Check router power or physical cable."
        }

        self._record_incident(incident)

    def _execute_heal_dhcp(self, context: Dict[str, Any]) -> None:
        """Remediation Level 3: Renew expired or invalid DHCP lease."""
        log_event("AUTO-HEAL TRIGGERED: APIPA 169.254.x.x detected. Renewing DHCP lease...", "warning")
        t_start = time.time()

        if platform.system() == "Windows":
            try:
                subprocess.run("ipconfig /renew", shell=True, capture_output=True, text=True, check=False)
            except Exception as e:
                log_event(f"Auto-heal error renewing IP: {e}", "warning")

        time.sleep(2.0)
        from src.diagnostics.adapter import detect_adapter_info
        adapter = detect_adapter_info()
        resolved = (not adapter.is_apipa) and is_valid_ipv4(adapter.ipv4_address)

        self.last_heal_time = time.time()

        incident = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trigger": "APIPA 169.254.x.x (DHCP Lease Failed)",
            "action": "Executed ipconfig /renew to obtain fresh IP from router",
            "verified": resolved,
            "duration_sec": round(time.time() - t_start, 2),
            "message": f"Fresh IP obtained: {adapter.ipv4_address}" if resolved else "DHCP renew attempted. Router DHCP server might be offline."
        }

        self._record_incident(incident)

    def _record_incident(self, incident: Dict[str, Any]) -> None:
        """Log incident, play sound notification, and notify callbacks."""
        self.total_incidents_healed += 1
        self.incident_history.append(incident)
        log_event(f"AUTO-HEAL COMPLETE: {incident['action']} -> Verified: {incident['verified']}", "info")

        # Play subtle notification beep on Windows
        if sys.platform == "win32":
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        if self.on_incident:
            try:
                self.on_incident(incident)
            except Exception:
                pass


def run_guardian_cli() -> None:
    """Run interactive terminal session of the Network Guardian."""
    print("=" * 65)
    print("   SMITH IT COMPANY - REAL-TIME NETWORK GUARDIAN (AUTO-HEAL)")
    print("=" * 65)
    print(" • Continuous monitoring active (Probe cycle every 5 seconds)")
    print(" • Real-time self-healing enabled (DNS Flush, ARP Reset, DHCP Renew)")
    print(" • Press Ctrl+C at any time to return to main menu.\n")
    print(f"{'Time':<10} {'Gateway':<16} {'DNS':<10} {'Internet':<16} {'Guardian Status'}")
    print("-" * 68)

    guardian = None
    try:
        def print_heartbeat(hb: Dict[str, Any]):
            gw_str = f"{hb['gateway_latency_ms']:.0f} ms" if hb['gateway_ok'] and hb['gateway_latency_ms'] else ("OK" if hb['gateway_ok'] else "DOWN")
            dns_str = "OK" if hb['dns_ok'] else "FAIL"
            net_str = f"{hb['internet_latency_ms']:.0f} ms" if hb['internet_ok'] and hb['internet_latency_ms'] else ("OK" if hb['internet_ok'] else "DOWN")
            status_tag = "ACTIVE [Protected]" if hb['status'] == "HEALTHY" else "HEALING / DEGRADED"
            print(f"{hb['timestamp']:<10} {gw_str:<16} {dns_str:<10} {net_str:<16} {status_tag}")

        def print_incident(inc: Dict[str, Any]):
            print(f"\n⚡ [SELF-HEALED at {inc['timestamp']}]")
            print(f"   Cause:  {inc['trigger']}")
            print(f"   Action: {inc['action']}")
            print(f"   Result: {inc['message']} ({inc['duration_sec']}s)\n")
            print("-" * 68)

        guardian = NetworkGuardian(
            probe_interval=5.0,
            on_heartbeat=print_heartbeat,
            on_incident=print_incident
        )
        guardian.start()

        while True:
            time.sleep(1.0)

    except (KeyboardInterrupt, EOFError):
        print("\nStopping Network Guardian...")
    finally:
        if guardian:
            guardian.stop()
        print("Network Guardian stopped. Returning to menu.\n")
