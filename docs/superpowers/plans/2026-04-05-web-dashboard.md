# Phone Farm Web Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a web dashboard at localhost:8000 that lets users drop an APK, manage emulators, and view QA bug reports — all from the browser.

**Architecture:** FastAPI serves Jinja2 templates with HTMX for live updates. REST API endpoints power the UI and enable MCP integration. Reuses all existing phone_farm modules unchanged.

**Tech Stack:** FastAPI, Jinja2, HTMX (CDN), Tailwind CSS (CDN), uvicorn, python-multipart

---

## File Structure

```
phone_farm/web/
├── __init__.py          # Package marker
├── app.py               # FastAPI app, HTML routes, startup
├── api.py               # REST API routes (/api/*)
├── state.py             # In-memory app state (running tests, phones)
└── templates/
    ├── base.html         # Dark theme layout, nav tabs, HTMX/Tailwind CDN
    ├── qa_test.html      # APK upload + test progress
    ├── phones.html       # Phone grid
    ├── reports.html      # Report list
    ├── settings.html     # Settings + doctor checks
    └── partials/
        ├── phone_card.html     # Single phone card (HTMX fragment)
        └── test_progress.html  # Test progress panel (HTMX fragment)
```

**Modified files:**
- `phone_farm/cli.py` — add `serve` command
- `pyproject.toml` — add web dependencies
- `.claude/launch.json` — add server config

---

### Task 1: Add Web Dependencies + Serve Command

**Files:**
- Modify: `pyproject.toml`
- Modify: `phone_farm/cli.py`
- Modify: `.claude/launch.json`
- Create: `phone_farm/web/__init__.py`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Add to the `dependencies` list in `pyproject.toml`:

```toml
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
```

- [ ] **Step 2: Create web package**

Create `phone_farm/web/__init__.py`:

```python
"""Phone Farm web dashboard."""
```

- [ ] **Step 3: Add serve command to CLI**

Add to `phone_farm/cli.py` imports:

```python
import uvicorn
```

Add after the `emu_crashes` command (before the file ends):

```python
@cli.command()
@click.option("--port", default=8000, help="Port to serve on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
def serve(port: int, host: str) -> None:
    """Start the web dashboard."""
    console.print(f"[bold green]Phone Farm[/bold green] dashboard starting at http://{host}:{port}")
    uvicorn.run("phone_farm.web.app:app", host=host, port=port, reload=True)
```

- [ ] **Step 4: Update launch.json**

Add to `.claude/launch.json` configurations array:

```json
    {
      "name": "phone-farm-serve",
      "runtimeExecutable": "uv",
      "runtimeArgs": ["run", "phone-farm", "serve"],
      "port": 8000
    }
```

- [ ] **Step 5: Install dependencies**

Run: `uv sync`
Expected: All packages install successfully

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml phone_farm/cli.py phone_farm/web/__init__.py .claude/launch.json uv.lock
git commit -m "feat: add web dependencies and serve command"
```

---

### Task 2: App State Module

**Files:**
- Create: `phone_farm/web/state.py`
- Create: `tests/test_web/__init__.py`
- Create: `tests/test_web/test_state.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_web/__init__.py`: (empty file)

Write `tests/test_web/test_state.py`:

```python
"""Tests for web app state management."""

from phone_farm.web.state import AppState, PhoneState, TestRun


def test_app_state_initial() -> None:
    state = AppState()
    assert state.phones == {}
    assert state.test_runs == {}


def test_add_phone() -> None:
    state = AppState()
    state.add_phone(0, "emulator-5554")
    assert 0 in state.phones
    assert state.phones[0].adb_serial == "emulator-5554"
    assert state.phones[0].status == "booting"


def test_remove_phone() -> None:
    state = AppState()
    state.add_phone(0, "emulator-5554")
    state.remove_phone(0)
    assert 0 not in state.phones


