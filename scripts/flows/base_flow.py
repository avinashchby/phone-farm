"""Abstract base class for all test flows."""

from abc import ABC, abstractmethod

from appium.webdriver import Remote as AppiumDriver


class BaseFlow(ABC):
    """Base class that all test flows must extend."""

    def __init__(self, *, driver: AppiumDriver, account_email: str) -> None:
        self.driver = driver
        self.account_email = account_email

    @abstractmethod
    def run(self) -> None:
        """Execute the test flow. Must be implemented by subclasses."""

    def capture_screenshot(self, path: str) -> None:
        """Save a screenshot to the given path."""
        self.driver.save_screenshot(path)
