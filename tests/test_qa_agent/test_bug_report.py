"""Tests for bug report data model and generation."""

import json
from pathlib import Path

from phone_farm.qa_agent.bug_report import (
    Bug,
    generate_report,
    save_report_json,
)


def test_bug_has_auto_generated_id() -> None:
    bug = Bug(
        severity="high",
        category="crash",
        title="App crashes on login",
        description="Force close when tapping login button",
        steps_to_reproduce=["Open app", "Tap login"],
        screen_signature="abc123",
    )
    assert len(bug.bug_id) == 8
    assert isinstance(bug.bug_id, str)


def test_generate_report_assembles_correctly() -> None:
    bugs = [
        Bug(severity="high", category="crash", title="Crash", description="desc",
            steps_to_reproduce=["step1"], screen_signature="sig1"),
    ]
    report = generate_report(
        bugs=bugs,
        app_description="Test app",
        apk_path="./app.apk",
        start_time="2024-01-01T00:00:00",
        end_time="2024-01-01T00:05:00",
        total_actions=50,
        unique_screens=8,
        coverage_summary="8 screens, 50 actions",
    )
    assert report.total_actions == 50
    assert len(report.bugs) == 1
    assert report.bugs[0].title == "Crash"


def test_save_report_json_writes_file(tmp_path: Path) -> None:
    report = generate_report(
        bugs=[],
        app_description="Test",
        apk_path="./app.apk",
        start_time="t0",
        end_time="t1",
        total_actions=10,
        unique_screens=3,
        coverage_summary="summary",
    )
    output = tmp_path / "reports" / "report.json"
    save_report_json(report, output)
    assert output.exists()
    data = json.loads(output.read_text())
    assert data["total_actions"] == 10
    assert data["bugs"] == []


def test_report_json_includes_bug_details(tmp_path: Path) -> None:
    bugs = [
        Bug(severity="medium", category="visual", title="Overlap",
            description="Button overlaps text", steps_to_reproduce=["Open settings"],
            screen_signature="sig2", screenshot_path="/tmp/ss.png"),
    ]
    report = generate_report(
        bugs=bugs, app_description="App", apk_path="./a.apk",
        start_time="t0", end_time="t1", total_actions=5,
        unique_screens=2, coverage_summary="s",
    )
    output = tmp_path / "r.json"
    save_report_json(report, output)
    data = json.loads(output.read_text())
    assert len(data["bugs"]) == 1
    assert data["bugs"][0]["category"] == "visual"
    assert data["bugs"][0]["screenshot_path"] == "/tmp/ss.png"
