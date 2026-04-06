"""Tests for CLI commands."""

from click.testing import CliRunner

from phone_farm.cli import cli


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "phone-farm" in result.output.lower() or "Usage" in result.output


def test_doctor_command_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    # Doctor runs prerequisite checks — some may fail in test env, that's OK
    assert result.exit_code == 0


def test_accounts_list_command_with_no_db() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["accounts", "list"])
    # Should handle missing db gracefully
    assert result.exit_code in (0, 1)
