"""Session memory for tracking screen coverage and action history."""

from dataclasses import dataclass


@dataclass
class ActionRecord:
    """A single action taken during the session."""

    action_type: str
    target: str
    screen_signature: str
    step_number: int


class SessionMemory:
    """Tracks which screens and actions have been explored."""

    def __init__(self, max_actions: int = 200) -> None:
        self.max_actions = max_actions
        self._screens: dict[str, int] = {}  # signature -> visit count
        self._action_log: list[ActionRecord] = []
        self._screen_interactions: dict[str, set[str]] = {}  # sig -> set of targets interacted
        self._last_new_screen_step: int = 0

    def record_screen(self, signature: str) -> bool:
        """Record a screen visit. Returns True if this is a NEW screen."""
        is_new = signature not in self._screens
        self._screens[signature] = self._screens.get(signature, 0) + 1
        if is_new:
            self._last_new_screen_step = len(self._action_log)
            self._screen_interactions[signature] = set()
        return is_new

    def record_action(self, action_type: str, target: str, screen_signature: str) -> None:
        """Record an action taken on a specific screen."""
        self._action_log.append(ActionRecord(
            action_type=action_type,
            target=target,
            screen_signature=screen_signature,
            step_number=len(self._action_log),
        ))
        if screen_signature in self._screen_interactions:
            self._screen_interactions[screen_signature].add(target)

    def get_summary(self) -> str:
        """Produce a text summary for the AI context window.

        Kept short to minimize token usage.
        """
        total = len(self._action_log)
        screens = len(self._screens)
        recent = self._action_log[-5:] if self._action_log else []
        recent_str = "; ".join(
            f"{a.action_type}({a.target})" for a in recent
        )
        return (
            f"Explored {screens} screens in {total} actions. "
            f"Recent: {recent_str}"
        )

    def get_unexplored_hints(self, current_elements: list[str], screen_signature: str) -> str:
        """Return hints about elements on current screen not yet interacted with."""
        interacted = self._screen_interactions.get(screen_signature, set())
        unexplored = [e for e in current_elements if e not in interacted]
        if not unexplored:
            return "All elements on this screen have been explored."
        return f"Unexplored elements: {', '.join(unexplored[:10])}"

    @property
    def total_actions(self) -> int:
        """Total number of actions taken."""
        return len(self._action_log)

    @property
    def unique_screens(self) -> int:
        """Number of unique screens discovered."""
        return len(self._screens)

    @property
    def coverage_stalled(self) -> bool:
        """True if no new screens discovered in last 15 actions."""
        if len(self._action_log) < 15:
            return False
        return (len(self._action_log) - self._last_new_screen_step) >= 15

    def get_recent_actions(self, n: int = 10) -> list[ActionRecord]:
        """Get the last N actions for steps-to-reproduce generation."""
        return self._action_log[-n:]
