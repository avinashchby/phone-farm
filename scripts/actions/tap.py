"""Tap an element with retry logic."""

import time

from appium.webdriver import Remote as AppiumDriver


def tap_element(
    driver: AppiumDriver,
    by: str,
    value: str,
    *,
    retries: int = 3,
    wait_between: float = 1.0,
) -> None:
    """Find and tap an element, retrying on failure."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            element = driver.find_element(by, value)
            element.click()
            return
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(wait_between)
    raise last_error  # type: ignore[misc]
