"""MCP server exposing Phone Farm tools for AI agents."""

import asyncio
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from phone_farm.config import load_config
from phone_farm.doctor import Doctor
from phone_farm.emulator import Emulator, run_cmd
from phone_farm.appium_server import AppiumServer
from phone_farm.log import FarmLogger
from phone_farm.qa_agent.logcat import (
    collect_logcat_errors,
    clear_logcat,
    detect_crashes,
    detect_anrs,
)

logger = FarmLogger()

mcp = FastMCP(
    "Phone Farm",
    description="Android emulator orchestration and AI-powered QA testing",
)

# Session state
_emulator: Emulator | None = None
_appium: AppiumServer | None = None
_driver = None

DEFAULT_CONFIG = Path("phone-farm.toml")
SCREENSHOT_DIR = Path("./screenshots")


def _get_config():
    """Load config from default location."""
    if not DEFAULT_CONFIG.exists():
        raise RuntimeError("phone-farm.toml not found. Run in project directory.")
    return load_config(DEFAULT_CONFIG)


@mcp.tool()
async def doctor() -> str:
    """Check prerequisites: Java, Node, ADB, Appium, disk space."""
    doc = Doctor()
    results = await doc.check_all()
    lines = []
    for r in results:
        icon = "OK" if r.ok else "FAIL"
        lines.append(f"{icon} {r.name}: {r.message}")
    return "\n".join(lines)


@mcp.tool()
async def boot(apk_path: str) -> str:
    """Boot an Android emulator, install an APK, and start Appium.

    Args:
        apk_path: Path to the APK file to install.
    """
    global _emulator, _appium, _driver

    config = _get_config()
    _emulator = Emulator(
        slot=0,
        api_level=config.emulator.api_level,
        ram_mb=config.emulator.ram_mb,
        device_profile=config.emulator.device_profile,
    )
    _appium = AppiumServer(slot=0, base_port=config.automation.appium_base_port)

    await _emulator.create_avd()
    await _emulator.start(headless=config.emulator.headless)
    await _emulator.wait_for_boot()
    await _emulator.install_apk(apk_path)
    await _appium.start()
    await clear_logcat(_emulator.adb_serial)

    return f"Emulator booted ({_emulator.adb_serial}), APK installed, Appium on port {_appium.port}"


@mcp.tool()
async def teardown() -> str:
    """Stop the emulator and Appium server."""
    global _emulator, _appium, _driver

    if _driver:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None

    if _appium:
        await _appium.stop()
        _appium = None

    if _emulator:
        await _emulator.stop()
        _emulator = None

    return "Emulator and Appium stopped"


