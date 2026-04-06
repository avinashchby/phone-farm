"""Scroll actions for Appium automation."""

from appium.webdriver import Remote as AppiumDriver


def scroll_down(driver: AppiumDriver, amount: int = 500) -> None:
    """Scroll down by a pixel amount using mobile gesture."""
    driver.execute_script(
        "mobile: scrollGesture",
        {"left": 100, "top": 300, "width": 200, "height": amount, "direction": "down", "percent": 0.75},
    )


def scroll_up(driver: AppiumDriver, amount: int = 500) -> None:
    """Scroll up by a pixel amount using mobile gesture."""
    driver.execute_script(
        "mobile: scrollGesture",
        {"left": 100, "top": 300, "width": 200, "height": amount, "direction": "up", "percent": 0.75},
    )
