"""Screen state extraction from Appium driver."""

import base64
import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScreenElement:
    """A UI element extracted from the accessibility tree."""

    resource_id: str
    text: str
    content_desc: str
    class_name: str
    bounds: tuple[int, int, int, int]  # x1, y1, x2, y2
    clickable: bool
    scrollable: bool
    editable: bool


def get_screen_xml(driver) -> str:
    """Get the accessibility tree XML from Appium driver."""
    return driver.page_source


def take_screenshot_b64(driver, save_path: Path | None = None) -> str:
    """Take a screenshot, return base64-encoded PNG.

    Optionally saves to disk at save_path.
    """
    # driver.get_screenshot_as_base64() returns base64 string
    b64 = driver.get_screenshot_as_base64()
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        img_bytes = base64.b64decode(b64)
        save_path.write_bytes(img_bytes)
    return b64


def _parse_bounds(bounds_str: str) -> tuple[int, int, int, int]:
    """Parse UiAutomator2 bounds string '[x1,y1][x2,y2]' into tuple."""
    match = re.findall(r"\[(\d+),(\d+)\]", bounds_str)
    if len(match) != 2:
        return (0, 0, 0, 0)
    x1, y1 = int(match[0][0]), int(match[0][1])
    x2, y2 = int(match[1][0]), int(match[1][1])
    return (x1, y1, x2, y2)


def parse_screen_elements(xml_str: str) -> list[ScreenElement]:
    """Parse accessibility tree XML into structured elements.

    Extracts all elements with resource-id, text, or content-desc.
    """
    elements: list[ScreenElement] = []
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return elements

    for node in root.iter():
        resource_id = node.get("resource-id", "")
        text = node.get("text", "")
        content_desc = node.get("content-desc", "")
        class_name = node.get("class", "")
        bounds_str = node.get("bounds", "")

        # Skip nodes with no identifying info
        if not resource_id and not text and not content_desc:
            continue

        clickable = node.get("clickable", "false") == "true"
        scrollable = node.get("scrollable", "false") == "true"
        editable = class_name.endswith("EditText")

        elements.append(ScreenElement(
            resource_id=resource_id,
            text=text,
            content_desc=content_desc,
            class_name=class_name,
            bounds=_parse_bounds(bounds_str),
            clickable=clickable,
            scrollable=scrollable,
            editable=editable,
        ))

    return elements


def compute_screen_signature(xml_str: str) -> str:
    """Compute a stable hash signature for a screen.

    Hashes the sorted set of (resource-id, text, class) tuples.
    This produces a stable identifier even if scroll positions change.
    """
    elements = parse_screen_elements(xml_str)
    # Use frozenset of identifying tuples for order-independence
    id_tuples = sorted({(e.resource_id, e.text, e.class_name) for e in elements})
    content = str(id_tuples).encode()
    return hashlib.sha256(content).hexdigest()[:16]
