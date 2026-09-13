"""Unit tests for packet loss diagnostic."""

import pytest
from unittest.mock import patch
from src.diagnostics.packet_loss import test_packet_loss as run_test_packet_loss


def test_packet_loss_zero():
    mock_ping = {"success": True, "sent": 20, "received": 20, "lost": 0, "loss_percent": 0.0, "avg_ms": 10.0}
    with patch("src.diagnostics.packet_loss.ping_host", return_value=mock_ping):
        res = run_test_packet_loss()
        assert res.status == "PASS"
        assert res.value == "0%"


def test_packet_loss_acceptable():
    mock_ping = {"success": True, "sent": 20, "received": 19, "lost": 1, "loss_percent": 2.0, "avg_ms": 12.0}
    with patch("src.diagnostics.packet_loss.ping_host", return_value=mock_ping):
        res = run_test_packet_loss()
        assert res.status == "PASS"
        assert res.value == "2.0%"


def test_packet_loss_warning():
    mock_ping = {"success": True, "sent": 20, "received": 19, "lost": 1, "loss_percent": 4.0, "avg_ms": 15.0}
    with patch("src.diagnostics.packet_loss.ping_host", return_value=mock_ping):
        res = run_test_packet_loss()
        assert res.status == "WARN"
        assert res.value == "4.0%"


def test_packet_loss_poor():
    mock_ping = {"success": True, "sent": 20, "received": 16, "lost": 4, "loss_percent": 20.0, "avg_ms": 25.0}
    with patch("src.diagnostics.packet_loss.ping_host", return_value=mock_ping):
        res = run_test_packet_loss()
        assert res.status == "FAIL"
        assert res.value == "20.0%"
