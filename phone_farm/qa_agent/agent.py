"""Core QA agent decision loop."""

from pathlib import Path

from phone_farm.log import FarmLogger
from phone_farm.qa_agent.ai_backend import AIBackend, AgentAction
from phone_farm.qa_agent.bug_report import Bug
from phone_farm.qa_agent.logcat import collect_logcat_errors, clear_logcat, detect_crashes, detect_anrs
from phone_farm.qa_agent.memory import SessionMemory
from phone_farm.qa_agent.state import (
    get_screen_xml,
    take_screenshot_b64,
    parse_screen_elements,
    compute_screen_signature,
)

logger = FarmLogger()


def execute_action(driver, action: AgentAction) -> None:
    """Translate an AgentAction into Appium driver calls."""
    if action.action_type == "tap":
        _execute_tap(driver, action)
    elif action.action_type == "scroll":
        direction = action.scroll_direction or "down"
        driver.execute_script(
            "mobile: scrollGesture",
            {"left": 100, "top": 300, "width": 200, "height": 500, "direction": direction, "percent": 0.75},
        )
    elif action.action_type == "type":
        _execute_type(driver, action)
    elif action.action_type == "back":
        driver.back()


def _execute_tap(driver, action: AgentAction) -> None:
    """Execute a tap action by resource-id, text, or bounds."""
    if action.target_resource_id:
        element = driver.find_element("id", action.target_resource_id)
        element.click()
    elif action.target_text:
        element = driver.find_element("xpath", f'//*[@text="{action.target_text}"]')
        element.click()
    elif action.target_bounds:
        x = (action.target_bounds[0] + action.target_bounds[2]) // 2
        y = (action.target_bounds[1] + action.target_bounds[3]) // 2
        driver.execute_script("mobile: clickGesture", {"x": x, "y": y})


def _execute_type(driver, action: AgentAction) -> None:
    """Execute a type action on an input field."""
    if action.target_resource_id:
        element = driver.find_element("id", action.target_resource_id)
    elif action.target_text:
        element = driver.find_element("xpath", f'//*[@text="{action.target_text}"]')
    else:
        return
    element.clear()
    if action.input_text:
        element.send_keys(action.input_text)


def _crashes_to_bugs(crashes, memory: SessionMemory) -> list[Bug]:
    """Convert crash/ANR detections to Bug objects."""
    bugs: list[Bug] = []
    recent_actions = memory.get_recent_actions(10)
    steps = [f"{a.action_type}({a.target})" for a in recent_actions]
    for crash in crashes:
        bugs.append(Bug(
            severity="critical" if crash.crash_type != "anr" else "high",
            category=crash.crash_type,
            title=f"{crash.crash_type}: {crash.message[:80]}",
            description=crash.message,
            steps_to_reproduce=steps,
            screen_signature="",
            logcat_snippet=crash.stacktrace[:500],
        ))
    return bugs


def _visual_issues_to_bugs(issues, screen_sig: str, screenshot_path: str | None) -> list[Bug]:
    """Convert visual issues to Bug objects."""
    return [
        Bug(
            severity=issue.severity,
            category="visual",
            title=f"Visual: {issue.issue_type} — {issue.description[:60]}",
            description=issue.description,
            steps_to_reproduce=[f"Navigate to screen {screen_sig}"],
            screen_signature=screen_sig,
            screenshot_path=screenshot_path,
            ai_reasoning=f"{issue.issue_type} at {issue.location}",
        )
        for issue in issues
    ]


class QAAgent:
    """AI-powered QA agent that explores an app and finds bugs."""

    def __init__(
        self,
        *,
        driver,
        ai: AIBackend,
        adb_serial: str,
        app_description: str,
        screenshot_dir: Path,
        max_steps: int = 200,
        screenshot_interval: int = 10,
    ) -> None:
        self.driver = driver
        self.ai = ai
        self.adb_serial = adb_serial
        self.app_description = app_description
        self.screenshot_dir = screenshot_dir
        self.max_steps = max_steps
        self.screenshot_interval = screenshot_interval
        self.memory = SessionMemory(max_actions=max_steps)

    async def run(self) -> list[Bug]:
        """Run the full agent exploration loop. Returns discovered bugs."""
        await clear_logcat(self.adb_serial)
        bugs: list[Bug] = []

        for step in range(self.max_steps):
            try:
                step_bugs = await self._step(step)
                bugs.extend(step_bugs)
            except Exception as e:
                logger.error(f"Agent step {step} error: {e}")
                # Check if it's a crash
                crash_bugs = await self._check_crashes()
                bugs.extend(crash_bugs)
                if not crash_bugs:
                    break  # Unknown error, stop

            if self.memory.coverage_stalled:
                logger.info("Coverage stalled, pressing back")
                try:
                    self.driver.back()
                except Exception:
                    pass

        # Final crash check
        bugs.extend(await self._check_crashes())
        return bugs

    async def _step(self, step: int) -> list[Bug]:
        """Execute one step of the agent loop."""
        bugs: list[Bug] = []

        # 1. Observe
        xml = get_screen_xml(self.driver)
        sig = compute_screen_signature(xml)
        is_new = self.memory.record_screen(sig)

        # 2. Periodic crash check
        if step % 5 == 0:
            bugs.extend(await self._check_crashes())

        # 3. Decide if we need a screenshot
        need_screenshot = is_new or (step % self.screenshot_interval == 0)
        screenshot_b64 = None
        screenshot_path = None
        if need_screenshot:
            screenshot_path = str(self.screenshot_dir / f"step-{step}.png")
            try:
                screenshot_b64 = take_screenshot_b64(self.driver, save_path=Path(screenshot_path))
            except Exception as e:
                logger.error(f"Screenshot failed at step {step}: {e}")
                screenshot_path = None

        # 4. AI decides next action
        elements = parse_screen_elements(xml)
        unexplored = self.memory.get_unexplored_hints(
            [e.resource_id or e.text for e in elements if e.clickable or e.editable],
            sig,
        )
        summary = f"{self.memory.get_summary()}\n{unexplored}"

        action = await self.ai.decide_action(
            screen_xml=xml,
            memory_summary=summary,
            app_description=self.app_description,
            screenshot_b64=screenshot_b64,
        )

        logger.info(f"Step {step}: {action.action_type} — {action.reasoning[:60]}")

        # 5. Handle screenshot_check
        if action.action_type == "screenshot_check":
            ss_path = str(self.screenshot_dir / f"visual-{step}.png")
            ss_b64 = take_screenshot_b64(self.driver, save_path=Path(ss_path))
            issues = await self.ai.analyze_screenshot(ss_b64, xml, summary)
            bugs.extend(_visual_issues_to_bugs(issues, sig, ss_path))
            return bugs

        # 6. Handle done
        if action.action_type == "done":
            logger.info("AI signaled done")
            return bugs

        # 7. Execute action
        execute_action(self.driver, action)
        target = action.target_resource_id or action.target_text or action.action_type
        self.memory.record_action(action.action_type, target, sig)

        return bugs

    async def _check_crashes(self) -> list[Bug]:
        """Check logcat for crashes and ANRs."""
        entries = await collect_logcat_errors(self.adb_serial)
        crashes = detect_crashes(entries) + detect_anrs(entries)
        await clear_logcat(self.adb_serial)
        return _crashes_to_bugs(crashes, self.memory)
