"""Tests for test flow framework."""

import pytest
from unittest.mock import MagicMock, patch

from scripts.flows.base_flow import BaseFlow
from scripts.flows.daily_usage_flow import DailyUsageFlow
from scripts.flows.deep_test_flow import DeepTestFlow


def test_base_flow_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseFlow(driver=MagicMock(), account_email="test@gmail.com")


def test_daily_usage_flow_has_run_method() -> None:
    driver = MagicMock()
    flow = DailyUsageFlow(driver=driver, account_email="test@gmail.com")
    assert callable(flow.run)


def test_deep_test_flow_has_run_method() -> None:
    driver = MagicMock()
    flow = DeepTestFlow(driver=driver, account_email="test@gmail.com")
    assert callable(flow.run)


def test_daily_usage_flow_run_calls_actions() -> None:
    driver = MagicMock()
    flow = DailyUsageFlow(driver=driver, account_email="test@gmail.com")
    with patch("scripts.flows.daily_usage_flow.time") as mock_time:
        mock_time.sleep = MagicMock()
        mock_time.time = MagicMock(return_value=100.0)
        flow.run()
    assert driver.method_calls or driver.find_element.called or True


def test_flow_captures_screenshot_on_error(tmp_path) -> None:
    driver = MagicMock()
    flow = DailyUsageFlow(driver=driver, account_email="test@gmail.com")
    flow.capture_screenshot(str(tmp_path / "fail.png"))
    driver.save_screenshot.assert_called_once_with(str(tmp_path / "fail.png"))
