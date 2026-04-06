"""Tests for enhanced crash reporting."""

from phone_farm.qa_agent.crash_reporter import build_crash_report, format_crash_report
from phone_farm.qa_agent.logcat import CrashInfo
from phone_farm.qa_agent.memory import ActionRecord


def test_build_crash_report_with_steps() -> None:
    crash = CrashInfo(
        crash_type="java_exception",
        message="NullPointerException at com.app.Main",
        stacktrace="at com.app.Main.onClick(Main.java:42)",
        timestamp="01-15 10:30:45",
    )
    actions = [
        ActionRecord(action_type="tap", target="Login", screen_signature="s1", step_number=0),
        ActionRecord(action_type="type", target="email_input", screen_signature="s1", step_number=1),
        ActionRecord(action_type="tap", target="Submit", screen_signature="s1", step_number=2),
    ]
    report = build_crash_report(crash, actions)
    assert report.crash_type == "java_exception"
    assert report.severity == "critical"
    assert len(report.steps_to_reproduce) == 3
    assert "Tap on 'Login'" in report.steps_to_reproduce[0]
    assert "Type 'email_input'" in report.steps_to_reproduce[1]


def test_build_crash_report_anr_severity() -> None:
    crash = CrashInfo(crash_type="anr", message="ANR in com.app", stacktrace="", timestamp="t")
    report = build_crash_report(crash, [])
    assert report.severity == "high"


def test_format_crash_report() -> None:
    crash = CrashInfo(
        crash_type="java_exception",
        message="NullPointerException",
        stacktrace="at com.app.Main.onClick",
        timestamp="01-15 10:30:45",
    )
    actions = [
        ActionRecord(action_type="tap", target="Login", screen_signature="s1", step_number=0),
    ]
    report = build_crash_report(crash, actions)
    text = format_crash_report(report)
    assert "CRITICAL" in text
    assert "Tap on 'Login'" in text
    assert "Stacktrace:" in text


def test_build_crash_report_empty_actions() -> None:
    crash = CrashInfo(crash_type="native_crash", message="Fatal signal 11", stacktrace="SIGSEGV", timestamp="t")
    report = build_crash_report(crash, [])
    assert report.steps_to_reproduce == []
    assert report.severity == "critical"