def test_start_test_run() -> None:
    state = AppState()
    run_id = state.start_test_run("test.apk", "A test app")
    assert run_id in state.test_runs
    run = state.test_runs[run_id]
    assert run.apk_name == "test.apk"
    assert run.status == "running"
    assert run.bugs_found == 0


def test_update_test_progress() -> None:
    state = AppState()
    run_id = state.start_test_run("test.apk", "A test app")
    state.update_test_progress(run_id, steps=10, screens=3, bugs=2)
    run = state.test_runs[run_id]
    assert run.steps_completed == 10
    assert run.screens_found == 3
    assert run.bugs_found == 2


def test_complete_test_run() -> None:
    state = AppState()
    run_id = state.start_test_run("test.apk", "A test app")
    state.complete_test_run(run_id, report_path="/tmp/report.json")
    run = state.test_runs[run_id]
    assert run.status == "completed"
    assert run.report_path == "/tmp/report.json"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_web/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement state module**

Write `phone_farm/web/state.py`:

```python
"""In-memory state for the web dashboard."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PhoneState:
    """State of a single emulator phone."""

    slot: int
    adb_serial: str
    status: str = "booting"  # booting, running, error, stopped
    last_screenshot: str | None = None


@dataclass
class TestRun:
    """State of a running or completed QA test."""

    run_id: str
    apk_name: str
    app_description: str
    status: str = "running"  # running, completed, failed, stopped
    steps_completed: int = 0
    screens_found: int = 0
    bugs_found: int = 0
    latest_screenshot: str | None = None
    report_path: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AppState:
    """Global in-memory state for the web app."""

    def __init__(self) -> None:
        self.phones: dict[int, PhoneState] = {}
        self.test_runs: dict[str, TestRun] = {}

    def add_phone(self, slot: int, adb_serial: str) -> None:
        """Register a phone in the state."""
        self.phones[slot] = PhoneState(slot=slot, adb_serial=adb_serial)

    def remove_phone(self, slot: int) -> None:
        """Remove a phone from the state."""
        self.phones.pop(slot, None)

    def start_test_run(self, apk_name: str, app_description: str) -> str:
        """Start tracking a new test run. Returns run_id."""
        run_id = uuid.uuid4().hex[:8]
        self.test_runs[run_id] = TestRun(
            run_id=run_id,
            apk_name=apk_name,
            app_description=app_description,
        )
        return run_id

    def update_test_progress(
        self, run_id: str, *, steps: int, screens: int, bugs: int
    ) -> None:
        """Update progress for a running test."""
        if run_id in self.test_runs:
            run = self.test_runs[run_id]
            run.steps_completed = steps
            run.screens_found = screens
            run.bugs_found = bugs

    def complete_test_run(self, run_id: str, *, report_path: str) -> None:
        """Mark a test run as completed."""
        if run_id in self.test_runs:
            run = self.test_runs[run_id]
            run.status = "completed"
            run.report_path = report_path
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_web/test_state.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add phone_farm/web/state.py tests/test_web/
git commit -m "feat: add web app state management"
```

---

### Task 3: Base Template + FastAPI App

**Files:**
- Create: `phone_farm/web/templates/base.html`
- Create: `phone_farm/web/app.py`

- [ ] **Step 1: Create base HTML template**

