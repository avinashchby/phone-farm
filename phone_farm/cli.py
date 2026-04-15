"""CLI interface for phone-farm."""

import asyncio
import csv
import os
import sys
from pathlib import Path

import uvicorn

import click
from rich.console import Console
from rich.table import Table

from phone_farm.config import load_config, default_config, FarmConfig
from phone_farm.crypto import derive_key, encrypt
from phone_farm.db import Database
from phone_farm.doctor import Doctor
from phone_farm.log import FarmLogger
from phone_farm.orchestrator import Orchestrator
from phone_farm.qa_agent.bug_report import print_report_summary
from phone_farm.reporter import Reporter
from phone_farm.emu_cli import (
    boot_emulator, teardown_emulator, get_screen, take_screenshot,
    tap_element, type_text, scroll, press_back, check_crashes,
)

console = Console()
logger = FarmLogger()

DEFAULT_CONFIG = Path("phone-farm.toml")
DEFAULT_SALT = b"phone-farm-v1-salt"


def get_config() -> FarmConfig:
    """Load config from default location, or return defaults if not found."""
    if not DEFAULT_CONFIG.exists():
        console.print("[yellow]No phone-farm.toml found, using defaults[/yellow]")
        return default_config()
    return load_config(DEFAULT_CONFIG)


def get_db(config: FarmConfig) -> Database:
    """Get database instance from config."""
    return Database(Path(config.paths.db))


def run_async(coro):
    """Run an async coroutine from sync CLI context."""
    return asyncio.run(coro)


@click.group()
@click.version_option(version="0.1.0", prog_name="phone-farm")
def cli() -> None:
    """Phone Farm — Android emulator orchestration for app testing."""


# --- Run commands ---


@cli.command()
@click.argument("mode", type=click.Choice(["tester-gate", "qa"]))
def run(mode: str) -> None:
    """Run a test cycle. MODE is 'tester-gate' or 'qa'."""

    async def _run() -> None:
        config = get_config()
        db = get_db(config)
        await db.initialize()
        orch = Orchestrator(config=config)
        summary = await orch.run_cycle(db=db, mode=mode)
        console.print(f"\n[bold green]Done![/bold green] {summary['passed']}/{summary['total']} passed")

    run_async(_run())


# --- Account commands ---


@cli.group()
def accounts() -> None:
    """Manage test accounts."""


@accounts.command("add")
@click.option("--email", prompt="Email", help="Google account email")
@click.option("--password", prompt="App password", hide_input=True, help="Google app-specific password")
@click.option("--batch-group", type=int, prompt="Batch group (1-6)", help="Batch group number")
def accounts_add(email: str, password: str, batch_group: int) -> None:
    """Add a new test account."""

    async def _add() -> None:
        master = click.prompt("Master password", hide_input=True)
        key = derive_key(master, salt=DEFAULT_SALT)
        encrypted = encrypt(password, key)
        config = get_config()
        db = get_db(config)
        await db.initialize()
        await db.add_account(email, encrypted, batch_group=batch_group)
        console.print(f"[green]Added account: {email} (batch group {batch_group})[/green]")

    run_async(_add())


@accounts.command("import")
@click.argument("csv_path", type=click.Path(exists=True))
def accounts_import(csv_path: str) -> None:
    """Bulk import accounts from CSV (email,app_password,batch_group)."""

    async def _import() -> None:
        master = click.prompt("Master password", hide_input=True)
        key = derive_key(master, salt=DEFAULT_SALT)
        config = get_config()
        db = get_db(config)
        await db.initialize()
        count = 0
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                encrypted = encrypt(row["app_password"], key)
                await db.add_account(
                    row["email"], encrypted, batch_group=int(row["batch_group"])
                )
                count += 1
        console.print(f"[green]Imported {count} accounts[/green]")

    run_async(_import())


