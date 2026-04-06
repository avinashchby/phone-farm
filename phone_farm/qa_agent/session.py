"""QA session orchestrator: boots infra, runs agent, produces report."""

from datetime import datetime, timezone
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options

from phone_farm.appium_server import AppiumServer
from phone_farm.config import FarmConfig
from phone_farm.emulator import Emulator
from phone_farm.log import FarmLogger
from phone_farm.qa_agent.agent import QAAgent
from phone_farm.qa_agent.ai_backend import AIBackend, AnthropicBackend, MockBackend
from phone_farm.qa_agent.bug_report import generate_report, save_report_json, QAReport

logger = FarmLogger()


def create_backend(name: str) -> AIBackend:
    """Factory for AI backends."""
    if name in ("anthropic", "claude"):
        return AnthropicBackend()
    if name == "mock":
        return MockBackend()
    raise ValueError(f"Unknown AI backend: {name}. Available: anthropic, mock")


class QASession:
    """Orchestrates a full QA testing session."""

    def __init__(
        self,
        *,
        config: FarmConfig,
        apk_path: str,
        app_description: str,
        ai_backend: str = "anthropic",
        max_steps: int = 200,
        output_dir: str = "./qa_reports",
    ) -> None:
        self.config = config
        self.apk_path = apk_path
        self.app_description = app_description
        self.ai_backend_name = ai_backend
        self.max_steps = max_steps
        self.output_dir = Path(output_dir)

    async def run(self) -> QAReport:
        """Full session: boot emulator → install APK → run agent → report → teardown."""
        start_time = datetime.now(timezone.utc).isoformat()
        screenshot_dir = self.output_dir / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        emu = Emulator(
            slot=0,
            api_level=self.config.emulator.api_level,
            ram_mb=self.config.emulator.ram_mb,
            device_profile=self.config.emulator.device_profile,
        )
        appium = AppiumServer(slot=0, base_port=self.config.automation.appium_base_port)
        driver = None

        try:
            # 1. Boot emulator
            logger.info("Creating AVD...")
            await emu.create_avd()
            logger.info("Starting emulator...")
            await emu.start(headless=self.config.emulator.headless)
            logger.info("Waiting for boot...")
            await emu.wait_for_boot()

            # 2. Install APK
            logger.info(f"Installing APK: {self.apk_path}")
            await emu.install_apk(self.apk_path)

            # 3. Start Appium
            await appium.start()

            # 4. Create Appium driver
            options = UiAutomator2Options()
            options.udid = emu.adb_serial
            options.app = str(Path(self.apk_path).resolve())
            options.auto_grant_permissions = True
            options.no_reset = True

            driver = webdriver.Remote(
                command_executor=f"{appium.url}/wd/hub",
                options=options,
            )

            # 5. Create AI backend and agent
            ai = create_backend(self.ai_backend_name)
            agent = QAAgent(
                driver=driver,
                ai=ai,
                adb_serial=emu.adb_serial,
                app_description=self.app_description,
                screenshot_dir=screenshot_dir,
                max_steps=self.max_steps,
            )

            # 6. Run agent
            logger.info(f"Starting QA agent ({self.max_steps} max steps)...")
            bugs = await agent.run()

            # 7. Generate report
            end_time = datetime.now(timezone.utc).isoformat()
            report = generate_report(
                bugs=bugs,
                app_description=self.app_description,
                apk_path=self.apk_path,
                start_time=start_time,
                end_time=end_time,
                total_actions=agent.memory.total_actions,
                unique_screens=agent.memory.unique_screens,
                coverage_summary=agent.memory.get_summary(),
            )

            report_path = self.output_dir / "report.json"
            save_report_json(report, report_path)
            logger.info(f"Report saved: {report_path}")

            return report

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            await appium.stop()
            await emu.stop()
