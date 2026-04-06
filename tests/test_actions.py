"""Tests for automation actions."""

from unittest.mock import MagicMock

from scripts.actions.tap import tap_element
from scripts.actions.scroll import scroll_down
from scripts.actions.input_text import type_text


def test_tap_element_finds_and_clicks(monkeypatch) -> None:
    driver = MagicMock()
    element = MagicMock()
    driver.find_element.return_value = element
    tap_element(driver, "id", "com.example:id/button")
    element.click.assert_called_once()


def test_tap_element_retries_on_failure(monkeypatch) -> None:
    import time
    monkeypatch.setattr(time, "sleep", lambda _: None)
    driver = MagicMock()
    driver.find_element.side_effect = [Exception("not found"), Exception("not found"), MagicMock()]
    tap_element(driver, "id", "com.example:id/button", retries=3)
    assert driver.find_element.call_count == 3


def test_type_text_sends_keys_with_value(monkeypatch) -> None:
    monkeypatch.setattr("scripts.actions.input_text.random", MagicMock(uniform=MagicMock(return_value=0.1)))
    import time
    monkeypatch.setattr(time, "sleep", lambda _: None)
    driver = MagicMock()
    element = MagicMock()
    driver.find_element.return_value = element
    type_text(driver, "id", "com.example:id/input", "hello")
    element.send_keys.assert_called()


def test_scroll_down_executes_script() -> None:
    driver = MagicMock()
    scroll_down(driver)
    driver.execute_script.assert_called_once()
