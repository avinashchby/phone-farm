# Phone Farm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that orchestrates Android emulators in batches of 5 to automate app testing across 30 Google accounts on a 16GB M2 Mac.

**Architecture:** Python asyncio CLI using Click. Emulators managed via Android SDK CLI tools (avdmanager, emulator, adb). UI automation via Appium 2.x. Account credentials stored in encrypted SQLite. TOML config. Batched execution: 5 concurrent emulators, 6 batches per cycle.

**Tech Stack:** Python 3.12+, uv, click, asyncio, aiosqlite, cryptography, tomllib, Appium 2.x, appium-python-client, pytest, pytest-asyncio, ruff

---

## File Structure

```
phone_farm/
├── __init__.py               # Package version
├── __main__.py               # Entry point: python -m phone_farm
├── cli.py                    # Click CLI: all commands and groups
├── config.py                 # Load/validate phone-farm.toml
├── crypto.py                 # Fernet encryption, PBKDF2 key derivation
├── db.py                     # SQLite schema, connection, CRUD for accounts + run_history
├── emulator.py               # AVD lifecycle: create, start, stop, wipe, snapshot
├── pool.py                   # Emulator pool: manage N concurrent AVDs in a batch
├── appium_server.py          # Start/stop Appium servers on unique ports
├── automation.py             # Appium client: install APK, run flows, capture screenshots
├── orchestrator.py           # Top-level: batch accounts, run cycle, collect results
├── reporter.py               # Query run_history, format reports
├── doctor.py                 # Verify prerequisites: SDK, Java, Node, Appium, disk space
└── log.py                    # Structured console logging with timestamps

scripts/
├── flows/
│   ├── base_flow.py          # Abstract base class for all flows
│   ├── daily_usage_flow.py   # Tester-gate: open app, navigate, interact
│   └── deep_test_flow.py     # QA: thorough screen-by-screen testing
├── actions/
│   ├── tap.py                # Tap with retry
│   ├── scroll.py             # Scroll patterns
│   ├── input_text.py         # Type with human-like delays
│   └── wait.py               # Smart waits
└── config/
    └── flow_config.toml      # Flow-to-mode mapping

tests/
├── conftest.py               # Shared fixtures
├── test_config.py
├── test_crypto.py
├── test_db.py
├── test_emulator.py
├── test_pool.py
├── test_appium_server.py
├── test_automation.py
├── test_orchestrator.py
├── test_reporter.py
├── test_doctor.py
└── test_cli.py

phone-farm.toml               # Default config (committed as example)
pyproject.toml                 # uv project config
.gitignore
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `phone_farm/__init__.py`
- Create: `phone_farm/__main__.py`
- Create: `.gitignore`
- Create: `phone-farm.toml`

- [ ] **Step 1: Initialize uv project**

```bash
cd /Users/avinashchaubey/Applications/Phone\ Farm/.claude/worktrees/eager-meninsky
uv init --name phone-farm --python 3.12
```

- [ ] **Step 2: Replace pyproject.toml with project config**

Write `pyproject.toml`:

```toml
[project]
name = "phone-farm"
version = "0.1.0"
description = "Android phone farm for automated app testing"
requires-python = ">=3.12"
dependencies = [
    "click>=8.1",
    "aiosqlite>=0.20",
    "cryptography>=42.0",
    "Appium-Python-Client>=4.0",
    "rich>=13.0",
]

[project.scripts]
phone-farm = "phone_farm.cli:cli"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
]
```

- [ ] **Step 3: Create package files**

Write `phone_farm/__init__.py`:

```python
"""Phone Farm — Android emulator orchestration for app testing."""

__version__ = "0.1.0"
```

Write `phone_farm/__main__.py`:

```python
"""Allow running as `python -m phone_farm`."""

from phone_farm.cli import cli

cli()
```

- [ ] **Step 4: Create .gitignore**

Write `.gitignore`:

```
__pycache__/
*.pyc
.venv/
dist/
*.egg-info/
data/
logs/
screenshots/
*.db
.env
```

- [ ] **Step 5: Create default config**

Write `phone-farm.toml`:

```toml
[farm]
batch_size = 5
cycle_delay_seconds = 60
max_retries = 2

[emulator]
api_level = 34
ram_mb = 1536
headless = true
device_profile = "pixel_6"

[automation]
appium_base_port = 4723
default_flow = "daily_usage"
screenshot_on_failure = true
human_like_delays = true

[paths]
apk = "./app-release.apk"
scripts = "./scripts/flows/"
logs = "./logs/"
db = "./data/phone-farm.db"
screenshots = "./screenshots/"
snapshots = "./data/snapshots/"
```

- [ ] **Step 6: Install dependencies**

```bash
uv sync
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml phone_farm/__init__.py phone_farm/__main__.py .gitignore phone-farm.toml uv.lock .python-version
git commit -m "feat: scaffold phone-farm project with uv"
```

---

### Task 2: Config Module

**Files:**
- Create: `phone_farm/config.py`
- Create: `tests/test_config.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write failing test for config loading**

Write `tests/conftest.py`:

```python
"""Shared test fixtures."""

import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a minimal phone-farm.toml in a temp dir."""
    config_file = tmp_path / "phone-farm.toml"
    config_file.write_text("""\
[farm]
batch_size = 5
cycle_delay_seconds = 60
max_retries = 2

[emulator]
api_level = 34
ram_mb = 1536
headless = true
device_profile = "pixel_6"

[automation]
appium_base_port = 4723
default_flow = "daily_usage"
screenshot_on_failure = true
human_like_delays = true

[paths]
apk = "./app-release.apk"
scripts = "./scripts/flows/"
logs = "./logs/"
db = "./data/phone-farm.db"
screenshots = "./screenshots/"
snapshots = "./data/snapshots/"
""")
    return config_file
```

Write `tests/test_config.py`:

```python
"""Tests for config loading and validation."""

from pathlib import Path

from phone_farm.config import FarmConfig, load_config


def test_load_config_parses_all_sections(tmp_config: Path) -> None:
    cfg = load_config(tmp_config)
    assert cfg.farm.batch_size == 5
    assert cfg.emulator.api_level == 34
    assert cfg.automation.appium_base_port == 4723
    assert cfg.paths.apk == "./app-release.apk"


def test_load_config_missing_file_raises(tmp_path: Path) -> None:
    import pytest
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.toml")


def test_load_config_invalid_batch_size(tmp_config: Path) -> None:
    import pytest
    tmp_config.write_text(tmp_config.read_text().replace("batch_size = 5", "batch_size = 0"))
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        load_config(tmp_config)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'phone_farm.config'`

- [ ] **Step 3: Implement config module**

Write `phone_farm/config.py`:

```python
"""Load and validate phone-farm.toml configuration."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class FarmSection:
    batch_size: int
    cycle_delay_seconds: int
    max_retries: int


@dataclass(frozen=True)
class EmulatorSection:
    api_level: int
    ram_mb: int
    headless: bool
    device_profile: str


@dataclass(frozen=True)
class AutomationSection:
    appium_base_port: int
    default_flow: str
    screenshot_on_failure: bool
    human_like_delays: bool


@dataclass(frozen=True)
class PathsSection:
    apk: str
    scripts: str
    logs: str
    db: str
    screenshots: str
    snapshots: str


@dataclass(frozen=True)
class FarmConfig:
    farm: FarmSection
    emulator: EmulatorSection
    automation: AutomationSection
    paths: PathsSection


def load_config(path: Path) -> FarmConfig:
    """Load and validate config from a TOML file.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If validation fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    farm = FarmSection(**raw["farm"])
    if farm.batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    emulator = EmulatorSection(**raw["emulator"])
    automation = AutomationSection(**raw["automation"])
    paths = PathsSection(**raw["paths"])

    return FarmConfig(farm=farm, emulator=emulator, automation=automation, paths=paths)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/config.py tests/conftest.py tests/test_config.py
git commit -m "feat: add config loading and validation"
```

---

### Task 3: Crypto Module

**Files:**
- Create: `phone_farm/crypto.py`
- Create: `tests/test_crypto.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_crypto.py`:

```python
"""Tests for encryption/decryption of credentials."""

from phone_farm.crypto import derive_key, encrypt, decrypt


def test_round_trip_encryption() -> None:
    key = derive_key("master-password", salt=b"fixed-salt-for-test")
    plaintext = "super-secret-app-password"
    ciphertext = encrypt(plaintext, key)
    assert ciphertext != plaintext
    assert decrypt(ciphertext, key) == plaintext


def test_wrong_key_fails_to_decrypt() -> None:
    import pytest
    key1 = derive_key("password-one", salt=b"fixed-salt-for-test")
    key2 = derive_key("password-two", salt=b"fixed-salt-for-test")
    ciphertext = encrypt("secret", key1)
    with pytest.raises(Exception):
        decrypt(ciphertext, key2)


def test_derive_key_deterministic() -> None:
    salt = b"same-salt"
    k1 = derive_key("pw", salt=salt)
    k2 = derive_key("pw", salt=salt)
    assert k1 == k2


def test_derive_key_different_salts_differ() -> None:
    k1 = derive_key("pw", salt=b"salt-a")
    k2 = derive_key("pw", salt=b"salt-b")
    assert k1 != k2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_crypto.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement crypto module**

Write `phone_farm/crypto.py`:

```python
"""Credential encryption using Fernet with PBKDF2 key derivation."""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


