# Phone Farm

**AI-powered Android QA testing on your own machine — no cloud, no accounts, no monthly bill.**

[![PyPI](https://img.shields.io/pypi/v/phone-farm)](https://pypi.org/project/phone-farm/)
[![Downloads](https://img.shields.io/pypi/dm/phone-farm)](https://pypi.org/project/phone-farm/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-139%20passing-brightgreen)](https://github.com/avinashchby/phone-farm/actions)
[![GitHub stars](https://img.shields.io/github/stars/avinashchby/phone-farm)](https://github.com/avinashchby/phone-farm)

Drop an APK. An AI agent boots an Android emulator, explores the app, finds bugs, and writes a report — all running locally.

<!-- screenshot -->

---

## Why Phone Farm?

| | Phone Farm | BrowserStack | Firebase Test Lab |
|---|---|---|---|
| Cost | Free | $129+/mo | Pay per device-hour |
| Privacy | Local only | Cloud | Cloud |
| AI exploration | Yes | No | No |
| MCP integration | Yes | No | No |
| Self-hosted | Yes | No | No |

---

## Features

- **Zero-cost alternative** to BrowserStack and Firebase Test Lab
- **Autonomous AI QA** — the agent reads the screen, makes decisions, and files structured bug reports
- **Web dashboard** at `localhost:8000` — dark theme, real-time updates, no terminal required
- **MCP server** — any MCP-compatible AI agent can drive the emulator with simple tool calls
- **Local-first** — everything runs on your machine; no data leaves your network
- **CLI control** — full emulator control from the terminal for scripted or manual testing
- **Crash detection** — logcat monitoring catches crashes and ANRs automatically
- **Structured reports** — bugs filed with severity, steps to reproduce, and screenshots
- **139+ tests** — pytest suite covering all core modules
- **Built on solid foundations** — Python 3.12, FastAPI, HTMX, Appium, ADB

---

## Quick Start

**1. Install prerequisites**

```bash
# Java 17+, Android SDK (with emulator + platform-tools), Node.js, Appium
npx appium driver install uiautomator2
```

**2. Install Phone Farm**

```bash
pip install phone-farm
# or with AI backend support:
pip install "phone-farm[ai]"
```

**3. Initialize and verify**

```bash
phone-farm doctor          # Check all prerequisites
```

**4. Try the demo (no APK needed)**

```bash
phone-farm demo            # Downloads Wikipedia app, runs QA test automatically
```

**5. Launch the web dashboard**

```bash
phone-farm serve           # Opens at http://localhost:8000
```

---

## Usage

### Web Dashboard

Start the dashboard and open your browser:

```bash
phone-farm serve
# or on a custom port:
phone-farm serve --port 9000
```

Pages:
- `/` — Run an AI QA test, upload an APK, watch live progress
- `/phones` — View running emulators with live status
- `/reports` — Browse past test runs and bug reports
- `/settings` — Configure API keys, emulator settings

### CLI Commands

Full manual control over the emulator from your terminal:

```bash
phone-farm emu boot ./app.apk        # Boot emulator, install APK, start Appium
phone-farm emu screen                # Print accessibility tree XML
phone-farm emu screenshot ./ss.png   # Save screenshot
phone-farm emu tap --text "Login"    # Tap by element text
phone-farm emu tap --id "com.app:id/button"  # Tap by resource ID
phone-farm emu tap --xy "540,1200"   # Tap by coordinates
phone-farm emu type --id "com.app:id/email" --value "test@example.com"
phone-farm emu scroll down           # Scroll (up/down/left/right)
phone-farm emu back                  # Press back button
phone-farm emu crashes               # Check for crashes (JSON output)
phone-farm emu teardown              # Stop emulator and Appium
```

Other commands:

```bash
phone-farm doctor                    # Check prerequisites
phone-farm report                    # View run history
phone-farm accounts add              # Add a test account
phone-farm accounts import accounts.csv
phone-farm cleanup                   # Remove stale AVDs and logs
```

### MCP Server

Phone Farm exposes an MCP server so any compatible AI agent can control the emulator directly.

```bash
# Add to your MCP client config
phone-farm-mcp
```

Available MCP tools: `boot`, `teardown`, `screen`, `screenshot`, `tap`, `type_text`, `scroll`, `back`, `crashes`, `launch_app`, `doctor`

Example MCP config entry:

```json
{
  "mcpServers": {
    "phone-farm": {
      "command": "phone-farm-mcp"
    }
  }
}
```

### AI QA Testing

Run the autonomous AI agent against an APK:

```bash
# Requires ANTHROPIC_API_KEY in environment
phone-farm qa-test ./app.apk
phone-farm qa-test ./app.apk --description "E-commerce checkout app" --max-steps 300
phone-farm qa-test ./app.apk --output ./reports
```

The agent will:
1. Boot an emulator and install the APK
2. Explore screens, tap elements, fill forms, scroll, navigate back
3. Monitor logcat for crashes after each action
4. File structured bug reports with severity and reproduction steps
5. Generate a summary report in the output directory

---

## Configuration

Create `phone-farm.toml` in your project directory:

```toml
[emulator]
api_level = 33
ram_mb = 4096
device_profile = "pixel_6"
headless = true

[automation]
appium_base_port = 4723

[paths]
db = "./phone-farm.db"
```

---

## Architecture

```
+------------------+     +-------------------+     +----------------+
|   Web Dashboard  |     |   CLI / MCP       |     |  AI QA Agent   |
|  FastAPI + HTMX  |     |  phone-farm CLI   |     |  qa_agent/     |
+--------+---------+     +--------+----------+     +-------+--------+
         |                        |                        |
         +------------------------+------------------------+
                                  |
                     +------------+------------+
                     |      Core Layer         |
                     |  emulator.py  db.py     |
                     |  appium_server.py        |
                     |  orchestrator.py         |
                     +------------+------------+
                                  |
                     +------------+------------+
                     |   Android Emulator      |
                     |   ADB + Appium          |
                     |   UIAutomator2          |
                     +-------------------------+
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI |
| Frontend | HTMX + Jinja2 templates |
| CLI | Click + Rich |
| Database | SQLite (aiosqlite) |
| Emulator control | ADB + Appium (UIAutomator2) |
| AI backend | Anthropic API (optional) |
| MCP integration | FastMCP (mcp>=1.27) |
| Encryption | cryptography (Fernet) |
| Testing | pytest + pytest-asyncio |
| Linting | ruff |

---

## Development

```bash
git clone https://github.com/avinashchby/phone-farm
cd phone-farm
uv sync
uv run pytest -v           # Run 139+ tests
uv run ruff check --fix    # Lint
phone-farm doctor          # Verify setup
```

### Project Layout

```
phone_farm/
  cli.py              CLI entry point
  mcp_server.py       MCP server (FastMCP)
  emulator.py         AVD lifecycle, ADB helpers
  appium_server.py    Appium process management
  orchestrator.py     Batch test orchestration
  config.py           TOML config loading
  db.py               SQLite database
  crypto.py           Account password encryption
  doctor.py           Prerequisite checks
  web/
    app.py            FastAPI application
    api.py            REST + HTMX endpoints
    state.py          In-memory app state
  qa_agent/
    agent.py          AI exploration loop
    session.py        QA session lifecycle
    state.py          Screen XML parsing
    memory.py         Agent memory/context
    bug_report.py     Structured bug filing
    logcat.py         Crash and ANR detection
    ai_backend.py     LLM provider abstraction
tests/                139+ pytest tests
scripts/
  actions/            Reusable UI action scripts
  flows/              Pre-scripted test flows
```

---

## Roadmap: Phone Farm Pro

The free version finds crashes. Pro finds *everything else*.

| Feature | Community (Free) | Pro (Coming) |
|---|---|---|
| Crash & ANR detection | Yes | Yes |
| Deterministic explorer | Yes | Yes |
| CLI + MCP + Web dashboard | Yes | Yes |
| AI vision testing | - | Yes |
| Smart test data generation | - | Yes |
| Multi-device parallel testing | - | Yes |
| CI/CD GitHub Action | - | Yes |
| Regression detection (APK diff) | - | Yes |
| Export bugs as Maestro/Appium scripts | - | Yes |

See [ROADMAP.md](ROADMAP.md) for the full plan.

Want early access? Star the repo or email avinash@remotelama.com.

---

## Contributing

Contributions welcome. Please:

1. Fork the repo and create a feature branch
2. Follow the existing code style (ruff, max 100 chars/line)
3. Add tests for new functionality
4. Keep functions under 50 lines; split files over 500 lines
5. Use conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
6. Open a pull request against `main`

Run checks before submitting:

```bash
uv run ruff check --fix
uv run pytest -v
```

---

## License

MIT — see [LICENSE](LICENSE).

---

## Credits

Built with:
- [Appium](https://appium.io/) — mobile automation framework
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [FastAPI](https://fastapi.tiangolo.com/) — web framework
- [HTMX](https://htmx.org/) — frontend interactivity
- [Android Emulator](https://developer.android.com/studio/run/emulator) — virtual device runtime
- [Anthropic](https://anthropic.com/) — AI backend (optional)
