"""Tests for session memory and coverage tracking."""

from phone_farm.qa_agent.memory import SessionMemory


def test_record_new_screen_returns_true() -> None:
    mem = SessionMemory()
    assert mem.record_screen("screen-a") is True
    assert mem.unique_screens == 1


def test_record_same_screen_returns_false() -> None:
    mem = SessionMemory()
    mem.record_screen("screen-a")
    assert mem.record_screen("screen-a") is False
    assert mem.unique_screens == 1


def test_record_action_increments_count() -> None:
    mem = SessionMemory()
    mem.record_screen("s1")
    mem.record_action("tap", "btn_login", "s1")
    mem.record_action("type", "input_email", "s1")
    assert mem.total_actions == 2


def test_get_summary_contains_stats() -> None:
    mem = SessionMemory()
    mem.record_screen("s1")
    mem.record_action("tap", "btn", "s1")
    summary = mem.get_summary()
    assert "1 screens" in summary
    assert "1 actions" in summary
    assert "tap(btn)" in summary


def test_coverage_stalled_false_initially() -> None:
    mem = SessionMemory()
    assert mem.coverage_stalled is False


def test_coverage_stalled_after_15_actions_no_new_screen() -> None:
    mem = SessionMemory()
    mem.record_screen("s1")
    for i in range(15):
        mem.record_action("tap", f"btn{i}", "s1")
    assert mem.coverage_stalled is True


def test_coverage_not_stalled_with_recent_new_screen() -> None:
    mem = SessionMemory()
    mem.record_screen("s1")
    for i in range(10):
        mem.record_action("tap", f"btn{i}", "s1")
    mem.record_screen("s2")  # new screen resets stall
    for i in range(4):
        mem.record_action("tap", f"btn{i}", "s2")
    assert mem.coverage_stalled is False


def test_unexplored_hints_shows_uninteracted() -> None:
    mem = SessionMemory()
    mem.record_screen("s1")
    mem.record_action("tap", "btn_a", "s1")
    hints = mem.get_unexplored_hints(["btn_a", "btn_b", "btn_c"], "s1")
    assert "btn_b" in hints
    assert "btn_c" in hints
    assert "btn_a" not in hints


def test_unexplored_hints_all_explored() -> None:
    mem = SessionMemory()
    mem.record_screen("s1")
    mem.record_action("tap", "btn_a", "s1")
    hints = mem.get_unexplored_hints(["btn_a"], "s1")
    assert "All elements" in hints


def test_get_recent_actions() -> None:
    mem = SessionMemory()
    mem.record_screen("s1")
    for i in range(20):
        mem.record_action("tap", f"btn{i}", "s1")
    recent = mem.get_recent_actions(5)
    assert len(recent) == 5
    assert recent[-1].target == "btn19"
