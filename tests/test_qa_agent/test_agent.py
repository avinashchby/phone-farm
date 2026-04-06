"""Tests for the QA agent decision loop."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

from phone_farm.qa_agent.agent import QAAgent, execute_action, _crashes_to_bugs, _visual_issues_to_bugs
from phone_farm.qa_agent.ai_backend import AgentAction, MockBackend, VisualIssue
from phone_farm.qa_agent.logcat import CrashInfo
from phone_farm.qa_agent.memory import SessionMemory

SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <android.widget.Button resource-id="com.app:id/btn" text="Click"
      class="android.widget.Button" bounds="[100,200][300,400]"
      clickable="true" scrollable="false" content-desc="" />
</hierarchy>
"""


def test_execute_action_tap_by_id() -> None:
    driver = MagicMock()
    element = MagicMock()
    driver.find_element.return_value = element
    action = AgentAction(action_type="tap", target_resource_id="com.app:id/btn")
    execute_action(driver, action)
    driver.find_element.assert_called_with("id", "com.app:id/btn")
    element.click.assert_called_once()


def test_execute_action_tap_by_text() -> None:
    driver = MagicMock()
    element = MagicMock()
    driver.find_element.return_value = element
    action = AgentAction(action_type="tap", target_text="Login")
    execute_action(driver, action)
    driver.find_element.assert_called_with("xpath", '//*[@text="Login"]')
    element.click.assert_called_once()


def test_execute_action_tap_by_bounds() -> None:
    driver = MagicMock()
    action = AgentAction(action_type="tap", target_bounds=(100, 200, 300, 400))
    execute_action(driver, action)
    driver.execute_script.assert_called_once()
    args = driver.execute_script.call_args
    assert args[0][0] == "mobile: clickGesture"
    assert args[0][1]["x"] == 200  # center x
    assert args[0][1]["y"] == 300  # center y


def test_execute_action_scroll() -> None:
    driver = MagicMock()
    action = AgentAction(action_type="scroll", scroll_direction="down")
    execute_action(driver, action)
    driver.execute_script.assert_called_once()


def test_execute_action_type() -> None:
    driver = MagicMock()
    element = MagicMock()
    driver.find_element.return_value = element
    action = AgentAction(action_type="type", target_resource_id="com.app:id/input", input_text="hello")
    execute_action(driver, action)
    element.clear.assert_called_once()
    element.send_keys.assert_called_with("hello")


def test_execute_action_back() -> None:
    driver = MagicMock()
    action = AgentAction(action_type="back")
    execute_action(driver, action)
    driver.back.assert_called_once()


def test_crashes_to_bugs_converts() -> None:
    mem = SessionMemory()
    mem.record_screen("s1")
    mem.record_action("tap", "btn", "s1")
    crash = CrashInfo(
        crash_type="java_exception",
        message="NullPointerException at com.app.Main",
        stacktrace="at com.app.Main.onClick",
        timestamp="01-15 10:30:45",
    )
    bugs = _crashes_to_bugs([crash], mem)
    assert len(bugs) == 1
    assert bugs[0].severity == "critical"
    assert bugs[0].category == "java_exception"


def test_visual_issues_to_bugs_converts() -> None:
    issue = VisualIssue(
        issue_type="overlap",
        severity="high",
        location="header",
        description="Button overlaps title text",
    )
    bugs = _visual_issues_to_bugs([issue], "sig123", "/tmp/ss.png")
    assert len(bugs) == 1
    assert bugs[0].category == "visual"
    assert bugs[0].screenshot_path == "/tmp/ss.png"


@pytest.mark.asyncio
async def test_agent_runs_mock_backend(tmp_path: Path) -> None:
    driver = MagicMock()
    driver.page_source = SAMPLE_XML
    driver.get_screenshot_as_base64.return_value = "fakebase64"
    driver.find_element.return_value = MagicMock()

    backend = MockBackend()

    with patch("phone_farm.qa_agent.agent.clear_logcat", new_callable=AsyncMock):
        with patch("phone_farm.qa_agent.agent.collect_logcat_errors", new_callable=AsyncMock) as mock_logcat:
            mock_logcat.return_value = []
            agent = QAAgent(
                driver=driver,
                ai=backend,
                adb_serial="emulator-5554",
                app_description="Test app",
                screenshot_dir=tmp_path / "screenshots",
                max_steps=10,
            )
            bugs = await agent.run()
    assert isinstance(bugs, list)


@pytest.mark.asyncio
async def test_agent_detects_crash(tmp_path: Path) -> None:
    driver = MagicMock()
    driver.page_source = SAMPLE_XML
    driver.get_screenshot_as_base64.return_value = "fakebase64"
    driver.find_element.return_value = MagicMock()

    backend = MockBackend()

    from phone_farm.qa_agent.logcat import LogcatEntry

    crash_entries = [
        LogcatEntry("01-15 10:30:45.123", "E", "AndroidRuntime", "FATAL EXCEPTION: main"),
        LogcatEntry("01-15 10:30:45.124", "E", "AndroidRuntime", "java.lang.NullPointerException"),
    ]

    with patch("phone_farm.qa_agent.agent.clear_logcat", new_callable=AsyncMock):
        with patch("phone_farm.qa_agent.agent.collect_logcat_errors", new_callable=AsyncMock) as mock_logcat:
            # Return crash on step 5 check
            mock_logcat.side_effect = [[], [], crash_entries, []]
            agent = QAAgent(
                driver=driver,
                ai=backend,
                adb_serial="emulator-5554",
                app_description="Test app",
                screenshot_dir=tmp_path / "screenshots",
                max_steps=10,
            )
            bugs = await agent.run()

    crash_bugs = [b for b in bugs if b.category in ("java_exception", "native_crash")]
    assert len(crash_bugs) >= 1
