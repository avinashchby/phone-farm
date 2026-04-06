"""Tests for web app state management."""

from phone_farm.web.state import AppState


def test_app_state_initial() -> None:
    state = AppState()
    assert state.phones == {}
    assert state.test_runs == {}


def test_add_phone() -> None:
    state = AppState()
    state.add_phone(0, "emulator-5554")
    assert 0 in state.phones
    assert state.phones[0].adb_serial == "emulator-5554"
    assert state.phones[0].status == "booting"


def test_remove_phone() -> None:
    state = AppState()
    state.add_phone(0, "emulator-5554")
    state.remove_phone(0)
    assert 0 not in state.phones


def test_start_test_run() -> None:
    state = AppState()
    run_id = state.start_test_run("test.apk", "A test app")
    assert run_id in state.test_runs
    assert state.test_runs[run_id].apk_name == "test.apk"
    assert state.test_runs[run_id].status == "running"


def test_update_test_progress() -> None:
    state = AppState()
    run_id = state.start_test_run("test.apk", "A test app")
    state.update_test_progress(run_id, steps=10, screens=3, bugs=2)
    run = state.test_runs[run_id]
    assert run.steps_completed == 10
    assert run.screens_found == 3
    assert run.bugs_found == 2


def test_complete_test_run() -> None:
    state = AppState()
    run_id = state.start_test_run("test.apk", "A test app")
    state.complete_test_run(run_id, report_path="/tmp/report.json")
    assert state.test_runs[run_id].status == "completed"
    assert state.test_runs[run_id].report_path == "/tmp/report.json"
