"""Crash and ANR detection via ADB logcat."""

import re
from dataclasses import dataclass

from phone_farm.emulator import run_cmd


@dataclass
class LogcatEntry:
    """A single logcat line."""

    timestamp: str
    level: str
    tag: str
    message: str


@dataclass
class CrashInfo:
    """A detected crash or ANR."""

    crash_type: str       # "java_exception", "anr", "native_crash"
    message: str
    stacktrace: str
    timestamp: str


def parse_logcat_output(raw: str) -> list[LogcatEntry]:
    """Parse raw logcat output into structured entries.

    Logcat format: 'MM-DD HH:MM:SS.mmm  PID  TID LEVEL TAG: message'
    """
    entries: list[LogcatEntry] = []
    pattern = re.compile(
        r"(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\d+\s+\d+\s+([VDIWEF])\s+(\S+?)\s*:\s*(.*)"
    )
    for line in raw.splitlines():
        match = pattern.match(line)
        if match:
            entries.append(LogcatEntry(
                timestamp=match.group(1),
                level=match.group(2),
                tag=match.group(3),
                message=match.group(4),
            ))
    return entries


def detect_crashes(entries: list[LogcatEntry]) -> list[CrashInfo]:
    """Find Java exceptions and fatal crashes in logcat entries."""
    crashes: list[CrashInfo] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        if "FATAL EXCEPTION" in entry.message or "Fatal signal" in entry.message:
            # Collect stacktrace lines following the crash
            stacktrace_lines = [entry.message]
            j = i + 1
            while j < len(entries) and j < i + 30:
                if entries[j].tag == entry.tag or "at " in entries[j].message:
                    stacktrace_lines.append(entries[j].message)
                else:
                    break
                j += 1
            crash_type = "native_crash" if "Fatal signal" in entry.message else "java_exception"
            crashes.append(CrashInfo(
                crash_type=crash_type,
                message=entry.message,
                stacktrace="\n".join(stacktrace_lines),
                timestamp=entry.timestamp,
            ))
            i = j
        else:
            i += 1
    return crashes


def detect_anrs(entries: list[LogcatEntry]) -> list[CrashInfo]:
    """Find ANR (Application Not Responding) events in logcat entries."""
    anrs: list[CrashInfo] = []
    for entry in entries:
        if "ANR in" in entry.message or "anr" in entry.tag.lower():
            anrs.append(CrashInfo(
                crash_type="anr",
                message=entry.message,
                stacktrace="",
                timestamp=entry.timestamp,
            ))
    return anrs


async def collect_logcat_errors(adb_serial: str) -> list[LogcatEntry]:
    """Run `adb logcat -d *:E` and return error-level entries."""
    _, stdout, _ = await run_cmd(
        ["adb", "-s", adb_serial, "logcat", "-d", "*:E"],
        timeout=15,
    )
    return parse_logcat_output(stdout)


async def clear_logcat(adb_serial: str) -> None:
    """Clear the logcat buffer."""
    await run_cmd(["adb", "-s", adb_serial, "logcat", "-c"], timeout=10)