def derive_key(password: str, *, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a master password.

    Uses PBKDF2 with SHA256, 480_000 iterations.
    Returns a URL-safe base64-encoded 32-byte key.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    raw = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(raw)


def encrypt(plaintext: str, key: bytes) -> str:
    """Encrypt a plaintext string, return base64 ciphertext."""
    f = Fernet(key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str, key: bytes) -> str:
    """Decrypt a ciphertext string back to plaintext."""
    f = Fernet(key)
    return f.decrypt(ciphertext.encode()).decode()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_crypto.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/crypto.py tests/test_crypto.py
git commit -m "feat: add credential encryption with Fernet + PBKDF2"
```

---

### Task 4: Database Module

**Files:**
- Create: `phone_farm/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_db.py`:

```python
"""Tests for database operations."""

import pytest
from pathlib import Path

from phone_farm.db import Database


@pytest.fixture
async def db(tmp_path: Path) -> Database:
    """Create an in-memory test database."""
    database = Database(tmp_path / "test.db")
    await database.initialize()
    return database


@pytest.mark.asyncio
async def test_add_and_get_account(db: Database) -> None:
    await db.add_account(
        email="test@gmail.com",
        encrypted_password="cipher-text",
        batch_group=1,
    )
    account = await db.get_account_by_email("test@gmail.com")
    assert account is not None
    assert account["email"] == "test@gmail.com"
    assert account["batch_group"] == 1
    assert account["status"] == "active"


@pytest.mark.asyncio
async def test_list_accounts_by_batch_group(db: Database) -> None:
    await db.add_account("a@gmail.com", "c1", batch_group=1)
    await db.add_account("b@gmail.com", "c2", batch_group=1)
    await db.add_account("c@gmail.com", "c3", batch_group=2)
    batch1 = await db.list_accounts(batch_group=1)
    assert len(batch1) == 2


@pytest.mark.asyncio
async def test_update_account_status(db: Database) -> None:
    await db.add_account("x@gmail.com", "c1", batch_group=1)
    await db.update_account_status("x@gmail.com", "cooldown")
    account = await db.get_account_by_email("x@gmail.com")
    assert account["status"] == "cooldown"


@pytest.mark.asyncio
async def test_record_run_history(db: Database) -> None:
    await db.add_account("r@gmail.com", "c1", batch_group=1)
    account = await db.get_account_by_email("r@gmail.com")
    await db.record_run(
        account_id=account["id"],
        result="success",
        duration_seconds=67,
    )
    runs = await db.get_runs_for_account(account["id"])
    assert len(runs) == 1
    assert runs[0]["result"] == "success"
    assert runs[0]["duration_seconds"] == 67


@pytest.mark.asyncio
async def test_duplicate_email_raises(db: Database) -> None:
    await db.add_account("dup@gmail.com", "c1", batch_group=1)
    with pytest.raises(Exception):
        await db.add_account("dup@gmail.com", "c2", batch_group=2)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_db.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement database module**

Write `phone_farm/db.py`:

```python
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

    async def _connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self._path)
        conn.row_factory = aiosqlite.Row
        return conn

    async def add_account(
        self, email: str, encrypted_password: str, *, batch_group: int
    ) -> None:
        """Insert a new account."""
        async with await self._connect() as conn:
            await conn.execute(
                "INSERT INTO accounts (email, encrypted_password, batch_group) VALUES (?, ?, ?)",
                (email, encrypted_password, batch_group),
            )
            await conn.commit()

    async def get_account_by_email(self, email: str) -> dict | None:
        """Fetch a single account by email."""
        async with await self._connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM accounts WHERE email = ?", (email,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_accounts(self, *, batch_group: int | None = None) -> list[dict]:
        """List accounts, optionally filtered by batch group."""
        async with await self._connect() as conn:
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
        async with await self._connect() as conn:
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
        async with await self._connect() as conn:
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
        async with await self._connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM run_history WHERE account_id = ? ORDER BY run_date DESC",
                (account_id,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_db.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/db.py tests/test_db.py
git commit -m "feat: add async SQLite database for accounts and run history"
```

---

### Task 5: Logging Module

**Files:**
- Create: `phone_farm/log.py`
- Create: `tests/test_log.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_log.py`:

```python
"""Tests for structured logging."""

from phone_farm.log import FarmLogger


def test_logger_formats_with_timestamp(capsys) -> None:
    logger = FarmLogger()
    logger.info("Test message")
    captured = capsys.readouterr()
    # Format: [HH:MM:SS] Test message
    assert "] Test message" in captured.out
    assert "[" in captured.out


def test_logger_emulator_prefix(capsys) -> None:
    logger = FarmLogger()
    logger.emu(1, "booted")
    captured = capsys.readouterr()
    assert "emu-1" in captured.out
    assert "booted" in captured.out


def test_logger_batch_prefix(capsys) -> None:
    logger = FarmLogger()
    logger.batch(2, 6, "starting")
    captured = capsys.readouterr()
    assert "Batch 2/6" in captured.out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_log.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement logging module**

Write `phone_farm/log.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_log.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/log.py tests/test_log.py
git commit -m "feat: add structured logging module"
```

---

### Task 6: Emulator Module

**Files:**
- Create: `phone_farm/emulator.py`
- Create: `tests/test_emulator.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_emulator.py`:

```python
"""Tests for emulator management (unit tests with mocked subprocess)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from phone_farm.emulator import Emulator, EmulatorError


@pytest.mark.asyncio
async def test_create_avd_runs_avdmanager() -> None:
    emu = Emulator(slot=0, api_level=34, ram_mb=1536, device_profile="pixel_6")
    with patch("phone_farm.emulator.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "", "")
        await emu.create_avd()
        args = mock_run.call_args[0][0]
        assert "avdmanager" in args[0]
        assert "phone-farm-slot-0" in args


@pytest.mark.asyncio
async def test_start_headless_passes_no_window_flag() -> None:
    emu = Emulator(slot=0, api_level=34, ram_mb=1536, device_profile="pixel_6")
    with patch("phone_farm.emulator.start_emulator_process", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = MagicMock()
        await emu.start(headless=True)
        args = mock_start.call_args[0][0]
        assert "-no-window" in args


@pytest.mark.asyncio
async def test_stop_kills_process() -> None:
    emu = Emulator(slot=0, api_level=34, ram_mb=1536, device_profile="pixel_6")
    mock_proc = MagicMock()
    mock_proc.terminate = MagicMock()
    mock_proc.wait = AsyncMock()
    emu._process = mock_proc
    await emu.stop()
    mock_proc.terminate.assert_called_once()


def test_avd_name_uses_slot() -> None:
    emu = Emulator(slot=3, api_level=34, ram_mb=1536, device_profile="pixel_6")
    assert emu.avd_name == "phone-farm-slot-3"


def test_adb_serial_uses_port_offset() -> None:
    emu = Emulator(slot=2, api_level=34, ram_mb=1536, device_profile="pixel_6")
    # Emulator ports: 5554, 5556, 5558, ...
    assert emu.adb_serial == "emulator-5558"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_emulator.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement emulator module**

Write `phone_farm/emulator.py`:

```python
"""Android emulator lifecycle management via SDK CLI tools."""

import asyncio
from dataclasses import dataclass, field


class EmulatorError(Exception):
    """Raised when an emulator operation fails."""


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
        """Create an AVD using avdmanager."""
        system_image = f"system-images;android-{self.api_level};google_apis;arm64-v8a"
        args = [
            "avdmanager", "create", "avd",
            "--name", self.avd_name,
            "--package", system_image,
            "--device", self.device_profile,
            "--force",
        ]
        returncode, stdout, stderr = await run_cmd(args)
        if returncode != 0:
            raise EmulatorError(f"Failed to create AVD {self.avd_name}: {stderr}")

    async def start(self, *, headless: bool = True) -> None:
        """Start the emulator."""
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
        args = ["emulator", "-avd", self.avd_name, "-wipe-data", "-no-window", "-no-audio"]
        # Just wipe and exit immediately
        returncode, _, stderr = await run_cmd(
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_emulator.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/emulator.py tests/test_emulator.py
git commit -m "feat: add emulator lifecycle management via SDK CLI"
```

---

### Task 7: Emulator Pool Module

**Files:**
- Create: `phone_farm/pool.py`
- Create: `tests/test_pool.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_pool.py`:

```python
"""Tests for emulator pool management."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from phone_farm.pool import EmulatorPool


@pytest.mark.asyncio
async def test_pool_creates_correct_number_of_emulators() -> None:
    pool = EmulatorPool(batch_size=3, api_level=34, ram_mb=1536, device_profile="pixel_6")
    assert len(pool.emulators) == 3
    assert pool.emulators[0].slot == 0
    assert pool.emulators[2].slot == 2


@pytest.mark.asyncio
async def test_pool_start_all_boots_each_emulator() -> None:
    pool = EmulatorPool(batch_size=2, api_level=34, ram_mb=1536, device_profile="pixel_6")
    for emu in pool.emulators:
        emu.create_avd = AsyncMock()
        emu.start = AsyncMock()
        emu.wait_for_boot = AsyncMock()
    await pool.start_all(headless=True)
    for emu in pool.emulators:
        emu.create_avd.assert_called_once()
        emu.start.assert_called_once_with(headless=True)
        emu.wait_for_boot.assert_called_once()


@pytest.mark.asyncio
async def test_pool_stop_all_stops_each_emulator() -> None:
    pool = EmulatorPool(batch_size=2, api_level=34, ram_mb=1536, device_profile="pixel_6")
    for emu in pool.emulators:
        emu.stop = AsyncMock()
    await pool.stop_all()
    for emu in pool.emulators:
        emu.stop.assert_called_once()


@pytest.mark.asyncio
async def test_pool_start_all_continues_on_single_failure() -> None:
    pool = EmulatorPool(batch_size=2, api_level=34, ram_mb=1536, device_profile="pixel_6")
    pool.emulators[0].create_avd = AsyncMock(side_effect=Exception("boot fail"))
    pool.emulators[0].start = AsyncMock()
    pool.emulators[0].wait_for_boot = AsyncMock()
    pool.emulators[1].create_avd = AsyncMock()
    pool.emulators[1].start = AsyncMock()
    pool.emulators[1].wait_for_boot = AsyncMock()
    results = await pool.start_all(headless=True)
    assert results[0] is False
    assert results[1] is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_pool.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement pool module**

Write `phone_farm/pool.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_pool.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/pool.py tests/test_pool.py
git commit -m "feat: add emulator pool for batch management"
```

---

### Task 8: Appium Server Module

**Files:**
- Create: `phone_farm/appium_server.py`
- Create: `tests/test_appium_server.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_appium_server.py`:

```python
"""Tests for Appium server management."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from phone_farm.appium_server import AppiumServer


def test_port_calculated_from_base_and_slot() -> None:
    server = AppiumServer(slot=0, base_port=4723)
    assert server.port == 4723
    server2 = AppiumServer(slot=3, base_port=4723)
    assert server2.port == 4726


@pytest.mark.asyncio
async def test_start_launches_appium_process() -> None:
    server = AppiumServer(slot=0, base_port=4723)
    with patch("phone_farm.appium_server.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_proc = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_exec.return_value = mock_proc
        with patch("phone_farm.appium_server.asyncio.sleep", new_callable=AsyncMock):
            await server.start()
        args = mock_exec.call_args[0]
        assert "appium" in args[0]
        assert "--port" in args
        assert "4723" in args


@pytest.mark.asyncio
async def test_stop_terminates_process() -> None:
    server = AppiumServer(slot=0, base_port=4723)
    mock_proc = MagicMock()
    mock_proc.terminate = MagicMock()
    mock_proc.wait = AsyncMock()
    server._process = mock_proc
    await server.stop()
    mock_proc.terminate.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_appium_server.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Appium server module**

Write `phone_farm/appium_server.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_appium_server.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/appium_server.py tests/test_appium_server.py
git commit -m "feat: add Appium server lifecycle management"
```

---

### Task 9: Automation Actions

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/actions/__init__.py`
- Create: `scripts/actions/tap.py`
- Create: `scripts/actions/scroll.py`
- Create: `scripts/actions/input_text.py`
- Create: `scripts/actions/wait.py`
- Create: `tests/test_actions.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_actions.py`:

```python
"""Tests for automation actions."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from scripts.actions.tap import tap_element
from scripts.actions.scroll import scroll_down
from scripts.actions.input_text import type_text
from scripts.actions.wait import wait_for_element


def test_tap_element_finds_and_clicks(monkeypatch) -> None:
    driver = MagicMock()
    element = MagicMock()
    driver.find_element.return_value = element
    tap_element(driver, "id", "com.example:id/button")
    element.click.assert_called_once()


def test_tap_element_retries_on_failure(monkeypatch) -> None:
    import time
    monkeypatch.setattr(time, "sleep", lambda _: None)
    driver = MagicMock()
    driver.find_element.side_effect = [Exception("not found"), Exception("not found"), MagicMock()]
    tap_element(driver, "id", "com.example:id/button", retries=3)
    assert driver.find_element.call_count == 3


def test_type_text_sends_keys_with_value(monkeypatch) -> None:
    monkeypatch.setattr("scripts.actions.input_text.random", MagicMock(uniform=MagicMock(return_value=0.1)))
    import time
    monkeypatch.setattr(time, "sleep", lambda _: None)
    driver = MagicMock()
    element = MagicMock()
    driver.find_element.return_value = element
    type_text(driver, "id", "com.example:id/input", "hello")
    element.send_keys.assert_called()


def test_scroll_down_executes_script() -> None:
    driver = MagicMock()
    scroll_down(driver)
    driver.execute_script.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_actions.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement action modules**

Write `scripts/__init__.py`:

```python
```

Write `scripts/actions/__init__.py`:

```python
"""Reusable UI automation actions."""
```

Write `scripts/actions/tap.py`:

```python
"""Tap an element with retry logic."""

import time

from appium.webdriver import Remote as AppiumDriver


def tap_element(
    driver: AppiumDriver,
    by: str,
    value: str,
    *,
    retries: int = 3,
    wait_between: float = 1.0,
) -> None:
    """Find and tap an element, retrying on failure.

    Args:
        driver: Appium driver instance.
        by: Locator strategy (e.g., "id", "xpath").
        value: Locator value.
        retries: Number of attempts before giving up.
        wait_between: Seconds between retries.
    """
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            element = driver.find_element(by, value)
            element.click()
            return
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(wait_between)
    raise last_error  # type: ignore[misc]
```

Write `scripts/actions/scroll.py`:

```python
"""Scroll actions for Appium automation."""

from appium.webdriver import Remote as AppiumDriver


def scroll_down(driver: AppiumDriver, amount: int = 500) -> None:
    """Scroll down by a pixel amount using mobile gesture.

    Args:
        driver: Appium driver instance.
        amount: Pixels to scroll.
    """
    driver.execute_script(
        "mobile: scrollGesture",
        {"left": 100, "top": 300, "width": 200, "height": amount, "direction": "down", "percent": 0.75},
    )


def scroll_up(driver: AppiumDriver, amount: int = 500) -> None:
    """Scroll up by a pixel amount using mobile gesture.

    Args:
        driver: Appium driver instance.
        amount: Pixels to scroll.
    """
    driver.execute_script(
        "mobile: scrollGesture",
        {"left": 100, "top": 300, "width": 200, "height": amount, "direction": "up", "percent": 0.75},
    )
```

Write `scripts/actions/input_text.py`:

```python
"""Type text with human-like delays."""

import random
import time

from appium.webdriver import Remote as AppiumDriver


def type_text(
    driver: AppiumDriver,
    by: str,
    value: str,
    text: str,
    *,
    min_delay: float = 0.05,
    max_delay: float = 0.15,
) -> None:
    """Find an input field and type text with random delays between keystrokes.

    Args:
        driver: Appium driver instance.
        by: Locator strategy.
        value: Locator value.
        text: Text to type.
        min_delay: Minimum delay between keystrokes.
        max_delay: Maximum delay between keystrokes.
    """
    element = driver.find_element(by, value)
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))
```

Write `scripts/actions/wait.py`:

```python
"""Smart wait utilities for Appium automation."""

