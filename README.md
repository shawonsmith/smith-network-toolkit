# Smith Network Diagnostic Toolkit 🛠️🌐

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style: Clean](https://img.shields.io/badge/code%20style-modular-brightgreen.svg)]()
[![Build & Tests](https://img.shields.io/badge/tests-passing-success.svg)]()

A lightweight, modular, and cross-platform network troubleshooting toolkit engineered for IT support students, junior systems engineers, helpdesk technicians, and small office administrators. It systematically diagnoses connectivity issues, assigns an empirical 0–100 health score, diagnoses root causes (e.g., DHCP APIPA failure, DNS resolver failure, ISP/upstream outages, local router issues), and generates readable terminal dashboards and modern HTML reports.

---

## Overview

Troubleshooting network issues on end-user machines often leads to guesswork: guessing whether the Wi-Fi is broken, if the router is down, if DNS has stalled, or if the ISP is suffering an upstream outage.

**Smith Network Diagnostic Toolkit** replaces guesswork with structured diagnostic evidence. In seconds, it audits:
- **Local Network Stack**: Hostname, OS, primary network interface, MAC address, IPv4 address, and subnet mask.
- **Gateway Reachability**: Local default router discovery and latency benchmark (with ICMP and TCP fallback).
- **Multi-Stage Internet Connectivity**: Differentiates between local LAN failure, ISP upstream loss, and DNS resolution failures.
- **Isolated DNS Performance**: Benchmarks domain resolution response times against major internet infrastructure independently of web browsing.
- **Link Stability**: High-precision packet loss grading and round-trip latency statistics.
- **Informational Public IP**: Automatic external IPv4 detection.
- **100-Point Health Score**: Weighted scoring system grading overall connection health from *Poor* to *Excellent*.
- **Root-Cause Diagnosis Engine**: Rule-based detection pinpointing specific issues (APIPA 169.254.x.x, ISP outages, packet loss spikes) with step-by-step remediation advice.
- **Privacy Shield**: Built-in `--privacy` masking for screenshots, bug reports, and portfolio sharing.
- **Export Formats**: Modern standalone responsive HTML dashboard reports and JSON output for automated pipelines.

---

## Why I Built This

> *"I built this project to practise structured IT support troubleshooting and demonstrate how common network problems can be diagnosed using evidence rather than guesswork."*

In IT helpdesk and support environments, junior technicians often execute disjointed commands (`ping 8.8.8.8`, `ipconfig`, `tracert`) without a unified mental model of the network layers. This project synthesizes foundational networking principles (OSI Layers 2 through 7) into a clean, reproducible, and automated workflow.

---

## Features

- ⚡ **Zero-Delay Diagnostics**: Rapid scans complete in seconds using non-blocking socket checks and optimized ping counts.
- 🛡️ **Firewall & ICMP Resilient**: Automatic TCP handshake fallback ensures accurate testing even when local firewalls or upstream ISPs block ICMP ping.
- 🎯 **Dual-Tier Latency Scoring**: Distinguishes local LAN latency (router) from regional internet latency, preventing international distance from unfairly penalizing a healthy local connection.
- 🔒 **Privacy Mode**: Masks sensitive private IPs (`192.168.0.xxx`), public IPs (`103.xxx.xxx.128`), and MAC addresses across CLI, JSON, HTML reports, and log files.
- 📊 **Modern HTML Report**: Beautiful, single-file, responsive dashboard featuring circular SVG health gauges, summary cards, diagnostic tables, and remediation lists.
- 🤖 **Automated Diagnostics**: Evaluates 6+ industry troubleshooting rules and provides numbered action steps.
- 💻 **Cross-Platform**: Fully tested on Windows 10/11, Linux, and macOS.

---

## How It Works

When launched, the toolkit executes a methodical top-to-bottom troubleshooting pipeline:

```text
       START
         │
         ▼
 ┌───────────────┐
 │   Detect OS   │ ──► Hostname, OS distribution/version
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │  Network NIC  │ ──► Active adapter, MAC, IPv4, Subnet, APIPA check
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ Find Gateway  │ ──► Auto-discover default router IP
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ Test Gateway  │ ──► ICMP Ping + TCP 80/53 fallback (<15 ms expected)
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ Test Internet │ ──► Stage 1: Gateway -> Stage 2: Direct IP -> Stage 3: HTTPS
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │   Test DNS    │ ──► Domain resolution speed across Google, Cloudflare, GitHub
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ Latency & Loss│ ──► Multi-target RTT metrics & packet loss grading
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │   Public IP   │ ──► External IPv4 lookup (informational only)
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ Diagnosis &   │ ──► Evaluate troubleshooting rules & 100-pt rubric
 │ Health Score  │
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ Output Report │ ──► Rich Terminal Console, JSON, or Modern HTML Dashboard
 └───────────────┘
```

---

## Installation

### Prerequisites
- Python 3.8 or higher
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/smith-network-toolkit.git
cd smith-network-toolkit
```

### 2. Create Virtual Environment & Install Dependencies
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

---

## Usage

Run standard full scan:
```bash
python run.py
```

### Command-Line Options

| Command | Purpose |
| :--- | :--- |
| `python run.py` | Full end-to-end network diagnostic scan |
| `python run.py --quick` | Rapid scan using fewer test packets |
| `python run.py --report` | Generate modern HTML report in `reports/` |
| `python run.py --privacy` | Mask private IP, public IP, and MAC addresses |
| `python run.py --json` | Output machine-readable JSON to stdout |
| `python run.py --dns` | Run isolated DNS resolution benchmarks only |
| `python run.py --gateway` | Run gateway detection and ping only |
| `python run.py --output custom.html` | Specify custom path for HTML report |

---

## Example Terminal Output

### Standard Scan
```text
┌──────────────────────────────────────────────────┐
│ SMITH NETWORK DIAGNOSTIC TOOLKIT                 │
│ Automated Network Troubleshooting & Health Score │
└──────────────────────────────────────────────────┘
        Device & Network Adapter        
                                        
  Hostname           DESKTOP-TJEGCB6    
  Operating System   Windows 10         
  Adapter Name       Ethernet           
  MAC Address        1C-1B-0D-7F-88-64  
  IPv4 Address       192.168.0.205      
  Subnet Mask        255.255.255.0      
  Default Gateway    192.168.0.1        
  DNS Servers        192.168.0.1        
  Public IP          103.16.248.128     
                                        
                               Diagnostic Checks                               
┌──────────────┬────────┬─────────────────┬───────────────────────────────────┐
│ Target Check │ Status │ Measured Metric │ Summary Message                   │
├──────────────┼────────┼─────────────────┼───────────────────────────────────┤
│ Gateway      │ [PASS] │ <1 ms           │ Gateway reachable                 │
│ Internet     │ [PASS] │ Connected       │ Internet connection healthy.      │
│ DNS          │ [PASS] │ 22 ms           │ DNS resolution is fast and        │
│              │        │                 │ consistent.                       │
│ Packet Loss  │ [PASS] │ 0%              │ No packet loss detected.          │
│ Latency      │ [PASS] │ 14 ms           │ Low latency connection.           │
└──────────────┴────────┴─────────────────┴───────────────────────────────────┘
╔═══════════════════════════════════════════╗
║ Network Health Score: 100/100 (Excellent) ║
╚═══════════════════════════════════════════╝

[PASS] No network connectivity or DNS issues identified.
```

### Privacy Mode Output (`--privacy`)
```text
┌─────────────────────────────────────────────────────────────────────────┐
│ SMITH NETWORK DIAGNOSTIC TOOLKIT                                        │
│ Automated Network Troubleshooting & Health Score  [Privacy Mode Active] │
└─────────────────────────────────────────────────────────────────────────┘
        Device & Network Adapter        
                                        
  Hostname           DESKTOP-TJEGCB6    
  Operating System   Windows 10         
  Adapter Name       Ethernet           
  MAC Address        1C-xx-xx-xx-88-xx  
  IPv4 Address       192.168.0.xxx      
  Subnet Mask        255.255.255.0      
  Default Gateway    192.168.0.xxx      
  DNS Servers        192.168.0.xxx      
  Public IP          103.xxx.xxx.128    
```

---

## Diagnostic Logic & Root-Cause Rules

| Rule ID | Condition | Diagnosis | Actionable Advice |
| :--- | :--- | :--- | :--- |
| **RULE-01-APIPA** | IP is `169.254.x.x` | **DHCP Assignment Failure** | Power cycle router/DHCP server, check cable/Wi-Fi connection, run `ipconfig /renew`. |
| **RULE-02-DNS-FAIL** | IP reachable, DNS fails | **DNS Resolution Outage** | Change DNS to `1.1.1.1` or `8.8.8.8`, flush local DNS cache (`ipconfig /flushdns`). |
| **RULE-03-GATEWAY-DOWN** | Gateway unreachable | **Local Network Unreachable** | Inspect physical link, restart router/AP, verify static IP subnet configuration. |
| **RULE-04-ISP-OUTAGE** | Gateway up, External IP down | **ISP / Upstream Outage** | Check modem WAN indicator, reboot optical terminal (ONT)/modem, call ISP support. |
| **RULE-05-PACKET-LOSS** | Packet loss > 5% | **Unstable Connection** | Check for Wi-Fi interference, test wired Ethernet cable, check for bandwidth hogs. |
| **RULE-06-LAN-LATENCY** | Gateway latency > 15 ms | **High LAN Delay** | Local Wi-Fi congestion or interference. Move closer to AP or switch to 5 GHz. |
| **RULE-07-DNS-SLOW** | DNS avg latency > 200 ms | **Degraded DNS Speed** | Switch DNS resolver to Cloudflare (1.1.1.1) or Google (8.8.8.8). |

---

## Health Score Rubric (100 Points Total)

| Check Name | Points | Evaluation Criteria |
| :--- | :---: | :--- |
| **Valid IP Configuration** | 15 | Valid routable IPv4 assigned (0 pts if APIPA or absent) |
| **Gateway Detected** | 10 | Default gateway route present in routing table |
| **Gateway Reachable** | 15 | 15 pts (<5 ms), 12 pts (5-15 ms), 8 pts (>15 ms), 0 pts (down) |
| **Internet Reachability** | 20 | 20 pts (Full HTTPS), 10 pts (Direct IP ping only), 0 pts (offline) |
| **DNS Working** | 15 | 15 pts (<80 ms), 13 pts (80-200 ms), 8 pts (>200 ms), 0 pts (failed) |
| **Packet Loss** | 10 | 10 pts (0%), 9 pts (<=2%), 5 pts (3-5%), 0 pts (>5%) |
| **Internet Latency** | 10 | 10 pts (<80 ms), 8 pts (80-150 ms), 5 pts (>150 ms), 0 pts (down) |
| **Adapter Health** | 5 | Physical or wireless interface UP and operating |
| **Total** | **100** | **90-100: Excellent \| 75-89: Good \| 60-74: Needs Attention \| <60: Poor** |

*Note: External Public IP lookups are informational only and never deduct points.*

---

## Privacy Mode

Sharing screenshots or diagnostic files online often exposes internal IP schemes, MAC hardware IDs, and public IP locations.

Invoking `--privacy` automatically sanitizes:
- **Private IPv4**: `192.168.0.105` ➔ `192.168.0.xxx`
- **MAC Address**: `1C-1B-0D-7F-88-64` ➔ `1C-xx-xx-xx-88-xx`
- **Public IPv4**: `103.16.248.128` ➔ `103.xxx.xxx.128`
- **Logs & JSON**: Sanitization applies to `logs/toolkit.log`, stdout JSON, and HTML reports.

---

## Project Structure

```
smith-network-toolkit/
│
├── src/
│   ├── main.py                         # CLI entry point, argument parsing, rendering
│   │
│   ├── models/
│   │   └── result.py                   # Standardized DiagnosticResult & ScanReport models
│   │
│   ├── diagnostics/                    # Modular network inspection checks
│   │   ├── adapter.py                  # Hostname, OS, NIC, MAC, IPv4, Subnet, APIPA
│   │   ├── gateway.py                  # Default gateway discovery & ICMP/TCP ping
│   │   ├── connectivity.py             # Multi-stage internet check (Gateway -> IP -> HTTPS)
│   │   ├── dns.py                      # Pure DNS query resolution time & consistency
│   │   ├── latency.py                  # Dual-tier latency across Gateway & public hosts
│   │   ├── packet_loss.py              # Packet loss rate & quality grading
│   │   └── public_ip.py                # Public IP detection with fallback endpoints
│   │
│   ├── scoring/
│   │   └── health_score.py             # 100-point weighted health score rubric
│   │
│   ├── diagnosis/
│   │   └── diagnosis_engine.py         # Rule-based root-cause identification & recommendations
│   │
│   ├── reporting/
│   │   └── report_generator.py         # Self-contained, responsive HTML report generator
│   │
│   └── utils/
│       ├── platform_utils.py           # Cross-platform ping, TCP ping, routing utilities
│       ├── privacy.py                  # Privacy masking engine
│       └── logger.py                   # File logging to logs/toolkit.log
│
├── tests/                              # Comprehensive test suite with pytest & mock data
│   ├── test_adapter.py
│   ├── test_gateway.py
│   ├── test_connectivity.py
│   ├── test_dns.py
│   ├── test_packet_loss.py
│   ├── test_latency.py
│   ├── test_scoring.py
│   ├── test_diagnosis.py
│   └── test_privacy.py
│
├── reports/                            # Generated HTML diagnostic reports
├── logs/                               # Diagnostic event logs (logs/toolkit.log)
├── screenshots/                        # Terminal and report screenshots
├── README.md                           # Documentation
├── requirements.txt                    # Project dependencies
├── .gitignore                          # Git ignore configuration
├── LICENSE                             # MIT License
└── run.py                              # Convenient root runner script
```

---

## Testing

The test suite includes 23 unit tests with mock networking to test every scenario without requiring active internet:
- APIPA detection & diagnosis
- Gateway reachability and TCP fallback
- Tiered connectivity states (Healthy, Limited, ISP Down, LAN Down)
- DNS resolution timeouts and speed thresholds
- Packet loss grading calculations
- Health score edge cases (100% perfect, APIPA, DNS fail)
- Privacy masking verification

Run the complete test suite:
```bash
pytest -v tests/
```

---

## Roadmap

### Future Features (v2.0)
- [ ] **Cross-Platform GUI**: Modern desktop interface using PyQt / Tkinter / Electron.
- [ ] **Wi-Fi Signal Analysis**: RSSI signal strength (dBm), channel congestion, BSSID inspection.
- [ ] **Visual Traceroute**: Interactive hop-by-hop latency and autonomous system (ASN) path mapping.
- [ ] **Port Testing**: Built-in scanning for common service ports (SSH, RDP, HTTP, HTTPS).
- [ ] **DNS Benchmark**: Side-by-side benchmark comparing Google, Cloudflare, Quad9, and OpenDNS.
- [ ] **Automated AI Technician**: LLM-assisted root-cause explanations and command generation.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Author

**Shawon**  
Aspiring IT Support & Systems Engineer  
Passionate about automated diagnostics, networking fundamentals, and clean software design.
