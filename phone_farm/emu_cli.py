"""Emulator session manager for CLI-driven QA testing."""

import json
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options

from phone_farm.appium_server import AppiumServer
from phone_farm.config import FarmConfig
from phone_farm.emulator import Emulator
from phone_farm.log import FarmLogger
from phone_farm.qa_agent.logcat import collect_logcat_errors, clear_logcat, detect_crashes, detect_anrs
from phone_farm.qa_agent.state import get_screen_xml, take_screenshot_b64

logger = FarmLogger()

STATE_FILE = Path(".phone-farm-session.json")


def _save_state(adb_serial: str, appium_port: int) -> None:
    """Save session state to disk so CLI commands can reconnect."""
    STATE_FILE.write_text(json.dumps({
        "adb_serial": adb_serial,
        "appium_port": appium_port,
    }))


def _load_state() -> dict:
    """Load session state from disk."""
    if not STATE_FILE.exists():
        raise RuntimeError("No active session. Run: phone-farm emu boot <apk>")
    return json.loads(STATE_FILE.read_text())


def _clear_state() -> None:
    """Remove session state file."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def _get_driver(state: dict):
    """Create an Appium driver from saved session state."""
    options = UiAutomator2Options()
    options.udid = state["adb_serial"]
    options.no_reset = True
    return webdriver.Remote(
        command_executor=f"http://127.0.0.1:{state['appium_port']}/wd/hub",
        options=options,
    )


async def boot_emulator(config: FarmConfig, apk_path: str) -> None:
    """Boot emulator, install APK, start Appium."""
    emu = Emulator(
        slot=0,
        api_level=config.emulator.api_level,
        ram_mb=config.emulator.ram_mb,
        device_profile=config.emulator.device_profile,
    )
    appium = AppiumServer(slot=0, base_port=config.automation.appium_base_port)

    logger.info("Creating AVD...")
    await emu.create_avd()
    logger.info("Starting emulator...")
    await emu.start(headless=config.emulator.headless)
    logger.info("Waiting for boot...")
    await emu.wait_for_boot()
    logger.info(f"Installing APK: {apk_path}")
    await emu.install_apk(apk_path)
    logger.info("Starting Appium...")
    await appium.start()

    _save_state(emu.adb_serial, appium.port)
    await clear_logcat(emu.adb_serial)
    logger.success(f"Ready! Emulator {emu.adb_serial}, Appium port {appium.port}")


async def teardown_emulator(config: FarmConfig) -> None:
    """Stop emulator and Appium."""
    _load_state()  # Verify session exists
    appium = AppiumServer(slot=0, base_port=config.automation.appium_base_port)
    emu = Emulator(
        slot=0,
        api_level=config.emulator.api_level,
        ram_mb=config.emulator.ram_mb,
        device_profile=config.emulator.device_profile,
    )
    await appium.stop()
    await emu.stop()
    _clear_state()
    logger.success("Emulator and Appium stopped")


def get_screen() -> str:
    """Get accessibility tree XML from the running emulator."""
    state = _load_state()
    driver = _get_driver(state)
    try:
        return get_screen_xml(driver)
    finally:
        driver.quit()


def take_screenshot(output_path: str) -> str:
    """Take a screenshot and save to output_path. Returns the path."""
    state = _load_state()
    driver = _get_driver(state)
    try:
        take_screenshot_b64(driver, save_path=Path(output_path))
        return output_path
    finally:
        driver.quit()


def tap_element(*, resource_id: str | None, text: str | None, xy: str | None) -> None:
    """Tap an element by resource-id, text, or x,y coordinates."""
    state = _load_state()
    driver = _get_driver(state)
    try:
        if resource_id:
            driver.find_element("id", resource_id).click()
        elif text:
            driver.find_element("xpath", f'//*[@text="{text}"]').click()
        elif xy:
            x, y = [int(v) for v in xy.split(",")]
            driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
        else:
            raise ValueError("Provide --id, --text, or --xy")
    finally:
        driver.quit()


def type_text(*, resource_id: str | None, text: str | None, value: str) -> None:
    """Type text into an input field."""
    state = _load_state()
    driver = _get_driver(state)
    try:
        if resource_id:
            el = driver.find_element("id", resource_id)
        elif text:
            el = driver.find_element("xpath", f'//*[@text="{text}"]')
        else:
            raise ValueError("Provide --id or --text to identify the input field")
        el.clear()
        el.send_keys(value)
    finally:
        driver.quit()


def scroll(direction: str) -> None:
    """Scroll in the given direction."""
    state = _load_state()
    driver = _get_driver(state)
    try:
        driver.execute_script(
            "mobile: scrollGesture",
            {"left": 100, "top": 300, "width": 200, "height": 500,
             "direction": direction, "percent": 0.75},
        )
    finally:
        driver.quit()


def press_back() -> None:
    """Press the back button."""
    state = _load_state()
    driver = _get_driver(state)
    try:
        driver.back()
    finally:
        driver.quit()


async def check_crashes(adb_serial: str | None = None) -> list[dict]:
    """Check logcat for crashes and ANRs. Returns JSON-serializable list."""
    if adb_serial is None:
        state = _load_state()
        adb_serial = state["adb_serial"]
    entries = await collect_logcat_errors(adb_serial)
    crashes = detect_crashes(entries) + detect_anrs(entries)
    return [
        {
            "type": c.crash_type,
            "message": c.message,
            "stacktrace": c.stacktrace[:500],
            "timestamp": c.timestamp,
        }
        for c in crashes
    ]
