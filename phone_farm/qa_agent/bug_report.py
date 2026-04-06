"""Bug data model and report generation."""

import json
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path

from rich.console import Console
from rich.table import Table


@dataclass
class Bug:
    """A single discovered bug."""

    severity: str                  # "critical", "high", "medium", "low"
    category: str                  # "crash", "anr", "visual", "functional", "accessibility"
    title: str
    description: str
    steps_to_reproduce: list[str]
    screen_signature: str
    screenshot_path: str | None = None
    logcat_snippet: str | None = None
    ai_reasoning: str = ""
    bug_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


@dataclass
class QAReport:
    """Complete QA session report."""

    app_description: str
    apk_path: str
    start_time: str
    end_time: str
    total_actions: int
    unique_screens: int
    bugs: list[Bug]
    coverage_summary: str


def generate_report(
    *,
    bugs: list[Bug],
    app_description: str,
    apk_path: str,
    start_time: str,
    end_time: str,
    total_actions: int,
    unique_screens: int,
    coverage_summary: str,
) -> QAReport:
    """Assemble a QA report from session results."""
    return QAReport(
        app_description=app_description,
        apk_path=apk_path,
        start_time=start_time,
        end_time=end_time,
        total_actions=total_actions,
        unique_screens=unique_screens,
        bugs=bugs,
        coverage_summary=coverage_summary,
    )


def save_report_json(report: QAReport, output_path: Path) -> None:
    """Save report as JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(report)
    output_path.write_text(json.dumps(data, indent=2))


def print_report_summary(report: QAReport, console: Console) -> None:
    """Print a rich-formatted summary to the terminal."""
    console.print(f"\n[bold]QA Report: {report.app_description}[/bold]")
    console.print(f"APK: {report.apk_path}")
    console.print(f"Duration: {report.start_time} → {report.end_time}")
    console.print(f"Actions: {report.total_actions} | Screens: {report.unique_screens}")
    console.print(f"Bugs found: {len(report.bugs)}\n")

    if not report.bugs:
        console.print("[green]No bugs found![/green]")
        return

    table = Table(title="Bugs Found")
    table.add_column("ID", style="dim")
    table.add_column("Severity")
    table.add_column("Category")
    table.add_column("Title")
    for bug in report.bugs:
        severity_style = {
            "critical": "bold red",
            "high": "red",
            "medium": "yellow",
            "low": "dim",
        }.get(bug.severity, "")
        table.add_row(bug.bug_id, f"[{severity_style}]{bug.severity}[/]", bug.category, bug.title)
    console.print(table)
