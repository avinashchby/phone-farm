"""Tests for AI backend interface and implementations."""

import json
import pytest

from phone_farm.qa_agent.ai_backend import (
    MockBackend,
    _parse_action_json,
    _parse_visual_issues_json,
)


def test_parse_action_json_basic() -> None:
    raw = json.dumps({
        "action_type": "tap",
        "target_resource_id": "com.app:id/btn",
        "target_text": "Login",
        "target_bounds": [100, 200, 300, 400],
        "input_text": None,
        "scroll_direction": None,
        "reasoning": "Tap login button",
    })
    action = _parse_action_json(raw)
    assert action.action_type == "tap"
    assert action.target_resource_id == "com.app:id/btn"
    assert action.target_bounds == (100, 200, 300, 400)
    assert action.reasoning == "Tap login button"


def test_parse_action_json_markdown_wrapped() -> None:
    raw = '```json\n{"action_type": "scroll", "scroll_direction": "down", "reasoning": "scroll"}\n```'
    action = _parse_action_json(raw)
    assert action.action_type == "scroll"
    assert action.scroll_direction == "down"


def test_parse_action_json_missing_fields_defaults() -> None:
    raw = json.dumps({"action_type": "back"})
    action = _parse_action_json(raw)
    assert action.action_type == "back"
    assert action.target_resource_id is None
    assert action.reasoning == ""


def test_parse_action_json_invalid_returns_back() -> None:
    action = _parse_action_json("not json at all")
    assert action.action_type == "back"
    assert "Failed to parse" in action.reasoning


def test_parse_visual_issues_json_finds_issues() -> None:
    raw = json.dumps([
        {"issue_type": "overlap", "severity": "high", "location": "top bar", "description": "Button overlaps title"},
        {"issue_type": "truncation", "severity": "medium", "location": "card", "description": "Text cut off"},
    ])
    issues = _parse_visual_issues_json(raw)
    assert len(issues) == 2
    assert issues[0].issue_type == "overlap"
    assert issues[1].severity == "medium"


def test_parse_visual_issues_json_empty_array() -> None:
    issues = _parse_visual_issues_json("[]")
    assert issues == []


def test_parse_visual_issues_json_markdown_wrapped() -> None:
    raw = '```json\n[{"issue_type": "contrast", "severity": "low", "location": "footer", "description": "low contrast"}]\n```'
    issues = _parse_visual_issues_json(raw)
    assert len(issues) == 1


def test_parse_visual_issues_json_invalid_returns_empty() -> None:
    issues = _parse_visual_issues_json("not json")
    assert issues == []


@pytest.mark.asyncio
async def test_mock_backend_cycles_actions() -> None:
    backend = MockBackend()
    actions = []
    for _ in range(10):
        action = await backend.decide_action("xml", "summary", "app")
        actions.append(action.action_type)
    assert "tap" in actions
    assert "scroll" in actions


@pytest.mark.asyncio
async def test_mock_backend_eventually_done() -> None:
    backend = MockBackend()
    for _ in range(25):
        action = await backend.decide_action("xml", "summary", "app")
    assert action.action_type == "done"


@pytest.mark.asyncio
async def test_mock_backend_no_visual_issues() -> None:
    backend = MockBackend()
    issues = await backend.analyze_screenshot("b64", "xml", "context")
    assert issues == []
