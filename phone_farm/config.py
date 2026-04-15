"""Load and validate phone-farm.toml configuration."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class FarmSection:
    batch_size: int
    cycle_delay_seconds: int
    max_retries: int


@dataclass(frozen=True)
class EmulatorSection:
    api_level: int
    ram_mb: int
    headless: bool
    device_profile: str


@dataclass(frozen=True)
class AutomationSection:
    appium_base_port: int
    default_flow: str
    screenshot_on_failure: bool
    human_like_delays: bool


@dataclass(frozen=True)
class PathsSection:
    apk: str
    scripts: str
    logs: str
    db: str
    screenshots: str
    snapshots: str


@dataclass(frozen=True)
class QAAgentSection:
    """Configuration for the AI-powered QA agent."""

    ai_backend: str
    max_steps: int
    screenshot_interval: int
    output_dir: str


@dataclass(frozen=True)
class FarmConfig:
    farm: FarmSection
    emulator: EmulatorSection
    automation: AutomationSection
    paths: PathsSection
    qa_agent: QAAgentSection | None = None


def default_config() -> FarmConfig:
    """Return sensible defaults when no phone-farm.toml exists.

    Safe to use for: phone-farm audit <apk> with zero config.
    """
    return FarmConfig(
        farm=FarmSection(
            batch_size=4,
            cycle_delay_seconds=30,
            max_retries=3,
        ),
        emulator=EmulatorSection(
            api_level=34,
            ram_mb=2048,
            headless=True,
            device_profile="pixel_6",
        ),
        automation=AutomationSection(
            appium_base_port=4723,
            default_flow="explore",
            screenshot_on_failure=True,
            human_like_delays=True,
        ),
        paths=PathsSection(
            apk="",
            scripts="scripts",
            logs="logs",
            db="phone-farm.db",
            screenshots="screenshots",
            snapshots="snapshots",
        ),
        qa_agent=None,
    )


def load_config(path: Path) -> FarmConfig:
    """Load and validate config from a TOML file.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If validation fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    farm = FarmSection(**raw["farm"])
    if farm.batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    emulator = EmulatorSection(**raw["emulator"])
    automation = AutomationSection(**raw["automation"])
    paths = PathsSection(**raw["paths"])

    qa_agent = None
    if "qa_agent" in raw:
        qa_agent = QAAgentSection(**raw["qa_agent"])

    return FarmConfig(farm=farm, emulator=emulator, automation=automation, paths=paths, qa_agent=qa_agent)
