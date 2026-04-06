"""Pluggable AI backend for QA agent decision-making."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AgentAction:
    """An action decided by the AI."""

    action_type: str              # "tap", "scroll", "type", "back", "screenshot_check", "done"
    target_resource_id: str | None = None
    target_text: str | None = None
    target_bounds: tuple[int, int, int, int] | None = None
    input_text: str | None = None
    scroll_direction: str | None = None  # "up", "down", "left", "right"
    reasoning: str = ""


@dataclass
class VisualIssue:
    """A visual issue detected from screenshot analysis."""

    issue_type: str     # "overlap", "truncation", "contrast", "alignment", "missing_text"
    severity: str       # "high", "medium", "low"
    location: str       # description of where on screen
    description: str


ACTION_SCHEMA = """\
Return a JSON object with these fields:
{
    "action_type": "tap" | "scroll" | "type" | "back" | "screenshot_check" | "done",
    "target_resource_id": "resource-id of element to interact with" or null,
    "target_text": "text content of element" or null,
    "target_bounds": [x1, y1, x2, y2] or null,
    "input_text": "text to type" or null (only for "type" actions),
    "scroll_direction": "up" | "down" | "left" | "right" or null,
    "reasoning": "brief explanation of why this action"
}
"""

DECIDE_SYSTEM_PROMPT = """\
You are a QA testing agent exploring an Android app. Your goal is to thoroughly test the app \
by navigating all screens, interacting with all elements, and finding bugs.

You receive the current screen's accessibility tree (XML) and a memory summary of what \
you've explored so far. Decide the next action to take.

Guidelines:
- Prioritize unexplored elements and screens
- Try all interactive elements (buttons, inputs, scrollable areas)
- Enter realistic test data in text fields (emails, names, etc.)
- Use "back" to navigate to previous screens when current screen is fully explored
- Use "screenshot_check" when you suspect visual issues (overlapping, misaligned elements)
- Use "done" only when you've explored most of the app or are stuck in a loop
- Vary your exploration strategy to maximize coverage

""" + ACTION_SCHEMA

VISUAL_SYSTEM_PROMPT = """\
You are a QA visual inspector. Analyze this screenshot of an Android app for visual defects.

Check for:
- Overlapping UI elements
- Truncated or clipped text
- Poor color contrast (text hard to read)
- Misaligned elements
- Missing or placeholder text/images
- Broken layouts or unexpected gaps

Return a JSON array of issues found:
[{"issue_type": "overlap|truncation|contrast|alignment|missing_text",
  "severity": "high|medium|low",
  "location": "description of where",
  "description": "what's wrong"}]

Return an empty array [] if no issues found.
"""


class AIBackend(ABC):
    """Abstract base class for AI decision-making backends."""

    @abstractmethod
    async def decide_action(
        self,
        screen_xml: str,
        memory_summary: str,
        app_description: str,
        screenshot_b64: str | None = None,
    ) -> AgentAction:
        """Decide the next action based on current screen state."""

    @abstractmethod
    async def analyze_screenshot(
        self,
        screenshot_b64: str,
        screen_xml: str,
        context: str,
    ) -> list[VisualIssue]:
        """Analyze a screenshot for visual issues."""


def _parse_action_json(raw: str) -> AgentAction:
    """Parse AI response JSON into an AgentAction.

    Handles both raw JSON and markdown-wrapped JSON (```json ... ```).
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    data = json.loads(text)
    bounds = data.get("target_bounds")
    if bounds and isinstance(bounds, list) and len(bounds) == 4:
        bounds = tuple(bounds)
    else:
        bounds = None
    return AgentAction(
        action_type=data.get("action_type", "done"),
        target_resource_id=data.get("target_resource_id"),
        target_text=data.get("target_text"),
        target_bounds=bounds,
        input_text=data.get("input_text"),
        scroll_direction=data.get("scroll_direction"),
        reasoning=data.get("reasoning", ""),
    )


def _parse_visual_issues_json(raw: str) -> list[VisualIssue]:
    """Parse AI response JSON into a list of VisualIssues."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    data = json.loads(text)
    if not isinstance(data, list):
        return []
    return [
        VisualIssue(
            issue_type=item.get("issue_type", "unknown"),
            severity=item.get("severity", "medium"),
            location=item.get("location", ""),
            description=item.get("description", ""),
        )
        for item in data
    ]


class ClaudeBackend(AIBackend):
    """Claude API backend for QA agent decisions."""

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required for ClaudeBackend. "
                "Install with: uv pip install 'phone-farm[ai]'"
            )
        self._client = anthropic.AsyncAnthropic()
        self._model = model

    async def decide_action(
        self,
        screen_xml: str,
        memory_summary: str,
        app_description: str,
        screenshot_b64: str | None = None,
    ) -> AgentAction:
        """Ask Claude to decide the next action."""
        user_content: list[dict] = []
        if screenshot_b64:
            user_content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64},
            })
        user_content.append({
            "type": "text",
            "text": (
                f"App: {app_description}\n\n"
                f"Memory: {memory_summary}\n\n"
                f"Current screen XML:\n{screen_xml[:8000]}"
            ),
        })
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=500,
            temperature=0,
            system=DECIDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],  # type: ignore[arg-type]
        )
        raw: str = getattr(response.content[0], "text", "")
        return _parse_action_json(raw)

    async def analyze_screenshot(
        self,
        screenshot_b64: str,
        screen_xml: str,
        context: str,
    ) -> list[VisualIssue]:
        """Ask Claude to analyze a screenshot for visual issues."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1000,
            temperature=0,
            system=VISUAL_SYSTEM_PROMPT,
            messages=[{  # type: ignore[arg-type]
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64},
                    },
                    {
                        "type": "text",
                        "text": f"Context: {context}\n\nAccessibility XML:\n{screen_xml[:4000]}",
                    },
                ],
            }],
        )
        raw: str = getattr(response.content[0], "text", "")
        return _parse_visual_issues_json(raw)


class MockBackend(AIBackend):
    """Mock backend for testing without API calls.

    Cycles through tapping interactive elements, then scrolls, then signals done.
    """

    def __init__(self) -> None:
        self._step = 0

    async def decide_action(
        self,
        screen_xml: str,
        memory_summary: str,
        app_description: str,
        screenshot_b64: str | None = None,
    ) -> AgentAction:
        """Return deterministic actions for testing."""
        self._step += 1
        if self._step > 20:
            return AgentAction(action_type="done", reasoning="mock done after 20 steps")
        if self._step % 5 == 0:
            return AgentAction(action_type="scroll", scroll_direction="down", reasoning="mock scroll")
        if self._step % 7 == 0:
            return AgentAction(action_type="back", reasoning="mock back")
        return AgentAction(
            action_type="tap",
            target_text=f"element-{self._step}",
            reasoning=f"mock tap step {self._step}",
        )

    async def analyze_screenshot(
        self,
        screenshot_b64: str,
        screen_xml: str,
        context: str,
    ) -> list[VisualIssue]:
        """Return empty list (no visual issues in mock mode)."""
        return []
