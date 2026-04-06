"""Enhanced crash reporting with reproduction steps."""

from dataclasses import dataclass

from phone_farm.qa_agent.logcat import CrashInfo
from phone_farm.qa_agent.memory import ActionRecord


@dataclass
class CrashReport:
    """A crash report with reproduction steps."""

    crash_type: str
    title: str
    stacktrace: str
    timestamp: str
    severity: str
    steps_to_reproduce: list[str]
    device_info: str


def build_crash_report(
    crash: CrashInfo,
    recent_actions: list[ActionRecord],
    device_info: str = "Android Emulator (API 34)",
) -> CrashReport:
    """Build a structured crash report from a crash and recent actions.

    The key differentiator: we know the exact sequence of actions
    that led to the crash, which no other crash reporter provides.
    """
    steps = []
    for i, action in enumerate(recent_actions, 1):
        if action.action_type == "tap":
            steps.append(f"{i}. Tap on '{action.target}'")
        elif action.action_type == "type":
            steps.append(f"{i}. Type '{action.target}'")
        elif action.action_type == "scroll":
            steps.append(f"{i}. Scroll {action.target}")
        elif action.action_type == "back":
            steps.append(f"{i}. Press back")
        else:
            steps.append(f"{i}. {action.action_type}({action.target})")

    severity = "critical"
    if crash.crash_type == "anr":
        severity = "high"

    # Extract short title from crash message
    title = crash.message.strip().split("\n")[0][:100]

    return CrashReport(
        crash_type=crash.crash_type,
        title=title,
        stacktrace=crash.stacktrace,
        timestamp=crash.timestamp,
        severity=severity,
        steps_to_reproduce=steps,
        device_info=device_info,
    )


def format_crash_report(report: CrashReport) -> str:
    """Format a crash report as readable text."""
    lines = [
        f"[{report.severity.upper()}] {report.crash_type}: {report.title}",
        f"Device: {report.device_info}",
        f"Time: {report.timestamp}",
        "",
        "Steps to reproduce:",
    ]
    lines.extend(report.steps_to_reproduce)
    lines.append("")
    lines.append("Stacktrace:")
    lines.append(report.stacktrace[:1000])
    return "\n".join(lines)
