# phone_farm/report_renderer.py
"""Standalone HTML report renderer for QA audit results.

Produces a single self-contained HTML file with inline CSS.
No external dependencies required to open in a browser.
"""
from __future__ import annotations

import base64
from pathlib import Path

from phone_farm.qa_agent.accessibility import AccessibilityIssue
from phone_farm.qa_agent.bug_report import QAReport

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f5f5f5; color: #333; }
.header { background: #1a1a2e; color: white; padding: 24px 40px; }
.header h1 { font-size: 1.6rem; font-weight: 700; }
.header .meta { font-size: 0.85rem; color: #aaa; margin-top: 4px; }
.container { max-width: 960px; margin: 0 auto; padding: 32px 20px; }
.score-section { display: flex; align-items: center; gap: 32px;
                 background: white; border-radius: 12px;
                 padding: 24px 32px; margin-bottom: 24px;
                 box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.score-badge { width: 90px; height: 90px; border-radius: 50%;
               display: flex; flex-direction: column; align-items: center;
               justify-content: center; font-weight: 800; flex-shrink: 0; }
.score-badge.green { background: #d4edda; color: #155724; border: 4px solid #28a745; }
.score-badge.yellow { background: #fff3cd; color: #856404; border: 4px solid #ffc107; }
.score-badge.red { background: #f8d7da; color: #721c24; border: 4px solid #dc3545; }
.score-badge .num { font-size: 1.8rem; line-height: 1; }
.score-badge .grade { font-size: 1rem; }
.score-summary h2 { font-size: 1.2rem; margin-bottom: 6px; }
.score-summary p { color: #555; line-height: 1.5; }
.card { background: white; border-radius: 12px; padding: 24px 32px;
        margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.card h2 { font-size: 1.1rem; font-weight: 700; margin-bottom: 16px;
           padding-bottom: 8px; border-bottom: 2px solid #eee; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 0.8rem; text-transform: uppercase;
     color: #888; padding: 8px 12px; border-bottom: 2px solid #eee; }
td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; font-size: 0.9rem; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
         font-size: 0.75rem; font-weight: 600; }
.badge-critical { background: #f8d7da; color: #721c24; }
.badge-high { background: #ffe5d0; color: #7d3200; }
.badge-medium { background: #fff3cd; color: #856404; }
.badge-low { background: #d4edda; color: #155724; }
details { margin-top: 4px; }
details summary { cursor: pointer; font-size: 0.85rem; color: #0066cc; }
details pre { background: #1a1a1a; color: #f8f8f8; padding: 12px;
              border-radius: 6px; font-size: 0.8rem; overflow-x: auto;
              margin-top: 8px; white-space: pre-wrap; }
.gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.gallery-item img { width: 100%; border-radius: 6px; cursor: pointer; }
.gallery-item .label { font-size: 0.75rem; color: #666; margin-top: 4px; text-align: center; }
.lightbox-toggle { display: none; }
.lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.85); z-index: 999; align-items: center; justify-content: center; }
.lightbox-toggle:checked ~ .lightbox { display: flex; }
.lightbox img { max-width: 90%; max-height: 90%; border-radius: 8px; cursor: pointer; }
.footer { text-align: center; padding: 24px; color: #999; font-size: 0.8rem; }
@media print {
  .header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .score-badge { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  details { display: block; }
  details summary { display: none; }
}
"""


def _score_color(score: int) -> str:
    if score >= 80:
        return "green"
    if score >= 50:
        return "yellow"
    return "red"


def _severity_badge(severity: str) -> str:
    return f'<span class="badge badge-{severity}">{severity}</span>'


def _embed_image(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    data = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" style="max-width:80px;border-radius:4px;" />'


def _header_section(report: QAReport, client_name: str) -> str:
    client = f" — {client_name}" if client_name else ""
    apk = Path(report.apk_path).name
    return (
        f'<div class="header">'
        f'<h1>Phone Farm QA Report{client}</h1>'
        f'<div class="meta">{apk} &nbsp;·&nbsp; {report.start_time[:10]}</div>'
        f'</div>'
    )


def _score_section(report: QAReport, score: dict) -> str:
    color = _score_color(score["score"])
    n_critical = sum(1 for b in report.bugs if b.severity == "critical")
    summary = (
        f"{Path(report.apk_path).name} scored {score['score']}/100. "
        f"{len(report.bugs)} bugs found ({n_critical} critical). "
        f"{report.coverage_summary}."
    )
    return (
        f'<div class="score-section">'
        f'<div class="score-badge {color}">'
        f'<span class="num">{score["score"]}</span>'
        f'<span class="grade">{score["grade"]}</span>'
        f'</div>'
        f'<div class="score-summary"><h2>Executive Summary</h2><p>{summary}</p></div>'
        f'</div>'
    )


def _bugs_section(report: QAReport) -> str:
    if not report.bugs:
        return '<div class="card"><h2>Bugs Found</h2><p>No bugs found.</p></div>'
    rows = "".join(_bug_row(i, bug) for i, bug in enumerate(report.bugs, 1))
    return (
        f'<div class="card"><h2>Bugs Found ({len(report.bugs)})</h2>'
        f'<table><thead><tr><th>#</th><th>Severity</th><th>Category</th>'
        f'<th>Details</th><th>Screenshot</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )


def _bug_row(i: int, bug) -> str:
    img = _embed_image(bug.screenshot_path)
    steps = "".join(f"<li>{s}</li>" for s in bug.steps_to_reproduce)
    logcat = (
        f"<details><summary>Logcat</summary><pre>{bug.logcat_snippet}</pre></details>"
        if bug.logcat_snippet
        else ""
    )
    return (
        f"<tr><td>{i}</td><td>{_severity_badge(bug.severity)}</td>"
        f"<td>{bug.category}</td>"
        f"<td><strong>{bug.title}</strong><br/><small>{bug.description}</small>"
        f"<details><summary>Reproduction steps</summary><ol>{steps}</ol></details>"
        f"{logcat}</td><td>{img}</td></tr>"
    )


def _a11y_section(issues: list[AccessibilityIssue] | None) -> str:
    if not issues:
        return '<div class="card"><h2>Accessibility</h2><p>No accessibility issues found.</p></div>'
    rows = "".join(
        f"<tr><td>{i.rule}</td><td>{_severity_badge(i.severity)}</td>"
        f"<td>{i.element}</td><td>{i.suggestion}</td></tr>"
        for i in issues
    )
    return (
        f'<div class="card"><h2>Accessibility ({len(issues)} issues)</h2>'
        f"<table><thead><tr><th>Rule</th><th>Severity</th><th>Element</th>"
        f"<th>Suggestion</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _screenshot_gallery(screenshots_dir: Path | None) -> str:
    """Build a grid gallery of all screenshots in the directory.

    Each screenshot gets a thumbnail. Uses pure CSS lightbox (checkbox hack)
    for click-to-enlarge — no JS needed.
    """
    if not screenshots_dir or not Path(screenshots_dir).is_dir():
        return '<div class="card"><h2>Screenshots</h2><p>No screenshots captured.</p></div>'
    pngs = sorted(Path(screenshots_dir).glob("*.png"))
    if not pngs:
        return '<div class="card"><h2>Screenshots</h2><p>No screenshots captured.</p></div>'
    items = "".join(_gallery_item(i, p) for i, p in enumerate(pngs))
    return (
        f'<div class="card"><h2>Screenshots ({len(pngs)})</h2>'
        f'<div class="gallery">{items}</div></div>'
    )


def _gallery_item(i: int, p: Path) -> str:
    label = p.stem.replace("-", " ").replace("_", " ")
    data = base64.b64encode(p.read_bytes()).decode()
    cb_id = f"ss-{i}"
    return (
        f'<div class="gallery-item">'
        f'<label for="{cb_id}"><img src="data:image/png;base64,{data}" alt="{label}" /></label>'
        f'<input type="checkbox" id="{cb_id}" class="lightbox-toggle" />'
        f'<div class="lightbox"><label for="{cb_id}">'
        f'<img src="data:image/png;base64,{data}" alt="{label}" /></label></div>'
        f'<div class="label">{label}</div></div>'
    )


def _metadata_section(report: QAReport) -> str:
    apk = Path(report.apk_path).name
    rows = (
        f"<tr><td><strong>APK</strong></td><td>{apk}</td></tr>"
        f"<tr><td><strong>Started</strong></td><td>{report.start_time}</td></tr>"
        f"<tr><td><strong>Finished</strong></td><td>{report.end_time}</td></tr>"
        f"<tr><td><strong>Total Actions</strong></td><td>{report.total_actions}</td></tr>"
        f"<tr><td><strong>Unique Screens</strong></td><td>{report.unique_screens}</td></tr>"
        f"<tr><td><strong>Coverage</strong></td><td>{report.coverage_summary}</td></tr>"
    )
    return (
        f'<div class="card"><h2>Run Metadata</h2>'
        f"<table><tbody>{rows}</tbody></table></div>"
    )


def render_html_report(
    report: QAReport,
    score: dict,
    screenshots_dir: Path | None = None,
    accessibility_issues: list[AccessibilityIssue] | None = None,
    client_name: str = "",
    auditor_name: str = "",
) -> str:
    """Render a standalone HTML QA report.

    Returns a complete HTML string with all CSS inlined.
    No external dependencies — safe to email as a single file.
    """
    footer_extra = f"Auditor: {auditor_name} &nbsp;·&nbsp; " if auditor_name else ""
    body = "".join([
        _header_section(report, client_name),
        '<div class="container">',
        _score_section(report, score),
        _bugs_section(report),
        _screenshot_gallery(screenshots_dir),
        _a11y_section(accessibility_issues),
        _metadata_section(report),
        "</div>",
    ])
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "<title>Phone Farm QA Report</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n"
        f"<body>\n{body}\n"
        f'<div class="footer">{footer_extra}Generated by <strong>Phone Farm</strong></div>\n'
        "</body>\n</html>"
    )
