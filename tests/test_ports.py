"""Unit tests for port scanner module."""

import pytest
from unittest.mock import patch
from src.diagnostics.ports import probe_port, scan_ports


def test_probe_port_open():
    with patch("socket.socket.connect", return_value=None):
        res = probe_port("1.1.1.1", {"port": 80, "service": "HTTP", "category": "Web"})
        assert res["status"] == "OPEN"
        assert res["port"] == 80


def test_probe_port_filtered():
    import socket
    with patch("socket.socket.connect", side_effect=socket.timeout):
        res = probe_port("1.1.1.1", {"port": 22, "service": "SSH", "category": "Remote"})
        assert res["status"] == "FILTERED"


def test_scan_ports_summary():
    mock_probe = lambda host, p, timeout_sec=1.5: {
        "port": p["port"],
        "service": p["service"],
        "category": p["category"],
        "status": "OPEN" if p["port"] == 80 else "FILTERED",
        "latency_ms": 10.0 if p["port"] == 80 else None,
        "message": ""
    }
    with patch("src.diagnostics.ports.probe_port", side_effect=mock_probe):
        res = scan_ports("1.1.1.1", ports=[
            {"port": 80, "service": "HTTP", "category": "Web"},
            {"port": 22, "service": "SSH", "category": "Remote"}
        ])
        assert res["open_count"] == 1
        assert res["filtered_count"] == 1
