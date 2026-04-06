"""Smart wait utilities for Appium automation."""

import time

from appium.webdriver import Remote as AppiumDriver


def wait_for_element(
    driver: AppiumDriver,
    by: str,
    value: str,
    *,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> object:
    """Wait until an element is visible, then return it."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            element = driver.find_element(by, value)
            if element.is_displayed():
                return element
        except Exception:
            pass
        time.sleep(poll_interval)
    raise TimeoutError(f"Element {by}={value} not found within {timeout}s")
