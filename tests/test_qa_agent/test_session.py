"""Tests for QA session orchestrator."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from phone_farm.qa_agent.session import QASession, create_backend
from phone_farm.qa_agent.ai_backend import MockBackend
from phone_farm.config import FarmConfig, FarmSection, EmulatorSection, AutomationSection, PathsSection


@pytest.fixture
def config() -> FarmConfig:
    return FarmConfig(
        farm=FarmSection(batch_size=1, cycle_delay_seconds=0, max_retries=1),
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


def test_create_backend_mock() -> None:
    backend = create_backend("mock")
    assert isinstance(backend, MockBackend)


def test_create_backend_claude() -> None:
    mock_anthropic = MagicMock()
    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        backend = create_backend("claude")
    assert backend is not None


def test_create_backend_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown AI backend"):
        create_backend("gpt4")


def test_session_initializes(config: FarmConfig, tmp_path: Path) -> None:
    session = QASession(
        config=config,
        apk_path="./app.apk",
        app_description="Test app",
        ai_backend="mock",
        max_steps=50,
        output_dir=str(tmp_path / "reports"),
    )
    assert session.max_steps == 50
    assert session.ai_backend_name == "mock"