@accounts.command("list")
def accounts_list() -> None:
    """List all test accounts."""

    async def _list() -> None:
        config = get_config()
        db = get_db(config)
        await db.initialize()
        accs = await db.list_accounts()
        if not accs:
            console.print("No accounts found. Run: phone-farm accounts add")
            return
        table = Table(title="Test Accounts")
        table.add_column("ID", style="dim")
        table.add_column("Email")
        table.add_column("Batch Group")
        table.add_column("Status")
        table.add_column("Last Used")
        for a in accs:
            table.add_row(
                str(a["id"]),
                a["email"],
                str(a["batch_group"]),
                a["status"],
                str(a.get("last_used", "never")),
            )
        console.print(table)

    run_async(_list())


# --- Report commands ---


@cli.command()
@click.option("--account", default=None, help="Show detail for one account email")
def report(account: str | None) -> None:
    """Show run history reports."""

    async def _report() -> None:
        config = get_config()
        db = get_db(config)
        await db.initialize()
        reporter = Reporter(db=db)
        if account:
            detail = await reporter.account_detail(account)
            console.print(f"\n[bold]{detail['email']}[/bold] — {detail['status']}")
            console.print(f"Runs: {detail['total_runs']} | Pass: {detail['success_count']} | Fail: {detail['fail_count']}")
            if detail["recent_errors"]:
                console.print("\nRecent errors:")
                for err in detail["recent_errors"]:
                    console.print(f"  - {err}")
        else:
            summary = await reporter.summary()
            console.print("\n[bold]Phone Farm Summary[/bold]")
            console.print(f"Accounts: {summary['total_accounts']}")
            console.print(f"Total runs: {summary['total_runs']}")
            console.print(f"Pass rate: {summary['pass_rate']:.1%}")

    run_async(_report())


# --- Doctor command ---


@cli.command()
def doctor() -> None:
    """Check prerequisites (Java, Node, ADB, Appium, disk)."""

    async def _doctor() -> None:
        doc = Doctor()
        results = await doc.check_all()
        all_ok = True
        for r in results:
            icon = "[green]OK[/green]" if r.ok else "[red]FAIL[/red]"
            console.print(f"  {icon} {r.name}: {r.message}")
            if not r.ok:
                all_ok = False
        if all_ok:
            console.print("\n[bold green]All checks passed![/bold green]")
        else:
            console.print("\n[bold red]Some checks failed. Fix issues above before running.[/bold red]")

    run_async(_doctor())


# --- QA test command ---


@cli.command("qa-test")
@click.argument("apk_path", type=click.Path(exists=True))
@click.option("--description", "-d", default="", help="App description for the AI")
@click.option("--max-steps", default=200, help="Max exploration steps")
@click.option("--backend", default="anthropic", type=click.Choice(["anthropic", "mock"]))
@click.option("--output", default="./qa_reports", help="Report output directory")
def qa_test(apk_path: str, description: str, max_steps: int, backend: str, output: str) -> None:
    """Run AI-powered QA testing on an APK (requires phone-farm-pro)."""
    try:
        from phone_farm_pro.session import QASession
    except ImportError:
        console.print(
            "[red]phone-farm-pro is required for AI-powered QA testing.[/red]\n"
            "Install with: uv pip install phone-farm-pro"
        )
        sys.exit(1)

    async def _qa_test() -> None:
        from phone_farm.scoring import compute_score
        from phone_farm.report_renderer import render_html_report
        config = get_config()
        session = QASession(
            config=config,
            apk_path=apk_path,
            app_description=description,
            ai_backend=backend,
            max_steps=max_steps,
            output_dir=output,
        )
        report = await session.run()
        print_report_summary(report, console)
        score = compute_score(report)
        html_path = Path(output) / f"report-{Path(apk_path).stem}.html"
        html_path.write_text(render_html_report(report, score), encoding="utf-8")
        console.print(f"[cyan]HTML report:[/cyan] {html_path}")

    run_async(_qa_test())


# --- Cleanup command ---


@cli.command()
def cleanup() -> None:
    """Remove stale AVDs and old logs."""
    logs_dir = Path("logs")
    screenshots_dir = Path("screenshots")
    removed = 0
    for d in [logs_dir, screenshots_dir]:
        if d.exists():
            for f in d.iterdir():
                f.unlink()
                removed += 1
    console.print(f"[green]Cleaned up {removed} files[/green]")


