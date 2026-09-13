"""Unit tests for traceroute module."""

import pytest
from unittest.mock import patch, MagicMock
from src.diagnostics.traceroute import run_traceroute


def test_run_traceroute_parsing():
    sample_output = """
Tracing route to 1.1.1.1 over a maximum of 30 hops
  1    <1 ms    <1 ms     1 ms  192.168.0.1
  2     2 ms     1 ms     1 ms  10.126.8.1
  3     *        *        *     Request timed out.
  4     3 ms     2 ms     2 ms  1.1.1.1
Trace complete.
"""
    mock_proc = MagicMock(stdout=sample_output)
    with patch("subprocess.run", return_value=mock_proc):
        res = run_traceroute("1.1.1.1")
        assert res["success"] is True
        assert len(res["hops"]) == 4
        assert res["hops"][0]["ip"] == "192.168.0.1"
        assert res["hops"][0]["desc"] == "Local Router / Gateway"
        assert res["hops"][2]["timeout"] is True
        assert res["hops"][3]["ip"] == "1.1.1.1"
        assert res["hops"][3]["desc"] == "Destination Target"
