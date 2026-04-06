"""Tests for screen state extraction."""

from pathlib import Path
from unittest.mock import MagicMock

from phone_farm.qa_agent.state import (
    get_screen_xml,
    take_screenshot_b64,
    parse_screen_elements,
    compute_screen_signature,
    _parse_bounds,
)

SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <android.widget.FrameLayout bounds="[0,0][1080,2340]">
    <android.widget.Button resource-id="com.app:id/btn_login" text="Login"
        class="android.widget.Button" bounds="[100,500][300,600]"
        clickable="true" scrollable="false" content-desc="Login button" />
    <android.widget.EditText resource-id="com.app:id/input_email" text=""
        class="android.widget.EditText" bounds="[100,300][900,400]"
        clickable="true" scrollable="false" content-desc="Email input" />
    <android.widget.ScrollView resource-id="com.app:id/scroll"
        class="android.widget.ScrollView" bounds="[0,0][1080,2340]"
        clickable="false" scrollable="true" text="" content-desc="" />
    <android.widget.TextView text="Welcome" class="android.widget.TextView"
        bounds="[100,100][500,200]" clickable="false" scrollable="false"
        resource-id="" content-desc="" />
  </android.widget.FrameLayout>
</hierarchy>
"""


def test_parse_bounds() -> None:
    assert _parse_bounds("[100,500][300,600]") == (100, 500, 300, 600)
    assert _parse_bounds("invalid") == (0, 0, 0, 0)
    assert _parse_bounds("[0,0][1080,2340]") == (0, 0, 1080, 2340)


def test_parse_screen_elements_extracts_all() -> None:
    elements = parse_screen_elements(SAMPLE_XML)
    # Should find: button, edittext, scrollview, textview (all have some id/text/desc)
    assert len(elements) >= 3
    resource_ids = {e.resource_id for e in elements if e.resource_id}
    assert "com.app:id/btn_login" in resource_ids
    assert "com.app:id/input_email" in resource_ids


def test_parse_screen_elements_detects_clickable() -> None:
    elements = parse_screen_elements(SAMPLE_XML)
    btn = next(e for e in elements if e.resource_id == "com.app:id/btn_login")
    assert btn.clickable is True
    assert btn.text == "Login"


def test_parse_screen_elements_detects_editable() -> None:
    elements = parse_screen_elements(SAMPLE_XML)
    edit = next(e for e in elements if e.resource_id == "com.app:id/input_email")
    assert edit.editable is True


def test_parse_screen_elements_detects_scrollable() -> None:
    elements = parse_screen_elements(SAMPLE_XML)
    scroll = next(e for e in elements if e.resource_id == "com.app:id/scroll")
    assert scroll.scrollable is True


def test_compute_screen_signature_is_stable() -> None:
    sig1 = compute_screen_signature(SAMPLE_XML)
    sig2 = compute_screen_signature(SAMPLE_XML)
    assert sig1 == sig2
    assert len(sig1) == 16


def test_compute_screen_signature_differs_for_different_screens() -> None:
    other_xml = SAMPLE_XML.replace("Login", "Register")
    sig1 = compute_screen_signature(SAMPLE_XML)
    sig2 = compute_screen_signature(other_xml)
    assert sig1 != sig2


def test_get_screen_xml_calls_page_source() -> None:
    driver = MagicMock()
    driver.page_source = SAMPLE_XML
    result = get_screen_xml(driver)
    assert result == SAMPLE_XML


def test_take_screenshot_b64_saves_to_disk(tmp_path: Path) -> None:
    import base64
    driver = MagicMock()
    # Return a small valid base64 PNG-like string
    fake_b64 = base64.b64encode(b"fake-png-data").decode()
    driver.get_screenshot_as_base64.return_value = fake_b64
    save_path = tmp_path / "screenshots" / "test.png"
    result = take_screenshot_b64(driver, save_path=save_path)
    assert result == fake_b64
    assert save_path.exists()
    assert save_path.read_bytes() == b"fake-png-data"


def test_parse_invalid_xml_returns_empty() -> None:
    elements = parse_screen_elements("not valid xml <<<")
    assert elements == []
