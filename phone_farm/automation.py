"""Appium automation runner: connects to emulator, installs APK, runs flows."""

import time
from dataclasses import dataclass
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options

from scripts.flows.base_flow import BaseFlow
from scripts.flows.daily_usage_flow import DailyUsageFlow
from scripts.flows.deep_test_flow import DeepTestFlow


FLOW_MAP: dict[str, type[BaseFlow]] = {
    "daily_usage": DailyUsageFlow,
    "deep_test": DeepTestFlow,
}


def load_flow(flow_name: str) -> type[BaseFlow]:
    """Load a flow class by name.

    Raises:
        ValueError: If flow_name is not recognized.
    """
    if flow_name not in FLOW_MAP:
        raise ValueError(f"Unknown flow: {flow_name}. Available: {list(FLOW_MAP.keys())}")
    return FLOW_MAP[flow_name]


@dataclass
class RunResult:
    """Result of a single automation run."""

    account_email: str
    success: bool
    duration_seconds: int
    error: str | None


class AutomationRunner:
    """Runs a test flow against a single emulator via Appium."""

    def __init__(
        self,
        *,
        appium_url: str,
        adb_serial: str,
        apk_path: str,
        flow_name: str,
        screenshot_dir: str,
    ) -> None:
        self.appium_url = appium_url
        self.adb_serial = adb_serial
        self.apk_path = apk_path
        self.flow_name = flow_name
        self.screenshot_dir = screenshot_dir

    async def run(self, *, account_email: str) -> RunResult:
        """Execute the flow and return the result."""
        start = time.time()
        driver = None
        try:
            options = UiAutomator2Options()
            options.udid = self.adb_serial
            options.app = str(Path(self.apk_path).resolve())
            options.auto_grant_permissions = True
            options.no_reset = True

            driver = webdriver.Remote(
                command_executor=f"{self.appium_url}/wd/hub",
                options=options,
            )

            flow_cls = load_flow(self.flow_name)
            flow = flow_cls(driver=driver, account_email=account_email)
            flow.run()

            duration = int(time.time() - start)
            return RunResult(
                account_email=account_email,
                success=True,
                duration_seconds=duration,
                error=None,
            )
        except Exception as e:
            duration = int(time.time() - start)
            if driver:
                try:
                    Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
                    ts = int(time.time())
                    driver.save_screenshot(
                        f"{self.screenshot_dir}/{account_email}-{ts}.png"
                    )
                except Exception:
                    pass
            return RunResult(
                account_email=account_email,
                success=False,
                duration_seconds=duration,
                error=str(e),
            )
        finally:
            if driver:
                driver.quit()
