# tests/test_audit_cli.py
from click.testing import CliRunner
from phone_farm.cli import cli


def test_audit_requires_apk():
    runner = CliRunner()
    result = runner.invoke(cli, ["audit"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output or result.exit_code == 2


def test_audit_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "--help"])
    assert result.exit_code == 0
    assert "--client-name" in result.output
    assert "--output" in result.output


def test_audit_with_nonexistent_apk():
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "nonexistent.apk"])
    assert result.exit_code != 0
