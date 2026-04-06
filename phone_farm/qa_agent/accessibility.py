"""Accessibility audit from Android accessibility tree XML."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class AccessibilityIssue:
    """A single accessibility issue found."""

    rule: str
    severity: str  # "high", "medium", "low"
    element: str
    description: str
    suggestion: str


def audit_screen(xml_str: str) -> list[AccessibilityIssue]:
    """Audit a screen's accessibility tree for common issues.

    Checks for:
    - Missing content descriptions on interactive elements
    - Small touch targets (< 48dp)
    - Missing text on buttons
    - Unlabeled images
    """
    issues: list[AccessibilityIssue] = []

    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return issues

    for node in root.iter():
        resource_id = node.get("resource-id", "")
        text = node.get("text", "")
        content_desc = node.get("content-desc", "")
        class_name = node.get("class", "")
        clickable = node.get("clickable", "false") == "true"
        bounds_str = node.get("bounds", "")

        element_id = resource_id or text or class_name

        # Rule 1: Interactive elements without content description
        if clickable and not content_desc and not text:
            issues.append(AccessibilityIssue(
                rule="missing-content-description",
                severity="high",
                element=element_id,
                description=f"Interactive element '{element_id}' has no content description or text",
                suggestion="Add android:contentDescription to make this element accessible to screen readers",
            ))

        # Rule 2: ImageView without content description
        if "ImageView" in class_name and not content_desc:
            issues.append(AccessibilityIssue(
                rule="unlabeled-image",
                severity="medium",
                element=element_id,
                description=f"ImageView '{element_id}' has no content description",
                suggestion="Add android:contentDescription or set importantForAccessibility='no' if decorative",
            ))

        # Rule 3: Small touch targets
        # At ~420dpi (Pixel 6), 48dp ≈ 75px. We flag targets below this threshold.
        _MIN_TOUCH_PX = 75
        if clickable and bounds_str:
            size = _parse_touch_target_size(bounds_str)
            if size and (size[0] < _MIN_TOUCH_PX or size[1] < _MIN_TOUCH_PX):
                issues.append(AccessibilityIssue(
                    rule="small-touch-target",
                    severity="medium",
                    element=element_id,
                    description=f"Touch target '{element_id}' is {size[0]}x{size[1]}dp (minimum 48x48dp)",
                    suggestion="Increase the element's size or add padding to meet the 48dp minimum",
                ))

        # Rule 4: Button without text or description
        if "Button" in class_name and not text and not content_desc:
            issues.append(AccessibilityIssue(
                rule="empty-button",
                severity="high",
                element=element_id,
                description=f"Button '{element_id}' has no text or content description",
                suggestion="Add text or contentDescription to the button",
            ))

    return issues


def _parse_touch_target_size(bounds_str: str) -> tuple[int, int] | None:
    """Parse bounds string and return (width, height) in pixels.

    Bounds format: '[x1,y1][x2,y2]'
    Note: returns pixels, not dp. At 420dpi (Pixel 6), 48dp = ~75px.
    """
    match = re.findall(r"\[(\d+),(\d+)\]", bounds_str)
    if len(match) != 2:
        return None
    x1, y1 = int(match[0][0]), int(match[0][1])
    x2, y2 = int(match[1][0]), int(match[1][1])
    width = x2 - x1
    height = y2 - y1
    return (width, height)


def format_audit_report(issues: list[AccessibilityIssue]) -> str:
    """Format accessibility issues as readable text."""
    if not issues:
        return "No accessibility issues found."

    lines = [f"Found {len(issues)} accessibility issue(s):", ""]
    for issue in issues:
        lines.append(f"[{issue.severity.upper()}] {issue.rule}")
        lines.append(f"  Element: {issue.element}")
        lines.append(f"  {issue.description}")
        lines.append(f"  Fix: {issue.suggestion}")
        lines.append("")
    return "\n".join(lines)
