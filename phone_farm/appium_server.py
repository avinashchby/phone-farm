"""Appium server lifecycle management."""

import asyncio
from dataclasses import dataclass, field

from phone_farm.log import FarmLogger

logger = FarmLogger()


@dataclass
class AppiumServer:
    """Manages a single Appium server instance for one emulator slot."""

    slot: int
    base_port: int
    _process: asyncio.subprocess.Process | None = field(default=None, repr=False)

    @property
    def port(self) -> int:
        """Appium port for this slot."""
        return self.base_port + self.slot

    @property
    def url(self) -> str:
        """Appium server URL."""
        return f"http://127.0.0.1:{self.port}"

    async def start(self) -> None:
        """Start the Appium server."""
        args = [
            "appium",
            "--port", str(self.port),
            "--base-path", "/wd/hub",
            "--relaxed-security",
            "--log-level", "warn",
        ]
        self._process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Wait for server to be ready
        await asyncio.sleep(3)
        logger.emu(self.slot, f"Appium started on port {self.port}")

    async def stop(self) -> None:
        """Stop the Appium server."""
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None
            logger.emu(self.slot, "Appium stopped")
