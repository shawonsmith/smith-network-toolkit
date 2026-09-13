"""Unit tests for network adapter detection."""

import pytest
from unittest.mock import patch, MagicMock
from src.diagnostics.adapter import detect_adapter_info, is_apipa_ip, is_valid_ipv4
from src.models.result import AdapterInfo


def test_is_valid_ipv4():
    assert is_valid_ipv4("192.168.1.1") is True
    assert is_valid_ipv4("10.0.0.1") is True
    assert is_valid_ipv4("256.0.0.1") is False
    assert is_valid_ipv4("invalid") is False
    assert is_valid_ipv4("") is False
    assert is_valid_ipv4(None) is False


def test_is_apipa_ip():
    assert is_apipa_ip("169.254.1.100") is True
    assert is_apipa_ip("169.254.255.254") is True
    assert is_apipa_ip("192.168.1.1") is False
    assert is_apipa_ip("10.169.254.1") is False


def test_detect_adapter_info_apipa():
    mock_addrs = {
        "Ethernet": [
            MagicMock(family=-1, address="AA:BB:CC:DD:EE:FF"),
            MagicMock(family=2, address="169.254.50.25", netmask="255.255.0.0")
        ]
    }
    mock_stats = {
        "Ethernet": MagicMock(isup=True)
    }

    with patch("psutil.net_if_addrs", return_value=mock_addrs), \
         patch("psutil.net_if_stats", return_value=mock_stats), \
         patch("src.diagnostics.adapter.get_windows_ipconfig_data", return_value={}):
        
        info = detect_adapter_info()
        assert info.is_apipa is True
        assert info.ipv4_address == "169.254.50.25"
        assert info.subnet_mask == "255.255.0.0"
        assert info.mac_address == "AA:BB:CC:DD:EE:FF"
