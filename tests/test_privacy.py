"""Unit tests for privacy masking engine."""

import pytest
from src.utils.privacy import mask_ipv4, mask_mac, mask_text, mask_scan_report
from src.models.result import ScanReport, AdapterInfo, DiagnosticResult


def test_mask_private_ipv4():
    assert mask_ipv4("192.168.0.105") == "192.168.0.xxx"
    assert mask_ipv4("10.0.1.50") == "10.0.1.xxx"
    assert mask_ipv4("172.16.5.4") == "172.16.5.xxx"


def test_mask_public_ipv4():
    masked = mask_ipv4("103.45.67.89")
    assert masked == "103.xxx.xxx.89"


def test_mask_mac():
    assert mask_mac("1C-1B-0D-7F-88-64") == "1C-xx-xx-xx-88-xx"
    assert mask_mac("a4:83:e7:45:91:2b") == "a4:xx:xx:xx:91:xx"


def test_mask_text():
    sample = "Device 192.168.1.50 connected with MAC 1C-1B-0D-7F-88-64 to 103.45.67.89"
    masked = mask_text(sample)
    assert "192.168.1.50" not in masked
    assert "192.168.1.xxx" in masked
    assert "1C-1B-0D-7F-88-64" not in masked
    assert "1C-xx-xx-xx-88-xx" in masked
    assert "103.xxx.xxx.89" in masked


def test_mask_scan_report():
    report = ScanReport(
        adapter_info=AdapterInfo(
            ipv4_address="192.168.0.205",
            mac_address="1C-1B-0D-7F-88-64",
            default_gateway="192.168.0.1",
            dns_servers=["192.168.0.1"]
        ),
        results=[
            DiagnosticResult(name="Gateway", status="PASS", value="<1 ms", details={"gateway": "192.168.0.1"})
        ],
        public_ip_info={"ip": "103.16.248.128", "status": "Detected"}
    )
    masked_report = mask_scan_report(report)
    assert masked_report.is_privacy_masked is True
    assert masked_report.adapter_info.ipv4_address == "192.168.0.xxx"
    assert masked_report.adapter_info.mac_address == "1C-xx-xx-xx-88-xx"
    assert masked_report.adapter_info.default_gateway == "192.168.0.xxx"
    assert masked_report.adapter_info.dns_servers == ["192.168.0.xxx"]
    assert masked_report.results[0].details["gateway"] == "192.168.0.xxx"
    assert masked_report.public_ip_info["ip"] == "103.xxx.xxx.128"