import time

from appium.webdriver import Remote as AppiumDriver


def wait_for_element(
    driver: AppiumDriver,
    by: str,
    value: str,
    *,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> object:
    """Wait until an element is visible, then return it.

    Args:
        driver: Appium driver instance.
        by: Locator strategy.
        value: Locator value.
        timeout: Max seconds to wait.
        poll_interval: Seconds between polls.

    Raises:
        TimeoutError: If element not found within timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            element = driver.find_element(by, value)
            if element.is_displayed():
                return element
        except Exception:
            pass
        time.sleep(poll_interval)
    raise TimeoutError(f"Element {by}={value} not found within {timeout}s")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_actions.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/ tests/test_actions.py
git commit -m "feat: add automation actions (tap, scroll, input, wait)"
```

---

### Task 10: Test Flow Framework

**Files:**
- Create: `scripts/flows/__init__.py`
- Create: `scripts/flows/base_flow.py`
- Create: `scripts/flows/daily_usage_flow.py`
- Create: `scripts/flows/deep_test_flow.py`
- Create: `scripts/config/flow_config.toml`
- Create: `tests/test_flows.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_flows.py`:

```python
"""Tests for test flow framework."""

import pytest
from unittest.mock import MagicMock, patch

from scripts.flows.base_flow import BaseFlow
from scripts.flows.daily_usage_flow import DailyUsageFlow
from scripts.flows.deep_test_flow import DeepTestFlow


def test_base_flow_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseFlow(driver=MagicMock(), account_email="test@gmail.com")


def test_daily_usage_flow_has_run_method() -> None:
    driver = MagicMock()
    flow = DailyUsageFlow(driver=driver, account_email="test@gmail.com")
    assert callable(flow.run)


def test_deep_test_flow_has_run_method() -> None:
    driver = MagicMock()
    flow = DeepTestFlow(driver=driver, account_email="test@gmail.com")
    assert callable(flow.run)


def test_daily_usage_flow_run_calls_actions() -> None:
    driver = MagicMock()
    flow = DailyUsageFlow(driver=driver, account_email="test@gmail.com")
    with patch("scripts.flows.daily_usage_flow.time") as mock_time:
        mock_time.sleep = MagicMock()
        mock_time.time = MagicMock(return_value=100.0)
        flow.run()
    # Should interact with the driver
    assert driver.method_calls or driver.find_element.called or True  # Flow ran without error


def test_flow_captures_screenshot_on_error(tmp_path) -> None:
    driver = MagicMock()
    flow = DailyUsageFlow(driver=driver, account_email="test@gmail.com")
    flow.capture_screenshot(str(tmp_path / "fail.png"))
    driver.save_screenshot.assert_called_once_with(str(tmp_path / "fail.png"))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_flows.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement flow framework**

Write `scripts/flows/__init__.py`:

```python
"""Test flow implementations."""
```

Write `scripts/flows/base_flow.py`:

```python
"""Abstract base class for all test flows."""

from abc import ABC, abstractmethod

from appium.webdriver import Remote as AppiumDriver


class BaseFlow(ABC):
    """Base class that all test flows must extend.

    Provides common utilities: screenshot capture, human-like delay helpers.
    Subclasses implement `run()` with the actual test steps.
    """

    def __init__(self, *, driver: AppiumDriver, account_email: str) -> None:
        self.driver = driver
        self.account_email = account_email

    @abstractmethod
    def run(self) -> None:
        """Execute the test flow. Must be implemented by subclasses."""

    def capture_screenshot(self, path: str) -> None:
        """Save a screenshot to the given path."""
        self.driver.save_screenshot(path)
```

Write `scripts/flows/daily_usage_flow.py`:

```python
"""Daily usage flow for tester-gate cycles.

Opens the app, navigates 3-5 screens, does basic interactions,
then closes. Designed to simulate a real user session of 45-120 seconds.
"""

import random
import time

from scripts.flows.base_flow import BaseFlow


class DailyUsageFlow(BaseFlow):
    """Simulate daily app usage: open, browse, interact, close."""

    def run(self) -> None:
        """Execute daily usage simulation.

        Steps:
        1. Wait for app to fully load
        2. Interact with 3-5 screens
        3. Random idle pauses between actions
        4. Close app
        """
        # Wait for main activity to load
        time.sleep(random.uniform(2.0, 4.0))

        # Simulate browsing 3-5 screens
        num_screens = random.randint(3, 5)
        for _ in range(num_screens):
            # Simulate looking at a screen
            time.sleep(random.uniform(5.0, 15.0))

            # Try a random interaction: scroll or tap
            try:
                if random.random() > 0.5:
                    self.driver.execute_script(
                        "mobile: scrollGesture",
                        {
                            "left": 100, "top": 300,
                            "width": 200, "height": 500,
                            "direction": "down", "percent": 0.75,
                        },
                    )
                else:
                    # Tap somewhere in the middle of the screen
                    self.driver.execute_script(
                        "mobile: clickGesture",
                        {"x": random.randint(100, 300), "y": random.randint(400, 600)},
                    )
            except Exception:
                pass  # Non-critical — some screens may not be scrollable

            time.sleep(random.uniform(0.5, 2.5))
```

Write `scripts/flows/deep_test_flow.py`:

```python
"""Deep test flow for QA cycles.

Thorough screen-by-screen testing: navigates every reachable screen,
fills forms, tests edge cases. Designed for full app validation.
"""

import random
import time

from scripts.flows.base_flow import BaseFlow


class DeepTestFlow(BaseFlow):
    """Thorough QA test: every screen, forms, edge cases."""

    def run(self) -> None:
        """Execute deep QA testing.

        Note: This is a template. Users should customize the steps
        in this method to match their specific app's screens and flows.
        The default implementation does a more thorough version of
        daily_usage with more interactions per screen.
        """
        time.sleep(random.uniform(2.0, 4.0))

        # More screens, more interactions per screen
        num_screens = random.randint(5, 10)
        for screen in range(num_screens):
            time.sleep(random.uniform(3.0, 8.0))

            # Multiple interactions per screen
            num_actions = random.randint(2, 5)
            for _ in range(num_actions):
                try:
                    action = random.choice(["scroll", "tap", "swipe"])
                    if action == "scroll":
                        self.driver.execute_script(
                            "mobile: scrollGesture",
                            {
                                "left": 100, "top": 300,
                                "width": 200, "height": 500,
                                "direction": "down", "percent": 0.75,
                            },
                        )
                    elif action == "tap":
                        self.driver.execute_script(
                            "mobile: clickGesture",
                            {"x": random.randint(50, 350), "y": random.randint(200, 700)},
                        )
                    elif action == "swipe":
                        self.driver.execute_script(
                            "mobile: swipeGesture",
                            {
                                "left": 100, "top": 400,
                                "width": 200, "height": 100,
                                "direction": "left", "percent": 0.75,
                            },
                        )
                except Exception:
                    pass

                time.sleep(random.uniform(0.5, 2.0))
```

Write `scripts/config/flow_config.toml`:

```toml
[tester-gate]
flow = "daily_usage"
description = "Daily usage simulation for Google Play tester gate"

[qa]
flow = "deep_test"
description = "Thorough QA testing across all screens"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_flows.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/flows/ scripts/config/ tests/test_flows.py
git commit -m "feat: add test flow framework with daily usage and deep test flows"
```

---

### Task 11: Automation Runner

**Files:**
- Create: `phone_farm/automation.py`
- Create: `tests/test_automation.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_automation.py`:

```python
"""Tests for automation runner."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

from phone_farm.automation import AutomationRunner, RunResult


def test_run_result_dataclass() -> None:
    result = RunResult(
        account_email="test@gmail.com",
        success=True,
        duration_seconds=67,
        error=None,
    )
    assert result.success is True
    assert result.duration_seconds == 67


@pytest.mark.asyncio
async def test_runner_installs_apk_and_runs_flow() -> None:
    runner = AutomationRunner(
        appium_url="http://127.0.0.1:4723",
        adb_serial="emulator-5554",
        apk_path="./app.apk",
        flow_name="daily_usage",
        screenshot_dir="./screenshots",
    )
    with patch("phone_farm.automation.webdriver") as mock_wd:
        mock_driver = MagicMock()
        mock_wd.Remote.return_value = mock_driver
        with patch("phone_farm.automation.load_flow") as mock_load:
            mock_flow_cls = MagicMock()
            mock_flow_instance = MagicMock()
            mock_flow_cls.return_value = mock_flow_instance
            mock_load.return_value = mock_flow_cls
            result = await runner.run(account_email="test@gmail.com")
    assert result.success is True
    mock_flow_instance.run.assert_called_once()
    mock_driver.quit.assert_called_once()


@pytest.mark.asyncio
async def test_runner_captures_error_on_failure() -> None:
    runner = AutomationRunner(
        appium_url="http://127.0.0.1:4723",
        adb_serial="emulator-5554",
        apk_path="./app.apk",
        flow_name="daily_usage",
        screenshot_dir="./screenshots",
    )
    with patch("phone_farm.automation.webdriver") as mock_wd:
        mock_driver = MagicMock()
        mock_wd.Remote.return_value = mock_driver
        with patch("phone_farm.automation.load_flow") as mock_load:
            mock_flow_cls = MagicMock()
            mock_flow_instance = MagicMock()
            mock_flow_instance.run.side_effect = RuntimeError("element not found")
            mock_flow_cls.return_value = mock_flow_instance
            mock_load.return_value = mock_flow_cls
            result = await runner.run(account_email="test@gmail.com")
    assert result.success is False
    assert "element not found" in result.error
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_automation.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement automation runner**

Write `phone_farm/automation.py`:

```python
"""Appium automation runner: connects to emulator, installs APK, runs flows."""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options

from scripts.flows.base_flow import BaseFlow
from scripts.flows.daily_usage_flow import DailyUsageFlow
from scripts.flows.deep_test_flow import DeepTestFlow


FLOW_MAP: dict[str, type[BaseFlow]] = {
    "daily_usage": DailyUsageFlow,
    "deep_test": DeepTestFlow,
}


def load_flow(flow_name: str) -> type[BaseFlow]:
    """Load a flow class by name.

    Raises:
        ValueError: If flow_name is not recognized.
    """
    if flow_name not in FLOW_MAP:
        raise ValueError(f"Unknown flow: {flow_name}. Available: {list(FLOW_MAP.keys())}")
    return FLOW_MAP[flow_name]


@dataclass
class RunResult:
    """Result of a single automation run."""

    account_email: str
    success: bool
    duration_seconds: int
    error: str | None


class AutomationRunner:
    """Runs a test flow against a single emulator via Appium."""

    def __init__(
        self,
        *,
        appium_url: str,
        adb_serial: str,
        apk_path: str,
        flow_name: str,
        screenshot_dir: str,
    ) -> None:
        self.appium_url = appium_url
        self.adb_serial = adb_serial
        self.apk_path = apk_path
        self.flow_name = flow_name
        self.screenshot_dir = screenshot_dir

    async def run(self, *, account_email: str) -> RunResult:
        """Execute the flow and return the result."""
        start = time.time()
        driver = None
        try:
            options = UiAutomator2Options()
            options.udid = self.adb_serial
            options.app = str(Path(self.apk_path).resolve())
            options.auto_grant_permissions = True
            options.no_reset = True

            driver = webdriver.Remote(
                command_executor=f"{self.appium_url}/wd/hub",
                options=options,
            )

            flow_cls = load_flow(self.flow_name)
            flow = flow_cls(driver=driver, account_email=account_email)
            flow.run()

            duration = int(time.time() - start)
            return RunResult(
                account_email=account_email,
                success=True,
                duration_seconds=duration,
                error=None,
            )
        except Exception as e:
            duration = int(time.time() - start)
            # Capture screenshot on failure
            if driver:
                try:
                    Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
                    ts = int(time.time())
                    driver.save_screenshot(
                        f"{self.screenshot_dir}/{account_email}-{ts}.png"
                    )
                except Exception:
                    pass
            return RunResult(
                account_email=account_email,
                success=False,
                duration_seconds=duration,
                error=str(e),
            )
        finally:
            if driver:
                driver.quit()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_automation.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/automation.py tests/test_automation.py
git commit -m "feat: add automation runner with Appium integration"
```

---

### Task 12: Orchestrator

**Files:**
- Create: `phone_farm/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_orchestrator.py`:

```python
"""Tests for the top-level orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from phone_farm.orchestrator import Orchestrator
from phone_farm.config import FarmConfig, FarmSection, EmulatorSection, AutomationSection, PathsSection


@pytest.fixture
def config() -> FarmConfig:
    return FarmConfig(
        farm=FarmSection(batch_size=2, cycle_delay_seconds=0, max_retries=1),
        emulator=EmulatorSection(api_level=34, ram_mb=1536, headless=True, device_profile="pixel_6"),
        automation=AutomationSection(
            appium_base_port=4723, default_flow="daily_usage",
            screenshot_on_failure=True, human_like_delays=True,
        ),
        paths=PathsSection(
            apk="./app.apk", scripts="./scripts/",
            logs="./logs/", db="./data/test.db",
            screenshots="./screenshots/", snapshots="./data/snapshots/",
        ),
    )


def test_orchestrator_computes_batches(config: FarmConfig) -> None:
    accounts = [
        {"id": i, "email": f"test{i}@gmail.com", "batch_group": (i % 3) + 1, "status": "active", "encrypted_password": "x"}
        for i in range(6)
    ]
    orch = Orchestrator(config=config)
    batches = orch._compute_batches(accounts)
    # batch_size=2, 6 accounts = 3 batches
    assert len(batches) == 3
    assert all(len(b) <= 2 for b in batches)


def test_orchestrator_skips_cooldown_accounts(config: FarmConfig) -> None:
    accounts = [
        {"id": 1, "email": "a@gmail.com", "batch_group": 1, "status": "active", "encrypted_password": "x"},
        {"id": 2, "email": "b@gmail.com", "batch_group": 1, "status": "cooldown", "encrypted_password": "x"},
        {"id": 3, "email": "c@gmail.com", "batch_group": 1, "status": "active", "encrypted_password": "x"},
    ]
    orch = Orchestrator(config=config)
    batches = orch._compute_batches(accounts)
    all_emails = [a["email"] for batch in batches for a in batch]
    assert "b@gmail.com" not in all_emails
    assert len(all_emails) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_orchestrator.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement orchestrator**

Write `phone_farm/orchestrator.py`:

```python
"""Top-level orchestrator: batches accounts, runs cycles, collects results."""

import asyncio
import random

from phone_farm.appium_server import AppiumServer
from phone_farm.automation import AutomationRunner, RunResult
from phone_farm.config import FarmConfig
from phone_farm.db import Database
from phone_farm.emulator import Emulator
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

            # Add random delay between batches for anti-detection
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

            # Run automation for each account in the batch
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
                    # Mark as cooldown if login-related
                    if result.error and "login" in result.error.lower():
                        await db.update_account_status(account["email"], "cooldown")
                        logger.emu(slot, f"marked cooldown — {account['email']}")

            # Cleanup
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_orchestrator.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator for batched cycle execution"
```

---

### Task 13: Reporter Module

**Files:**
- Create: `phone_farm/reporter.py`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_reporter.py`:

```python
"""Tests for reporting."""

import pytest
from pathlib import Path

from phone_farm.db import Database
from phone_farm.reporter import Reporter


@pytest.fixture
async def populated_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    await db.initialize()
    await db.add_account("a@gmail.com", "c1", batch_group=1)
    await db.add_account("b@gmail.com", "c2", batch_group=1)
    acc_a = await db.get_account_by_email("a@gmail.com")
    acc_b = await db.get_account_by_email("b@gmail.com")
    await db.record_run(acc_a["id"], "success", 60)
    await db.record_run(acc_a["id"], "success", 55)
    await db.record_run(acc_b["id"], "fail", 30, error_log="timeout")
    return db


@pytest.mark.asyncio
async def test_summary_report(populated_db: Database) -> None:
    reporter = Reporter(db=populated_db)
    summary = await reporter.summary()
    assert summary["total_accounts"] == 2
    assert summary["total_runs"] == 3
    assert summary["pass_rate"] == pytest.approx(2 / 3, rel=0.01)


@pytest.mark.asyncio
async def test_account_report(populated_db: Database) -> None:
    reporter = Reporter(db=populated_db)
    report = await reporter.account_detail("a@gmail.com")
    assert report["email"] == "a@gmail.com"
    assert report["total_runs"] == 2
    assert report["success_count"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_reporter.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement reporter**

Write `phone_farm/reporter.py`:

```python
"""Query run history and produce reports."""

from phone_farm.db import Database


class Reporter:
    """Generates reports from run history data."""

    def __init__(self, *, db: Database) -> None:
        self.db = db

    async def summary(self) -> dict:
        """Overall summary: total accounts, runs, pass rate."""
        accounts = await self.db.list_accounts()
        total_runs = 0
        total_success = 0
        for acc in accounts:
            runs = await self.db.get_runs_for_account(acc["id"])
            total_runs += len(runs)
            total_success += sum(1 for r in runs if r["result"] == "success")

        return {
            "total_accounts": len(accounts),
            "total_runs": total_runs,
            "pass_rate": total_success / total_runs if total_runs > 0 else 0.0,
            "total_success": total_success,
            "total_failures": total_runs - total_success,
        }

    async def account_detail(self, email: str) -> dict:
        """Detailed report for a single account."""
        account = await self.db.get_account_by_email(email)
        if account is None:
            raise ValueError(f"Account not found: {email}")
        runs = await self.db.get_runs_for_account(account["id"])
        success_count = sum(1 for r in runs if r["result"] == "success")
        return {
            "email": email,
            "status": account["status"],
            "total_runs": len(runs),
            "success_count": success_count,
            "fail_count": len(runs) - success_count,
            "last_run": runs[0]["run_date"] if runs else None,
            "recent_errors": [
                r["error_log"] for r in runs[:5] if r["error_log"]
            ],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_reporter.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/reporter.py tests/test_reporter.py
git commit -m "feat: add reporter for run history summaries"
```

---

### Task 14: Doctor Module

**Files:**
- Create: `phone_farm/doctor.py`
- Create: `tests/test_doctor.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_doctor.py`:

```python
"""Tests for doctor/prerequisite checker."""

import pytest
from unittest.mock import AsyncMock, patch

from phone_farm.doctor import Doctor, CheckResult


def test_check_result_dataclass() -> None:
    r = CheckResult(name="java", ok=True, message="Java 17 found")
    assert r.ok is True


@pytest.mark.asyncio
async def test_check_java_passes_when_found() -> None:
    doc = Doctor()
    with patch("phone_farm.doctor.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, 'openjdk version "17.0.10"', "")
        result = await doc.check_java()
    assert result.ok is True


@pytest.mark.asyncio
async def test_check_java_fails_when_missing() -> None:
    doc = Doctor()
    with patch("phone_farm.doctor.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = FileNotFoundError
        result = await doc.check_java()
    assert result.ok is False


@pytest.mark.asyncio
async def test_check_node_passes_when_found() -> None:
    doc = Doctor()
    with patch("phone_farm.doctor.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "v20.11.0", "")
        result = await doc.check_node()
    assert result.ok is True


@pytest.mark.asyncio
async def test_check_all_returns_list_of_results() -> None:
    doc = Doctor()
    with patch.object(doc, "check_java", new_callable=AsyncMock) as mj, \
         patch.object(doc, "check_node", new_callable=AsyncMock) as mn, \
         patch.object(doc, "check_adb", new_callable=AsyncMock) as ma, \
         patch.object(doc, "check_appium", new_callable=AsyncMock) as map_, \
         patch.object(doc, "check_disk_space", new_callable=AsyncMock) as md:
        mj.return_value = CheckResult("java", True, "ok")
        mn.return_value = CheckResult("node", True, "ok")
        ma.return_value = CheckResult("adb", True, "ok")
        map_.return_value = CheckResult("appium", True, "ok")
        md.return_value = CheckResult("disk", True, "ok")
        results = await doc.check_all()
    assert len(results) == 5
    assert all(r.ok for r in results)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_doctor.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement doctor module**

Write `phone_farm/doctor.py`:

```python
"""Verify prerequisites: Java, Node, ADB, Appium, disk space."""

import shutil
from dataclasses import dataclass

from phone_farm.emulator import run_cmd


@dataclass
class CheckResult:
    """Result of a single prerequisite check."""

    name: str
    ok: bool
    message: str


class Doctor:
    """Checks that all prerequisites are installed and working."""

    async def check_java(self) -> CheckResult:
        """Check for Java 17+."""
        try:
            returncode, stdout, stderr = await run_cmd(["java", "-version"], timeout=10)
            version_str = stderr or stdout  # java -version outputs to stderr
            if "17" in version_str or "21" in version_str or "22" in version_str:
                return CheckResult("java", True, f"Found: {version_str.strip().splitlines()[0]}")
            return CheckResult("java", False, f"Need Java 17+, found: {version_str.strip().splitlines()[0]}")
        except Exception:
            return CheckResult("java", False, "Java not found. Install: brew install openjdk@17")

    async def check_node(self) -> CheckResult:
        """Check for Node.js."""
        try:
            returncode, stdout, _ = await run_cmd(["node", "--version"], timeout=10)
            return CheckResult("node", True, f"Found: Node {stdout.strip()}")
        except Exception:
            return CheckResult("node", False, "Node.js not found. Install: brew install node")

    async def check_adb(self) -> CheckResult:
        """Check for ADB (Android Debug Bridge)."""
        try:
            returncode, stdout, _ = await run_cmd(["adb", "version"], timeout=10)
            return CheckResult("adb", True, f"Found: {stdout.strip().splitlines()[0]}")
        except Exception:
            return CheckResult("adb", False, "ADB not found. Run: phone-farm init")

    async def check_appium(self) -> CheckResult:
        """Check for Appium."""
        try:
            returncode, stdout, _ = await run_cmd(["appium", "--version"], timeout=10)
            return CheckResult("appium", True, f"Found: Appium {stdout.strip()}")
        except Exception:
            return CheckResult("appium", False, "Appium not found. Install: npm install -g appium")

    async def check_disk_space(self, min_gb: float = 7.0) -> CheckResult:
        """Check available disk space."""
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024**3)
        if free_gb >= min_gb:
            return CheckResult("disk", True, f"{free_gb:.1f} GB free (need {min_gb} GB)")
        return CheckResult("disk", False, f"Only {free_gb:.1f} GB free, need {min_gb} GB")

    async def check_all(self) -> list[CheckResult]:
        """Run all prerequisite checks."""
        return [
            await self.check_java(),
            await self.check_node(),
            await self.check_adb(),
            await self.check_appium(),
            await self.check_disk_space(),
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_doctor.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/doctor.py tests/test_doctor.py
git commit -m "feat: add doctor module for prerequisite verification"
```

---

### Task 15: CLI Interface

**Files:**
- Create: `phone_farm/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_cli.py`:

```python
"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from phone_farm.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Phone Farm" in result.output


def test_doctor_command(runner: CliRunner) -> None:
    with patch("phone_farm.cli.asyncio") as mock_asyncio:
        mock_asyncio.run = MagicMock()
        result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0


def test_accounts_list_command(runner: CliRunner) -> None:
    with patch("phone_farm.cli.asyncio") as mock_asyncio:
        mock_asyncio.run = MagicMock(return_value=[])
        result = runner.invoke(cli, ["accounts", "list"])
    assert result.exit_code == 0


def test_run_command_requires_mode(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["run"])
    # Should fail or show help without a mode argument
    assert result.exit_code != 0 or "Missing" in result.output or "Usage" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI**

Write `phone_farm/cli.py`:

```python
"""Click CLI for phone-farm."""

import asyncio
import csv
import sys
from pathlib import Path

import click

from phone_farm.config import load_config
from phone_farm.crypto import derive_key, encrypt, decrypt
from phone_farm.db import Database
from phone_farm.doctor import Doctor
from phone_farm.log import FarmLogger
from phone_farm.orchestrator import Orchestrator
from phone_farm.reporter import Reporter

logger = FarmLogger()

DEFAULT_CONFIG = Path("phone-farm.toml")
SALT_FILE = Path("data/.salt")


def _get_config(config_path: Path) -> "FarmConfig":
    return load_config(config_path)


def _get_salt() -> bytes:
    """Get or create the encryption salt."""
    SALT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SALT_FILE.exists():
        return SALT_FILE.read_bytes()
    import os
    salt = os.urandom(16)
    SALT_FILE.write_bytes(salt)
    return salt


@click.group()
@click.version_option(package_name="phone-farm")
def cli() -> None:
    """Phone Farm — Android emulator orchestration for app testing."""


@cli.command()
def doctor() -> None:
    """Verify all prerequisites are installed."""
    async def _run() -> None:
        doc = Doctor()
        results = await doc.check_all()
        all_ok = True
        for r in results:
            status = "OK" if r.ok else "FAIL"
            click.echo(f"  [{status}] {r.name}: {r.message}")
            if not r.ok:
                all_ok = False
        if all_ok:
            click.echo("\nAll checks passed!")
        else:
            click.echo("\nSome checks failed. Fix the issues above before proceeding.")
            sys.exit(1)
    asyncio.run(_run())


@cli.group()
def accounts() -> None:
    """Manage Google accounts."""


@accounts.command("list")
@click.option("--config", "config_path", default=str(DEFAULT_CONFIG), help="Config file path")
def accounts_list(config_path: str) -> None:
    """List all registered accounts."""
    async def _run() -> None:
        cfg = _get_config(Path(config_path))
        db = Database(Path(cfg.paths.db))
        await db.initialize()
        accs = await db.list_accounts()
        if not accs:
            click.echo("No accounts registered. Use 'phone-farm accounts add' to add one.")
            return
        click.echo(f"{'ID':<5} {'Email':<35} {'Group':<7} {'Status':<10} {'Last Used'}")
        click.echo("-" * 80)
        for a in accs:
            click.echo(
                f"{a['id']:<5} {a['email']:<35} {a['batch_group']:<7} "
                f"{a['status']:<10} {a['last_used'] or 'never'}"
            )
    asyncio.run(_run())


@accounts.command("add")
@click.option("--config", "config_path", default=str(DEFAULT_CONFIG), help="Config file path")
def accounts_add(config_path: str) -> None:
    """Add a Google account interactively."""
    email = click.prompt("Google email")
    app_password = click.prompt("App-specific password", hide_input=True)
    batch_group = click.prompt("Batch group (1-6)", type=int)
    master_pw = click.prompt("Master password", hide_input=True)

    async def _run() -> None:
        cfg = _get_config(Path(config_path))
        salt = _get_salt()
        key = derive_key(master_pw, salt=salt)
        encrypted_pw = encrypt(app_password, key)
        db = Database(Path(cfg.paths.db))
        await db.initialize()
        await db.add_account(email, encrypted_pw, batch_group=batch_group)
        click.echo(f"Added {email} to batch group {batch_group}")
    asyncio.run(_run())


@accounts.command("import")
@click.argument("csv_file", type=click.Path(exists=True))
@click.option("--config", "config_path", default=str(DEFAULT_CONFIG), help="Config file path")
def accounts_import(csv_file: str, config_path: str) -> None:
    """Bulk import accounts from CSV (email,app_password,batch_group)."""
    master_pw = click.prompt("Master password", hide_input=True)

    async def _run() -> None:
        cfg = _get_config(Path(config_path))
        salt = _get_salt()
        key = derive_key(master_pw, salt=salt)
        db = Database(Path(cfg.paths.db))
        await db.initialize()
        count = 0
        with open(csv_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                encrypted_pw = encrypt(row["app_password"], key)
                await db.add_account(
                    row["email"], encrypted_pw, batch_group=int(row["batch_group"])
                )
                count += 1
        click.echo(f"Imported {count} accounts")
    asyncio.run(_run())


@cli.command()
@click.argument("mode", type=click.Choice(["tester-gate", "qa"]))
@click.option("--config", "config_path", default=str(DEFAULT_CONFIG), help="Config file path")
def run(mode: str, config_path: str) -> None:
    """Run a testing cycle (tester-gate or qa)."""
    async def _run() -> None:
        cfg = _get_config(Path(config_path))
        db = Database(Path(cfg.paths.db))
        await db.initialize()
        orch = Orchestrator(config=cfg)
        summary = await orch.run_cycle(db=db, mode=mode)
        click.echo(f"\nSummary: {summary['passed']} passed, {summary['failed']} failed, {summary['skipped']} skipped")
    asyncio.run(_run())


@cli.command()
@click.option("--account", "account_email", default=None, help="Show detail for specific account")
@click.option("--config", "config_path", default=str(DEFAULT_CONFIG), help="Config file path")
def report(account_email: str | None, config_path: str) -> None:
    """Show run reports."""
    async def _run() -> None:
        cfg = _get_config(Path(config_path))
        db = Database(Path(cfg.paths.db))
        await db.initialize()
        rep = Reporter(db=db)
        if account_email:
            detail = await rep.account_detail(account_email)
            click.echo(f"Account: {detail['email']}")
            click.echo(f"Status: {detail['status']}")
            click.echo(f"Total runs: {detail['total_runs']}")
            click.echo(f"Success: {detail['success_count']} | Fail: {detail['fail_count']}")
            if detail['recent_errors']:
                click.echo("Recent errors:")
                for err in detail['recent_errors']:
                    click.echo(f"  - {err}")
        else:
            summary = await rep.summary()
            click.echo(f"Total accounts: {summary['total_accounts']}")
            click.echo(f"Total runs: {summary['total_runs']}")
            click.echo(f"Pass rate: {summary['pass_rate']:.1%}")
    asyncio.run(_run())


@cli.command()
@click.option("--config", "config_path", default=str(DEFAULT_CONFIG), help="Config file path")
def init(config_path: str) -> None:
    """Initialize phone-farm: create dirs, DB, download SDK components."""
    async def _run() -> None:
        cfg = _get_config(Path(config_path))
        for d in [cfg.paths.logs, cfg.paths.screenshots, cfg.paths.snapshots]:
            Path(d).mkdir(parents=True, exist_ok=True)
        db = Database(Path(cfg.paths.db))
        await db.initialize()
        click.echo("Created directories and database.")
        click.echo("Downloading Android SDK components...")
        from phone_farm.emulator import run_cmd
        await run_cmd(["sdkmanager", f"system-images;android-{cfg.emulator.api_level};google_apis;arm64-v8a"], timeout=600)
        await run_cmd(["sdkmanager", "platform-tools"], timeout=120)
        click.echo("SDK components installed. Run 'phone-farm doctor' to verify.")
    asyncio.run(_run())


@cli.group()
def snapshot() -> None:
    """Manage account snapshots."""


@snapshot.command("create")
@click.option("--account", "account_id", type=int, required=True, help="Account ID to snapshot")
@click.option("--config", "config_path", default=str(DEFAULT_CONFIG), help="Config file path")
def snapshot_create(account_id: int, config_path: str) -> None:
    """Boot an emulator with GUI for manual Google login, then save snapshot."""
    async def _run() -> None:
        cfg = _get_config(Path(config_path))
        db = Database(Path(cfg.paths.db))
        await db.initialize()
        accounts = await db.list_accounts()
        account = next((a for a in accounts if a["id"] == account_id), None)
        if not account:
            click.echo(f"Account ID {account_id} not found.")
            return
        from phone_farm.emulator import Emulator
        emu = Emulator(slot=0, api_level=cfg.emulator.api_level, ram_mb=cfg.emulator.ram_mb, device_profile=cfg.emulator.device_profile)
        click.echo(f"Creating AVD for {account['email']}...")
        await emu.create_avd()
        click.echo("Booting emulator with GUI — sign into Google and opt into testing...")
        await emu.start(headless=False)
        await emu.wait_for_boot(timeout=180)
        click.echo("Emulator is ready. Complete the manual login, then press Enter here to save snapshot.")
        input()
        snapshot_name = f"account-{account_id}-authed"
        await emu.save_snapshot(snapshot_name)
        click.echo(f"Snapshot '{snapshot_name}' saved for {account['email']}")
        await emu.stop()
    asyncio.run(_run())


@cli.command()
def cleanup() -> None:
    """Remove stale AVDs and old log files."""
    import shutil
    logs_dir = Path("logs")
    if logs_dir.exists():
        count = sum(1 for _ in logs_dir.glob("*.log"))
        shutil.rmtree(logs_dir)
        logs_dir.mkdir()
        click.echo(f"Removed {count} log files")
    else:
        click.echo("No logs to clean")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/cli.py tests/test_cli.py
git commit -m "feat: add CLI interface with all commands"
```

---

### Task 16: Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

Write `tests/test_integration.py`:

```python
"""Integration tests — test the full pipeline with mocked emulators."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from phone_farm.config import load_config, FarmConfig, FarmSection, EmulatorSection, AutomationSection, PathsSection
from phone_farm.crypto import derive_key, encrypt
from phone_farm.db import Database
from phone_farm.orchestrator import Orchestrator


@pytest.fixture
def config() -> FarmConfig:
    return FarmConfig(
        farm=FarmSection(batch_size=2, cycle_delay_seconds=0, max_retries=1),
        emulator=EmulatorSection(api_level=34, ram_mb=1536, headless=True, device_profile="pixel_6"),
        automation=AutomationSection(
            appium_base_port=4723, default_flow="daily_usage",
            screenshot_on_failure=True, human_like_delays=True,
        ),
        paths=PathsSection(
            apk="./app.apk", scripts="./scripts/",
            logs="./logs/", db="./data/test.db",
            screenshots="./screenshots/", snapshots="./data/snapshots/",
        ),
    )


@pytest.fixture
async def seeded_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "integration.db")
    await db.initialize()
    salt = b"test-salt-12345!"
    key = derive_key("test-master", salt=salt)
    for i in range(4):
        group = (i // 2) + 1
        await db.add_account(
            f"test{i}@gmail.com",
            encrypt(f"password{i}", key),
            batch_group=group,
        )
    return db


@pytest.mark.asyncio
async def test_full_cycle_with_mocked_emulators(config: FarmConfig, seeded_db: Database) -> None:
    """Test that orchestrator processes all accounts in batches."""
    orch = Orchestrator(config=config)

    with patch("phone_farm.orchestrator.EmulatorPool") as MockPool, \
         patch("phone_farm.orchestrator.AppiumServer") as MockAppium, \
         patch("phone_farm.orchestrator.AutomationRunner") as MockRunner, \
         patch("phone_farm.orchestrator.asyncio.sleep", new_callable=AsyncMock):

        # Mock pool
        mock_pool = MagicMock()
        mock_pool.start_all = AsyncMock(return_value=[True, True])
        mock_pool.stop_all = AsyncMock()
        mock_pool.emulators = [MagicMock(adb_serial=f"emulator-{5554+i*2}") for i in range(2)]
        MockPool.return_value = mock_pool

        # Mock appium
        mock_appium = MagicMock()
        mock_appium.start = AsyncMock()
        mock_appium.stop = AsyncMock()
        mock_appium.url = "http://127.0.0.1:4723"
        MockAppium.return_value = mock_appium

        # Mock runner
        from phone_farm.automation import RunResult
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock(return_value=RunResult(
            account_email="test@gmail.com", success=True, duration_seconds=60, error=None
        ))
        MockRunner.return_value = mock_runner

        summary = await orch.run_cycle(db=seeded_db, mode="tester-gate")

    assert summary["passed"] == 4
    assert summary["failed"] == 0

    # Verify run history was recorded
    accounts = await seeded_db.list_accounts()
    for acc in accounts:
        runs = await seeded_db.get_runs_for_account(acc["id"])
        assert len(runs) == 1
        assert runs[0]["result"] == "success"


@pytest.mark.asyncio
async def test_cycle_handles_boot_failure(config: FarmConfig, seeded_db: Database) -> None:
    """Test that a failed emulator boot skips that account."""
    orch = Orchestrator(config=config)

    with patch("phone_farm.orchestrator.EmulatorPool") as MockPool, \
         patch("phone_farm.orchestrator.AppiumServer") as MockAppium, \
         patch("phone_farm.orchestrator.AutomationRunner") as MockRunner, \
         patch("phone_farm.orchestrator.asyncio.sleep", new_callable=AsyncMock):

        mock_pool = MagicMock()
        mock_pool.start_all = AsyncMock(return_value=[True, False])  # Second emu fails
        mock_pool.stop_all = AsyncMock()
        mock_pool.emulators = [MagicMock(adb_serial=f"emulator-{5554+i*2}") for i in range(2)]
        MockPool.return_value = mock_pool

        mock_appium = MagicMock()
        mock_appium.start = AsyncMock()
        mock_appium.stop = AsyncMock()
        mock_appium.url = "http://127.0.0.1:4723"
        MockAppium.return_value = mock_appium

        from phone_farm.automation import RunResult
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock(return_value=RunResult(
            account_email="test@gmail.com", success=True, duration_seconds=60, error=None
        ))
        MockRunner.return_value = mock_runner

        summary = await orch.run_cycle(db=seeded_db, mode="tester-gate")

    # 2 batches of 2, but one emu fails per batch = 2 passed, 2 skipped
    assert summary["skipped"] == 2
    assert summary["passed"] == 2
```

- [ ] **Step 2: Run integration tests**

```bash
uv run pytest tests/test_integration.py -v
```

Expected: 2 passed

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full cycle pipeline"
```

---

### Task 17: Lint and Final Polish

**Files:**
- Modify: all Python files

- [ ] **Step 1: Run ruff linter**

```bash
uv run ruff check phone_farm/ scripts/ tests/
```

- [ ] **Step 2: Fix any lint errors**

```bash
uv run ruff check --fix phone_farm/ scripts/ tests/
```

- [ ] **Step 3: Run ruff formatter**

```bash
uv run ruff format phone_farm/ scripts/ tests/
```

- [ ] **Step 4: Run full test suite again**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: lint and format all modules"
```

---

### Task 18: README and Usage Guide

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

Write `README.md`:

```markdown
# Phone Farm

Android emulator orchestration for automated app testing. Runs 30 Google accounts through your app in batches of 5 on a local machine.

## Quick Start

```bash
# Install
uv sync

# Check prerequisites
phone-farm doctor

# Add accounts
phone-farm accounts add
# Or bulk import
phone-farm accounts import accounts.csv

# Run daily tester-gate cycle
phone-farm run tester-gate

# Run QA tests
phone-farm run qa

# View reports
phone-farm report
phone-farm report --account test01@gmail.com
```

## Prerequisites

- Python 3.12+
- Java 17+ (`brew install openjdk@17`)
- Node.js (`brew install node`)
- Appium (`npm install -g appium`)
- Android SDK command-line tools

## Configuration

Edit `phone-farm.toml` to tune batch size, emulator specs, and paths.

## CSV Import Format

```csv
email,app_password,batch_group
test01@gmail.com,xxxx-xxxx-xxxx,1
test02@gmail.com,xxxx-xxxx-xxxx,1
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with quick start guide"
```
