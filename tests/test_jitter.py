"""Unit tests for VoIP & Gaming Jitter / Stability analyzer."""

import pytest
from unittest.mock import patch
from src.diagnostics.jitter import (
    calculate_rfc3550_jitter,
    estimate_mos_score,
    run_jitter_stability_test
)


def test_calculate_rfc3550_jitter():
    # Constant latency -> jitter = 0.0
    latencies = [20.0, 20.0, 20.0, 20.0]
    assert calculate_rfc3550_jitter(latencies) == 0.0

    # Variable latencies
    latencies_var = [20.0, 25.0, 22.0, 28.0]
    j = calculate_rfc3550_jitter(latencies_var)
    assert j > 0.0


def test_estimate_mos_score():
    # Ideal connection -> High MOS (close to 4.4 - 4.5)
    mos_good = estimate_mos_score(avg_latency=20.0, jitter=1.0, packet_loss_pct=0.0)
    assert mos_good >= 4.0

    # Degraded connection -> Lower MOS
    mos_poor = estimate_mos_score(avg_latency=250.0, jitter=45.0, packet_loss_pct=10.0)
    assert mos_poor < 3.0


def test_run_jitter_stability_test_mocked():
    # Mock ping responses
    mock_ping = lambda host, count=1, timeout_sec=1.5: {
        "success": True,
        "avg_ms": 25.0
    }
    with patch("src.diagnostics.jitter.ping_host", side_effect=mock_ping):
        res = run_jitter_stability_test(target_host="1.1.1.1", packet_count=5, interval_sec=0.0)
        assert res["target"] == "1.1.1.1"
        assert res["packets_sent"] == 5
        assert res["packets_received"] == 5
        assert res["packet_loss_pct"] == 0.0
        assert res["grade"] == "EXCELLENT"
        assert "Flawless" in res["zoom_status"]
