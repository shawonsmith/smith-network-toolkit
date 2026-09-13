"""Self-contained, responsive HTML diagnostic report generator."""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.models.result import ScanReport


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smith IT Company Network Diagnostic Report - {hostname}</title>
    <style>
        :root {{
            --bg-body: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #273549;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #3b82f6;
            --primary-gradient: linear-gradient(135deg, #2563eb, #1d4ed8);
            --border: #334155;
            --pass-color: #10b981;
            --pass-bg: rgba(16, 185, 129, 0.15);
            --warn-color: #f59e0b;
            --warn-bg: rgba(245, 158, 11, 0.15);
            --fail-color: #ef4444;
            --fail-bg: rgba(239, 68, 68, 0.15);
            --radius-md: 10px;
            --radius-lg: 16px;
            --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}

        body {{
            background-color: var(--bg-body);
            color: var(--text-main);
            padding: 30px 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1050px;
            margin: 0 auto;
        }}

        .header {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: var(--shadow);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }}

        .header-title h1 {{
            font-size: 26px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 6px;
        }}

        .header-title p {{
            color: var(--text-muted);
            font-size: 14px;
        }}

        .badge-privacy {{
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
            border: 1px solid #3b82f6;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
        }}

        .score-banner {{
            display: flex;
            align-items: center;
            gap: 25px;
        }}

        .gauge-container {{
            position: relative;
            width: 110px;
            height: 110px;
        }}

        .gauge-svg {{
            transform: rotate(-90deg);
        }}

        .gauge-bg {{
            fill: none;
            stroke: #334155;
            stroke-width: 8;
        }}

        .gauge-fill {{
            fill: none;
            stroke: {score_color};
            stroke-width: 8;
            stroke-linecap: round;
            stroke-dasharray: 283;
            stroke-dashoffset: {dash_offset};
            transition: stroke-dashoffset 1s ease-in-out;
        }}

        .gauge-center {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }}

        .gauge-number {{
            font-size: 26px;
            font-weight: 800;
            color: {score_color};
            line-height: 1;
        }}

        .gauge-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
        }}

        @media (max-width: 768px) {{
            .grid-2 {{
                grid-template-columns: 1fr;
            }}
            .header {{
                flex-direction: column;
                align-items: flex-start;
            }}
        }}

        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 24px;
            box-shadow: var(--shadow);
        }}

        .card-header {{
            font-size: 17px;
            font-weight: 600;
            margin-bottom: 18px;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 10px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 10px;
        }}

        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 14px;
        }}

        .info-row:last-child {{
            border-bottom: none;
        }}

        .info-label {{
            color: var(--text-muted);
        }}

        .info-val {{
            color: var(--text-main);
            font-weight: 600;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}

        th {{
            text-align: left;
            padding: 12px 14px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }}

        td {{
            padding: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            vertical-align: middle;
        }}

        .badge {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            display: inline-block;
            text-align: center;
        }}

        .badge-pass {{
            background: var(--pass-bg);
            color: var(--pass-color);
            border: 1px solid var(--pass-color);
        }}

        .badge-warn {{
            background: var(--warn-bg);
            color: var(--warn-color);
            border: 1px solid var(--warn-color);
        }}

        .badge-fail {{
            background: var(--fail-bg);
            color: var(--fail-color);
            border: 1px solid var(--fail-color);
        }}

        .issue-box {{
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: var(--radius-md);
            padding: 16px;
            margin-bottom: 14px;
        }}

        .issue-box.warning {{
            background: rgba(245, 158, 11, 0.08);
            border-color: rgba(245, 158, 11, 0.3);
        }}

        .issue-title {{
            font-weight: 700;
            font-size: 15px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .issue-desc {{
            color: var(--text-muted);
            font-size: 13.5px;
            margin-bottom: 10px;
        }}

        .rec-item {{
            margin-left: 20px;
            color: #cbd5e1;
            font-size: 13.5px;
            margin-bottom: 5px;
        }}

        .footer {{
            text-align: center;
            color: var(--text-muted);
            font-size: 13px;
            margin-top: 35px;
            padding-bottom: 20px;
        }}

        @media print {{
            body {{
                background-color: #ffffff;
                color: #0f172a;
                padding: 10px;
            }}
            .card, .header {{
                box-shadow: none;
                border: 1px solid #cbd5e1;
                background: #ffffff;
                color: #0f172a;
            }}
            .card-header {{
                color: #0f172a;
                border-bottom: 1px solid #e2e8f0;
            }}
            .info-label {{
                color: #475569;
            }}
            .info-val {{
                color: #0f172a;
            }}
            th {{
                color: #475569;
                border-bottom: 1px solid #cbd5e1;
            }}
            td {{
                border-bottom: 1px solid #e2e8f0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-title">
                <h1>Smith IT Company Network Diagnostic Toolkit</h1>
                <p>Automated Network Troubleshooting & Health Assessment Report</p>
                <div style="margin-top: 8px;">
                    <span class="badge-privacy">{privacy_badge_text}</span>
                    <span style="color: var(--text-muted); font-size: 12px; margin-left: 10px;">Generated: {timestamp}</span>
                </div>
            </div>
            <div class="score-banner">
                <div class="gauge-container">
                    <svg class="gauge-svg" width="110" height="110">
                        <circle class="gauge-bg" cx="55" cy="55" r="45"></circle>
                        <circle class="gauge-fill" cx="55" cy="55" r="45"></circle>
                    </svg>
                    <div class="gauge-center">
                        <div class="gauge-number">{total_score}</div>
                        <div class="gauge-label">{grade}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Info Grid -->
        <div class="grid-2">
            <!-- Device Info -->
            <div class="card">
                <div class="card-header">💻 Device & Network Adapter</div>
                <div class="info-row"><span class="info-label">Hostname</span><span class="info-val">{hostname}</span></div>
                <div class="info-row"><span class="info-label">Operating System</span><span class="info-val">{os_name}</span></div>
                <div class="info-row"><span class="info-label">Network Adapter</span><span class="info-val">{adapter_name}</span></div>
                <div class="info-row"><span class="info-label">MAC Address</span><span class="info-val">{mac_address}</span></div>
                <div class="info-row"><span class="info-label">IPv4 Address</span><span class="info-val">{ipv4_address}</span></div>
                <div class="info-row"><span class="info-label">Subnet Mask</span><span class="info-val">{subnet_mask}</span></div>
                <div class="info-row"><span class="info-label">Default Gateway</span><span class="info-val">{default_gateway}</span></div>
                <div class="info-row"><span class="info-label">DNS Servers</span><span class="info-val">{dns_servers}</span></div>
            </div>

            <!-- Public & Health Breakdown -->
            <div class="card">
                <div class="card-header">📊 Public Connection & Scoring</div>
                <div class="info-row"><span class="info-label">Public IPv4</span><span class="info-val">{public_ip}</span></div>
                <div class="info-row"><span class="info-label">Public IP Provider</span><span class="info-val">{public_ip_service}</span></div>
                <div class="info-row"><span class="info-label">Valid IP Config</span><span class="info-val">{score_ip}/15</span></div>
                <div class="info-row"><span class="info-label">Gateway Detected</span><span class="info-val">{score_gw_det}/10</span></div>
                <div class="info-row"><span class="info-label">Gateway Reachable</span><span class="info-val">{score_gw_reach}/15</span></div>
                <div class="info-row"><span class="info-label">Internet Reachability</span><span class="info-val">{score_internet}/20</span></div>
                <div class="info-row"><span class="info-label">DNS Resolution</span><span class="info-val">{score_dns}/15</span></div>
                <div class="info-row"><span class="info-label">Packet Loss Quality</span><span class="info-val">{score_loss}/10</span></div>
                <div class="info-row"><span class="info-label">Latency Quality</span><span class="info-val">{score_latency}/10</span></div>
                <div class="info-row"><span class="info-label">Adapter Health</span><span class="info-val">{score_adapter}/5</span></div>
            </div>
        </div>

        <!-- Diagnostic Table -->
        <div class="card" style="margin-bottom: 25px;">
            <div class="card-header">🔍 Diagnostic Checks Summary</div>
            <table>
                <thead>
                    <tr>
                        <th>Check Name</th>
                        <th>Status</th>
                        <th>Measured Metric</th>
                        <th>Summary Message</th>
                    </tr>
                </thead>
                <tbody>
                    {diagnostic_rows}
                </tbody>
            </table>
        </div>

        <!-- Identified Issues & Recommendations -->
        <div class="card">
            <div class="card-header">🛠️ Root-Cause Diagnosis & IT Recommendations</div>
            {issues_html}
        </div>

        <div class="footer">
            Smith IT Company Network Diagnostic Toolkit v{version} • Engineered for IT Support & Systems Diagnostics
        </div>
    </div>
</body>
</html>
"""


def generate_html_report(
    report: ScanReport,
    output_path: Optional[str] = None
) -> str:
    """Generate modern, responsive HTML report from a ScanReport model."""
    adapter = report.adapter_info
    score = report.health_score

    # Score color
    if score.total_score >= 90:
        score_color = "#10b981"
    elif score.total_score >= 75:
        score_color = "#3b82f6"
    elif score.total_score >= 60:
        score_color = "#f59e0b"
    else:
        score_color = "#ef4444"

    # SVG dash offset: circumference = 2 * pi * 45 = 282.74 ~ 283
    dash_offset = int(283 - (score.total_score / 100.0) * 283)

    # Privacy badge text
    privacy_badge = "🔒 Privacy Masked" if report.is_privacy_masked else "🌐 Full Diagnostics"

    # Public IP details
    pub_ip = report.public_ip_info.get("ip", "Unavailable")
    pub_service = report.public_ip_info.get("service", "None")

    # Diagnostic table rows
    table_rows = []
    for r in report.results:
        if r.status == "PASS":
            badge_class = "badge-pass"
            badge_icon = "✓ PASS"
        elif r.status == "WARN":
            badge_class = "badge-warn"
            badge_icon = "⚠ WARN"
        else:
            badge_class = "badge-fail"
            badge_icon = "✕ FAIL"

        row = f"""<tr>
            <td style="font-weight: 600;">{r.name}</td>
            <td><span class="badge {badge_class}">{badge_icon}</span></td>
            <td style="font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-weight: 600;">{r.value}</td>
            <td style="color: var(--text-muted);">{r.message}</td>
        </tr>"""
        table_rows.append(row)

    diagnostic_rows = "\n".join(table_rows)

    # Diagnosed Issues HTML
    if not report.diagnosed_issues:
        issues_html = """<div style="padding: 20px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; color: #10b981;">
            <strong>✓ All Network Checks Passed!</strong>
            <p style="margin-top: 6px; color: #94a3b8; font-size: 14px;">No configuration anomalies, DNS failures, or packet loss issues detected on this connection.</p>
        </div>"""
    else:
        issues_list = []
        for item in report.diagnosed_issues:
            box_type = "warning" if item.severity == "warning" else "error"
            badge_color = "#f59e0b" if item.severity == "warning" else "#ef4444"
            recs_html = "".join([f"<li class='rec-item'>{rec}</li>" for rec in item.recommendations])

            block = f"""<div class="issue-box {box_type}">
                <div class="issue-title" style="color: {badge_color};">
                    <span>⚠</span> {item.title} <span style="font-size: 11px; font-weight: normal; color: var(--text-muted);">[{item.rule_id}]</span>
                </div>
                <div class="issue-desc">{item.description}</div>
                <div style="font-weight: 600; font-size: 13.5px; margin-bottom: 6px;">Recommended Actions:</div>
                <ul>{recs_html}</ul>
            </div>"""
            issues_list.append(block)
        issues_html = "\n".join(issues_list)

    # DNS servers string
    dns_str = ", ".join(adapter.dns_servers) if adapter.dns_servers else "None"

    # Fill template
    html_content = REPORT_TEMPLATE.format(
        hostname=adapter.hostname,
        os_name=adapter.os_name,
        adapter_name=adapter.adapter_name,
        mac_address=adapter.mac_address,
        ipv4_address=adapter.ipv4_address,
        subnet_mask=adapter.subnet_mask,
        default_gateway=adapter.default_gateway,
        dns_servers=dns_str,
        public_ip=pub_ip,
        public_ip_service=pub_service,
        privacy_badge_text=privacy_badge,
        timestamp=report.timestamp,
        version=report.version,
        total_score=score.total_score,
        grade=score.grade,
        score_color=score_color,
        dash_offset=dash_offset,
        score_ip=score.breakdown.get("valid_ip", 0),
        score_gw_det=score.breakdown.get("gateway_detected", 0),
        score_gw_reach=score.breakdown.get("gateway_reachable", 0),
        score_internet=score.breakdown.get("internet_reachable", 0),
        score_dns=score.breakdown.get("dns_working", 0),
        score_loss=score.breakdown.get("packet_loss", 0),
        score_latency=score.breakdown.get("latency", 0),
        score_adapter=score.breakdown.get("adapter_healthy", 0),
        diagnostic_rows=diagnostic_rows,
        issues_html=issues_html
    )

    if not output_path:
        reports_dir = Path(__file__).resolve().parent.parent.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        file_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_file = reports_dir / f"network_report_{file_timestamp}.html"
    else:
        target_file = Path(output_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)

    target_file.write_text(html_content, encoding="utf-8")
    return str(target_file.resolve())
