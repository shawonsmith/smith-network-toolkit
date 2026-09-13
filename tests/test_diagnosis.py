"""Unit tests for automatic diagnosis rules."""

import pytest
from src.models.result import AdapterInfo, DiagnosticResult
from src.diagnosis.diagnosis_engine import run_diagnosis


def test_rule_1_apipa_diagnosis():
    adapter = AdapterInfo(
        ipv4_address="169.254.80.120",
        is_apipa=True
    )
    issues = run_diagnosis(adapter, [])
    rule_ids = [i.rule_id for i in issues]
    assert "RULE-01-APIPA" in rule_ids
    apipa_issue = [i for i in issues if i.rule_id == "RULE-01-APIPA"][0]
    assert "DHCP" in apipa_issue.title
    assert len(apipa_issue.recommendations) > 0


def test_rule_2_dns_failure():
    adapter = AdapterInfo(ipv4_address="192.168.1.10", is_apipa=False)
    results = [
        DiagnosticResult(name="Gateway", status="PASS", value="2 ms"),
        DiagnosticResult(name="Internet", status="WARN", value="Limited", details={"external_ip_reachable": True}),
        DiagnosticResult(name="DNS", status="FAIL", value="Failed")
    ]
    issues = run_diagnosis(adapter, results)
    rule_ids = [i.rule_id for i in issues]
    assert "RULE-02-DNS-FAIL" in rule_ids


def test_rule_3_gateway_unreachable():
    adapter = AdapterInfo(ipv4_address="192.168.1.10", default_gateway="192.168.1.1")
    results = [
        DiagnosticResult(name="Gateway", status="FAIL", value="Unreachable"),
        DiagnosticResult(name="Internet", status="FAIL", value="Disconnected")
    ]
    issues = run_diagnosis(adapter, results)
    rule_ids = [i.rule_id for i in issues]
    assert "RULE-03-GATEWAY-DOWN" in rule_ids


def test_rule_4_isp_outage():
    adapter = AdapterInfo(ipv4_address="192.168.1.10", default_gateway="192.168.1.1")
    results = [
        DiagnosticResult(name="Gateway", status="PASS", value="2 ms"),
        DiagnosticResult(name="Internet", status="FAIL", value="No Internet", details={"external_ip_reachable": False})
    ]
    issues = run_diagnosis(adapter, results)
    rule_ids = [i.rule_id for i in issues]
    assert "RULE-04-ISP-OUTAGE" in rule_ids


def test_rule_5_packet_loss():
    adapter = AdapterInfo(ipv4_address="192.168.1.10")
    results = [
        DiagnosticResult(name="Gateway", status="PASS", value="2 ms"),
        DiagnosticResult(name="Packet Loss", status="FAIL", value="15.0%", details={"loss_percent": 15.0})
    ]
    issues = run_diagnosis(adapter, results)
    rule_ids = [i.rule_id for i in issues]
    assert "RULE-05-PACKET-LOSS" in rule_ids
