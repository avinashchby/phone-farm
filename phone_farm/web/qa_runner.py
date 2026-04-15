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
from phone_farm.qa_agent.login_detect import detect_login_screen, extract_login_fields
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
    api_key: str | None = None,
) -> None:
    """Run the full QA test lifecycle as a background task.

    When api_key is provided, uses the AI agent (Pro mode) with the
    Anthropic API for intelligent exploration. Otherwise falls back
    to deterministic ADB-based exploration (Free mode).
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

        if api_key and state.pro_mode_available:
            from phone_farm_pro.exploration import run_ai_exploration
            bugs = await run_ai_exploration(
                emu, appium, apk_path, run, state, api_key, max_steps,
            )
        else:
            bugs = await _run_deterministic_exploration(
                emu, run, state, max_steps, bugs,
                test_email=getattr(run, "test_email", ""),
                test_password=getattr(run, "test_password", ""),
                skip_login=getattr(run, "skip_login", False),
            )

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

        from phone_farm.scoring import compute_score
        from phone_farm.report_renderer import render_html_report
        score = compute_score(report)
        run_ss_dir = SCREENSHOT_DIR / run_id
        html = render_html_report(
            report, score, screenshots_dir=run_ss_dir if run_ss_dir.is_dir() else None
        )
        html_path = REPORT_DIR / f"report-{run_id}.html"
        html_path.write_text(html, encoding="utf-8")

        state.complete_test_run(
            run_id, report_path=str(report_path), html_report_path=str(html_path)
        )
        logger.success(f"QA test {run_id} completed: {len(bugs)} bugs found")
        if not api_key and len(bugs) > 0:
            logger.info("Tip: AI mode finds visual bugs and auto-categorizes by severity")

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


async def _handle_login(driver, xml: str, email: str, password: str) -> None:
    """Fill login form and submit. Attempts once; caller retries if needed.

    driver: Appium WebDriver or None (skips field interaction if None).
    """
    if driver is None:
        return
    fields = extract_login_fields(xml)
    if fields["email_field"]:
        el = driver.find_element("id", fields["email_field"])
        el.clear()
        el.send_keys(email)
    if fields["password_field"]:
        el = driver.find_element("id", fields["password_field"])
        el.clear()
        el.send_keys(password)
    if fields["submit_button"]:
        driver.find_element("id", fields["submit_button"]).click()


async def _run_deterministic_exploration(
    emu,
    run,
    state: AppState,
    max_steps: int,
    bugs: list[Bug],
    test_email: str = "",
    test_password: str = "",
    skip_login: bool = False,
) -> list[Bug]:
    """Run deterministic exploration using ADB commands."""
    seen_screens: set[str] = set()
    stale_count = 0

    for step in range(max_steps):
        if run.status == "stopped":
            break

        try:
            # Fetch current XML to check for login screen before acting
            await run_cmd(
                ["adb", "-s", emu.adb_serial, "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                timeout=10,
            )
            _, current_xml, _ = await run_cmd(
                ["adb", "-s", emu.adb_serial, "shell", "cat", "/sdcard/ui.xml"],
                timeout=10,
            )

            if detect_login_screen(current_xml):
                if skip_login:
                    await run_cmd(
                        ["adb", "-s", emu.adb_serial, "shell", "input", "keyevent", "BACK"],
                        timeout=5,
                    )
                    continue
                elif test_email and test_password:
                    login_attempts = getattr(run, "_login_attempts", 0) + 1
                    run._login_attempts = login_attempts
                    if login_attempts >= 3:
                        bugs.append(Bug(
                            severity="medium",
                            category="functional",
                            title="Unable to authenticate with test credentials",
                            description="Login failed after 3 attempts",
                            steps_to_reproduce=["Attempted login with provided test credentials"],
                            screen_signature="login",
                        ))
                    else:
                        await _handle_login(None, current_xml, test_email, test_password)
                    continue
                else:
                    await run_cmd(
                        ["adb", "-s", emu.adb_serial, "shell", "input", "keyevent", "BACK"],
                        timeout=5,
                    )
                    continue

            step_bugs = await _exploration_step(
                emu.adb_serial, step, seen_screens, run, state, bugs
            )
            bugs.extend(step_bugs)

            prev_count = len(seen_screens)
            seen_screens.add(f"step-{step}")
            if run.screens_found > prev_count:
                stale_count = 0
            else:
                stale_count += 1
            run.steps_completed = step + 1

            if stale_count > 10:
                await run_cmd(
                    ["adb", "-s", emu.adb_serial, "shell", "input", "keyevent", "BACK"],
                    timeout=5,
                )
                stale_count = 0

        except Exception as e:
            logger.error(f"Step {step} error: {e}")
            crash_bugs = await _check_crashes(emu.adb_serial)
            bugs.extend(crash_bugs)
            run.bugs_found = len(bugs)
            if crash_bugs:
                continue
            break

    final_crashes = await _check_crashes(emu.adb_serial)
    bugs.extend(final_crashes)
    return bugs


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

    # Take a screenshot at every step, stored in a per-run subdirectory
    run_ss_dir = SCREENSHOT_DIR / run.run_id
    run_ss_dir.mkdir(parents=True, exist_ok=True)
    ss_path = run_ss_dir / f"step-{step:03d}.png"
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
    """Compute a screen signature from structural elements in the UI XML.

    Hashes resource-ids, text content, and class names rather than the
    raw XML, so minor attribute changes (e.g. focused state, scroll
    position) don't create false-new screens.
    """
    import hashlib
    import re

    resource_ids = sorted(re.findall(r'resource-id="([^"]+)"', xml))
    texts = sorted(re.findall(r'text="([^"]+)"', xml))
    classes = sorted(re.findall(r'class="([^"]+)"', xml))
    structural = "|".join(resource_ids) + "||" + "|".join(texts) + "||" + "|".join(classes)
    return hashlib.sha256(structural.encode()).hexdigest()[:16]


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
    api_key: str | None = None,
) -> asyncio.Task:
    """Launch the QA test as a background asyncio task.

    When api_key is provided, uses AI-powered exploration (Pro mode).
    Returns the task so it can be cancelled if needed.
    """
    if not DEFAULT_CONFIG.exists():
        raise RuntimeError("phone-farm.toml not found")

    config = load_config(DEFAULT_CONFIG)
    task = asyncio.create_task(
        _run_qa_loop(state, run_id, apk_path, config, api_key=api_key),
        name=f"qa-{run_id}",
    )
    # Store task on the run for cancellation
    if run_id in state.test_runs:
        state.test_runs[run_id].task = task
    return task
