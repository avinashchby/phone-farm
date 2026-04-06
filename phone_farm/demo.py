"""Demo mode: download a sample APK and run a QA test with zero setup.

Downloads the Wikipedia Android app (Apache 2.0 licensed, ~30MB) on first run
and launches an automated QA exploration session.
"""

import asyncio
from pathlib import Path

from rich.console import Console

from phone_farm.config import load_config
from phone_farm.doctor import Doctor
from phone_farm.emulator import Emulator, run_cmd
from phone_farm.appium_server import AppiumServer
from phone_farm.log import FarmLogger
from phone_farm.qa_agent.logcat import clear_logcat

logger = FarmLogger()
console = Console()

DEMO_DIR = Path.home() / ".phone-farm" / "demo"
DEMO_APK = DEMO_DIR / "wikipedia.apk"
# Wikipedia APK from F-Droid (Apache 2.0, open source)
DEMO_APK_URL = (
    "https://f-droid.org/repo/org.wikipedia_50522.apk"
)
DEMO_PACKAGE = "org.wikipedia"

CONFIG_PATH = Path("phone-farm.toml")


async def _download_apk() -> Path:
    """Download the demo APK if not already cached."""
    if DEMO_APK.exists():
        console.print(f"[dim]Using cached APK: {DEMO_APK}[/dim]")
        return DEMO_APK

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    console.print("[bold]Downloading Wikipedia APK (~30MB)...[/bold]")

    _, _, _ = await run_cmd(
        ["curl", "-sSL", "-o", str(DEMO_APK), DEMO_APK_URL],
        timeout=120,
    )

    if not DEMO_APK.exists() or DEMO_APK.stat().st_size < 1_000_000:
        raise RuntimeError("APK download failed. Check your internet connection.")

    size_mb = DEMO_APK.stat().st_size / 1_000_000
    console.print(f"[green]Downloaded {size_mb:.1f}MB[/green]")
    return DEMO_APK


async def _check_prerequisites() -> bool:
    """Quick prerequisite check before demo."""
    doc = Doctor()
    results = await doc.check_all()
    failed = [r for r in results if not r.ok]
    if failed:
        console.print("[bold red]Prerequisites missing:[/bold red]")
        for r in failed:
            console.print(f"  [red]FAIL[/red] {r.name}: {r.message}")
        console.print("\n[dim]Run: phone-farm doctor  for details[/dim]")
        console.print("[dim]Run: curl -sSL https://raw.githubusercontent.com/"
                      "avinashchby/phone-farm/main/install.sh | bash[/dim]")
        return False
    return True


async def run_demo(max_steps: int = 30) -> None:
    """Run the full demo: download APK, boot emulator, explore app.

    Args:
        max_steps: Number of exploration steps (default 30 for a quick demo).
    """
    console.print("\n[bold accent]Phone Farm Demo[/bold accent]")
    console.print("=" * 50)
    console.print("This will:")
    console.print("  1. Download Wikipedia app (open source, Apache 2.0)")
    console.print("  2. Boot an Android emulator")
    console.print("  3. Install the app and explore it automatically")
    console.print("  4. Generate a QA bug report")
    console.print()

    # Check prerequisites
    if not await _check_prerequisites():
        return

    # Download APK
    apk_path = await _download_apk()

    # Load or create minimal config
    if CONFIG_PATH.exists():
        config = load_config(CONFIG_PATH)
    else:
        console.print("[dim]No phone-farm.toml found, using defaults[/dim]")
        from phone_farm.config import (
            FarmConfig, FarmSection, EmulatorSection,
            AutomationSection, PathsSection, QAAgentSection,
        )
        config = FarmConfig(
            farm=FarmSection(batch_size=1, cycle_delay_seconds=60, max_retries=2),
            emulator=EmulatorSection(
                api_level=34, ram_mb=1536, headless=True, device_profile="pixel_6",
            ),
            automation=AutomationSection(
                appium_base_port=4723, default_flow="daily_usage",
                screenshot_on_failure=True, human_like_delays=False,
            ),
            paths=PathsSection(
                apk=".", scripts="scripts", logs="logs",
                db="data/farm.db", screenshots="screenshots", snapshots="snapshots",
            ),
            qa_agent=QAAgentSection(
                ai_backend="mock", max_steps=max_steps,
                screenshot_interval=10, output_dir="./qa_reports",
            ),
        )

    # Boot emulator
    emu = Emulator(
        slot=0,
        api_level=config.emulator.api_level,
        ram_mb=config.emulator.ram_mb,
        device_profile=config.emulator.device_profile,
    )
    appium = AppiumServer(slot=0, base_port=config.automation.appium_base_port)

    try:
        console.print("\n[bold]Step 1/4:[/bold] Creating emulator...")
        await emu.create_avd()

        console.print("[bold]Step 2/4:[/bold] Booting emulator...")
        await emu.start(headless=config.emulator.headless)
        await emu.wait_for_boot()

        console.print("[bold]Step 3/4:[/bold] Installing Wikipedia...")
        await emu.install_apk(str(apk_path))
        await clear_logcat(emu.adb_serial)
        await appium.start()

        # Launch the app
        await run_cmd(
            ["adb", "-s", emu.adb_serial, "shell",
             "monkey", "-p", DEMO_PACKAGE, "1"],
            timeout=10,
        )
        await asyncio.sleep(3)

        console.print(f"[bold]Step 4/4:[/bold] Exploring app ({max_steps} steps)...")

        # Run exploration using the qa_runner logic
        from phone_farm.web.state import AppState
        from phone_farm.web.qa_runner import _run_qa_loop

        state = AppState()
        run_id = state.start_test_run("wikipedia.apk", "Wikipedia - free encyclopedia app")

        await _run_qa_loop(state, run_id, apk_path, config)

        # Print results
        run = state.test_runs[run_id]
        console.print("\n" + "=" * 50)
        console.print("[bold green]Demo Complete![/bold green]")
        console.print(f"  Steps: {run.steps_completed}")
        console.print(f"  Screens discovered: {run.screens_found}")
        console.print(f"  Bugs found: {run.bugs_found}")
        if run.report_path:
            console.print(f"  Report: {run.report_path}")
        console.print()
        console.print("[dim]To test your own app:[/dim]")
        console.print("  phone-farm emu boot ./your-app.apk")
        console.print("  phone-farm serve  # web dashboard")

    finally:
        console.print("\n[dim]Cleaning up...[/dim]")
        try:
            await appium.stop()
        except Exception:
            pass
        try:
            await emu.stop()
        except Exception:
            pass