Write `phone_farm/web/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phone Farm — {% block title %}Dashboard{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        bg: '#1a1a2e',
                        card: '#16213e',
                        border: '#0f3460',
                        accent: '#e94560',
                        success: '#4ecca3',
                        warn: '#f0c040',
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-bg text-gray-200 min-h-screen">
    <nav class="border-b border-border px-6 py-3 flex items-center gap-4">
        <span class="text-accent font-bold text-lg">📱 Phone Farm</span>
        <div class="flex gap-1 ml-4">
            <a href="/" class="px-4 py-2 rounded {% if active_tab == 'qa' %}bg-accent text-white{% else %}bg-card border border-border hover:bg-border{% endif %}">QA Test</a>
            <a href="/phones" class="px-4 py-2 rounded {% if active_tab == 'phones' %}bg-accent text-white{% else %}bg-card border border-border hover:bg-border{% endif %}">Phones</a>
            <a href="/reports" class="px-4 py-2 rounded {% if active_tab == 'reports' %}bg-accent text-white{% else %}bg-card border border-border hover:bg-border{% endif %}">Reports</a>
            <a href="/settings" class="px-4 py-2 rounded {% if active_tab == 'settings' %}bg-accent text-white{% else %}bg-card border border-border hover:bg-border{% endif %}">Settings</a>
        </div>
        <div class="ml-auto text-gray-500 text-sm">v0.1.0</div>
    </nav>
    <main class="p-6">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

- [ ] **Step 2: Create FastAPI app**

Write `phone_farm/web/app.py`:

```python
"""FastAPI web application for Phone Farm dashboard."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from phone_farm.web.state import AppState

TEMPLATE_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Phone Farm", version="0.1.0")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

state = AppState()


@app.get("/", response_class=HTMLResponse)
async def qa_test_page(request: Request) -> HTMLResponse:
    """QA Test home page."""
    return templates.TemplateResponse(
        "qa_test.html",
        {"request": request, "active_tab": "qa", "state": state},
    )


@app.get("/phones", response_class=HTMLResponse)
async def phones_page(request: Request) -> HTMLResponse:
    """Phones management page."""
    return templates.TemplateResponse(
        "phones.html",
        {"request": request, "active_tab": "phones", "state": state},
    )


@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request) -> HTMLResponse:
    """Reports page."""
    return templates.TemplateResponse(
        "reports.html",
        {"request": request, "active_tab": "reports", "state": state},
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    """Settings page."""
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "active_tab": "settings", "state": state},
    )
```

- [ ] **Step 3: Create minimal page templates**

Write `phone_farm/web/templates/qa_test.html`:

```html
{% extends "base.html" %}
{% block title %}QA Test{% endblock %}
{% block content %}
<div class="grid grid-cols-2 gap-6">
    <div class="bg-card border-2 border-dashed border-accent rounded-lg p-8">
        <form action="/api/qa/start" method="post" enctype="multipart/form-data" class="text-center">
            <div class="text-4xl mb-4">📦</div>
            <div class="text-accent font-bold text-lg mb-2">Drop APK here</div>
            <div class="text-gray-500 mb-4">or click to browse</div>
            <input type="file" name="apk" accept=".apk" class="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-accent file:text-white file:cursor-pointer">
            <textarea name="description" placeholder="Describe your app for better testing..." class="w-full mt-4 p-3 bg-border rounded text-gray-300 text-sm" rows="3"></textarea>
            <button type="submit" class="w-full mt-4 bg-accent text-white py-3 rounded-lg font-bold hover:bg-red-600 transition">Start AI QA Test</button>
        </form>
    </div>
    <div>
        <div class="bg-card border border-border rounded-lg p-4">
            <h3 class="font-bold mb-3">Recent Tests</h3>
            {% if state.test_runs %}
                {% for run_id, run in state.test_runs.items() %}
                <div class="flex justify-between py-2 border-b border-border text-sm">
                    <span>{{ run.apk_name }}</span>
                    <span class="{% if run.status == 'completed' %}text-success{% else %}text-warn{% endif %}">{{ run.status }}</span>
                </div>
                {% endfor %}
            {% else %}
                <p class="text-gray-500 text-sm">No tests yet. Upload an APK to start.</p>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
```

Write `phone_farm/web/templates/phones.html`:

```html
{% extends "base.html" %}
{% block title %}Phones{% endblock %}
{% block content %}
<div class="grid grid-cols-4 gap-4" id="phone-grid" hx-get="/api/phones/grid" hx-trigger="every 3s" hx-swap="innerHTML">
    {% for slot, phone in state.phones.items() %}
    <div class="bg-card border border-border rounded-lg p-3 text-center">
        <div class="bg-border h-32 rounded mb-2 flex items-center justify-content-center">
            <span class="text-gray-500 mx-auto">📱</span>
        </div>
        <div class="{% if phone.status == 'running' %}text-success{% elif phone.status == 'error' %}text-accent{% else %}text-gray-500{% endif %}">● Phone {{ slot + 1 }}</div>
        <div class="text-gray-500 text-xs">{{ phone.status }}</div>
    </div>
    {% endfor %}
    <div class="bg-card border border-border rounded-lg p-3 text-center opacity-50 cursor-pointer" hx-post="/api/phones/boot" hx-swap="none">
        <div class="bg-border h-32 rounded mb-2 flex items-center justify-center">
            <span class="text-2xl">+</span>
        </div>
        <div>Add Phone</div>
    </div>
</div>
{% endblock %}
```

Write `phone_farm/web/templates/reports.html`:

```html
{% extends "base.html" %}
{% block title %}Reports{% endblock %}
{% block content %}
<div class="bg-card border border-border rounded-lg p-4">
    <h2 class="font-bold text-lg mb-4">QA Reports</h2>
    {% if state.test_runs %}
        <table class="w-full">
            <thead><tr class="text-left text-gray-500 text-sm border-b border-border">
                <th class="py-2">App</th><th>Status</th><th>Bugs</th><th>Screens</th><th>Started</th>
            </tr></thead>
            <tbody>
            {% for run_id, run in state.test_runs.items() %}
                <tr class="border-b border-border">
                    <td class="py-2">{{ run.apk_name }}</td>
                    <td class="{% if run.status == 'completed' %}text-success{% else %}text-warn{% endif %}">{{ run.status }}</td>
                    <td>{{ run.bugs_found }}</td>
                    <td>{{ run.screens_found }}</td>
                    <td class="text-gray-500 text-sm">{{ run.started_at[:19] }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    {% else %}
        <p class="text-gray-500">No reports yet. Run a QA test first.</p>
    {% endif %}
</div>
{% endblock %}
```

Write `phone_farm/web/templates/settings.html`:

```html
{% extends "base.html" %}
{% block title %}Settings{% endblock %}
{% block content %}
<div class="max-w-2xl">
    <h2 class="font-bold text-lg mb-4">Prerequisites</h2>
    <div id="health-checks" hx-get="/api/health" hx-trigger="load" hx-swap="innerHTML">
        <p class="text-gray-500">Checking...</p>
    </div>
    <h2 class="font-bold text-lg mt-8 mb-4">About</h2>
    <div class="bg-card border border-border rounded-lg p-4">
        <p><span class="text-accent font-bold">Phone Farm</span> v0.1.0</p>
        <p class="text-gray-500 text-sm mt-2">Open-source AI-powered Android QA testing</p>
        <p class="text-gray-500 text-sm mt-1">github.com/your-org/phone-farm</p>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Create partial templates**

Write `phone_farm/web/templates/partials/phone_card.html`:

```html
<div class="bg-card border border-{% if phone.status == 'running' %}success{% else %}border{% endif %} rounded-lg p-3 text-center">
    {% if phone.last_screenshot %}
    <img src="/api/phones/{{ phone.slot }}/screenshot" class="h-32 rounded mb-2 mx-auto" alt="Phone {{ phone.slot + 1 }}">
    {% else %}
    <div class="bg-border h-32 rounded mb-2 flex items-center justify-center">
        <span class="text-gray-500">📱</span>
    </div>
    {% endif %}
    <div class="{% if phone.status == 'running' %}text-success{% elif phone.status == 'error' %}text-accent{% else %}text-gray-500{% endif %}">● Phone {{ phone.slot + 1 }}</div>
    <div class="text-gray-500 text-xs">{{ phone.status }}</div>
    <div class="flex gap-1 mt-2 justify-center">
        {% if phone.status == 'running' %}
        <button hx-post="/api/phones/{{ phone.slot }}/stop" hx-swap="none" class="bg-border px-2 py-1 rounded text-xs">Stop</button>
        {% endif %}
    </div>
</div>
```

Write `phone_farm/web/templates/partials/test_progress.html`:

```html
<div class="bg-card border border-accent rounded-lg p-6">
    <div class="flex justify-between items-center mb-4">
        <h3 class="text-accent font-bold">Testing: {{ run.apk_name }}</h3>
        <span class="text-sm px-2 py-1 rounded {% if run.status == 'running' %}bg-warn text-black{% else %}bg-success text-black{% endif %}">{{ run.status }}</span>
    </div>
    {% if run.latest_screenshot %}
    <img src="/api/qa/screenshot/{{ run.run_id }}" class="max-h-48 rounded mb-4 mx-auto" alt="Current screen">
    {% endif %}
    <div class="grid grid-cols-3 gap-4 text-center">
        <div><div class="text-2xl font-bold">{{ run.steps_completed }}</div><div class="text-gray-500 text-xs">Steps</div></div>
        <div><div class="text-2xl font-bold">{{ run.screens_found }}</div><div class="text-gray-500 text-xs">Screens</div></div>
        <div><div class="text-2xl font-bold text-accent">{{ run.bugs_found }}</div><div class="text-gray-500 text-xs">Bugs</div></div>
    </div>
    {% if run.status == 'running' %}
    <button hx-post="/api/qa/stop/{{ run.run_id }}" hx-swap="none" class="w-full mt-4 bg-border text-white py-2 rounded hover:bg-gray-600">Stop Test</button>
    {% else %}
    <a href="/reports" class="block w-full mt-4 bg-success text-black py-2 rounded text-center font-bold">View Report</a>
    {% endif %}
</div>
```

- [ ] **Step 5: Test the server starts**

Run: `uv run phone-farm serve &`
Then: `curl -s http://localhost:8000/ | head -5`
Expected: HTML output with "Phone Farm" in it

Kill the server after testing.

- [ ] **Step 6: Commit**

```bash
git add phone_farm/web/
git commit -m "feat: add FastAPI app with base template and page routes"
```

---

### Task 4: REST API Endpoints

**Files:**
- Create: `phone_farm/web/api.py`
- Modify: `phone_farm/web/app.py`
- Create: `tests/test_web/test_api.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_web/test_api.py`:

```python
"""Tests for web API endpoints."""

import pytest
from fastapi.testclient import TestClient

from phone_farm.web.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_home_page_returns_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Phone Farm" in response.text


def test_phones_page_returns_html(client: TestClient) -> None:
    response = client.get("/phones")
    assert response.status_code == 200


def test_reports_page_returns_html(client: TestClient) -> None:
    response = client.get("/reports")
    assert response.status_code == 200


def test_settings_page_returns_html(client: TestClient) -> None:
    response = client.get("/settings")
    assert response.status_code == 200


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    assert isinstance(data["checks"], list)


def test_phones_list_endpoint(client: TestClient) -> None:
    response = client.get("/api/phones")
    assert response.status_code == 200
    data = response.json()
    assert "phones" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_web/test_api.py -v`
Expected: FAIL — missing `/api/health` route

- [ ] **Step 3: Implement API module**

Write `phone_farm/web/api.py`:

```python
"""REST API endpoints for Phone Farm dashboard."""

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse

from phone_farm.config import load_config
from phone_farm.doctor import Doctor
from phone_farm.emulator import Emulator
from phone_farm.appium_server import AppiumServer
from phone_farm.web.state import AppState

router = APIRouter(prefix="/api")

DEFAULT_CONFIG = Path("phone-farm.toml")
UPLOAD_DIR = Path("./uploads")
SCREENSHOT_DIR = Path("./screenshots")


def _get_state() -> AppState:
    """Get the global app state. Injected by app.py."""
    raise RuntimeError("State not initialized")


@router.get("/health")
async def health_check() -> JSONResponse:
    """Run prerequisite checks and return results."""
    doc = Doctor()
    results = await doc.check_all()
    return JSONResponse({
        "checks": [
            {"name": r.name, "ok": r.ok, "message": r.message}
            for r in results
        ]
    })


@router.get("/phones")
async def list_phones() -> JSONResponse:
    """List all active phones."""
    state = _get_state()
    return JSONResponse({
        "phones": [
            {
                "slot": p.slot,
                "adb_serial": p.adb_serial,
                "status": p.status,
            }
            for p in state.phones.values()
        ]
    })


@router.post("/phones/boot")
async def boot_phone() -> JSONResponse:
    """Boot a new emulator phone."""
    state = _get_state()
    slot = len(state.phones)
    if slot >= 5:
        return JSONResponse({"error": "Maximum 5 phones"}, status_code=400)

    adb_serial = f"emulator-{5554 + slot * 2}"
    state.add_phone(slot, adb_serial)

    try:
        if DEFAULT_CONFIG.exists():
            config = load_config(DEFAULT_CONFIG)
        else:
            state.phones[slot].status = "error"
            return JSONResponse({"error": "Config not found"}, status_code=500)

        emu = Emulator(
            slot=slot,
            api_level=config.emulator.api_level,
            ram_mb=config.emulator.ram_mb,
            device_profile=config.emulator.device_profile,
        )
        await emu.create_avd()
        await emu.start(headless=config.emulator.headless)
        await emu.wait_for_boot()
        state.phones[slot].status = "running"
    except Exception as e:
        state.phones[slot].status = "error"
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({"slot": slot, "status": "running"})


@router.post("/phones/{slot}/stop")
async def stop_phone(slot: int) -> JSONResponse:
    """Stop an emulator phone."""
    state = _get_state()
    if slot not in state.phones:
        return JSONResponse({"error": "Phone not found"}, status_code=404)

    if DEFAULT_CONFIG.exists():
        config = load_config(DEFAULT_CONFIG)
        emu = Emulator(
            slot=slot,
            api_level=config.emulator.api_level,
            ram_mb=config.emulator.ram_mb,
            device_profile=config.emulator.device_profile,
        )
        await emu.stop()

    state.remove_phone(slot)
    return JSONResponse({"status": "stopped"})


@router.get("/phones/{slot}/screenshot")
async def phone_screenshot(slot: int) -> FileResponse:
    """Get a screenshot from a phone."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"phone-{slot}.png"

    state = _get_state()
    if slot not in state.phones:
        return JSONResponse({"error": "Phone not found"}, status_code=404)

    from phone_farm.emulator import run_cmd
    adb_serial = state.phones[slot].adb_serial
    await run_cmd(
        ["adb", "-s", adb_serial, "shell", "screencap", "-p", "/sdcard/screen.png"],
        timeout=10,
    )
    await run_cmd(
        ["adb", "-s", adb_serial, "pull", "/sdcard/screen.png", str(path)],
        timeout=10,
    )
    return FileResponse(str(path), media_type="image/png")


