# phone_farm/scoring.py
"""Production Readiness Score computation for QA reports."""
from __future__ import annotations

from phone_farm.qa_agent.bug_report import QAReport


def compute_score(report: QAReport, accessibility_issues: int = 0) -> dict:
    """Compute a 0-100 Production Readiness Score from a QAReport.

    Weights: crashes 40, ANRs 20, visual bugs 15, accessibility 15, coverage 10.
    Returns {"score": int, "grade": str, "breakdown": dict}.
    """
    crashes = sum(1 for b in report.bugs if b.category == "crash")
    anrs = sum(1 for b in report.bugs if b.category == "anr")
    visual = sum(1 for b in report.bugs if b.category == "visual")

    crash_pts = _crash_points(crashes)
    anr_pts = _anr_points(anrs)
    visual_pts = _visual_points(visual)
    a11y_pts = _a11y_points(accessibility_issues)
    coverage_pts = _coverage_points(report.unique_screens)

    score = crash_pts + anr_pts + visual_pts + a11y_pts + coverage_pts
    return {
        "score": score,
        "grade": _grade(score),
        "breakdown": {
            "crashes": crash_pts,
            "anrs": anr_pts,
            "visual": visual_pts,
            "accessibility": a11y_pts,
            "coverage": coverage_pts,
        },
    }


def _crash_points(n: int) -> int:
    if n == 0:
        return 40
    if n == 1:
        return 25
    if n == 2:
        return 15
    return 0


def _anr_points(n: int) -> int:
    if n == 0:
        return 20
    if n == 1:
        return 10
    return 0


def _visual_points(n: int) -> int:
    if n == 0:
        return 15
    if n <= 2:
        return 10
    if n <= 5:
        return 5
    return 0


def _a11y_points(n: int) -> int:
    if n == 0:
        return 15
    if n <= 3:
        return 10
    if n <= 8:
        return 5
    return 0


def _coverage_points(screens: int) -> int:
    if screens >= 10:
        return 10
    if screens >= 5:
        return 7
    if screens >= 2:
        return 3
    return 0


def _grade(score: int) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 65:
        return "C"
    if score >= 50:
        return "D"
    return "F"
