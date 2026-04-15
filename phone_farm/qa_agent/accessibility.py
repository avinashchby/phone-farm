# phone_farm/qa_agent/accessibility.py
"""Basic accessibility audit rules for the free package.

Checks 4 rules: missing content-desc on interactive elements,
small touch targets, empty buttons, unlabeled images.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class AccessibilityIssue:
    """A single accessibility finding."""

    rule: str
    severity: str  # "high", "medium", "low"
    element: str
    description: str
    suggestion: str


def audit_screen(xml_str: str) -> list[AccessibilityIssue]:
    """Audit a screen's XML accessibility tree for basic issues.

    Rules checked: missing-content-description, small-touch-target,
    empty-button, missing-image-description.
    Returns empty list on parse error.
    """
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []

    issues: list[AccessibilityIssue] = []
    for node in root.iter():
        issues.extend(_check_node(node))
    return issues


def _element_id(node: ET.Element) -> str:
    return node.get("resource-id") or node.get("class", "unknown")


def _check_node(node: ET.Element) -> list[AccessibilityIssue]:
    issues: list[AccessibilityIssue] = []
    # Android XML uses the tag as the widget class name; fall back to class attr.
    class_name = node.tag or node.get("class", "")
    text = node.get("text", "")
    content_desc = node.get("content-desc", "")
    clickable = node.get("clickable", "false") == "true"
    bounds_str = node.get("bounds", "")
    elem = _element_id(node)

    if clickable and not content_desc and not text and "Button" not in class_name:
        issues.append(AccessibilityIssue(
            rule="missing-content-description",
            severity="high",
            element=elem,
            description="Interactive element has no content description or text",
            suggestion="Add android:contentDescription attribute",
        ))

    if "ImageView" in class_name and not content_desc:
        issues.append(AccessibilityIssue(
            rule="missing-image-description",
            severity="medium",
            element=elem,
            description="ImageView has no content description",
            suggestion="Add android:contentDescription or mark as decorative",
        ))

    if clickable and bounds_str:
        size = _parse_bounds(bounds_str)
        if size and (size[0] < 75 or size[1] < 75):
            issues.append(AccessibilityIssue(
                rule="small-touch-target",
                severity="medium",
                element=elem,
                description=f"Touch target {size[0]}x{size[1]}px is below 48dp minimum",
                suggestion="Increase touch target to at least 48x48dp",
            ))

    if "Button" in class_name and not text and not content_desc:
        issues.append(AccessibilityIssue(
            rule="empty-button",
            severity="high",
            element=elem,
            description="Button has no text or content description",
            suggestion="Add text or android:contentDescription to button",
        ))

    return issues


def _parse_bounds(bounds: str) -> tuple[int, int] | None:
    """Parse '[x1,y1][x2,y2]' bounds string into (width, height)."""
    try:
        parts = bounds.replace("][", ",").strip("[]").split(",")
        x1, y1, x2, y2 = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        return abs(x2 - x1), abs(y2 - y1)
    except (ValueError, IndexError):
        return None
