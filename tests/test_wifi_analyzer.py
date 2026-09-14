"""Unit tests for advanced Wi-Fi analyzer."""

import pytest
from unittest.mock import patch, MagicMock
from src.diagnostics.wifi_analyzer import (
    get_wifi_generation,
    determine_wifi_band,
    estimate_rssi_dbm,
    analyze_wifi_status
)


def test_get_wifi_generation():
    assert get_wifi_generation("802.11ax") == "Wi-Fi 6 (802.11ax)"
    assert get_wifi_generation("802.11ax", band="5.0 GHz") == "Wi-Fi 6 (802.11ax)"
    assert get_wifi_generation("802.11ax", band="6.0 GHz") == "Wi-Fi 6E (802.11ax 6GHz)"
    assert "Wi-Fi 5" in get_wifi_generation("802.11ac")
    assert "Wi-Fi 4" in get_wifi_generation("802.11n")
    assert "Wi-Fi 7" in get_wifi_generation("802.11be")


def test_determine_wifi_band():
    assert determine_wifi_band(6) == "2.4 GHz"
    assert determine_wifi_band(11) == "2.4 GHz"
    assert determine_wifi_band(36) == "5.0 GHz"
    assert determine_wifi_band(149) == "5.0 GHz"
    assert determine_wifi_band(190) == "6.0 GHz"
    assert determine_wifi_band(None) == "Unknown"


def test_estimate_rssi_dbm():
    assert estimate_rssi_dbm(100) == -50
    assert estimate_rssi_dbm(80) == -60
    assert estimate_rssi_dbm(50) == -75
    assert estimate_rssi_dbm(None) is None


def test_analyze_wifi_status_active_wifi():
    fake_netsh = (
        "There is 1 interface on the system:\n"
        "    Name                   : Wi-Fi\n"
        "    Description            : Intel(R) Wi-Fi 6 AX201 160MHz\n"
        "    State                  : connected\n"
        "    SSID                   : Smith_Corporate_5G\n"
        "    BSSID                  : 00:11:22:33:44:55\n"
        "    Network type           : Infrastructure\n"
        "    Radio type             : 802.11ax\n"
        "    Authentication         : WPA2-Personal\n"
        "    Cipher                 : CCMP\n"
        "    Channel                : 36\n"
        "    Receive rate (Mbps)    : 866\n"
        "    Transmit rate (Mbps)   : 866\n"
        "    Signal                 : 88%\n"
    )
    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = fake_netsh
    fake_proc.stderr = ""

    with patch("platform.system", return_value="Windows"), \
         patch("subprocess.run", return_value=fake_proc):
        res = analyze_wifi_status()
        assert res["is_wifi"] is True
        assert res["ssid"] == "Smith_Corporate_5G"
        assert res["channel"] == 36
        assert res["band"] == "5.0 GHz"
        assert "Wi-Fi 6" in res["wifi_generation"]
        assert res["signal_pct"] == 88
        assert res["rssi_dbm"] == -56
        assert res["rx_rate_mbps"] == 866.0
        assert len(res["advice"]) > 0
