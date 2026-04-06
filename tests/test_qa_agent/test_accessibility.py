"""Tests for accessibility audit."""

from phone_farm.qa_agent.accessibility import audit_screen, format_audit_report, AccessibilityIssue

SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <android.widget.FrameLayout bounds="[0,0][1080,2400]">
    <android.widget.Button resource-id="com.app:id/btn_login" text="Login"
        class="android.widget.Button" bounds="[100,500][300,600]"
        clickable="true" content-desc="" />
    <android.widget.ImageButton resource-id="com.app:id/btn_menu"
        class="android.widget.ImageButton" bounds="[0,0][80,80]"
        clickable="true" text="" content-desc="" />
    <android.widget.ImageView resource-id="com.app:id/logo"
        class="android.widget.ImageView" bounds="[200,100][400,300]"
        clickable="false" text="" content-desc="" />
    <android.widget.Button resource-id="com.app:id/btn_ok" text=""
        class="android.widget.Button" bounds="[100,700][200,750]"
        clickable="true" content-desc="" />
    <android.widget.EditText resource-id="com.app:id/input_email" text=""
        class="android.widget.EditText" bounds="[100,400][900,480]"
        clickable="true" content-desc="Email input" />
  </android.widget.FrameLayout>
</hierarchy>
"""


def test_audit_finds_missing_content_description() -> None:
    issues = audit_screen(SAMPLE_XML)
    missing_desc = [i for i in issues if i.rule == "missing-content-description"]
    # btn_menu (ImageButton) has no text or content-desc and is clickable
    assert len(missing_desc) >= 1


def test_audit_finds_unlabeled_image() -> None:
    issues = audit_screen(SAMPLE_XML)
    unlabeled = [i for i in issues if i.rule == "unlabeled-image"]
    assert len(unlabeled) >= 1
    assert any("logo" in i.element for i in unlabeled)


def test_audit_finds_small_touch_target() -> None:
    issues = audit_screen(SAMPLE_XML)
    small = [i for i in issues if i.rule == "small-touch-target"]
    # btn_menu is 80x80px which at 420dpi is ~30dp — below 48dp minimum
    # btn_ok is 100x50px
    assert len(small) >= 1


def test_audit_finds_empty_button() -> None:
    issues = audit_screen(SAMPLE_XML)
    empty = [i for i in issues if i.rule == "empty-button"]
    # btn_ok and btn_menu have no text and no content-desc
    assert len(empty) >= 1


def test_audit_skips_valid_elements() -> None:
    issues = audit_screen(SAMPLE_XML)
    # btn_login has text="Login" so should NOT be flagged as missing-content-description
    login_issues = [i for i in issues if "btn_login" in i.element and i.rule == "missing-content-description"]
    assert len(login_issues) == 0


def test_audit_handles_invalid_xml() -> None:
    issues = audit_screen("not valid xml <<<")
    assert issues == []


def test_format_audit_report_with_issues() -> None:
    issues = [
        AccessibilityIssue("missing-content-description", "high", "btn_menu", "No desc", "Add desc"),
    ]
    text = format_audit_report(issues)
    assert "1 accessibility issue" in text
    assert "HIGH" in text


def test_format_audit_report_no_issues() -> None:
    text = format_audit_report([])
    assert "No accessibility issues" in text
