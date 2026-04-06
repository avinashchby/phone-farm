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
