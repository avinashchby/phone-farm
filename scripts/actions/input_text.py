"""Type text with human-like delays."""

import random
import time

from appium.webdriver import Remote as AppiumDriver


def type_text(
    driver: AppiumDriver,
    by: str,
    value: str,
    text: str,
    *,
    min_delay: float = 0.05,
    max_delay: float = 0.15,
) -> None:
    """Find an input field and type text with random delays between keystrokes."""
    element = driver.find_element(by, value)
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))
