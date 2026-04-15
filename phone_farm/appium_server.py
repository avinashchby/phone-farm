"""Appium server lifecycle management."""

import asyncio
import logging
from dataclasses import dataclass, field

from phone_farm.log import FarmLogger

try:
    from appium import webdriver
except ImportError:  # pragma: no cover
    webdriver = None  # type: ignore[assignment]

logger = FarmLogger()
_log = logging.getLogger(__name__)

_HEALTH_RETRIES = 3
_HEALTH_DELAY = 2.0
_DRIVER_RETRIES = 3
_DRIVER_DELAY = 5.0


async def _http_get(url: str, timeout: int = 5):
    """Async-compatible HTTP GET using executor to avoid blocking."""
    from urllib.request import Request, urlopen

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: urlopen(Request(url), timeout=timeout))


async def create_driver_with_retry(
    appium_url: str,
    caps: dict | None = None,
    max_attempts: int = _DRIVER_RETRIES,
    delay: float = _DRIVER_DELAY,
):
    """Create Appium WebDriver with retry on connection errors.

    Retries on 'connection refused' and 'session not created'.
    Raises ConnectionError after max_attempts.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return webdriver.Remote(appium_url, options=caps)
        except Exception as exc:
            last_exc = exc
            _log.warning(
                "WebDriver connection failed (attempt %d/%d): %s",
                attempt,
                max_attempts,
                exc,
            )
            if attempt < max_attempts:
                await asyncio.sleep(delay)
    raise ConnectionError(
        f"Failed to create WebDriver after {max_attempts} attempts: {last_exc}"
    ) from last_exc


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

    async def _health_check(self) -> bool:
        """Check Appium /status endpoint. Returns True if healthy, False after max retries."""
        url = f"http://localhost:{self.port}/status"
        for attempt in range(1, _HEALTH_RETRIES + 1):
            try:
                resp = await _http_get(url)
                if resp.status == 200:
                    return True
            except Exception as exc:
                _log.warning(
                    "Appium health check failed (attempt %d/%d): %s",
                    attempt,
                    _HEALTH_RETRIES,
                    exc,
                )
                if attempt < _HEALTH_RETRIES:
                    await asyncio.sleep(_HEALTH_DELAY)
        return False

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
