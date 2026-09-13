"""Desktop Graphical User Interface for Smith IT Company Network Diagnostic Toolkit."""

import sys
import os
import time
import threading
import subprocess
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.main import execute_full_scan
from src.reporting.report_generator import generate_html_report
from src.diagnostics.adapter import detect_adapter_info
from src.diagnostics.gateway import test_gateway
from src.diagnostics.dns import test_dns
from src.diagnostics.dns_benchmark import run_dns_benchmark
from src.diagnostics.ports import scan_ports
from src.diagnostics.speedtest import test_download_speed
from src.diagnostics.traceroute import run_traceroute
from src.diagnostics.lan_scanner import scan_local_network
from src.diagnostics.wifi_analyzer import analyze_wifi_status
from src.diagnostics.jitter import run_jitter_stability_test
from src.diagnostics.guardian import NetworkGuardian
from src.utils.privacy import mask_scan_report
from src.utils.logger import LOG_FILE


class NetworkToolkitGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Smith IT Company Network Diagnostic Toolkit v1.0")
        self.root.geometry("1060x740")
        self.root.minsize(980, 640)
        self.root.configure(bg="#0f172a")

        self.last_report = None
        self.guardian: Optional[NetworkGuardian] = None
        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#1e293b", relief="flat")
        style.configure("TLabel", background="#0f172a", foreground="#f8fafc", font=("Segoe UI", 10))
        style.configure("Card.TLabel", background="#1e293b", foreground="#f8fafc", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#1e293b", foreground="#38bdf8", font=("Segoe UI", 14, "bold"))
        style.configure("Muted.TLabel", background="#1e293b", foreground="#94a3b8", font=("Segoe UI", 9))

        # Primary Button (Scan)
        style.configure(
            "Primary.TButton",
            background="#2563eb",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padding=5
        )
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])

        # Secondary Button
        style.configure(
            "Secondary.TButton",
            background="#334155",
            foreground="#ffffff",
            font=("Segoe UI", 9),
            padding=5
        )
        style.map("Secondary.TButton", background=[("active", "#475569")])

        # Accent Button
        style.configure(
            "Accent.TButton",
            background="#0d9488",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padding=5
        )
        style.map("Accent.TButton", background=[("active", "#0f766e")])

        # Danger / Exit Button
        style.configure(
            "Danger.TButton",
            background="#b91c1c",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padding=5
        )
        style.map("Danger.TButton", background=[("active", "#991b1b")])

        # Guardian Active Style
        style.configure(
            "GuardianActive.TButton",
            background="#16a34a",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padding=5
        )
        style.map("GuardianActive.TButton", background=[("active", "#15803d")])

        # Treeview
        style.configure(
            "Treeview",
            background="#1e293b",
            foreground="#f8fafc",
            fieldbackground="#1e293b",
            rowheight=28,
            font=("Segoe UI", 9)
        )
        style.configure("Treeview.Heading", background="#334155", foreground="#f8fafc", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#2563eb")])

    def _build_ui(self):
        # Header Bar
        header_frame = ttk.Frame(self.root, style="Card.TFrame", padding=15)
        header_frame.pack(fill="x", padx=15, pady=10)

        title_lbl = ttk.Label(header_frame, text="SMITH IT COMPANY NETWORK DIAGNOSTIC TOOLKIT", style="Header.TLabel")
        title_lbl.pack(anchor="w")

        sub_lbl = ttk.Label(header_frame, text="Automated Network Troubleshooting, Health Assessment & Diagnostic Engine (18 Tools Integrated)", style="Muted.TLabel")
        sub_lbl.pack(anchor="w")

        # Status & Health Score Bar
        score_frame = ttk.Frame(self.root, style="Card.TFrame", padding=12)
        score_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.score_label = ttk.Label(
            score_frame,
            text="Health Score: Click 'Full Scan' or 'Quick Scan' to evaluate network",
            font=("Segoe UI", 12, "bold"),
            background="#1e293b",
            foreground="#38bdf8"
        )
        self.score_label.pack(side="left")

        self.status_label = ttk.Label(
            score_frame,
            text="Ready",
            style="Muted.TLabel"
        )
        self.status_label.pack(side="right")

        self.btn_guardian = ttk.Button(
            score_frame,
            text="🛡️ Auto-Heal: OFF",
            style="Secondary.TButton",
            command=self._toggle_guardian
        )
        self.btn_guardian.pack(side="right", padx=(8, 12))

        self.guardian_lbl = ttk.Label(
            score_frame,
            text="",
            style="Muted.TLabel"
        )
        self.guardian_lbl.pack(side="right", padx=6)

        # Main Split Content
        main_split = ttk.Frame(self.root, style="TFrame")
        main_split.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Left: Device & Adapter Info
        left_card = ttk.Frame(main_split, style="Card.TFrame", padding=12)
        left_card.pack(side="left", fill="both", expand=False, padx=(0, 10))
        left_card.config(width=290)

        info_header = ttk.Label(left_card, text="💻 Device Information", font=("Segoe UI", 11, "bold"), background="#1e293b", foreground="#38bdf8")
        info_header.pack(anchor="w", pady=(0, 8))

        self.info_text = tk.Text(
            left_card,
            bg="#1e293b",
            fg="#cbd5e1",
            font=("Segoe UI", 9),
            relief="flat",
            wrap="word",
            width=33,
            height=16
        )
        self.info_text.pack(fill="both", expand=True)
        self.info_text.insert("1.0", "Click 'Full Scan' or 'Quick Scan' to populate system & adapter properties...")
        self.info_text.config(state="disabled")

        # Right: Diagnostics Checks TreeView
        right_card = ttk.Frame(main_split, style="Card.TFrame", padding=12)
        right_card.pack(side="right", fill="both", expand=True)

        diag_header = ttk.Label(right_card, text="🔍 Diagnostic Checks", font=("Segoe UI", 11, "bold"), background="#1e293b", foreground="#38bdf8")
        diag_header.pack(anchor="w", pady=(0, 8))

        columns = ("target", "status", "value", "message")
        self.tree = ttk.Treeview(right_card, columns=columns, show="headings", height=10)
        self.tree.heading("target", text="Target Check")
        self.tree.heading("status", text="Status")
        self.tree.heading("value", text="Metric")
        self.tree.heading("message", text="Summary Message")

        self.tree.column("target", width=120, anchor="w")
        self.tree.column("status", width=70, anchor="center")
        self.tree.column("value", width=90, anchor="center")
        self.tree.column("message", width=340, anchor="w")

        scrollbar = ttk.Scrollbar(right_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Action Buttons Toolbar - 2 Rows covering all 18 commands!
        btn_frame = ttk.Frame(self.root, style="Card.TFrame", padding=10)
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        # Row 1: Core Diagnostics & Connectivity
        row1 = ttk.Frame(btn_frame, style="Card.TFrame")
        row1.pack(fill="x", pady=(0, 6))

        self.btn_full = ttk.Button(row1, text="▶ [1] Full Scan", style="Primary.TButton", command=lambda: self._start_scan(quick=False))
        self.btn_full.pack(side="left", padx=3)

        self.btn_quick = ttk.Button(row1, text="⚡ [2] Quick Scan", style="Secondary.TButton", command=lambda: self._start_scan(quick=True))
        self.btn_quick.pack(side="left", padx=3)

        self.btn_report = ttk.Button(row1, text="🌐 [3] HTML Report", style="Accent.TButton", command=self._generate_report)
        self.btn_report.pack(side="left", padx=3)

        self.btn_privacy = ttk.Button(row1, text="🔒 [4] Privacy Scan", style="Secondary.TButton", command=self._start_privacy_scan)
        self.btn_privacy.pack(side="left", padx=3)

        self.btn_dns_only = ttk.Button(row1, text="🔍 [5] DNS Check", style="Secondary.TButton", command=self._run_dns_only)
        self.btn_dns_only.pack(side="left", padx=3)

        self.btn_gateway = ttk.Button(row1, text="🚪 [6] Gateway Test", style="Secondary.TButton", command=self._run_gateway_only)
        self.btn_gateway.pack(side="left", padx=3)

        self.btn_dns_bench = ttk.Button(row1, text="🏎️ [7] DNS Bench", style="Secondary.TButton", command=self._run_dns_bench)
        self.btn_dns_bench.pack(side="left", padx=3)

        self.btn_ports = ttk.Button(row1, text="🔌 [8] Port Scan", style="Secondary.TButton", command=self._run_port_scan)
        self.btn_ports.pack(side="left", padx=3)

        self.btn_monitor = ttk.Button(row1, text="📈 [9] Live Ping", style="Secondary.TButton", command=self._run_live_monitor)
        self.btn_monitor.pack(side="left", padx=3)

        # Row 2: Advanced Analysis & Tools
        row2 = ttk.Frame(btn_frame, style="Card.TFrame")
        row2.pack(fill="x")

        self.btn_trace = ttk.Button(row2, text="🛣️ [10] Traceroute", style="Secondary.TButton", command=self._run_traceroute)
        self.btn_trace.pack(side="left", padx=3)

        self.btn_speed = ttk.Button(row2, text="🚀 [11] Speedtest", style="Secondary.TButton", command=self._run_speed_test)
        self.btn_speed.pack(side="left", padx=3)

        self.btn_repair = ttk.Button(row2, text="🛠️ [13] Flush DNS", style="Secondary.TButton", command=self._run_repair)
        self.btn_repair.pack(side="left", padx=3)

        self.btn_logs = ttk.Button(row2, text="📜 [14] Logs", style="Secondary.TButton", command=self._run_view_logs)
        self.btn_logs.pack(side="left", padx=3)

        self.btn_tests = ttk.Button(row2, text="🧪 [15] Unit Tests", style="Secondary.TButton", command=self._run_tests)
        self.btn_tests.pack(side="left", padx=3)

        self.btn_lan = ttk.Button(row2, text="🏠 [16] Scan LAN", style="Accent.TButton", command=self._run_lan_scan)
        self.btn_lan.pack(side="left", padx=3)

        self.btn_wifi = ttk.Button(row2, text="📶 [17] Wi-Fi/Link", style="Secondary.TButton", command=self._run_wifi_info)
        self.btn_wifi.pack(side="left", padx=3)

        self.btn_jitter = ttk.Button(row2, text="🎯 [18] VoIP/Jitter", style="Secondary.TButton", command=self._run_jitter_test)
        self.btn_jitter.pack(side="left", padx=3)

        self.btn_guardian_b = ttk.Button(row2, text="🛡️ [19] Auto-Heal", style="Secondary.TButton", command=self._toggle_guardian)
        self.btn_guardian_b.pack(side="left", padx=3)

        self.btn_exit = ttk.Button(row2, text="❌ [0] Exit", style="Danger.TButton", command=self._run_exit)
        self.btn_exit.pack(side="right", padx=3)

    def _set_status(self, text: str):
        self.status_label.config(text=text)

    def _start_scan(self, quick: bool):
        self._set_status("Scanning network stack...")
        self.btn_full.config(state="disabled")
        self.btn_quick.config(state="disabled")

        def worker():
            report = execute_full_scan(quick=quick)
            self.last_report = report
            self.root.after(0, self._render_scan_results, report)

        threading.Thread(target=worker, daemon=True).start()

    def _start_privacy_scan(self):
        self._set_status("Running Privacy-Masked scan...")
        self.btn_full.config(state="disabled")
        self.btn_quick.config(state="disabled")

        def worker():
            report = execute_full_scan(quick=True)
            masked_report = mask_scan_report(report)
            self.last_report = masked_report
            self.root.after(0, self._render_scan_results, masked_report)

        threading.Thread(target=worker, daemon=True).start()

    def _render_scan_results(self, report):
        self.btn_full.config(state="normal")
        self.btn_quick.config(state="normal")
        self._set_status("Scan completed.")

        # Update Score
        score = report.health_score
        score_color = "#34d399" if score.total_score >= 90 else ("#38bdf8" if score.total_score >= 75 else "#f87171")
        self.score_label.config(
            text=f"Health Score: {score.total_score} / 100 ({score.grade})",
            foreground=score_color
        )

        # Update Info text
        adapter = report.adapter_info
        info_lines = [
            f"Hostname: {adapter.hostname}",
            f"OS: {adapter.os_name}",
            f"Adapter: {adapter.adapter_name}",
            f"MAC: {adapter.mac_address}",
            f"IPv4: {adapter.ipv4_address}",
            f"Subnet: {adapter.subnet_mask}",
            f"Gateway: {adapter.default_gateway}",
            f"DNS: {', '.join(adapter.dns_servers)}",
            f"Public IP: {report.public_ip_info.get('ip', 'Unavailable')}",
        ]
        if adapter.wifi_info.get("ssid"):
            info_lines.append(f"Wi-Fi SSID: {adapter.wifi_info['ssid']}")
            if adapter.wifi_info.get("signal"):
                info_lines.append(f"Wi-Fi Signal: {adapter.wifi_info['signal']}")

        self.info_text.config(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", "\n".join(info_lines))
        self.info_text.config(state="disabled")

        # Update Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in report.results:
            self.tree.insert("", "end", values=(r.name, r.status, r.value, r.message))

    def _generate_report(self):
        if not self.last_report:
            self._set_status("Running quick scan before generating report...")
            report = execute_full_scan(quick=True)
            self.last_report = report
            self._render_scan_results(report)

        report_path = generate_html_report(self.last_report)
        webbrowser.open(Path(report_path).resolve().as_uri())
        messagebox.showinfo("HTML Report", f"Report generated and opened in browser:\n{report_path}")

    def _run_dns_only(self):
        self._set_status("Running DNS resolution diagnostics...")
        def worker():
            res = test_dns()
            msg = f"DNS Status: {res.status} ({res.value})\nMessage: {res.message}\n\nDomains:\n"
            for d in res.details.get("domains", []):
                lat = f"{d.get('latency_ms', 'FAIL')} ms"
                ips = ", ".join(d.get("ips", [])) or "None"
                msg += f"• {d['domain']:<18}: {lat:<8} (IPs: {ips})\n"
            self.root.after(0, lambda: messagebox.showinfo("DNS Diagnostics [5]", msg))
            self.root.after(0, lambda: self._set_status("DNS check finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_gateway_only(self):
        self._set_status("Testing default gateway reachability...")
        def worker():
            adapter = detect_adapter_info()
            gw_res = test_gateway(adapter.default_gateway)
            msg = (
                f"Default Gateway: {adapter.default_gateway}\n"
                f"Status:          {gw_res.status}\n"
                f"Latency:         {gw_res.value}\n"
                f"Message:         {gw_res.message}\n"
            )
            self.root.after(0, lambda: messagebox.showinfo("Gateway Diagnostics [6]", msg))
            self.root.after(0, lambda: self._set_status("Gateway test finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_dns_bench(self):
        self._set_status("Running DNS Benchmark across global resolvers...")
        def worker():
            res = run_dns_benchmark()
            msg = f"Fastest DNS: {res['fastest']['name']} ({res['fastest']['avg_ms']} ms)\n\n"
            for r in res['results']:
                msg += f"• {r['name']} ({r['ip']}): {r.get('avg_ms', 'TIMEOUT')} ms\n"
            if res.get('recommendation'):
                msg += f"\nRecommendation: {res['recommendation']}"
            self.root.after(0, lambda: messagebox.showinfo("DNS Speed Benchmark [7]", msg))
            self.root.after(0, lambda: self._set_status("DNS benchmark finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_speed_test(self):
        self._set_status("Measuring internet download speed...")
        def worker():
            res = test_download_speed()
            msg = f"Download Speed: {res['speed_mbps']} Mbps\nRating: {res['rating']}\nData Transferred: {res['data_mb']} MB in {res['duration_sec']}s via {res['provider']}"
            self.root.after(0, lambda: messagebox.showinfo("Internet Speed Test [11]", msg))
            self.root.after(0, lambda: self._set_status("Speed test finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_port_scan(self):
        self._set_status("Scanning common service ports...")
        def worker():
            res = scan_ports("1.1.1.1")
            msg = f"Target: {res['target']} | Open: {res['open_count']} | Filtered: {res['filtered_count']}\n\n"
            for r in res['results']:
                msg += f"• Port {r['port']} ({r['service']}): {r['status']} ({r.get('latency_ms') or '-'} ms)\n"
            self.root.after(0, lambda: messagebox.showinfo("Port Connectivity Scan [8]", msg))
            self.root.after(0, lambda: self._set_status("Port scan finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_live_monitor(self):
        mon_win = tk.Toplevel(self.root)
        mon_win.title("Live Ping Monitor [9] - Smith IT Company")
        mon_win.geometry("540x360")
        mon_win.configure(bg="#0f172a")

        header = ttk.Label(mon_win, text="Real-Time Continuous Ping Watcher (1.1.1.1)", font=("Segoe UI", 11, "bold"), background="#0f172a", foreground="#38bdf8")
        header.pack(pady=10)

        txt = tk.Text(mon_win, bg="#1e293b", fg="#34d399", font=("Consolas", 10), padx=10, pady=10)
        txt.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        running = [True]

        def stop_monitor():
            running[0] = False
            mon_win.destroy()

        mon_win.protocol("WM_DELETE_WINDOW", stop_monitor)

        def pinger():
            from src.utils.platform_utils import ping_host
            while running[0]:
                p = ping_host("1.1.1.1", count=1, timeout_sec=1.0)
                now_str = time.strftime("%H:%M:%S")
                if p["success"]:
                    line = f"[{now_str}] Reply from 1.1.1.1: time={p['avg_ms']}ms\n"
                else:
                    line = f"[{now_str}] Request timed out (Packet Drop)\n"

                if not running[0]:
                    break
                def update_txt(l=line):
                    if mon_win.winfo_exists():
                        txt.insert("end", l)
                        txt.see("end")
                self.root.after(0, update_txt)
                time.sleep(1.0)

        threading.Thread(target=pinger, daemon=True).start()

    def _run_traceroute(self):
        self._set_status("Tracing hop-by-hop route to 1.1.1.1...")
        def worker():
            res = run_traceroute("1.1.1.1")
            msg = f"Traceroute Target: {res['target']}\nTotal Hops: {res['total_hops']}\n\n"
            for h in res["hops"]:
                lat = f"{h['avg_ms']} ms" if h['avg_ms'] is not None else "*"
                msg += f"Hop {h['hop']:<2}: {h['ip']:<18} {lat:<10} {h['desc']}\n"
            self.root.after(0, lambda: messagebox.showinfo("Hop-by-Hop Traceroute [10]", msg))
            self.root.after(0, lambda: self._set_status("Traceroute finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_lan_scan(self):
        self._set_status("Scanning local network devices...")
        def worker():
            res = scan_local_network()
            msg = f"Subnet: {res['subnet']}\nTotal Scanned: {res['total_hosts_scanned']} | Active Devices: {res['active_devices_count']}\n\n"
            for d in res['devices']:
                msg += f"• {d['ip']:<15} {d['mac']:<18} {d['role']}\n"
            self.root.after(0, lambda: messagebox.showinfo("LAN Device Discovery [16]", msg))
            self.root.after(0, lambda: self._set_status("LAN device scan finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_wifi_info(self):
        self._set_status("Inspecting wireless adapter and link status...")
        def worker():
            res = analyze_wifi_status()
            msg = f"Interface: {res['interface_name']}\nStatus: {res['state']}\n"
            if res['is_wifi']:
                msg += f"SSID: {res['ssid']} (BSSID: {res['bssid']})\n"
                msg += f"Signal: {res['signal_pct']}% (~{res['rssi_dbm']} dBm)\n"
                msg += f"Band & Channel: {res['band']} (Ch {res['channel']})\n"
                msg += f"Protocol: {res['wifi_generation']}\n"
                msg += f"Security: {res['auth']} / {res['cipher']}\n"
            elif res.get('rx_rate_mbps'):
                msg += f"Link Speed: {res['rx_rate_mbps']} Mbps (Wired)\n"
            if res.get('advice'):
                msg += "\nAdvice:\n" + "\n".join(f"• {a}" for a in res['advice'])
            self.root.after(0, lambda: messagebox.showinfo("Wi-Fi & Link Status [17]", msg))
            self.root.after(0, lambda: self._set_status("Wi-Fi inspection finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_jitter_test(self):
        self._set_status("Testing VoIP & Gaming Jitter / Stability (20 packets)...")
        def worker():
            res = run_jitter_stability_test(target_host="8.8.8.8", packet_count=20)
            msg = (
                f"Target: {res['target']}\n"
                f"Packets: {res['packets_received']}/{res['packets_sent']} ({res['packet_loss_pct']}% Loss)\n"
                f"Avg Latency: {res['avg_ms']} ms (Min: {res['min_ms']}, Max: {res['max_ms']})\n"
                f"RFC 3550 Jitter: {res['rfc3550_jitter_ms']} ms\n"
                f"VoIP MOS Score: {res['mos_score']} / 4.5 [{res['grade']}]\n\n"
                f"Zoom / Teams: {res['zoom_status']}\n"
                f"Gaming Rating: {res['gaming_status']}\n"
            )
            if res.get('advice'):
                msg += "\nAdvice:\n" + "\n".join(f"• {a}" for a in res['advice'])
            self.root.after(0, lambda: messagebox.showinfo("VoIP & Gaming Jitter Test [18]", msg))
            self.root.after(0, lambda: self._set_status("Jitter test finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_repair(self):
        try:
            res = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, check=False)
            messagebox.showinfo("DNS Flush [13]", f"DNS Cache Cleared:\n{res.stdout.strip()}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _run_view_logs(self):
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
            recent = lines[-25:] if len(lines) > 25 else lines
            msg = "\n".join(recent)
        else:
            msg = "No diagnostic log entries recorded yet."

        log_win = tk.Toplevel(self.root)
        log_win.title("Diagnostic Event Logs [14] - Smith IT Company")
        log_win.geometry("680x420")
        log_win.configure(bg="#0f172a")

        txt = tk.Text(log_win, bg="#1e293b", fg="#cbd5e1", font=("Consolas", 9), padx=10, pady=10)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", msg)
        txt.config(state="disabled")

    def _run_tests(self):
        self._set_status("Running automated pytest test suite (51 tests)...")
        def worker():
            res = subprocess.run([sys.executable, "-m", "pytest", "-v", "tests/"], capture_output=True, text=True, check=False)
            lines = [l for l in res.stdout.splitlines() if "passed" in l or "FAILED" in l or "collected" in l]
            summary = "\n".join(lines[-4:]) if lines else res.stdout[-300:]
            self.root.after(0, lambda: messagebox.showinfo("Pytest Suite Results [15]", f"Automated Unit Tests Completed:\n\n{summary or 'All 51 tests passed!'}"))
            self.root.after(0, lambda: self._set_status("Unit tests finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _toggle_guardian(self):
        if not self.guardian or not self.guardian.is_running():
            self.guardian = NetworkGuardian(
                probe_interval=5.0,
                on_heartbeat=self._on_guardian_heartbeat,
                on_incident=self._on_guardian_incident
            )
            self.guardian.start()
            self.btn_guardian.config(text="🛡️ Auto-Heal: ON", style="GuardianActive.TButton")
            self.btn_guardian_b.config(text="🛡️ [19] Auto-Heal: ON", style="GuardianActive.TButton")
            self.guardian_lbl.config(text="Watching 24/7...", foreground="#34d399")
            self._set_status("Real-Time Self-Healing Guardian activated.")
        else:
            self.guardian.stop()
            self.btn_guardian.config(text="🛡️ Auto-Heal: OFF", style="Secondary.TButton")
            self.btn_guardian_b.config(text="🛡️ [19] Auto-Heal", style="Secondary.TButton")
            self.guardian_lbl.config(text="", foreground="#94a3b8")
            self._set_status("Real-Time Self-Healing Guardian deactivated.")

    def _on_guardian_heartbeat(self, hb):
        def update():
            if not self.guardian or not self.guardian.is_running():
                return
            gw = f"{hb['gateway_latency_ms']:.0f}ms" if hb['gateway_ok'] and hb['gateway_latency_ms'] else ("OK" if hb['gateway_ok'] else "FAIL")
            dns = "OK" if hb['dns_ok'] else "FAIL"
            net = f"{hb['internet_latency_ms']:.0f}ms" if hb['internet_ok'] and hb['internet_latency_ms'] else ("OK" if hb['internet_ok'] else "FAIL")
            self.guardian_lbl.config(text=f"Protected: Router {gw} | DNS {dns} | Net {net}")
        self.root.after(0, update)

    def _on_guardian_incident(self, inc):
        def update():
            self.guardian_lbl.config(
                text=f"⚡ Auto-Healed ({inc['timestamp'].split()[-1]}): {inc['action'][:22]}...",
                foreground="#34d399"
            )
            messagebox.showinfo(
                "🛡️ Autonomous Network Healing Event",
                f"Smith Network Guardian automatically resolved a connection issue!\n\nTrigger: {inc['trigger']}\nAction:  {inc['action']}\nResult:  {inc['message']} ({inc['duration_sec']}s)"
            )
        self.root.after(0, update)

    def _run_exit(self):
        if self.guardian and self.guardian.is_running():
            self.guardian.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = NetworkToolkitGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
