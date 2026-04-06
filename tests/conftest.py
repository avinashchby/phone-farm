"""Shared test fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a minimal phone-farm.toml in a temp dir."""
    config_file = tmp_path / "phone-farm.toml"
    config_file.write_text("""\
[farm]
batch_size = 5
cycle_delay_seconds = 60
max_retries = 2

[emulator]
api_level = 34
ram_mb = 1536
headless = true
device_profile = "pixel_6"

[automation]
appium_base_port = 4723
default_flow = "daily_usage"
screenshot_on_failure = true
human_like_delays = true

[paths]
apk = "./app-release.apk"
scripts = "./scripts/flows/"
logs = "./logs/"
db = "./data/phone-farm.db"
screenshots = "./screenshots/"
snapshots = "./data/snapshots/"
""")
    return config_file
