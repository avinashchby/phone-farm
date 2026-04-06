"""Manage a pool of concurrent emulators for a single batch."""

from phone_farm.emulator import Emulator
from phone_farm.log import FarmLogger

logger = FarmLogger()


class EmulatorPool:
    """A pool of N emulators that start/stop together."""

    def __init__(
        self, *, batch_size: int, api_level: int, ram_mb: int, device_profile: str
    ) -> None:
        self.emulators = [
            Emulator(slot=i, api_level=api_level, ram_mb=ram_mb, device_profile=device_profile)
            for i in range(batch_size)
        ]

    async def start_all(self, *, headless: bool = True) -> list[bool]:
        """Start all emulators. Returns list of success booleans per slot.

        Continues even if individual emulators fail to start.
        """
        results: list[bool] = []
        for emu in self.emulators:
            try:
                await emu.create_avd()
                await emu.start(headless=headless)
                await emu.wait_for_boot()
                logger.emu(emu.slot, f"booted ({emu.adb_serial})")
                results.append(True)
            except Exception as e:
                logger.error(f"emu-{emu.slot} failed to start: {e}")
                results.append(False)
        return results

    async def stop_all(self) -> None:
        """Stop all emulators in the pool."""
        for emu in self.emulators:
            try:
                await emu.stop()
                logger.emu(emu.slot, "stopped")
            except Exception as e:
                logger.error(f"emu-{emu.slot} failed to stop: {e}")
