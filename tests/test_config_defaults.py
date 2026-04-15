"""Test default_config() function."""

from phone_farm.config import default_config, FarmConfig


def test_default_config_returns_farm_config():
    """Verify default_config returns a FarmConfig instance."""
    cfg = default_config()
    assert isinstance(cfg, FarmConfig)


def test_default_config_api_level():
    """Verify emulator API level defaults to 34."""
    cfg = default_config()
    assert cfg.emulator.api_level == 34


def test_default_config_headless():
    """Verify emulator runs in headless mode by default."""
    cfg = default_config()
    assert cfg.emulator.headless is True


def test_default_config_has_paths():
    """Verify paths are set (non-empty strings)."""
    cfg = default_config()
    assert cfg.paths.db
    assert cfg.paths.scripts
    assert cfg.paths.logs