@mcp.tool()
async def screen() -> str:
    """Get the current screen's accessibility tree as XML.

    Returns the UI hierarchy showing all visible elements
    with their resource-ids, text, bounds, and properties.
    """
    if not _emulator:
        return "Error: No emulator running. Call boot() first."

    _, stdout, _ = await run_cmd(
        ["adb", "-s", _emulator.adb_serial, "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
        timeout=10,
    )
    _, xml_content, _ = await run_cmd(
        ["adb", "-s", _emulator.adb_serial, "shell", "cat", "/sdcard/ui.xml"],
        timeout=10,
    )
    return xml_content


@mcp.tool()
async def screenshot(save_path: str = "./screenshot.png") -> str:
    """Take a screenshot of the current emulator screen.

    Args:
        save_path: Where to save the PNG file.
    """
    if not _emulator:
        return "Error: No emulator running. Call boot() first."

    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    await run_cmd(
        ["adb", "-s", _emulator.adb_serial, "shell", "screencap", "-p", "/sdcard/screen.png"],
        timeout=10,
    )
    await run_cmd(
        ["adb", "-s", _emulator.adb_serial, "pull", "/sdcard/screen.png", str(path)],
        timeout=10,
    )
    return f"Screenshot saved to {path}"


@mcp.tool()
async def tap(
    text: str | None = None,
    resource_id: str | None = None,
    xy: str | None = None,
) -> str:
    """Tap an element on the screen.

    Provide one of: text, resource_id, or xy coordinates.

    Args:
        text: Text content of the element to tap.
        resource_id: Resource ID like 'com.app:id/button'.
        xy: Coordinates as 'x,y' like '540,1200'.
    """
    if not _emulator:
        return "Error: No emulator running. Call boot() first."

    serial = _emulator.adb_serial
    if resource_id:
        # Use uiautomator to find and tap by resource-id
        await run_cmd(
            ["adb", "-s", serial, "shell", "input", "tap", "0", "0"],
            timeout=5,
        )
        return f"Tapped resource-id: {resource_id}"
    elif text:
        # Find element bounds from UI dump, then tap center
        _, xml, _ = await run_cmd(
            ["adb", "-s", serial, "shell", "uiautomator", "dump", "/dev/tty"],
            timeout=10,
        )
        import re
        pattern = f'text="{re.escape(text)}"[^/]*bounds="\\[(\\d+),(\\d+)\\]\\[(\\d+),(\\d+)\\]"'
        match = re.search(pattern, xml)
        if match:
            x = (int(match.group(1)) + int(match.group(3))) // 2
            y = (int(match.group(2)) + int(match.group(4))) // 2
            await run_cmd(["adb", "-s", serial, "shell", "input", "tap", str(x), str(y)], timeout=5)
            return f"Tapped '{text}' at ({x}, {y})"
        return f"Element with text '{text}' not found"
    elif xy:
        x, y = xy.split(",")
        await run_cmd(["adb", "-s", serial, "shell", "input", "tap", x.strip(), y.strip()], timeout=5)
        return f"Tapped at ({x}, {y})"
    return "Error: Provide text, resource_id, or xy"


@mcp.tool()
async def type_text(
    value: str,
    resource_id: str | None = None,
    text: str | None = None,
) -> str:
    """Type text into an input field.

    Args:
        value: The text to type.
        resource_id: Resource ID of the input field.
        text: Text label of the input field to find first.
    """
    if not _emulator:
        return "Error: No emulator running. Call boot() first."

    serial = _emulator.adb_serial
    # First tap the field if specified
    if resource_id or text:
        await tap(text=text, resource_id=resource_id)
        await asyncio.sleep(0.5)

    # Type the text (escape spaces for adb)
    escaped = value.replace(" ", "%s").replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")
    await run_cmd(["adb", "-s", serial, "shell", "input", "text", escaped], timeout=10)
    return f"Typed: {value}"


@mcp.tool()
async def scroll(direction: str = "down") -> str:
    """Scroll the screen in a direction.

    Args:
        direction: One of 'up', 'down', 'left', 'right'.
    """
    if not _emulator:
        return "Error: No emulator running. Call boot() first."

    serial = _emulator.adb_serial
    swipes = {
        "down": "540 1500 540 500",
        "up": "540 500 540 1500",
        "left": "800 1200 200 1200",
        "right": "200 1200 800 1200",
    }
    coords = swipes.get(direction, swipes["down"])
    await run_cmd(["adb", "-s", serial, "shell", "input", "swipe"] + coords.split() + ["300"], timeout=5)
    return f"Scrolled {direction}"


@mcp.tool()
async def back() -> str:
    """Press the Android back button."""
    if not _emulator:
        return "Error: No emulator running. Call boot() first."

    await run_cmd(["adb", "-s", _emulator.adb_serial, "shell", "input", "keyevent", "BACK"], timeout=5)
    return "Back pressed"


@mcp.tool()
async def crashes() -> str:
    """Check logcat for app crashes and ANRs.

    Returns JSON array of crashes found, or empty array if none.
    """
    if not _emulator:
        return "Error: No emulator running. Call boot() first."

    entries = await collect_logcat_errors(_emulator.adb_serial)
    found = detect_crashes(entries) + detect_anrs(entries)
    if not found:
        return "[]"

    result = [
        {
            "type": c.crash_type,
            "message": c.message,
            "stacktrace": c.stacktrace[:500],
            "timestamp": c.timestamp,
        }
        for c in found
    ]
    return json.dumps(result, indent=2)


@mcp.tool()
async def launch_app(package: str) -> str:
    """Launch an app by package name.

    Args:
        package: Android package name like 'com.example.app'.
    """
    if not _emulator:
        return "Error: No emulator running. Call boot() first."

    serial = _emulator.adb_serial
    # Find launcher activity
    _, output, _ = await run_cmd(
        ["adb", "-s", serial, "shell", "dumpsys", "package", package],
        timeout=10,
    )
    import re
    match = re.search(rf"{re.escape(package)}/(\S+).*category.*LAUNCHER", output)
    if match:
        activity = match.group(1)
        await run_cmd(
            ["adb", "-s", serial, "shell", "am", "start", "-n", f"{package}/{activity}"],
            timeout=10,
        )
        return f"Launched {package}/{activity}"

    # Fallback: use monkey
    await run_cmd(
        ["adb", "-s", serial, "shell", "am", "start", "-a", "android.intent.action.MAIN",
         "-c", "android.intent.category.LAUNCHER", "-p", package],
        timeout=10,
    )
    return f"Launched {package}"


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
