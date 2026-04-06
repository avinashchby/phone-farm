"""Top-level orchestrator: batches accounts, runs cycles, collects results."""

import asyncio
import random

from phone_farm.appium_server import AppiumServer
from phone_farm.automation import AutomationRunner
from phone_farm.config import FarmConfig
from phone_farm.db import Database
from phone_farm.log import FarmLogger
from phone_farm.pool import EmulatorPool

logger = FarmLogger()


class Orchestrator:
    """Runs a full cycle: batch accounts across emulator pool."""

    def __init__(self, *, config: FarmConfig) -> None:
        self.config = config

    def _compute_batches(self, accounts: list[dict]) -> list[list[dict]]:
        """Split active accounts into batches of batch_size.

        Filters out cooldown/banned accounts. Shuffles order for anti-detection.
        """
        active = [a for a in accounts if a["status"] == "active"]
        random.shuffle(active)
        size = self.config.farm.batch_size
        return [active[i : i + size] for i in range(0, len(active), size)]

    async def run_cycle(self, *, db: Database, mode: str) -> dict:
        """Run a full cycle across all accounts.

        Args:
            db: Database instance for account lookup and run recording.
            mode: "tester-gate" or "qa".

        Returns:
            Summary dict with passed/failed/skipped counts.
        """
        flow_name = self.config.automation.default_flow
        if mode == "qa":
            flow_name = "deep_test"

        all_accounts = await db.list_accounts()
        batches = self._compute_batches(all_accounts)

        total_passed = 0
        total_failed = 0
        total_skipped = 0

        logger.info(
            f"Starting {mode} cycle ({len(all_accounts)} accounts, "
            f"{len(batches)} batches of {self.config.farm.batch_size})"
        )

        for batch_idx, batch in enumerate(batches, 1):
            logger.batch(batch_idx, len(batches), f"accounts: {', '.join(a['email'] for a in batch)}")

            if batch_idx > 1:
                delay = random.uniform(30, 60)
                logger.info(f"Waiting {delay:.0f}s before next batch")
                await asyncio.sleep(delay)

            pool = EmulatorPool(
                batch_size=len(batch),
                api_level=self.config.emulator.api_level,
                ram_mb=self.config.emulator.ram_mb,
                device_profile=self.config.emulator.device_profile,
            )

            boot_results = await pool.start_all(headless=self.config.emulator.headless)

            appium_servers: list[AppiumServer] = []
            for slot in range(len(batch)):
                server = AppiumServer(slot=slot, base_port=self.config.automation.appium_base_port)
                appium_servers.append(server)
                if boot_results[slot]:
                    await server.start()

            for slot, account in enumerate(batch):
                if not boot_results[slot]:
                    logger.emu(slot, f"skipped (boot failed) — {account['email']}")
                    total_skipped += 1
                    continue

                runner = AutomationRunner(
                    appium_url=appium_servers[slot].url,
                    adb_serial=pool.emulators[slot].adb_serial,
                    apk_path=self.config.paths.apk,
                    flow_name=flow_name,
                    screenshot_dir=self.config.paths.screenshots,
                )

                result = await runner.run(account_email=account["email"])

                await db.record_run(
                    account_id=account["id"],
                    result="success" if result.success else "fail",
                    duration_seconds=result.duration_seconds,
                    error_log=result.error,
                )

                if result.success:
                    logger.emu(slot, f"flow complete ({result.duration_seconds}s) — {account['email']}")
                    total_passed += 1
                else:
                    logger.emu(slot, f"FAILED: {result.error} — {account['email']}")
                    total_failed += 1
                    if result.error and "login" in result.error.lower():
                        await db.update_account_status(account["email"], "cooldown")
                        logger.emu(slot, f"marked cooldown — {account['email']}")

            for server in appium_servers:
                await server.stop()
            await pool.stop_all()

            logger.batch(batch_idx, len(batches), f"complete: {total_passed} passed, {total_failed} failed")

        summary = {
            "total": len(all_accounts),
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
        }
        logger.info(
            f"Cycle complete: {total_passed}/{total_passed + total_failed + total_skipped} passed, "
            f"{total_failed} failed, {total_skipped} skipped"
        )
        return summary
