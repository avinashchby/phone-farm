"""Tests for logcat crash/ANR detection."""

import pytest
from unittest.mock import AsyncMock, patch

from phone_farm.qa_agent.logcat import (
    parse_logcat_output,
    detect_crashes,
    detect_anrs,
    collect_logcat_errors,
    clear_logcat,
)

SAMPLE_LOGCAT = """\
01-15 10:30:45.123  1234  1234 E AndroidRuntime: FATAL EXCEPTION: main
01-15 10:30:45.124  1234  1234 E AndroidRuntime: java.lang.NullPointerException: Attempt to invoke virtual method
01-15 10:30:45.125  1234  1234 E AndroidRuntime: \tat com.example.app.MainActivity.onClick(MainActivity.java:42)
01-15 10:30:45.126  1234  1234 E AndroidRuntime: \tat android.view.View.performClick(View.java:7448)
01-15 10:30:50.000  5678  5678 E ActivityManager: ANR in com.example.app
01-15 10:31:00.000  9999  9999 E DEBUG: Fatal signal 11 (SIGSEGV), code 1
"""

CLEAN_LOGCAT = """\
01-15 10:30:45.123  1234  1234 E SomeTag: normal error message
01-15 10:30:45.124  1234  1234 E AnotherTag: another normal error
"""


def test_parse_logcat_output_extracts_entries() -> None:
    entries = parse_logcat_output(SAMPLE_LOGCAT)
    assert len(entries) >= 5
    assert entries[0].level == "E"
    assert entries[0].tag == "AndroidRuntime"
    assert "FATAL EXCEPTION" in entries[0].message


def test_parse_logcat_output_handles_empty() -> None:
    entries = parse_logcat_output("")
    assert entries == []


def test_parse_logcat_output_skips_malformed_lines() -> None:
    raw = "not a valid logcat line\n01-15 10:30:45.123  1234  1234 E Tag: valid"
    entries = parse_logcat_output(raw)
    assert len(entries) == 1
    assert entries[0].tag == "Tag"


def test_detect_crashes_finds_java_exception() -> None:
    entries = parse_logcat_output(SAMPLE_LOGCAT)
    crashes = detect_crashes(entries)
    java_crashes = [c for c in crashes if c.crash_type == "java_exception"]
    assert len(java_crashes) >= 1
    assert "FATAL EXCEPTION" in java_crashes[0].message
    assert "NullPointerException" in java_crashes[0].stacktrace


def test_detect_crashes_finds_native_crash() -> None:
    entries = parse_logcat_output(SAMPLE_LOGCAT)
    crashes = detect_crashes(entries)
    native = [c for c in crashes if c.crash_type == "native_crash"]
    assert len(native) >= 1
    assert "Fatal signal" in native[0].message


def test_detect_crashes_none_in_clean_log() -> None:
    entries = parse_logcat_output(CLEAN_LOGCAT)
    crashes = detect_crashes(entries)
    assert len(crashes) == 0


def test_detect_anrs_finds_anr() -> None:
    entries = parse_logcat_output(SAMPLE_LOGCAT)
    anrs = detect_anrs(entries)
    assert len(anrs) >= 1
    assert anrs[0].crash_type == "anr"
    assert "com.example.app" in anrs[0].message


def test_detect_anrs_none_in_clean_log() -> None:
    entries = parse_logcat_output(CLEAN_LOGCAT)
    anrs = detect_anrs(entries)
    assert len(anrs) == 0


@pytest.mark.asyncio
async def test_collect_logcat_errors_calls_adb() -> None:
    with patch("phone_farm.qa_agent.logcat.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, SAMPLE_LOGCAT, "")
        entries = await collect_logcat_errors("emulator-5554")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "logcat" in args
        assert "-s" in args
        assert "emulator-5554" in args
        assert len(entries) >= 5


@pytest.mark.asyncio
async def test_clear_logcat_calls_adb() -> None:
    with patch("phone_farm.qa_agent.logcat.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "", "")
        await clear_logcat("emulator-5554")
        args = mock_run.call_args[0][0]
        assert "logcat" in args
        assert "-c" in args
