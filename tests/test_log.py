"""Tests for structured logging."""

from phone_farm.log import FarmLogger


def test_logger_formats_with_timestamp(capsys) -> None:
    logger = FarmLogger()
    logger.info("Test message")
    captured = capsys.readouterr()
    # Format: [HH:MM:SS] Test message
    assert "] Test message" in captured.out
    assert "[" in captured.out


def test_logger_emulator_prefix(capsys) -> None:
    logger = FarmLogger()
    logger.emu(1, "booted")
    captured = capsys.readouterr()
    assert "emu-1" in captured.out
    assert "booted" in captured.out


def test_logger_batch_prefix(capsys) -> None:
    logger = FarmLogger()
    logger.batch(2, 6, "starting")
    captured = capsys.readouterr()
    assert "Batch 2/6" in captured.out
