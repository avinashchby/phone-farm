# tests/qa_agent/test_accessibility_free.py
from phone_farm.qa_agent.accessibility import audit_screen, AccessibilityIssue

LOGIN_XML = """<?xml version="1.0"?>
<hierarchy>
  <android.widget.FrameLayout bounds="[0,0][1080,2400]">
    <android.widget.ImageView bounds="[0,0][100,100]" clickable="false" content-desc="" />
    <android.widget.Button bounds="[0,0][30,30]" clickable="true" text="" content-desc="" />
    <android.widget.Button bounds="[0,200][200,280]" clickable="true" text="Login" content-desc="" />
    <android.widget.EditText bounds="[0,300][400,380]" clickable="true" text="" content-desc="Email" />
  </android.widget.FrameLayout>
</hierarchy>"""

CLEAN_XML = """<?xml version="1.0"?>
<hierarchy>
  <android.widget.FrameLayout bounds="[0,0][1080,2400]">
    <android.widget.Button bounds="[0,0][200,100]" clickable="true" text="Submit" content-desc="Submit button" />
    <android.widget.ImageView bounds="[0,200][200,400]" content-desc="App logo" clickable="false" />
  </android.widget.FrameLayout>
</hierarchy>"""

def test_no_issues_on_clean_screen():
    issues = audit_screen(CLEAN_XML)
    assert issues == []

def test_detects_small_touch_target():
    issues = audit_screen(LOGIN_XML)
    rules = [i.rule for i in issues]
    assert "small-touch-target" in rules

def test_detects_unlabeled_image():
    issues = audit_screen(LOGIN_XML)
    rules = [i.rule for i in issues]
    assert "missing-image-description" in rules

def test_detects_empty_button():
    issues = audit_screen(LOGIN_XML)
    rules = [i.rule for i in issues]
    assert "empty-button" in rules

def test_returns_list_of_accessibility_issues():
    issues = audit_screen(LOGIN_XML)
    for issue in issues:
        assert isinstance(issue, AccessibilityIssue)
        assert issue.rule
        assert issue.severity in ("high", "medium", "low")

def test_invalid_xml_returns_empty():
    assert audit_screen("not xml") == []
