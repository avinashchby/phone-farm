"""Structured console logging with timestamps."""

from datetime import datetime


class FarmLogger:
    """Simple structured logger for phone farm output."""

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def info(self, msg: str) -> None:
        """Log a general info message."""
        print(f"[{self._ts()}] {msg}")

    def emu(self, slot: int, msg: str) -> None:
        """Log an emulator-specific message."""
        print(f"[{self._ts()}]   emu-{slot} > {msg}")

    def batch(self, current: int, total: int, msg: str) -> None:
        """Log a batch-level message."""
        print(f"[{self._ts()}] Batch {current}/{total}: {msg}")

    def error(self, msg: str) -> None:
        """Log an error message."""
        print(f"[{self._ts()}] ERROR: {msg}")

    def success(self, msg: str) -> None:
        """Log a success message."""
        print(f"[{self._ts()}] OK: {msg}")
