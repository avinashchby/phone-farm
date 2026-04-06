"""Tests for the top-level orchestrator."""

import pytest

from phone_farm.orchestrator import Orchestrator
from phone_farm.config import FarmConfig, FarmSection, EmulatorSection, AutomationSection, PathsSection


@pytest.fixture
def config() -> FarmConfig:
    return FarmConfig(
        farm=FarmSection(batch_size=2, cycle_delay_seconds=0, max_retries=1),
        emulator=EmulatorSection(api_level=34, ram_mb=1536, headless=True, device_profile="pixel_6"),
        automation=AutomationSection(
            appium_base_port=4723, default_flow="daily_usage",
            screenshot_on_failure=True, human_like_delays=True,
        ),
        paths=PathsSection(
            apk="./app.apk", scripts="./scripts/",
            logs="./logs/", db="./data/test.db",
            screenshots="./screenshots/", snapshots="./data/snapshots/",
        ),
    )


def test_orchestrator_computes_batches(config: FarmConfig) -> None:
    accounts = [
        {"id": i, "email": f"test{i}@gmail.com", "batch_group": (i % 3) + 1, "status": "active", "encrypted_password": "x"}
        for i in range(6)
    ]
    orch = Orchestrator(config=config)
    batches = orch._compute_batches(accounts)
    assert len(batches) == 3
    assert all(len(b) <= 2 for b in batches)


def test_orchestrator_skips_cooldown_accounts(config: FarmConfig) -> None:
    accounts = [
        {"id": 1, "email": "a@gmail.com", "batch_group": 1, "status": "active", "encrypted_password": "x"},
        {"id": 2, "email": "b@gmail.com", "batch_group": 1, "status": "cooldown", "encrypted_password": "x"},
        {"id": 3, "email": "c@gmail.com", "batch_group": 1, "status": "active", "encrypted_password": "x"},
    ]
    orch = Orchestrator(config=config)
    batches = orch._compute_batches(accounts)
    all_emails = [a["email"] for batch in batches for a in batch]
    assert "b@gmail.com" not in all_emails
    assert len(all_emails) == 2