@router.post("/qa/start")
async def start_qa_test(
    apk: UploadFile = File(...),
    description: str = Form(""),
) -> JSONResponse:
    """Upload APK and start a QA test."""
    state = _get_state()

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    apk_path = UPLOAD_DIR / apk.filename
    with open(apk_path, "wb") as f:
        content = await apk.read()
        f.write(content)

    run_id = state.start_test_run(apk.filename, description)

    return JSONResponse({"run_id": run_id, "status": "started"})


@router.get("/qa/status/{run_id}")
async def qa_test_status(run_id: str) -> JSONResponse:
    """Get status of a running QA test."""
    state = _get_state()
    if run_id not in state.test_runs:
        return JSONResponse({"error": "Test not found"}, status_code=404)

    run = state.test_runs[run_id]
    return JSONResponse({
        "run_id": run.run_id,
        "apk_name": run.apk_name,
        "status": run.status,
        "steps_completed": run.steps_completed,
        "screens_found": run.screens_found,
        "bugs_found": run.bugs_found,
    })


@router.post("/qa/stop/{run_id}")
async def stop_qa_test(run_id: str) -> JSONResponse:
    """Stop a running QA test."""
    state = _get_state()
    if run_id not in state.test_runs:
        return JSONResponse({"error": "Test not found"}, status_code=404)

    state.test_runs[run_id].status = "stopped"
    return JSONResponse({"status": "stopped"})
