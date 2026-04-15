# tests/test_scoring.py
from phone_farm.scoring import compute_score
from phone_farm.qa_agent.bug_report import Bug, QAReport

def _make_report(bugs=None, unique_screens=10):
    return QAReport(
        bugs=bugs or [],
        app_description="Test App",
        apk_path="test.apk",
        start_time="2026-01-01T00:00:00",
        end_time="2026-01-01T00:05:00",
        total_actions=50,
        unique_screens=unique_screens,
        coverage_summary="10 screens explored",
    )

def _bug(category, severity="medium"):
    return Bug(
        severity=severity,
        category=category,
        title="Test",
        description="Desc",
        steps_to_reproduce=[],
        screen_signature="screen1",
    )

def test_perfect_score():
    report = _make_report(unique_screens=10)
    result = compute_score(report, accessibility_issues=0)
    assert result["score"] == 100
    assert result["grade"] == "A"

def test_zero_score():
    bugs = (
        [_bug("crash", "critical")] * 3
        + [_bug("anr")] * 2
        + [_bug("visual")] * 6
        + [_bug("accessibility")] * 9
    )
    report = _make_report(bugs=bugs, unique_screens=1)
    result = compute_score(report, accessibility_issues=9)
    assert result["score"] == 0
    assert result["grade"] == "F"

def test_crash_weight():
    report = _make_report(bugs=[_bug("crash", "critical")], unique_screens=10)
    result = compute_score(report, accessibility_issues=0)
    assert result["breakdown"]["crashes"] == 25
    assert result["score"] == 85  # 25+20+15+15+10

def test_grade_boundaries():
    from phone_farm.scoring import _grade
    for score, expected in [(95, "A"), (85, "B"), (70, "C"), (55, "D"), (40, "F")]:
        assert _grade(score) == expected

def test_coverage_weight_low():
    report = _make_report(unique_screens=2)
    result = compute_score(report, accessibility_issues=0)
    assert result["breakdown"]["coverage"] == 3