# --- Emulator commands (for AI agent control) ---


@cli.group()
def emu() -> None:
    """Control emulator for AI-driven testing."""


@emu.command("boot")
@click.argument("apk_path", type=click.Path(exists=True))
def emu_boot(apk_path: str) -> None:
    """Boot emulator, install APK, start Appium."""
    config = get_config()
    run_async(boot_emulator(config, apk_path))


@emu.command("teardown")
def emu_teardown() -> None:
    """Stop emulator and Appium."""
    config = get_config()
    run_async(teardown_emulator(config))


@emu.command("screen")
def emu_screen() -> None:
    """Print the current screen's accessibility tree XML."""
    xml = get_screen()
    click.echo(xml)


@emu.command("screenshot")
@click.argument("output_path", default="./screenshot.png")
def emu_screenshot(output_path: str) -> None:
    """Take a screenshot and save to a file."""
    path = take_screenshot(output_path)
    console.print(f"[green]Screenshot saved: {path}[/green]")


@emu.command("tap")
@click.option("--id", "resource_id", default=None, help="Element resource-id")
@click.option("--text", default=None, help="Element text content")
@click.option("--xy", default=None, help="x,y coordinates (e.g. '200,300')")
def emu_tap(resource_id: str | None, text: str | None, xy: str | None) -> None:
    """Tap an element on screen."""
    tap_element(resource_id=resource_id, text=text, xy=xy)
    console.print("[green]Tapped[/green]")


@emu.command("type")
@click.option("--id", "resource_id", default=None, help="Input field resource-id")
@click.option("--text", "field_text", default=None, help="Input field text label")
@click.option("--value", required=True, help="Text to type")
def emu_type(resource_id: str | None, field_text: str | None, value: str) -> None:
    """Type text into an input field."""
    type_text(resource_id=resource_id, text=field_text, value=value)
    console.print(f"[green]Typed: {value}[/green]")


@emu.command("scroll")
@click.argument("direction", type=click.Choice(["up", "down", "left", "right"]))
def emu_scroll(direction: str) -> None:
    """Scroll in a direction."""
    scroll(direction)
    console.print(f"[green]Scrolled {direction}[/green]")


@emu.command("back")
def emu_back() -> None:
    """Press the back button."""
    press_back()
    console.print("[green]Back pressed[/green]")


@emu.command("crashes")
def emu_crashes() -> None:
    """Check logcat for crashes and ANRs (JSON output)."""
    import json as json_mod
    crashes = run_async(check_crashes())
    if crashes:
        console.print(f"[red]Found {len(crashes)} crash(es):[/red]")
        click.echo(json_mod.dumps(crashes, indent=2))
    else:
        console.print("[green]No crashes detected[/green]")


# --- Demo command ---


@cli.command()
@click.option("--steps", default=30, help="Number of exploration steps")
def demo(steps: int) -> None:
    """Run a demo QA test on Wikipedia app (downloads automatically)."""
    from phone_farm.demo import run_demo
    run_async(run_demo(max_steps=steps))


# --- Web dashboard ---


@cli.command()
@click.option("--port", default=8000, help="Port to serve on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
def serve(port: int, host: str) -> None:
    """Start the web dashboard."""
    console.print(f"[bold green]Phone Farm[/bold green] dashboard at http://{host}:{port}")
    uvicorn.run("phone_farm.web.app:app", host=host, port=port, reload=True)


# --- Audit command ---


@cli.command()
@click.argument("apk", type=click.Path(exists=True))
@click.option("--output", default=None, help="Output directory")
@click.option("--max-steps", default=None, type=int)
@click.option("--client-name", default="", help="Client name for report header")
@click.option("--auditor-name", default="", help="Auditor name for report footer")
@click.option("--test-email", default="", help="Test account email")
@click.option("--test-password", default="", help="Test account password")
@click.option("--skip-login", is_flag=True, help="Skip login screens")
@click.option("--format", "fmt", default="both", type=click.Choice(["html", "json", "both"]))
def audit(apk, output, max_steps, client_name, auditor_name, test_email, test_password, skip_login, fmt):
    """Run a full QA audit on an APK and produce a client-ready report."""
    from pathlib import Path
    from datetime import datetime
    apk_path = Path(apk).resolve()
    out_dir = Path(output) if output else Path(f"audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    run_async(_run_audit(apk_path, out_dir, max_steps, client_name, auditor_name,
                          test_email, test_password, skip_login, fmt))


