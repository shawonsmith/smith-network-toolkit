"""Unit tests for LAN device discovery and scanner."""

import pytest
from unittest.mock import patch
from src.diagnostics.lan_scanner import parse_arp_table, scan_local_network, resolve_hostname_fast


def test_parse_arp_table():
    fake_arp = (
        "Interface: 192.168.1.100 --- 0x2\n"
        "  Internet Address      Physical Address      Type\n"
        "  192.168.1.1           98-ba-5f-2d-db-78     dynamic\n"
        "  192.168.1.50          aa-bb-cc-dd-ee-ff     dynamic\n"
        "  224.0.0.22            01-00-5e-00-00-16     static\n"
        "  255.255.255.255       ff-ff-ff-ff-ff-ff     static\n"
    )
    with patch("subprocess.check_output", return_value=fake_arp):
        with patch("platform.system", return_value="Windows"):
            table = parse_arp_table()
            assert "192.168.1.1" in table
            assert table["192.168.1.1"]["mac"] == "98:BA:5F:2D:DB:78"
            assert "192.168.1.50" in table
            # Multicast/broadcast should be excluded
            assert "224.0.0.22" not in table
            assert "255.255.255.255" not in table


def test_resolve_hostname_fast():
    with patch("socket.gethostbyaddr", return_value=("my-laptop.local", [], ["192.168.1.10"])):
        name = resolve_hostname_fast("192.168.1.10", timeout_sec=0.5)
        assert name == "my-laptop.local"


def test_scan_local_network_mocked():
    from src.models.result import AdapterInfo

    fake_adapter = AdapterInfo(
        ipv4_address="192.168.1.10",
        default_gateway="192.168.1.1",
        mac_address="11:22:33:44:55:66"
    )
    fake_arp = {
        "192.168.1.1": {"mac": "98:BA:5F:2D:DB:78", "type": "dynamic"},
        "192.168.1.20": {"mac": "AA:BB:CC:11:22:33", "type": "dynamic"},
    }

    with patch("src.diagnostics.adapter.detect_adapter_info", return_value=fake_adapter), \
         patch("src.diagnostics.lan_scanner.trigger_arp_resolution", return_value=True), \
         patch("src.diagnostics.lan_scanner.parse_arp_table", return_value=fake_arp), \
         patch("src.diagnostics.lan_scanner.ping_host", return_value={"success": True, "avg_ms": 2.5}), \
         patch("src.diagnostics.lan_scanner.resolve_hostname_fast", return_value="Device"):

        res = scan_local_network("192.168.1.0/24")
        assert res["active_devices_count"] >= 2
        ips = [d["ip"] for d in res["devices"]]
        assert "192.168.1.1" in ips
        assert "192.168.1.10" in ips
