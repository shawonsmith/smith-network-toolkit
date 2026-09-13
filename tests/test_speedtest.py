"""Unit tests for speedtest module."""

import pytest
from unittest.mock import patch, MagicMock
from src.diagnostics.speedtest import test_download_speed as run_test_download_speed


def test_speedtest_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content.return_value = [b"x" * 1024 * 1024 * 5]  # 5 MB chunk

    with patch("requests.get", return_value=mock_resp):
        res = run_test_download_speed()
        assert res["success"] is True
        assert res["speed_mbps"] > 0
        assert res["data_mb"] > 0
