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
