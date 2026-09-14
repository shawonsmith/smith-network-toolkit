"""Hop-by-hop visual traceroute module."""

import platform
import re
import subprocess
from typing import Dict, Any, List
from src.utils.logger import log_event


def run_traceroute(target: str = "1.1.1.1", max_hops: int = 15, timeout_ms: int = 800) -> Dict[str, Any]:
    """
    Execute hop-by-hop traceroute to target and parse latency per hop.
    Note: Timeouts ('* * *') or missing responses at intermediate router hops
    frequently indicate router ICMP rate-limiting or firewall policy rather than
    genuine packet loss, provided subsequent hops and the destination respond normally.
    """
    system = platform.system()
    log_event(f"Executing traceroute to {target} (max {max_hops} hops)...")

    if system == "Windows":
        cmd = ["tracert", "-d", "-w", str(timeout_ms), "-h", str(max_hops), target]
    else:
        cmd = ["traceroute", "-n", "-w", "1", "-m", str(max_hops), target]

    hops: List[Dict[str, Any]] = []

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=25.0,
            check=False
        )
        output = proc.stdout

        for line in output.splitlines():
            line = line.strip()
            # Windows format: 1    <1 ms    <1 ms    <1 ms  192.168.0.1
            # or:             2     *        *        *     Request timed out.
            win_match = re.match(r"^\s*(\d+)\s+([\s\S]+?)\s+((?:\d{1,3}\.){3}\d{1,3}|Request timed out\.?)$", line)
            if win_match:
                hop_num = int(win_match.group(1))
                rtt_part = win_match.group(2)
                ip_part = win_match.group(3)

                rtt_times = re.findall(r"(\d+(?:\.\d+)?)\s*ms|<1\s*ms|\*", rtt_part)
                avg_lat = None
                numeric_times = []
                for t in rtt_times:
                    if t == "<1 ms":
                        numeric_times.append(0.5)
                    elif t != "*":
                        try:
                            numeric_times.append(float(t))
                        except ValueError:
                            pass

                if numeric_times:
                    avg_lat = round(sum(numeric_times) / len(numeric_times), 1)

                is_timeout = "*" in rtt_part and not numeric_times

                desc = "Internet Transit"
                if hop_num == 1:
                    desc = "Local Router / Gateway"
                elif hop_num == 2:
                    desc = "ISP Gateway / Aggregation"
                elif ip_part == target:
                    desc = "Destination Target"

                hops.append({
                    "hop": hop_num,
                    "ip": ip_part if not is_timeout else "Request timed out",
                    "avg_ms": avg_lat,
                    "timeout": is_timeout,
                    "desc": desc
                })

        return {
            "target": target,
            "success": len(hops) > 0,
            "hops": hops,
            "total_hops": len(hops)
        }
    except Exception as e:
        log_event(f"Traceroute error: {e}", "warning")
        return {
            "target": target,
            "success": False,
            "hops": [],
            "error": str(e)
        }
