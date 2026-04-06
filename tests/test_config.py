"""Tests for config loading and validation."""

from pathlib import Path

from phone_farm.config import load_config


def test_load_config_parses_all_sections(tmp_config: Path) -> None:
    cfg = load_config(tmp_config)
    assert cfg.farm.batch_size == 5
    assert cfg.emulator.api_level == 34
    assert cfg.automation.appium_base_port == 4723
    assert cfg.paths.apk == "./app-release.apk"


def test_load_config_missing_file_raises(tmp_path: Path) -> None:
    import pytest
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.toml")


def test_load_config_invalid_batch_size(tmp_config: Path) -> None:
    import pytest
    tmp_config.write_text(tmp_config.read_text().replace("batch_size = 5", "batch_size = 0"))
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        load_config(tmp_config)
