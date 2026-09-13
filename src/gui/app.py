"""Desktop Graphical User Interface for Smith IT Company Network Diagnostic Toolkit."""

import sys
import os
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
from src.diagnostics.dns_benchmark import run_dns_benchmark
from src.diagnostics.ports import scan_ports
from src.diagnostics.speedtest import test_download_speed


class NetworkToolkitGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Smith IT Company Network Diagnostic Toolkit v1.0")
        self.root.geometry("960x680")
        self.root.minsize(850, 580)
        self.root.configure(bg="#0f172a")

        self.last_report = None
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

        # Buttons
        style.configure(
            "Primary.TButton",
            background="#2563eb",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padding=6
        )
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])

        style.configure(
            "Secondary.TButton",
            background="#334155",
            foreground="#ffffff",
            font=("Segoe UI", 9),
            padding=6
        )
        style.map("Secondary.TButton", background=[("active", "#475569")])

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

        sub_lbl = ttk.Label(header_frame, text="Automated Network Troubleshooting, Health Assessment & Diagnostic Engine", style="Muted.TLabel")
        sub_lbl.pack(anchor="w")

        # Status & Health Score Bar
        score_frame = ttk.Frame(self.root, style="Card.TFrame", padding=12)
        score_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.score_label = ttk.Label(
            score_frame,
            text="Health Score: Click 'Run Scan' to evaluate network",
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

        # Main Split Content
        main_split = ttk.Frame(self.root, style="TFrame")
        main_split.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Left: Device & Adapter Info
        left_card = ttk.Frame(main_split, style="Card.TFrame", padding=12)
        left_card.pack(side="left", fill="both", expand=False, padx=(0, 10))
        left_card.config(width=280)

        info_header = ttk.Label(left_card, text="💻 Device Information", font=("Segoe UI", 11, "bold"), background="#1e293b", foreground="#38bdf8")
        info_header.pack(anchor="w", pady=(0, 8))

        self.info_text = tk.Text(
            left_card,
            bg="#1e293b",
            fg="#cbd5e1",
            font=("Segoe UI", 9),
            relief="flat",
            wrap="word",
            width=32,
            height=16
        )
        self.info_text.pack(fill="both", expand=True)
        self.info_text.insert("1.0", "Click 'Run Scan' to populate system & adapter properties...")
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
        self.tree.column("message", width=300, anchor="w")

        scrollbar = ttk.Scrollbar(right_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Action Buttons Toolbar
        btn_frame = ttk.Frame(self.root, style="Card.TFrame", padding=10)
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_full = ttk.Button(btn_frame, text="▶ Full Scan", style="Primary.TButton", command=lambda: self._start_scan(quick=False))
        self.btn_full.pack(side="left", padx=4)

        self.btn_quick = ttk.Button(btn_frame, text="⚡ Quick Scan", style="Secondary.TButton", command=lambda: self._start_scan(quick=True))
        self.btn_quick.pack(side="left", padx=4)

        self.btn_report = ttk.Button(btn_frame, text="🌐 HTML Report", style="Secondary.TButton", command=self._generate_report)
        self.btn_report.pack(side="left", padx=4)

        self.btn_dns = ttk.Button(btn_frame, text="🏎️ DNS Benchmark", style="Secondary.TButton", command=self._run_dns_bench)
        self.btn_dns.pack(side="left", padx=4)

        self.btn_speed = ttk.Button(btn_frame, text="🚀 Speed Test", style="Secondary.TButton", command=self._run_speed_test)
        self.btn_speed.pack(side="left", padx=4)

        self.btn_ports = ttk.Button(btn_frame, text="🔌 Port Scan", style="Secondary.TButton", command=self._run_port_scan)
        self.btn_ports.pack(side="left", padx=4)

        self.btn_repair = ttk.Button(btn_frame, text="🛠️ Flush DNS", style="Secondary.TButton", command=self._run_repair)
        self.btn_repair.pack(side="right", padx=4)

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
            self._set_status("Running scan first before generating report...")
            report = execute_full_scan(quick=True)
            self.last_report = report
            self._render_scan_results(report)

        report_path = generate_html_report(self.last_report)
        webbrowser.open(Path(report_path).resolve().as_uri())
        messagebox.showinfo("HTML Report", f"Report generated and opened in browser:\n{report_path}")

    def _run_dns_bench(self):
        self._set_status("Running DNS Benchmark across global resolvers...")
        def worker():
            res = run_dns_benchmark()
            msg = f"Fastest DNS: {res['fastest']['name']} ({res['fastest']['avg_ms']} ms)\n\n"
            for r in res['results']:
                msg += f"• {r['name']} ({r['ip']}): {r.get('avg_ms', 'TIMEOUT')} ms\n"
            if res.get('recommendation'):
                msg += f"\nRecommendation: {res['recommendation']}"
            self.root.after(0, lambda: messagebox.showinfo("DNS Speed Benchmark", msg))
            self.root.after(0, lambda: self._set_status("DNS benchmark finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_speed_test(self):
        self._set_status("Measuring internet download speed...")
        def worker():
            res = test_download_speed()
            msg = f"Download Speed: {res['speed_mbps']} Mbps\nRating: {res['rating']}\nData Transferred: {res['data_mb']} MB in {res['duration_sec']}s via {res['provider']}"
            self.root.after(0, lambda: messagebox.showinfo("Internet Speed Test", msg))
            self.root.after(0, lambda: self._set_status("Speed test finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_port_scan(self):
        self._set_status("Scanning common service ports...")
        def worker():
            res = scan_ports("1.1.1.1")
            msg = f"Target: {res['target']} | Open: {res['open_count']} | Filtered: {res['filtered_count']}\n\n"
            for r in res['results']:
                msg += f"• Port {r['port']} ({r['service']}): {r['status']} ({r.get('latency_ms') or '-'} ms)\n"
            self.root.after(0, lambda: messagebox.showinfo("Port Connectivity Scan", msg))
            self.root.after(0, lambda: self._set_status("Port scan finished."))
        threading.Thread(target=worker, daemon=True).start()

    def _run_repair(self):
        try:
            res = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, check=False)
            messagebox.showinfo("DNS Flush", f"DNS Cache Cleared:\n{res.stdout.strip()}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


def main():
    root = tk.Tk()
    app = NetworkToolkitGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
