# tests/test_report_renderer.py
import struct
import zlib
from phone_farm.report_renderer import render_html_report
from phone_farm.scoring import compute_score
from phone_farm.qa_agent.bug_report import Bug, QAReport
from phone_farm.qa_agent.accessibility import AccessibilityIssue


def _sample_report():
    bugs = [
        Bug(
            severity="critical",
            category="crash",
            title="NullPointerException in MainActivity",
            description="App crashes on login",
            steps_to_reproduce=["Open app", "Tap Login"],
            screen_signature="main",
            logcat_snippet="FATAL: NullPointerException",
        ),
        Bug(
            severity="low",
            category="visual",
            title="Button overlaps title",
            description="Layout issue on small screens",
            steps_to_reproduce=["Open app"],
            screen_signature="main",
        ),
    ]
    return QAReport(
        bugs=bugs,
        app_description="Test App v1.0",
        apk_path="test-app.apk",
        start_time="2026-01-01T00:00:00",
        end_time="2026-01-01T00:05:00",
        total_actions=30,
        unique_screens=8,
        coverage_summary="8 screens explored",
    )


def test_renders_html_string():
    report = _sample_report()
    score = compute_score(report)
    html = render_html_report(report, score)
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_contains_score_badge():
    report = _sample_report()
    score = compute_score(report)
    html = render_html_report(report, score)
    assert str(score["score"]) in html
    assert score["grade"] in html


def test_contains_bug_table():
    report = _sample_report()
    score = compute_score(report)
    html = render_html_report(report, score)
    assert "NullPointerException" in html
    assert "Button overlaps title" in html


def test_contains_all_sections():
    report = _sample_report()
    score = compute_score(report)
    html = render_html_report(report, score)
    for section in ["Executive Summary", "Bugs Found", "Accessibility", "Run Metadata"]:
        assert section in html


def test_empty_bugs_renders():
    report = QAReport(
        bugs=[],
        app_description="Clean App",
        apk_path="clean.apk",
        start_time="2026-01-01T00:00:00",
        end_time="2026-01-01T00:01:00",
        total_actions=10,
        unique_screens=3,
        coverage_summary="3 screens",
    )
    score = compute_score(report)
    html = render_html_report(report, score)
    assert "No bugs found" in html


def test_client_name_appears():
    report = _sample_report()
    score = compute_score(report)
    html = render_html_report(report, score, client_name="Acme Corp")
    assert "Acme Corp" in html


def test_accessibility_issues_appear():
    report = _sample_report()
    score = compute_score(report)
    a11y = [AccessibilityIssue(
        rule="empty-button", severity="high",
        element="btn_login", description="Button has no text",
        suggestion="Add contentDescription",
    )]
    html = render_html_report(report, score, accessibility_issues=a11y)
    assert "empty-button" in html
    assert "btn_login" in html


def _mini_png() -> bytes:
    """Generate a minimal valid 1x1 PNG."""
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
    ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
    raw = zlib.compress(b'\x00\x00\x00\x00')
    idat_crc = zlib.crc32(b'IDAT' + raw) & 0xffffffff
    idat = struct.pack('>I', len(raw)) + b'IDAT' + raw + struct.pack('>I', idat_crc)
    iend_crc = zlib.crc32(b'IEND') & 0xffffffff
    iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
    return sig + ihdr + idat + iend


def test_screenshot_gallery_renders(tmp_path):
    """Gallery renders when screenshots_dir has PNGs."""
    ss_dir = tmp_path / "screenshots"
    ss_dir.mkdir()
    (ss_dir / "step-001.png").write_bytes(_mini_png())
    (ss_dir / "step-002.png").write_bytes(_mini_png())

    report = _sample_report()
    score = compute_score(report)
    html = render_html_report(report, score, screenshots_dir=ss_dir)
    assert "Screenshots (2)" in html
    assert "gallery" in html


def test_screenshot_gallery_empty_without_dir():
    report = _sample_report()
    score = compute_score(report)
    html = render_html_report(report, score, screenshots_dir=None)
    assert "No screenshots captured" in html
