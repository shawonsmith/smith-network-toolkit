"""Unit tests for Network Guardian Autonomous Self-Healing engine."""

import pytest
import time
from unittest.mock import patch, MagicMock
from src.diagnostics.guardian import NetworkGuardian


def test_guardian_lifecycle():
    guardian = NetworkGuardian(probe_interval=0.1)
    assert not guardian.is_running()
    guardian.start()
    assert guardian.is_running()
    time.sleep(0.2)
    guardian.stop()
    assert not guardian.is_running()


def test_guardian_debouncing():
    # Debounce requires 2 failures before healing
    guardian = NetworkGuardian(probe_interval=10.0, debounce_count=2, cooldown_sec=10.0)

    # 1st failure: should NOT trigger auto-heal
    with patch.object(guardian, "_probe_dns", return_value=False), \
         patch.object(guardian, "_execute_heal_dns") as mock_heal, \
         patch("src.diagnostics.guardian.ping_host", return_value={"success": True, "avg_ms": 20.0}), \
         patch("src.diagnostics.adapter.detect_adapter_info") as mock_adapter:

        fake_ad = MagicMock()
        fake_ad.default_gateway = "192.168.1.1"
        fake_ad.is_apipa = False
        fake_ad.is_connected = True
        mock_adapter.return_value = fake_ad

        guardian._run_probe_cycle()
        assert guardian.consecutive_dns_failures == 1
        mock_heal.assert_not_called()

        # 2nd failure: SHOULD trigger auto-heal!
        guardian._run_probe_cycle()
        assert mock_heal.call_count == 1


def test_guardian_cooldown_enforcement():
    guardian = NetworkGuardian(probe_interval=10.0, debounce_count=1, cooldown_sec=60.0)
    guardian.last_heal_time = time.time()  # Just healed!
    guardian.consecutive_dns_failures = 5

    with patch.object(guardian, "_execute_heal_dns") as mock_heal, \
         patch("src.diagnostics.adapter.detect_adapter_info") as mock_adapter:

        fake_ad = MagicMock()
        fake_ad.default_gateway = "192.168.1.1"
        fake_ad.is_apipa = False
        fake_ad.is_connected = True
        mock_adapter.return_value = fake_ad

        guardian._run_probe_cycle()
        # Should be blocked by cooldown
        mock_heal.assert_not_called()


def test_guardian_record_incident_callback():
    received_incidents = []

    def handle_incident(inc):
        received_incidents.append(inc)

    guardian = NetworkGuardian(on_incident=handle_incident)
    fake_inc = {
        "timestamp": "2026-09-13 22:15:30",
        "trigger": "DNS Freeze",
        "action": "ipconfig /flushdns",
        "verified": True,
        "duration_sec": 1.2,
        "message": "Success"
    }

    with patch("sys.platform", "win32"):
        guardian._record_incident(fake_inc)

    assert guardian.total_incidents_healed == 1
    assert len(received_incidents) == 1
    assert received_incidents[0]["trigger"] == "DNS Freeze"