```

- [ ] **Step 4: Register API router in app.py**

Add to `phone_farm/web/app.py` imports:

```python
from phone_farm.web.api import router as api_router, _get_state
```

Add after the `state = AppState()` line:

```python
# Wire up API routes with shared state
import phone_farm.web.api as api_module
api_module._get_state = lambda: state
app.include_router(api_router)
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_web/ -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add phone_farm/web/api.py phone_farm/web/app.py tests/test_web/test_api.py
git commit -m "feat: add REST API endpoints for phones, QA tests, and health"
```

---

### Task 5: Wire Up HTMX Live Updates

**Files:**
- Modify: `phone_farm/web/app.py`
- Modify: `phone_farm/web/templates/qa_test.html`
- Modify: `phone_farm/web/templates/settings.html`

- [ ] **Step 1: Add HTMX partial routes to app.py**

Add these routes to `phone_farm/web/app.py`:

```python
@app.get("/api/phones/grid", response_class=HTMLResponse)
async def phones_grid(request: Request) -> HTMLResponse:
    """HTMX partial: phone grid cards."""
    html_parts = []
    for slot, phone in state.phones.items():
        html_parts.append(templates.TemplateResponse(
            "partials/phone_card.html",
            {"request": request, "phone": phone},
        ).body.decode())
    # Add phone button
    html_parts.append(
        '<div class="bg-card border border-border rounded-lg p-3 text-center opacity-50 cursor-pointer" '
        'hx-post="/api/phones/boot" hx-swap="none">'
        '<div class="bg-border h-32 rounded mb-2 flex items-center justify-center">'
        '<span class="text-2xl">+</span></div><div>Add Phone</div></div>'
    )
    return HTMLResponse("".join(html_parts))