async def _run_audit(apk_path, out_dir, max_steps, client_name, auditor_name,
                     test_email, test_password, skip_login, fmt):
    """Orchestrate full audit: boot → install → explore → score → report."""
    from datetime import datetime, timezone
    from phone_farm.qa_agent.bug_report import generate_report
    from phone_farm.scoring import compute_score

    out_dir.mkdir(parents=True, exist_ok=True)
    config = get_config()
    if max_steps and config.qa_agent:
        from dataclasses import replace as _replace
        config = _replace(config, qa_agent=_replace(config.qa_agent, max_steps=max_steps))
    actual_steps = config.qa_agent.max_steps if config.qa_agent else 50

    console.print(f"[bold]Phone Farm Audit[/bold] — {apk_path.name}")
    console.print(f"Output: {out_dir}")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    bugs = await _explore(apk_path, config, api_key, test_email, test_password, skip_login)

    report = generate_report(
        bugs=bugs, app_description=apk_path.stem, apk_path=str(apk_path),
        start_time=datetime.now(timezone.utc).isoformat(),
        end_time=datetime.now(timezone.utc).isoformat(),
        total_actions=actual_steps,
        unique_screens=len({b.screen_signature for b in bugs}),
        coverage_summary=f"{len({b.screen_signature for b in bugs})} screens explored",
    )
    score = compute_score(report)

    _print_summary(report, score)
    _save_reports(report, score, out_dir, fmt, client_name, auditor_name)
    _print_cost(api_key)


async def _explore(apk_path, config, api_key, test_email, test_password, skip_login):
    """Run exploration — pro if API key set, free otherwise."""
    if api_key:
        try:
            from phone_farm_pro.agent import run_standalone_qa
            return await run_standalone_qa(str(apk_path), config, api_key,
                                           test_email=test_email, test_password=test_password)
        except ImportError:
            pass
    from phone_farm.web.qa_runner import run_standalone_qa as free_qa
    return await free_qa(str(apk_path), config, test_email=test_email,
                         test_password=test_password, skip_login=skip_login)


def _print_summary(report, score):
    color = "green" if score["score"] >= 80 else "yellow" if score["score"] >= 50 else "red"
    console.print(f"\n[bold {color}]Score: {score['score']}/100 ({score['grade']})[/bold {color}]")
    console.print(f"Bugs: {len(report.bugs)} | Screens: {report.unique_screens}")


def _save_reports(report, score, out_dir, fmt, client_name, auditor_name):
    from phone_farm.qa_agent.bug_report import save_report_json
    from phone_farm.report_renderer import render_html_report
    if fmt in ("json", "both"):
        json_path = out_dir / "report.json"
        save_report_json(report, json_path)
        console.print(f"JSON: {json_path}")
    if fmt in ("html", "both"):
        html = render_html_report(report, score, client_name=client_name, auditor_name=auditor_name)
        html_path = out_dir / "report.html"
        html_path.write_text(html, encoding="utf-8")
        console.print(f"[cyan]HTML report:[/cyan] {html_path}")


def _print_cost(api_key: str) -> None:
    if not api_key:
        return
    try:
        from phone_farm_pro.backend import AnthropicBackend
        usage = AnthropicBackend.last_usage()
        if usage:
            cost = (usage["input"] * 3 + usage["output"] * 15) / 1_000_000
            console.print(f"\n[dim]API Usage: {usage['input']:,} input + {usage['output']:,} output tokens[/dim]")
            console.print(f"[dim]Estimated cost: ${cost:.2f} (Sonnet 4.6)[/dim]")
    except (ImportError, AttributeError):
        pass
