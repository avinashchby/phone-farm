"""Tests for automation runner."""

import pytest
from unittest.mock import MagicMock, patch

from phone_farm.automation import AutomationRunner, RunResult


def test_run_result_dataclass() -> None:
    result = RunResult(
        account_email="test@gmail.com",
        success=True,
        duration_seconds=67,
        error=None,
    )
    assert result.success is True
    assert result.duration_seconds == 67


@pytest.mark.asyncio
async def test_runner_installs_apk_and_runs_flow() -> None:
    runner = AutomationRunner(
        appium_url="http://127.0.0.1:4723",
        adb_serial="emulator-5554",
        apk_path="./app.apk",
        flow_name="daily_usage",
        screenshot_dir="./screenshots",
    )
    with patch("phone_farm.automation.webdriver") as mock_wd:
        mock_driver = MagicMock()
        mock_wd.Remote.return_value = mock_driver
        with patch("phone_farm.automation.load_flow") as mock_load:
            mock_flow_cls = MagicMock()
            mock_flow_instance = MagicMock()
            mock_flow_cls.return_value = mock_flow_instance
            mock_load.return_value = mock_flow_cls
            result = await runner.run(account_email="test@gmail.com")
    assert result.success is True
    mock_flow_instance.run.assert_called_once()
    mock_driver.quit.assert_called_once()


@pytest.mark.asyncio
async def test_runner_captures_error_on_failure() -> None:
    runner = AutomationRunner(
        appium_url="http://127.0.0.1:4723",
        adb_serial="emulator-5554",
        apk_path="./app.apk",
        flow_name="daily_usage",
        screenshot_dir="./screenshots",
    )
    with patch("phone_farm.automation.webdriver") as mock_wd:
        mock_driver = MagicMock()
        mock_wd.Remote.return_value = mock_driver
        with patch("phone_farm.automation.load_flow") as mock_load:
            mock_flow_cls = MagicMock()
            mock_flow_instance = MagicMock()
            mock_flow_instance.run.side_effect = RuntimeError("element not found")
            mock_flow_cls.return_value = mock_flow_instance
            mock_load.return_value = mock_flow_cls
            result = await runner.run(account_email="test@gmail.com")
    assert result.success is False
    assert "element not found" in result.error
