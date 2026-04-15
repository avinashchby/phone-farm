"""SQLite database for account storage and run history."""

from pathlib import Path
from datetime import datetime, timezone

import aiosqlite

SCHEMA = """\
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    encrypted_password TEXT NOT NULL,
    last_used TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'active',
    batch_group INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS run_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    run_date TIMESTAMP NOT NULL,
    result TEXT NOT NULL,
    duration_seconds INTEGER,
    error_log TEXT
);

CREATE TABLE IF NOT EXISTS qa_runs (
    run_id TEXT PRIMARY KEY,
    apk_name TEXT NOT NULL,
    app_description TEXT,
    status TEXT NOT NULL,
    steps_completed INTEGER DEFAULT 0,
    screens_found INTEGER DEFAULT 0,
    bugs_found INTEGER DEFAULT 0,
    report_path TEXT,
    html_report_path TEXT,
    started_at TEXT,
    error_message TEXT
);
"""


class Database:
    """Async SQLite database for phone farm accounts and run history."""

    def __init__(self, path: Path) -> None:
        self._path = path

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._path) as conn:
            await conn.executescript(SCHEMA)
            await conn.commit()

    async def add_account(
        self, email: str, encrypted_password: str, *, batch_group: int
    ) -> None:
        """Insert a new account."""
        async with aiosqlite.connect(self._path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute(
                "INSERT INTO accounts (email, encrypted_password, batch_group) VALUES (?, ?, ?)",
                (email, encrypted_password, batch_group),
            )
            await conn.commit()

    async def get_account_by_email(self, email: str) -> dict | None:
        """Fetch a single account by email."""
        async with aiosqlite.connect(self._path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM accounts WHERE email = ?", (email,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_accounts(self, *, batch_group: int | None = None) -> list[dict]:
        """List accounts, optionally filtered by batch group."""
        async with aiosqlite.connect(self._path) as conn:
            conn.row_factory = aiosqlite.Row
            if batch_group is not None:
                cursor = await conn.execute(
                    "SELECT * FROM accounts WHERE batch_group = ? ORDER BY id",
                    (batch_group,),
                )
            else:
                cursor = await conn.execute("SELECT * FROM accounts ORDER BY id")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_account_status(self, email: str, status: str) -> None:
        """Update an account's status (active, cooldown, banned)."""
        async with aiosqlite.connect(self._path) as conn:
            await conn.execute(
                "UPDATE accounts SET status = ? WHERE email = ?",
                (status, email),
            )
            await conn.commit()

    async def record_run(
        self,
        account_id: int,
        result: str,
        duration_seconds: int,
        error_log: str | None = None,
    ) -> None:
        """Record a run result for an account."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._path) as conn:
            await conn.execute(
                "INSERT INTO run_history (account_id, run_date, result, duration_seconds, error_log) "
                "VALUES (?, ?, ?, ?, ?)",
                (account_id, now, result, duration_seconds, error_log),
            )
            await conn.execute(
                "UPDATE accounts SET last_used = ? WHERE id = ?",
                (now, account_id),
            )
            await conn.commit()

    async def get_runs_for_account(self, account_id: int) -> list[dict]:
        """Get all runs for a specific account."""
        async with aiosqlite.connect(self._path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM run_history WHERE account_id = ? ORDER BY run_date DESC",
                (account_id,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def save_run(self, run) -> None:
        """Persist a TestRun to the qa_runs table."""
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO qa_runs
                   (run_id, apk_name, app_description, status,
                    steps_completed, screens_found, bugs_found,
                    report_path, html_report_path, started_at, error_message)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run.run_id,
                    run.apk_name,
                    run.app_description,
                    run.status,
                    run.steps_completed,
                    run.screens_found,
                    run.bugs_found,
                    run.report_path,
                    getattr(run, "html_report_path", None),
                    run.started_at,
                    run.error_message,
                ),
            )
            await db.commit()

    async def load_runs(self) -> list[dict]:
        """Load all qa_runs from the database, most recent first."""
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM qa_runs ORDER BY started_at DESC"
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
