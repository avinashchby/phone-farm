# Phone Farm

### The Lighthouse for Android Apps

**One command. One score. One report. Open source.**

[![PyPI](https://img.shields.io/pypi/v/phone-farm)](https://pypi.org/project/phone-farm/)
[![Downloads](https://img.shields.io/pypi/dm/phone-farm)](https://pypi.org/project/phone-farm/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-193%20passing-brightgreen)](https://github.com/avinashchby/phone-farm/actions)
[![GitHub stars](https://img.shields.io/github/stars/avinashchby/phone-farm)](https://github.com/avinashchby/phone-farm)

Phone Farm is an **automated Android QA audit** tool that gives your APK a **Production Readiness Score** (0–100) — like Google Lighthouse, but for mobile apps. It boots an emulator, explores your app, catches crashes, checks accessibility, and generates a client-ready HTML report. Everything runs locally. No cloud. No accounts. No monthly bill.

```bash
pip install phone-farm
phone-farm audit ./my-app.apk
```

```
Score: 72/100 (C)
Bugs: 5 (1 critical, 2 high, 2 medium)
HTML report: ./audit-20260415-143022/report.html
```

<!-- screenshot of HTML report -->

---

## Who Is This For?

### Vibe Coders & Indie Developers

Built your app with Lovable, Bolt, or Cursor? Run `phone-farm audit` before you ship. It's free, it takes 5 minutes, and it'll catch the crashes your AI coding tool left behind.

### QA Consultants & Freelancers

Turn Phone Farm into a revenue stream. Run `phone-farm audit client-app.apk --client-name "Acme Corp" --auditor-name "Your Name"` and email the branded HTML report. Charge $99 for automated scans, $499 for human-reviewed audits.

### Development Teams

Add Phone Farm to your CI/CD pipeline. Every PR gets a Production Readiness Score. Crashes block the merge. No new SaaS subscription required — runs on your GitHub Actions runner.

### Android App Testing Services

If you provide **android app testing services**, Phone Farm gives you a professional audit toolkit — production readiness scoring, accessibility compliance checks, crash detection with logcat analysis, and branded HTML reports ready to deliver to clients.

---

## What You Get

### Production Readiness Score (0–100)

Every audit produces a weighted score across 5 dimensions:

| Dimension | Weight | What It Checks |
|-----------|--------|---------------|
| Crashes | 40% | App crashes detected via logcat monitoring |
| ANRs | 20% | Application Not Responding events |
| Visual Bugs | 15% | Overlapping elements, broken layouts, truncated text |
| Accessibility | 15% | Missing labels, small touch targets, empty buttons |
| Coverage | 10% | Number of unique screens explored |

**Grades:** A (90+), B (80–89), C (65–79), D (50–64), F (<50)

### Client-Ready HTML Report

A single standalone HTML file — no dependencies, no server needed. Open it in any browser or email it directly.

- Score badge with color-coded grade
- Executive summary (auto-generated)
- Bug table with severity, category, reproduction steps, logcat snippets
- Accessibility audit results with WCAG-aligned rules
- Screenshot gallery with click-to-enlarge lightbox
- Run metadata (APK name, duration, screens explored, mode)
- Print-friendly — works with Ctrl+P for PDF export
- Custom branding: `--client-name` and `--auditor-name` flags

### What It Catches

- **Crashes & ANRs** — logcat monitoring after every action
- **Accessibility issues** — missing content descriptions, small touch targets (<48dp), empty buttons, unlabeled images
- **Login screens** — auto-detects auth flows, fills test credentials, or skips gracefully
- **Functional bugs** — unresponsive buttons, broken navigation, form failures

---

## How It Compares

### vs. Cloud Testing Platforms (QualGent, BrowserStack, Apptest.ai)

| | Phone Farm | Cloud Platforms |
|---|---|---|
| Cost | **Free forever** | $129–$500+/mo |
| Data privacy | **Runs locally** — nothing leaves your machine | Your APK goes to their servers |
| Setup | `pip install phone-farm` | Account signup, API keys, billing |
| Audit report | **Client-ready HTML with score** | Dashboard screenshots |
| Open source | **Yes (MIT)** | No |

### vs. Testing Frameworks (Appium, Maestro, Espresso)

| | Phone Farm | Frameworks |
|---|---|---|
| Test scripts needed | **No — autonomous exploration** | Yes — you write them |
| Time to first result | **5 minutes** | Hours to days |
| Output | **Branded audit report** | Pass/fail logs |
| Learning curve | **Zero** | Significant |

### vs. Google Lighthouse

Lighthouse audits web pages. Phone Farm audits Android APKs. Same idea — one command, one score, one report.

---

## Quick Start

### Prerequisites

```bash
# Java 17+, Android SDK (emulator + platform-tools), Node.js 18+
npx appium driver install uiautomator2
```

### Install & Run

```bash
pip install phone-farm
phone-farm doctor              # Verify prerequisites
phone-farm audit ./my-app.apk  # Run full audit, get HTML report
```

### Try Without an APK

```bash
phone-farm demo    # Downloads Wikipedia app, runs audit, generates report
```

### Zero-Config

No `phone-farm.toml` needed. Phone Farm ships with sensible defaults (API level 34, Pixel 6, headless mode, 2GB RAM). Just point it at an APK.

---

## The `audit` Command

The single command that does everything:

```bash
phone-farm audit ./app.apk \
  --client-name "Acme Corp" \
  --auditor-name "Jane Smith" \
  --max-steps 100 \
  --test-email "test@example.com" \
  --test-password "TestPass123" \
  --format both
```

What happens:
1. Checks prerequisites (`doctor`)
2. Boots Android emulator (with retry — 3x exponential backoff)
3. Installs APK
4. Explores the app autonomously (taps, scrolls, types, navigates)
5. Detects login screens — fills credentials or skips
6. Monitors logcat for crashes and ANRs after every action
7. Runs accessibility audit on every unique screen
8. Computes Production Readiness Score
9. Generates HTML + JSON reports with all screenshots
10. Tears down emulator
11. Prints score, bug count, and report path

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output DIR` | `./audit-{timestamp}/` | Where to save reports and screenshots |
| `--max-steps N` | 50 (free) / 200 (pro) | Exploration depth |
| `--client-name` | — | Appears in report header |
| `--auditor-name` | — | Appears in report footer |
| `--test-email` | — | Test account email for login flows |
| `--test-password` | — | Test account password |
| `--skip-login` | false | Skip auth screens, test pre-login UI only |
| `--format` | both | Output: `html`, `json`, or `both` |

---

## CI/CD: GitHub Action

Block buggy PRs automatically. Every pull request gets a Production Readiness Score.

```yaml
# .github/workflows/qa.yml
name: QA Audit
on: [pull_request]

jobs:
  audit:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: avinashchby/phone-farm-pro/action@v1
        with:
          apk-path: app/build/outputs/apk/debug/app-debug.apk
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          fail-on-severity: critical
```

The action posts a comment on your PR:

```
## Phone Farm QA Report
APK: app-debug.apk | Score: 85/100 (B) | Steps: 30 | Screens: 12

### Bugs Found: 2
| # | Severity | Category | Title |
|---|----------|----------|-------|
| 1 | high | crash | NullPointerException on settings screen |
| 2 | medium | accessibility | 3 buttons missing content descriptions |
```

Full HTML report uploaded as an artifact.

---

## More Ways to Use Phone Farm

### Web Dashboard

```bash
phone-farm serve    # Opens at http://localhost:8000
```

Upload APKs, run audits, and browse reports — all from your browser. Dark theme, real-time progress via HTMX.

### CLI Emulator Control

Full manual control for scripted testing or Claude Code integration:

```bash
phone-farm emu boot ./app.apk        # Boot + install
phone-farm emu screen                # Accessibility tree XML
phone-farm emu screenshot ./ss.png   # Save screenshot
phone-farm emu tap --text "Login"    # Tap by text
phone-farm emu type --id "com.app:id/email" --value "test@example.com"
phone-farm emu scroll down
phone-farm emu back
phone-farm emu crashes               # JSON crash report
phone-farm emu teardown              # Clean up
```

### MCP Server

Any MCP-compatible AI agent (Claude Code, Cursor, etc.) can drive the emulator:

```json
{
  "mcpServers": {
    "phone-farm": {
      "command": "phone-farm-mcp"
    }
  }
}
```

Tools: `boot`, `teardown`, `screen`, `screenshot`, `tap`, `type_text`, `scroll`, `back`, `crashes`, `launch_app`, `doctor`

---

## Configuration

Works without any config file. Optionally create `phone-farm.toml`:

```toml
[emulator]
api_level = 34
ram_mb = 4096
device_profile = "pixel_6"
headless = true

[automation]
appium_base_port = 4723

[test_accounts]
email = "test@example.com"
password = "TestPass123"

[paths]
db = "./phone-farm.db"
reports = "./qa_reports"
screenshots = "./screenshots"
```

---

## Free vs. Pro

The free version catches crashes and accessibility issues. Pro adds AI vision for deeper exploration.

| Feature | Free (MIT) | Pro |
|---------|-----------|-----|
| Production Readiness Score | Yes | Yes |
| HTML audit reports | Yes | Yes |
| Crash & ANR detection | Yes | Yes |
| Accessibility audit (4 rules) | Yes | Yes + AI analysis |
| Deterministic exploration | Yes | Yes |
| Login flow handling | Yes | Yes |
| CLI + MCP + Web dashboard | Yes | Yes |
| AI vision exploration (Claude) | — | Yes |
| GitHub Action | — | Yes |
| CI/CD PR comments | — | Yes |
| Cost tracking per audit | — | Yes |

```bash
# Free — everything above
pip install phone-farm

# Pro — adds AI exploration + GitHub Action
pip install phone-farm-pro
```

---

## Architecture

```
phone-farm audit ./app.apk
        |
        v
+------------------+     +-------------------+     +------------------+
|   Web Dashboard  |     |   CLI / MCP       |     |  Audit Engine    |
|  FastAPI + HTMX  |     |  phone-farm CLI   |     |  scoring.py      |
+--------+---------+     +--------+----------+     |  report_renderer |
         |                        |                 |  accessibility   |
         +------------------------+-----------------+  login_detect    |
                                  |                 +--------+---------+
                     +------------+------------+             |
                     |      Core Layer         +-------------+
                     |  emulator.py (retry)    |
                     |  appium_server.py       |
                     |  db.py (SQLite)         |
                     +------------+------------+
                                  |
                     +------------+------------+
                     |   Android Emulator      |
                     |   ADB + Appium          |
                     |   UIAutomator2          |
                     +-------------------------+
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Web | FastAPI + HTMX + Jinja2 |
| CLI | Click + Rich |
| Database | SQLite (aiosqlite) |
| Emulator | ADB + Appium (UIAutomator2) |
| Reports | Standalone HTML (inline CSS, no deps) |
| AI (Pro) | Anthropic Claude Sonnet |
| MCP | FastMCP (mcp>=1.27) |
| Testing | pytest + pytest-asyncio (193 tests) |
| Linting | ruff |

---

## Development

```bash
git clone https://github.com/avinashchby/phone-farm
cd phone-farm
uv sync
uv run pytest -v           # 193 tests
uv run ruff check --fix    # Lint
phone-farm doctor          # Verify setup
```

---

## Contributing

Contributions welcome. Please:

1. Fork the repo and create a feature branch
2. Follow existing code style (ruff, max 100 chars/line)
3. Add tests for new functionality
4. Keep functions under 50 lines; split files over 500 lines
5. Use conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
6. Open a pull request against `main`

---

## FAQ

**How is this different from Appium or Maestro?**
Those are testing *frameworks* — you write test scripts, they execute them. Phone Farm is an *audit tool* — you give it an APK, it explores autonomously and produces a report. No scripts to write.

**How is this different from QualGent or Apptest.ai?**
Those are cloud SaaS platforms. Phone Farm runs locally, is open source, is free, and produces a Production Readiness Score — a concept they don't have.

**Does it work without an internet connection?**
The free version works fully offline (emulator runs locally). Pro mode needs internet to call the Anthropic API for AI-powered exploration.

**How long does an audit take?**
3–5 minutes for a quick scan (30 steps), 10–15 minutes for a deep audit (200 steps). Emulator boot adds ~60 seconds.

**Can I use this for client work?**
Yes. The `--client-name` and `--auditor-name` flags brand the report. The HTML is a single file you can email directly. Many QA consultants use Phone Farm as part of their **android app testing services**.

**What Android versions does it support?**
API level 28–35 (Android 9–15). Default is API 34 (Android 14).

---

## License

MIT — see [LICENSE](LICENSE).

---

## Star History

If Phone Farm saves you time or money, consider starring the repo. It helps others find it.

[![Star History Chart](https://api.star-history.com/svg?repos=avinashchby/phone-farm&type=Date)](https://star-history.com/#avinashchby/phone-farm&Date)