```

- [ ] **Step 2: Update settings.html to render health checks**

The `/api/health` endpoint returns JSON. Add an HTMX-compatible health route to `app.py`:

```python
@app.get("/api/health/html", response_class=HTMLResponse)
async def health_html(request: Request) -> HTMLResponse:
    """HTMX partial: health check results as HTML."""
    from phone_farm.doctor import Doctor
    doc = Doctor()
    results = await doc.check_all()
    html = ""
    for r in results:
        icon = "✅" if r.ok else "❌"
        color = "text-success" if r.ok else "text-accent"
        html += f'<div class="flex justify-between py-2 border-b border-border"><span class="{color}">{icon} {r.name}</span><span class="text-gray-500 text-sm">{r.message}</span></div>'
    return HTMLResponse(html)
```

Update `settings.html` to use this endpoint:

Change `hx-get="/api/health"` to `hx-get="/api/health/html"` in the settings template.

- [ ] **Step 3: Test the full flow**

Run: `uv run phone-farm serve &`
Open: `http://localhost:8000` in browser
Verify: All 4 tabs render, settings shows health checks
Kill server.

- [ ] **Step 4: Commit**

```bash
git add phone_farm/web/
git commit -m "feat: wire HTMX live updates for phones grid and health checks"
```

---

### Task 6: Lint + Full Test Suite

**Files:** All

- [ ] **Step 1: Fix lint**

Run: `uv run ruff check phone_farm/ tests/ --fix`

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass (110 existing + ~12 new)

- [ ] **Step 3: Verify serve command works**

Run: `uv run phone-farm serve --port 8001 &`
Then: `curl -s http://localhost:8001/ | grep "Phone Farm"`
Expected: Output contains "Phone Farm"
Kill server.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Phone Farm web dashboard v1

Web dashboard at localhost:8000 with:
- QA Test tab: APK upload, test progress
- Phones tab: emulator grid with live screenshots
- Reports tab: bug report list
- Settings tab: prerequisite checks
- REST API for all operations
- HTMX live updates"
```
