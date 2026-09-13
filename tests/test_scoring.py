"""Unit tests for Network Health Score engine."""

import pytest
from src.models.result import AdapterInfo, DiagnosticResult
from src.scoring.health_score import calculate_health_score


@pytest.fixture
def perfect_adapter():
    return AdapterInfo(
        hostname="TEST-PC",
        os_name="Windows 11",
        adapter_name="Wi-Fi",
        mac_address="AA:BB:CC:DD:EE:FF",
        ipv4_address="192.168.1.100",
        subnet_mask="255.255.255.0",
        default_gateway="192.168.1.1",
        dns_servers=["1.1.1.1"],
        is_apipa=False,
        is_connected=True
    )


def test_perfect_health_score(perfect_adapter):
    results = [
        DiagnosticResult(name="Gateway", status="PASS", value="2 ms", details={"latency_ms": 2.0}),
        DiagnosticResult(name="Internet", status="PASS", value="Connected", details={}),
        DiagnosticResult(name="DNS", status="PASS", value="30 ms", details={"avg_ms": 30.0}),
        DiagnosticResult(name="Packet Loss", status="PASS", value="0%", details={"loss_percent": 0.0}),
        DiagnosticResult(name="Latency", status="PASS", value="25 ms", details={"internet_avg_ms": 25.0})
    ]
    score = calculate_health_score(perfect_adapter, results)
    assert score.total_score == 100
    assert score.grade == "Excellent"


def test_apipa_deduction(perfect_adapter):
    perfect_adapter.ipv4_address = "169.254.10.20"
    perfect_adapter.is_apipa = True
    results = [
        DiagnosticResult(name="Gateway", status="FAIL", value="Unreachable", details={}),
        DiagnosticResult(name="Internet", status="FAIL", value="Disconnected", details={}),
        DiagnosticResult(name="DNS", status="FAIL", value="Failed", details={}),
        DiagnosticResult(name="Packet Loss", status="FAIL", value="100%", details={"loss_percent": 100.0}),
        DiagnosticResult(name="Latency", status="FAIL", value="Unreachable", details={})
    ]
    score = calculate_health_score(perfect_adapter, results)
    # Valid IP: 0, Gateway detected: 10, others 0, adapter healthy: 5 -> total 15
    assert score.breakdown["valid_ip"] == 0
    assert score.total_score <= 20
    assert score.grade == "Poor"


def test_dns_failure_deduction(perfect_adapter):
    results = [
        DiagnosticResult(name="Gateway", status="PASS", value="2 ms", details={"latency_ms": 2.0}),
        DiagnosticResult(name="Internet", status="WARN", value="Limited", details={}),
        DiagnosticResult(name="DNS", status="FAIL", value="Failed", details={"avg_ms": None}),
        DiagnosticResult(name="Packet Loss", status="PASS", value="0%", details={"loss_percent": 0.0}),
        DiagnosticResult(name="Latency", status="PASS", value="30 ms", details={"internet_avg_ms": 30.0})
    ]
    score = calculate_health_score(perfect_adapter, results)
    assert score.breakdown["dns_working"] == 0
    assert score.breakdown["internet_reachable"] == 10
    assert score.total_score == 75
    assert score.grade == "Good"
