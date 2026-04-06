"""Background QA test runner for the web dashboard.

Boots an emulator, installs the APK, runs the QA agent loop,
and streams progress updates back to AppState.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from phone_farm.appium_server import AppiumServer
from phone_farm.config import FarmConfig, load_config
from phone_farm.emulator import Emulator, run_cmd
from phone_farm.log import FarmLogger
from phone_farm.qa_agent.bug_report import Bug, generate_report, save_report_json
from phone_farm.qa_agent.logcat import (
    clear_logcat,
    collect_logcat_errors,
    detect_anrs,
    detect_crashes,
)
from phone_farm.web.state import AppState

logger = FarmLogger()

DEFAULT_CONFIG = Path("phone-farm.toml")
SCREENSHOT_DIR = Path("./screenshots")
REPORT_DIR = Path("./qa_reports")


async def _run_qa_loop(
    state: AppState,
    run_id: str,
    apk_path: Path,
    config: FarmConfig,
) -> None:
    """Run the full QA test lifecycle as a background task.

    Uses ADB commands directly (no Appium driver needed) to match
    the MCP server approach. This avoids the anthropic dependency —
    the loop does deterministic exploration without an AI backend.
    """
    emu: Emulator | None = None
    appium: AppiumServer | None = None
    run = state.test_runs[run_id]
    slot = 0
    bugs: list[Bug] = []
    start_time = datetime.now(timezone.utc).isoformat()

    max_steps = 50
    if config.qa_agent:
        max_steps = config.qa_agent.max_steps

    try:
        # 1. Boot emulator
        run.status = "booting"
        emu = Emulator(
            slot=slot,
            api_level=config.emulator.api_level,
            ram_mb=config.emulator.ram_mb,
            device_profile=config.emulator.device_profile,
        )
        appium = AppiumServer(slot=slot, base_port=config.automation.appium_base_port)

        state.add_phone(slot, f"emulator-{5554 + slot * 2}")
        state.phones[slot].status = "booting"

        await emu.create_avd()
        await emu.start(headless=config.emulator.headless)
        await emu.wait_for_boot()
        state.phones[slot].status = "running"

        # 2. Install APK
        run.status = "installing"
        await emu.install_apk(str(apk_path))
        await clear_logcat(emu.adb_serial)

        # 3. Start Appium
        await appium.start()

        # 4. Launch the app (find package from APK)
        run.status = "running"
        package = await _get_package_from_apk(str(apk_path))
        if package:
            await run_cmd(
                ["adb", "-s", emu.adb_serial, "shell", "monkey", "-p", package, "1"],
                timeout=10,
            )
            await asyncio.sleep(3)  # Wait for app launch

        # 5. Exploration loop
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        seen_screens: set[str] = set()
        stale_count = 0

        for step in range(max_steps):
            if run.status == "stopped":
                break

            try:
                step_bugs = await _exploration_step(
                    emu.adb_serial, step, seen_screens, run, state, bugs
                )
                bugs.extend(step_bugs)

                prev_count = len(seen_screens)
                seen_screens.add(f"step-{step}")  # fallback tracking
                if run.screens_found > prev_count:
                    stale_count = 0
                else:
                    stale_count += 1
                run.steps_completed = step + 1

                # If stuck, press back
                if stale_count > 10:
                    await run_cmd(
                        ["adb", "-s", emu.adb_serial, "shell", "input", "keyevent", "BACK"],
                        timeout=5,
                    )
                    stale_count = 0

            except Exception as e:
                logger.error(f"Step {step} error: {e}")
                # Check for crashes
                crash_bugs = await _check_crashes(emu.adb_serial)
                bugs.extend(crash_bugs)
                run.bugs_found = len(bugs)
                if crash_bugs:
                    continue
                break

        # 6. Final crash check
        final_crashes = await _check_crashes(emu.adb_serial)
        bugs.extend(final_crashes)
        run.bugs_found = len(bugs)

        # 7. Generate report
        end_time = datetime.now(timezone.utc).isoformat()
        report = generate_report(
            bugs=bugs,
            app_description=run.app_description or run.apk_name,
            apk_path=str(apk_path),
            start_time=start_time,
            end_time=end_time,
            total_actions=run.steps_completed,
            unique_screens=run.screens_found,
            coverage_summary=f"Explored {run.screens_found} unique screens in {run.steps_completed} steps",
        )
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f"report-{run_id}.json"
        save_report_json(report, report_path)

        state.complete_test_run(run_id, report_path=str(report_path))
        logger.success(f"QA test {run_id} completed: {len(bugs)} bugs found")

    except Exception as e:
        logger.error(f"QA test {run_id} failed: {e}")
        run.status = "error"
        run.error_message = str(e)

    finally:
        # Teardown
        if appium:
            try:
                await appium.stop()
            except Exception:
                pass
        if emu:
            try:
                await emu.stop()
            except Exception:
                pass
        state.remove_phone(slot)


async def _exploration_step(
    adb_serial: str,
    step: int,
    seen_screens: set[str],
    run,
    state: AppState,
    existing_bugs: list[Bug],
) -> list[Bug]:
    """Execute one exploration step: observe screen, interact, check crashes."""
    bugs: list[Bug] = []

    # Get UI hierarchy
    await run_cmd(
        ["adb", "-s", adb_serial, "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
        timeout=10,
    )
    _, xml, _ = await run_cmd(
        ["adb", "-s", adb_serial, "shell", "cat", "/sdcard/ui.xml"],
        timeout=10,
    )

    # Compute screen signature
    sig = _simple_screen_sig(xml)
    if sig not in seen_screens:
        seen_screens.add(sig)
        run.screens_found = len(seen_screens)

    # Take periodic screenshots
    if step % 5 == 0:
        ss_path = SCREENSHOT_DIR / f"qa-{run.run_id}-step-{step}.png"
        await run_cmd(
            ["adb", "-s", adb_serial, "shell", "screencap", "-p", "/sdcard/screen.png"],
            timeout=10,
        )
        await run_cmd(
            ["adb", "-s", adb_serial, "pull", "/sdcard/screen.png", str(ss_path)],
            timeout=10,
        )
        run.latest_screenshot = str(ss_path)

    # Find clickable elements and interact
    clickables = _extract_clickables(xml)
    if clickables:
        # Pick element based on step (round-robin through elements)
        target = clickables[step % len(clickables)]
        x, y = target["center"]
        await run_cmd(
            ["adb", "-s", adb_serial, "shell", "input", "tap", str(x), str(y)],
            timeout=5,
        )
        await asyncio.sleep(1)

    # Scroll every 10 steps to reveal more content
    if step % 10 == 0 and step > 0:
        await run_cmd(
            ["adb", "-s", adb_serial, "shell", "input", "swipe", "540", "1500", "540", "500", "300"],
            timeout=5,
        )
        await asyncio.sleep(0.5)

    # Check crashes every 5 steps
    if step % 5 == 0:
        crash_bugs = await _check_crashes(adb_serial)
        bugs.extend(crash_bugs)
        run.bugs_found = len(existing_bugs) + len(bugs)

    return bugs


def _simple_screen_sig(xml: str) -> str:
    """Compute a simple screen signature from UI XML."""
    import hashlib
    # Use a hash of text content and resource-ids for dedup
    return hashlib.sha256(xml.encode()).hexdigest()[:16]


def _extract_clickables(xml: str) -> list[dict]:
    """Extract clickable elements with their center coordinates from UI XML."""
    import re
    clickables = []
    pattern = r'clickable="true"[^/]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
    # Also try reverse attribute order
    pattern2 = r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^/]*clickable="true"'

    for match in re.finditer(pattern, xml):
        x1, y1, x2, y2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        clickables.append({"center": ((x1 + x2) // 2, (y1 + y2) // 2)})

    for match in re.finditer(pattern2, xml):
        x1, y1, x2, y2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        center = ((x1 + x2) // 2, (y1 + y2) // 2)
        if not any(c["center"] == center for c in clickables):
            clickables.append({"center": center})

    return clickables


async def _check_crashes(adb_serial: str) -> list[Bug]:
    """Check logcat for crashes and ANRs."""
    entries = await collect_logcat_errors(adb_serial)
    crashes = detect_crashes(entries) + detect_anrs(entries)
    bugs = []
    for crash in crashes:
        bugs.append(Bug(
            severity="critical" if crash.crash_type != "anr" else "high",
            category=crash.crash_type,
            title=f"{crash.crash_type}: {crash.message[:80]}",
            description=crash.message,
            steps_to_reproduce=["Automated exploration"],
            screen_signature="",
            logcat_snippet=crash.stacktrace[:500],
        ))
    return bugs


async def _get_package_from_apk(apk_path: str) -> str | None:
    """Extract package name from APK using aapt2 or aapt."""
    for tool in ["aapt2", "aapt"]:
        try:
            _, stdout, _ = await run_cmd(
                [tool, "dump", "badging", apk_path],
                timeout=15,
            )
            import re
            match = re.search(r"package: name='([^']+)'", stdout)
            if match:
                return match.group(1)
        except Exception:
            continue
    return None


def start_qa_background(
    state: AppState,
    run_id: str,
    apk_path: Path,
) -> asyncio.Task:
    """Launch the QA test as a background asyncio task.

    Returns the task so it can be cancelled if needed.
    """
    if not DEFAULT_CONFIG.exists():
        raise RuntimeError("phone-farm.toml not found")

    config = load_config(DEFAULT_CONFIG)
    task = asyncio.create_task(
        _run_qa_loop(state, run_id, apk_path, config),
        name=f"qa-{run_id}",
    )
    # Store task on the run for cancellation
    if run_id in state.test_runs:
        state.test_runs[run_id].task = task
    return task
