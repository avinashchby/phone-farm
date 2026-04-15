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
    html_report_path: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_message: str | None = None
    task: asyncio.Task | None = field(default=None, repr=False)
    test_email: str = ""
    test_password: str = ""
    skip_login: bool = False
    login_attempts: int = 0


class AppState:
    """Global in-memory state for the web app."""

    def __init__(self, db=None) -> None:
        self.phones: dict[int, PhoneState] = {}
        self.test_runs: dict[str, TestRun] = {}
        self.anthropic_api_key: str | None = None
        self.db = db  # Optional[Database]

    @property
    def pro_mode_available(self) -> bool:
        """Whether AI-powered Pro mode is available.

        Requires both an API key and the phone-farm-pro package.
        """
        if self.anthropic_api_key is None:
            return False
        try:
            import phone_farm_pro  # noqa: F401
            return True
        except ImportError:
            return False

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

    def complete_test_run(
        self, run_id: str, *, report_path: str, html_report_path: str | None = None
    ) -> None:
        """Mark a test run as complete with report paths (no-op if run_id unknown)."""
        if run_id not in self.test_runs:
            return
        run = self.test_runs[run_id]
        run.status = "completed"
        run.report_path = report_path
        run.html_report_path = html_report_path
        if self.db is not None:
            try:
                asyncio.create_task(self.db.save_run(run))
            except RuntimeError:
                pass  # No event loop — skip (e.g. in tests)

    @classmethod
    async def load_from_db(cls, db) -> "AppState":
        """Create AppState pre-populated with runs loaded from the database."""
        state = cls(db=db)
        runs = await db.load_runs()
        for r in runs:
            run = TestRun(
                run_id=r["run_id"],
                apk_name=r["apk_name"],
                app_description=r.get("app_description", ""),
                status=r["status"],
                steps_completed=r.get("steps_completed", 0),
                screens_found=r.get("screens_found", 0),
                bugs_found=r.get("bugs_found", 0),
                report_path=r.get("report_path"),
                html_report_path=r.get("html_report_path"),
                started_at=r.get("started_at", ""),
                error_message=r.get("error_message"),
            )
            state.test_runs[run.run_id] = run
        return state
