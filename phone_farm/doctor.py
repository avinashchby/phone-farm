"""Verify prerequisites: Java, Node, ADB, Appium, disk space."""

import shutil
from dataclasses import dataclass

from phone_farm.emulator import run_cmd


@dataclass
class CheckResult:
    """Result of a single prerequisite check."""

    name: str
    ok: bool
    message: str


class Doctor:
    """Checks that all prerequisites are installed and working."""

    async def check_java(self) -> CheckResult:
        """Check for Java 17+."""
        try:
            _, stdout, stderr = await run_cmd(["java", "-version"], timeout=10)
            version_str = stderr or stdout
            if "17" in version_str or "21" in version_str or "22" in version_str:
                return CheckResult("java", True, f"Found: {version_str.strip().splitlines()[0]}")
            return CheckResult("java", False, f"Need Java 17+, found: {version_str.strip().splitlines()[0]}")
        except Exception:
            return CheckResult("java", False, "Java not found. Install: brew install openjdk@17")

    async def check_node(self) -> CheckResult:
        """Check for Node.js."""
        try:
            _, stdout, _ = await run_cmd(["node", "--version"], timeout=10)
            return CheckResult("node", True, f"Found: Node {stdout.strip()}")
        except Exception:
            return CheckResult("node", False, "Node.js not found. Install: brew install node")

    async def check_adb(self) -> CheckResult:
        """Check for ADB (Android Debug Bridge)."""
        try:
            _, stdout, _ = await run_cmd(["adb", "version"], timeout=10)
            return CheckResult("adb", True, f"Found: {stdout.strip().splitlines()[0]}")
        except Exception:
            return CheckResult("adb", False, "ADB not found. Run: phone-farm init")

    async def check_appium(self) -> CheckResult:
        """Check for Appium."""
        try:
            _, stdout, _ = await run_cmd(["appium", "--version"], timeout=10)
            return CheckResult("appium", True, f"Found: Appium {stdout.strip()}")
        except Exception:
            return CheckResult("appium", False, "Appium not found. Install: npm install -g appium")

    async def check_disk_space(self, min_gb: float = 7.0) -> CheckResult:
        """Check available disk space."""
        _, _, free = shutil.disk_usage("/")
        free_gb = free / (1024**3)
        if free_gb >= min_gb:
            return CheckResult("disk", True, f"{free_gb:.1f} GB free (need {min_gb} GB)")
        return CheckResult("disk", False, f"Only {free_gb:.1f} GB free, need {min_gb} GB")

    async def check_all(self) -> list[CheckResult]:
        """Run all prerequisite checks."""
        return [
            await self.check_java(),
            await self.check_node(),
            await self.check_adb(),
            await self.check_appium(),
            await self.check_disk_space(),
        ]
