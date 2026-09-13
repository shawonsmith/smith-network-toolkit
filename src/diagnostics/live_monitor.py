"""Live continuous ping monitor and packet loss watcher."""

import time
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from src.utils.platform_utils import ping_host


def run_live_monitor(
    gateway_ip: Optional[str] = "192.168.0.1",
    internet_target: str = "1.1.1.1",
    duration_seconds: Optional[int] = None
) -> Dict[str, Any]:
    """
    Continuous real-time ping watcher.
    Monitors gateway and public internet every second.
    Stops after duration_seconds or on KeyboardInterrupt (Ctrl+C).
    """
    print("=" * 65)
    print("   LIVE REAL-TIME PING & PACKET DROP WATCHER")
    print(f"   Gateway: {gateway_ip or 'None'} | Internet Target: {internet_target}")
    print("   Press Ctrl+C at any time to stop monitoring.")
    print("=" * 65 + "\n")

    gw_latencies = []
    net_latencies = []
    total_samples = 0
    gw_drops = 0
    net_drops = 0

    start_time = time.time()

    try:
        while True:
            total_samples += 1
            now_str = datetime.now().strftime("%H:%M:%S")

            # 1. Ping Gateway
            gw_str = "N/A"
            if gateway_ip and gateway_ip != "Unknown":
                gw_ping = ping_host(gateway_ip, count=1, timeout_sec=0.8)
                if gw_ping["success"] and gw_ping["avg_ms"] is not None:
                    lat = gw_ping["avg_ms"]
                    gw_latencies.append(lat)
                    gw_str = f"{lat:.0f} ms" if lat >= 1 else "<1 ms"
                else:
                    gw_drops += 1
                    gw_str = "DROP!"

            # 2. Ping Internet
            net_ping = ping_host(internet_target, count=1, timeout_sec=0.8)
            if net_ping["success"] and net_ping["avg_ms"] is not None:
                lat = net_ping["avg_ms"]
                net_latencies.append(lat)
                net_str = f"{lat:.0f} ms"
            else:
                net_drops += 1
                net_str = "DROP!"

            loss_rate = round((net_drops / total_samples) * 100, 1)

            # Terminal visual bar
            print(f"[{now_str}] Gateway: {gw_str:<7} | Internet: {net_str:<8} | Samples: {total_samples:<3} | Net Loss: {loss_rate}%")

            if duration_seconds and (time.time() - start_time) >= duration_seconds:
                break

            time.sleep(0.8)

    except KeyboardInterrupt:
        print("\n[INFO] Monitor stopped by user.")

    # Summary
    print("\n" + "=" * 50)
    print("           MONITORING SUMMARY")
    print("=" * 50)
    print(f"Total Probes Sent:     {total_samples}")
    print(f"Gateway Packet Drops:  {gw_drops} ({round((gw_drops / total_samples) * 100, 1) if total_samples else 0}%)")
    print(f"Internet Packet Drops: {net_drops} ({round((net_drops / total_samples) * 100, 1) if total_samples else 0}%)")
    if net_latencies:
        print(f"Internet Min Latency:  {min(net_latencies):.0f} ms")
        print(f"Internet Avg Latency:  {round(sum(net_latencies)/len(net_latencies), 1)} ms")
        print(f"Internet Max Latency:  {max(net_latencies):.0f} ms")
    print("=" * 50)

    return {
        "samples": total_samples,
        "gw_drops": gw_drops,
        "net_drops": net_drops,
        "avg_net_latency": round(sum(net_latencies)/len(net_latencies), 1) if net_latencies else None
    }
