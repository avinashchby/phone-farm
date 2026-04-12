"""In-memory state for the web dashboard."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PhoneState:
    """State of a single emulator phone."""

    slot: int
    adb_serial: str
    status: str = "booting"
    last_screenshot: str | None = None
    emulator: object | None = field(default=None, repr=False)


@dataclass
class TestRun:
    """State of a running or completed QA test."""

    run_id: str
    apk_name: str
    app_description: str
    status: str = "running"
    steps_completed: int = 0
    screens_found: int = 0
    bugs_found: int = 0
    latest_screenshot: str | None = None
    report_path: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_message: str | None = None
    task: asyncio.Task | None = field(default=None, repr=False)


class AppState:
    """Global in-memory state for the web app."""

    def __init__(self) -> None:
        self.phones: dict[int, PhoneState] = {}
        self.test_runs: dict[str, TestRun] = {}
        self.anthropic_api_key: str | None = None

    @property
    def pro_mode_available(self) -> bool:
        """Whether AI-powered Pro mode is available."""
        return self.anthropic_api_key is not None

    def add_phone(self, slot: int, adb_serial: str) -> None:
        """Register a phone at the given slot."""
        self.phones[slot] = PhoneState(slot=slot, adb_serial=adb_serial)

    def remove_phone(self, slot: int) -> None:
        """Deregister a phone slot (no-op if not present)."""
        self.phones.pop(slot, None)

    def start_test_run(self, apk_name: str, app_description: str) -> str:
        """Create a new test run and return its run_id."""
        run_id = uuid.uuid4().hex[:8]
        self.test_runs[run_id] = TestRun(
            run_id=run_id,
            apk_name=apk_name,
            app_description=app_description,
        )
        return run_id

    def update_test_progress(self, run_id: str, *, steps: int, screens: int, bugs: int) -> None:
        """Update progress counters for a running test (no-op if run_id unknown)."""
        if run_id in self.test_runs:
            run = self.test_runs[run_id]
            run.steps_completed = steps
            run.screens_found = screens
            run.bugs_found = bugs

    def complete_test_run(self, run_id: str, *, report_path: str) -> None:
        """Mark a test run as completed and record its report path (no-op if run_id unknown)."""
        if run_id in self.test_runs:
            run = self.test_runs[run_id]
            run.status = "completed"
            run.report_path = report_path
