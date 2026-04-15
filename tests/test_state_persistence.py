# tests/test_state_persistence.py
import pytest
from pathlib import Path
from phone_farm.db import Database
from phone_farm.web.state import AppState, TestRun


@pytest.fixture
async def db(tmp_path):
    d = Database(tmp_path / "test.db")
    await d.initialize()
    return d


@pytest.mark.asyncio
async def test_save_and_load_run(db):
    state = AppState()
    run_id = state.start_test_run("app.apk", "Test App")
    state.complete_test_run(
        run_id,
        report_path="qa_reports/r.json",
        html_report_path="qa_reports/r.html",
    )
    run = state.test_runs[run_id]
    await db.save_run(run)
    loaded = await db.load_runs()
    assert any(r["run_id"] == run_id for r in loaded)


@pytest.mark.asyncio
async def test_loaded_run_has_correct_fields(db):
    state = AppState()
    run_id = state.start_test_run("myapp.apk", "My App")
    run = state.test_runs[run_id]
    run.steps_completed = 10
    run.screens_found = 3
    run.bugs_found = 1
    state.complete_test_run(run_id, report_path="r.json")
    await db.save_run(state.test_runs[run_id])
    runs = await db.load_runs()
    r = next(r for r in runs if r["run_id"] == run_id)
    assert r["apk_name"] == "myapp.apk"
    assert r["bugs_found"] == 1
    assert r["status"] == "completed"


@pytest.mark.asyncio
async def test_load_from_db_populates_state(db):
    state = AppState()
    run_id = state.start_test_run("test.apk", "Test")
    state.complete_test_run(run_id, report_path="r.json")
    await db.save_run(state.test_runs[run_id])

    loaded_state = await AppState.load_from_db(db)
    assert run_id in loaded_state.test_runs
    assert loaded_state.test_runs[run_id].apk_name == "test.apk"
