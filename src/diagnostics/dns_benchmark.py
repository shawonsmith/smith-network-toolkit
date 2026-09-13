"""DNS benchmark and speed comparison module."""

import time
from typing import Dict, Any, List, Optional
from src.utils.logger import log_event

try:
    import dns.resolver
    DNSPYTHON_AVAILABLE = True
except ImportError:
    DNSPYTHON_AVAILABLE = False

BENCHMARK_RESOLVERS = [
    {"name": "Cloudflare", "ip": "1.1.1.1", "desc": "Privacy-first Fast Anycast"},
    {"name": "Google Public DNS", "ip": "8.8.8.8", "desc": "Global High Availability"},
    {"name": "Quad9", "ip": "9.9.9.9", "desc": "Malware Blocking & Security"},
    {"name": "OpenDNS (Cisco)", "ip": "208.67.222.222", "desc": "Content Filtering & Reliability"},
]

BENCHMARK_DOMAINS = ["google.com", "cloudflare.com", "wikipedia.org"]


def benchmark_single_resolver(
    resolver_ip: str,
    domains: List[str] = None,
    timeout_sec: float = 2.0
) -> Dict[str, Any]:
    """Test resolution speed against a specific nameserver IP."""
    test_domains = domains or BENCHMARK_DOMAINS
    latencies = []
    success_count = 0

    if not DNSPYTHON_AVAILABLE:
        return {
            "ip": resolver_ip,
            "success": False,
            "avg_ms": None,
            "error": "dnspython library not installed"
        }

    custom_res = dns.resolver.Resolver(configure=False)
    custom_res.nameservers = [resolver_ip]
    custom_res.timeout = timeout_sec
    custom_res.lifetime = timeout_sec * 1.5

    for domain in test_domains:
        start = time.perf_counter()
        try:
            custom_res.resolve(domain, "A")
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)
            success_count += 1
        except Exception:
            pass

    avg_ms = round(sum(latencies) / len(latencies), 1) if latencies else None

    return {
        "ip": resolver_ip,
        "success": success_count > 0,
        "success_rate": f"{success_count}/{len(test_domains)}",
        "avg_ms": avg_ms,
        "latencies": latencies
    }


def run_dns_benchmark(
    local_dns: Optional[str] = None,
    progress_callback = None
) -> Dict[str, Any]:
    """
    Run comprehensive DNS benchmark comparing top global resolvers
    against the user local DNS.
    """
    log_event("Starting multi-provider DNS speed benchmark...")
    resolvers_to_test = list(BENCHMARK_RESOLVERS)

    if local_dns and local_dns not in [r["ip"] for r in resolvers_to_test] and local_dns != "Unknown":
        resolvers_to_test.append({
            "name": f"Your Current DNS ({local_dns})",
            "ip": local_dns,
            "desc": "Configured Network Adapter Resolver"
        })

    results = []

    for r in resolvers_to_test:
        if progress_callback:
            progress_callback(f"Testing {r['name']} ({r['ip']})...")
        bench = benchmark_single_resolver(r["ip"])
        bench["name"] = r["name"]
        bench["desc"] = r["desc"]
        results.append(bench)

    # Sort: successful first, then lowest avg_ms
    def sort_key(item):
        if not item["success"] or item["avg_ms"] is None:
            return 99999.0
        return item["avg_ms"]

    results.sort(key=sort_key)

    fastest = results[0] if results and results[0]["success"] else None
    recommendation = ""
    if fastest and local_dns:
        local_result = next((item for item in results if item["ip"] == local_dns), None)
        if local_result and local_result.get("avg_ms") and fastest.get("avg_ms"):
            diff = round(local_result["avg_ms"] - fastest["avg_ms"], 1)
            if diff > 10.0 and fastest["ip"] != local_dns:
                recommendation = f"{fastest['name']} is {diff} ms faster than your current resolver. Consider switching!"
            else:
                recommendation = "Your current DNS is performing with competitive latency."

    log_event(f"DNS benchmark completed. Fastest: {fastest['name'] if fastest else 'None'}")
    return {
        "results": results,
        "fastest": fastest,
        "recommendation": recommendation
    }
