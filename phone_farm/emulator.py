"""Android emulator lifecycle management via SDK CLI tools."""

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class EmulatorError(Exception):
    """Raised when an emulator operation fails."""


_BOOT_DELAYS = [5, 15, 30]


async def _retry(coro_fn, max_attempts: int, delay: float, label: str):
    """Retry an async callable up to max_attempts times with fixed delay.

    Raises EmulatorError on final failure.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_fn()
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts:
                logger.warning("%s failed (attempt %d/%d): %s", label, attempt, max_attempts, exc)
                await asyncio.sleep(delay)
    raise EmulatorError(f"{label} failed after {max_attempts} attempts: {last_exc}") from last_exc


async def run_cmd(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Run a shell command async, return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise EmulatorError(f"Command timed out after {timeout}s: {' '.join(args)}")
    return proc.returncode or 0, stdout.decode(), stderr.decode()


async def start_emulator_process(args: list[str]) -> asyncio.subprocess.Process:
    """Start an emulator as a long-running background process."""
    return await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


@dataclass
class Emulator:
    """Manages a single Android emulator slot."""

    slot: int
    api_level: int
    ram_mb: int
    device_profile: str
    _process: asyncio.subprocess.Process | None = field(default=None, repr=False)

    @property
    def avd_name(self) -> str:
        """AVD name for this slot."""
        return f"phone-farm-slot-{self.slot}"

    @property
    def adb_serial(self) -> str:
        """ADB serial for this emulator (port-based)."""
        port = 5554 + (self.slot * 2)
        return f"emulator-{port}"

    @property
    def adb_port(self) -> int:
        """Console port for this emulator."""
        return 5554 + (self.slot * 2)

    async def create_avd(self) -> None:
        """Create an AVD using avdmanager. Retries up to 2 times on failure."""
        system_image = f"system-images;android-{self.api_level};google_apis;arm64-v8a"
        args = [
            "avdmanager", "create", "avd",
            "--name", self.avd_name,
            "--package", system_image,
            "--device", self.device_profile,
            "--force",
        ]

        async def _do() -> None:
            returncode, _, stderr = await run_cmd(args)
            if returncode != 0:
                raise Exception(stderr.strip() or "avdmanager failed")

        await _retry(_do, max_attempts=2, delay=5.0, label=f"create_avd(slot={self.slot})")

    async def _start_once(self) -> None:
        """Launch the emulator process once (no retry). Reads self._headless."""
        headless = getattr(self, "_headless", True)
        args = [
            "emulator", "-avd", self.avd_name,
            "-port", str(self.adb_port),
            "-memory", str(self.ram_mb),
            "-no-audio",
            "-no-boot-anim",
        ]
        if headless:
            args.append("-no-window")
        self._process = await start_emulator_process(args)

    async def _boot_with_retry(self) -> None:
        """Boot emulator with exponential backoff retry (3 attempts: 5s, 15s, 30s)."""
        last_exc: Exception | None = None
        for i, delay in enumerate(_BOOT_DELAYS):
            try:
                await self._start_once()
                return
            except Exception as exc:
                last_exc = exc
                logger.warning("Emulator boot failed (attempt %d/3): %s", i + 1, exc)
                if i < len(_BOOT_DELAYS) - 1:
                    await asyncio.sleep(delay)
        raise EmulatorError(
            f"Emulator failed to boot after 3 attempts: {last_exc}\n"
            "Fix: check ANDROID_HOME is set, KVM is enabled, and system images are installed."
        ) from last_exc

    async def start(self, *, headless: bool = True) -> None:
        """Start the emulator with retry on boot failure."""
        self._headless = headless  # type: ignore[attr-defined]
        await self._boot_with_retry()

    async def wait_for_boot(self, timeout: int = 120) -> None:
        """Wait until the emulator has fully booted."""
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            returncode, stdout, _ = await run_cmd(
                ["adb", "-s", self.adb_serial, "shell", "getprop", "sys.boot_completed"],
                timeout=10,
            )
            if returncode == 0 and stdout.strip() == "1":
                return
            await asyncio.sleep(2)
        raise EmulatorError(f"Emulator {self.avd_name} did not boot within {timeout}s")

    async def stop(self) -> None:
        """Stop the emulator process."""
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None

    async def wipe(self) -> None:
        """Wipe emulator userdata for a clean state."""
        await run_cmd(
            ["adb", "-s", self.adb_serial, "emu", "kill"], timeout=10
        )

    async def install_apk(self, apk_path: str) -> None:
        """Install an APK onto the emulator."""
        returncode, _, stderr = await run_cmd(
            ["adb", "-s", self.adb_serial, "install", "-r", apk_path],
            timeout=120,
        )
        if returncode != 0:
            raise EmulatorError(f"APK install failed on {self.avd_name}: {stderr}")

    async def load_snapshot(self, snapshot_name: str) -> None:
        """Load a named snapshot."""
        returncode, _, stderr = await run_cmd(
            ["adb", "-s", self.adb_serial, "emu", "avd", "snapshot", "load", snapshot_name],
            timeout=30,
        )
        if returncode != 0:
            raise EmulatorError(f"Snapshot load failed on {self.avd_name}: {stderr}")

    async def save_snapshot(self, snapshot_name: str) -> None:
        """Save current state as a named snapshot."""
        returncode, _, stderr = await run_cmd(
            ["adb", "-s", self.adb_serial, "emu", "avd", "snapshot", "save", snapshot_name],
            timeout=30,
        )
        if returncode != 0:
            raise EmulatorError(f"Snapshot save failed on {self.avd_name}: {stderr}")
