# Phone Farm Web Dashboard — Design Spec

## Summary

A web-based dashboard (localhost:8000) for Android app QA testing. Users drop an APK, the system boots a headless emulator, AI explores the app via MCP, and generates a bug report. No terminal, no API keys.

**Target users:** Anyone with an APK — indie devs, QA teams, non-technical users.

**Open source** — free alternative to BrowserStack ($129/mo), Firebase Test Lab, and PrimeTestLab ($15-25).

## Architecture

```
Browser (localhost:8000)          AI Agents (Claude Code / MCP)
        |                                    |
        v                                    v
  ┌─────────────────────────────────────────────┐
  │           FastAPI Server (Python)           │
  │  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
  │  │  Web UI   │  │ REST API │  │MCP Server │ │
  │  │ Jinja2 +  │  │ /api/*   │  │ tools for │ │
  │  │  HTMX     │  │          │  │ AI agents │ │
  │  └──────────┘  └──────────┘  └───────────┘ │
  └─────────────────────────────────────────────┘
                      |
        ┌─────────────┼─────────────┐
        v             v             v
   Emulator      Appium        SQLite DB
   (headless)    Server        (reports)
```

Single process. One command: `phone-farm serve`.

## Screens

### 1. QA Test (Home Tab)

The landing page. Two zones:

**Left:** Drop zone for APK file upload. Drag-and-drop or file picker. Large, obvious.

**Right:**
- Text area for app description (helps AI test smarter)
- "Start AI QA Test" button (disabled until APK uploaded)
- Recent tests list with app name, bug count, timestamp

**When test starts:**
- Progress panel replaces the drop zone
- Shows: current step, screen count, action count, bugs found so far
- Live screenshot updates every 5 seconds via HTMX polling
- "Stop Test" button

### 2. Phones Tab

Grid of phone cards. Each card shows:
- Live screenshot (updates via HTMX polling every 3s)
- Status indicator (green=running, red=error, grey=off)
- Phone name (Phone 1, Phone 2, etc.)
- Action buttons: Start / Stop / Screenshot / Restart
- "Add Phone" card at the end

Max phones limited by RAM (auto-detected). Shows warning if near limit.

### 3. Reports Tab

List of all QA reports. Each expandable to show:
- Bug table: severity (critical/high/medium/low), category, title, screenshot
- Coverage stats: screens explored, actions taken, duration
- Steps to reproduce for each bug
- Export buttons: JSON, PDF (future)

### 4. Settings Tab

- Prerequisites status (same as `phone-farm doctor`)
- Emulator config: API level, RAM per emulator, max phones
- MCP server toggle (on/off) with connection URL
- About section with version, GitHub link

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | FastAPI | Async, fast, Python-native |
| Templates | Jinja2 | Server-rendered, no build step |
| Live updates | HTMX | Dynamic UI without JavaScript framework |
| CSS | Tailwind (CDN) | Dark theme, utility classes, no build step |
| Database | SQLite (aiosqlite) | Already in project, stores reports |
| Emulators | Android SDK CLI | Already built — emulator.py, pool.py |
| MCP | FastMCP or custom | Expose tools for AI agents |

## New Files

```
phone_farm/
├── web/
│   ├── __init__.py
│   ├── app.py              # FastAPI app, routes, startup/shutdown
│   ├── api.py              # REST API endpoints (/api/*)
│   ├── mcp_server.py       # MCP tool definitions
│   └── templates/
│       ├── base.html        # Dark theme layout, nav tabs, HTMX
│       ├── qa_test.html     # QA test page (drop zone + progress)
│       ├── phones.html      # Phone grid
│       ├── reports.html     # Report list
│       ├── report_detail.html  # Single report view
│       ├── settings.html    # Settings page
│       └── partials/
│           ├── phone_card.html    # Single phone card (HTMX partial)
│           ├── test_progress.html # Test progress panel (HTMX partial)
│           └── bug_row.html       # Single bug table row
```

## Modified Files

- `phone_farm/cli.py` — add `serve` command
- `pyproject.toml` — add fastapi, uvicorn, jinja2, python-multipart dependencies
- `.claude/launch.json` — add phone-farm-serve configuration

## REST API Endpoints

```
GET  /                          → QA Test page (HTML)
GET  /phones                    → Phones page (HTML)
GET  /reports                   → Reports page (HTML)
GET  /reports/{id}              → Report detail (HTML)
GET  /settings                  → Settings page (HTML)

POST /api/qa/start              → Upload APK + start QA test
GET  /api/qa/status/{id}        → Test progress (JSON, HTMX)
POST /api/qa/stop/{id}          → Stop running test

GET  /api/phones                → List phones (JSON)
POST /api/phones/boot           → Boot a new phone
POST /api/phones/{slot}/stop    → Stop a phone
GET  /api/phones/{slot}/screenshot → Get screenshot (PNG)

GET  /api/reports               → List reports (JSON)
GET  /api/reports/{id}          → Get report (JSON)

GET  /api/health                → System health check (JSON)
```

## MCP Tools (for AI agents)

```
phone_farm.boot(apk_path)       → Boot emulator + install APK
phone_farm.screen()             → Get accessibility tree XML
phone_farm.screenshot()         → Get screenshot as base64
phone_farm.tap(id/text/xy)      → Tap element
phone_farm.type(id/text, value) → Type text
phone_farm.scroll(direction)    → Scroll
phone_farm.back()               → Press back
phone_farm.crashes()            → Check for crashes
phone_farm.teardown()           → Stop emulator
```

## APK Upload Flow

1. User drops APK on the drop zone (or clicks to browse)
2. Frontend sends `POST /api/qa/start` with multipart form data (APK file + description)
3. Backend saves APK to `./uploads/`, starts background task:
   a. Boot headless emulator (slot 0)
   b. Install APK
   c. Start Appium
   d. Run QA agent loop (or wait for MCP agent to drive)
4. Frontend polls `GET /api/qa/status/{id}` every 3s via HTMX
5. Status response includes: step count, screen count, bugs found, latest screenshot
6. When done: redirect to report detail page

## Dark Theme

Colors:
- Background: `#1a1a2e`
- Card background: `#16213e`
- Card border: `#0f3460`
- Primary accent: `#e94560` (red-pink)
- Success: `#4ecca3` (green)
- Warning: `#f0c040` (yellow)
- Text: `#e0e0e0`
- Muted text: `#888888`

## Implementation Order

1. FastAPI app skeleton + serve command + base template
2. QA Test page (APK upload + test execution)
3. Phones page (boot/stop/screenshot)
4. Reports page (list + detail view)
5. Settings page
6. MCP server integration
7. Tests

## What We Reuse (existing modules, no changes)

- `phone_farm/emulator.py` — AVD lifecycle
- `phone_farm/pool.py` — concurrent emulator pool
- `phone_farm/appium_server.py` — Appium management
- `phone_farm/emu_cli.py` — session state management
- `phone_farm/qa_agent/` — all QA agent modules
- `phone_farm/config.py` — TOML config loading
- `phone_farm/doctor.py` — prerequisite checks
- `phone_farm/db.py` — SQLite database
- `phone_farm/log.py` — structured logging

## Out of Scope (v1)

- User authentication (it's localhost)
- Cloud deployment
- Real device support (emulators only)
- PDF export (JSON only for v1)
- Multi-user concurrent access
- Video recording of tests
