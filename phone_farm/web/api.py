"""REST API endpoints for Phone Farm dashboard."""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from phone_farm.config import load_config
from phone_farm.doctor import Doctor
from phone_farm.emulator import Emulator
from phone_farm.emulator import run_cmd
from phone_farm.web.qa_runner import start_qa_background
from phone_farm.web.state import AppState

router = APIRouter(prefix="/api")

DEFAULT_CONFIG = Path("phone-farm.toml")
UPLOAD_DIR = Path("./uploads")
SCREENSHOT_DIR = Path("./screenshots")

# Injected by app.py at startup
_state: AppState | None = None


def _get_state() -> AppState:
    """Get the global app state."""
    if _state is None:
        raise RuntimeError("State not initialized")
    return _state


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
            {"slot": p.slot, "adb_serial": p.adb_serial, "status": p.status}
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
        if not DEFAULT_CONFIG.exists():
            state.phones[slot].status = "error"
            return JSONResponse({"error": "Config not found"}, status_code=500)

        config = load_config(DEFAULT_CONFIG)
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
        state.phones[slot].emulator = emu
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

    phone = state.phones[slot]
    if phone.emulator:
        await phone.emulator.stop()
    else:
        # Fallback: kill via ADB if no stored emulator instance
        try:
            await run_cmd(
                ["adb", "-s", phone.adb_serial, "emu", "kill"],
                timeout=10,
            )
        except Exception:
            pass

    state.remove_phone(slot)
    return JSONResponse({"status": "stopped"})


@router.get("/phones/{slot}/screenshot", response_model=None)
async def phone_screenshot(slot: int):
    """Get a screenshot from a phone."""
    state = _get_state()
    if slot not in state.phones:
        return JSONResponse({"error": "Phone not found"}, status_code=404)

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"phone-{slot}.png"
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
    mode: str = Form("deterministic"),
    test_email: str = Form(""),
    test_password: str = Form(""),
    skip_login: str = Form(""),
) -> JSONResponse:
    """Upload APK and start a QA test.

    Saves the APK to disk, then launches a background task that:
    1. Boots an emulator
    2. Installs the APK
    3. Runs automated QA exploration
    4. Generates a bug report
    """
    state = _get_state()

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    apk_path = UPLOAD_DIR / apk.filename
    with open(apk_path, "wb") as f:
        content = await apk.read()
        f.write(content)

    use_ai = mode == "ai" and state.anthropic_api_key is not None
    run_id = state.start_test_run(apk.filename, description)

    # Attach optional login credentials to the run for use by the QA runner
    run = state.test_runs[run_id]
    run.test_email = test_email
    run.test_password = test_password
    run.skip_login = skip_login == "1"

    try:
        start_qa_background(
            state, run_id, apk_path,
            api_key=state.anthropic_api_key if use_ai else None,
        )
    except RuntimeError as e:
        state.test_runs[run_id].status = "error"
        state.test_runs[run_id].error_message = str(e)
        return JSONResponse(
            {"run_id": run_id, "status": "error", "error": str(e)},
            status_code=500,
        )

    mode_label = "AI" if use_ai else "deterministic"

    return HTMLResponse(
        f'<div class="py-3 border-b border-border">'
        f'<div class="flex justify-between text-sm">'
        f'<span class="font-mono">{apk.filename}</span>'
        f'<span class="text-warn">running ({mode_label})</span>'
        f'</div>'
        f'<div class="flex gap-4 mt-1 text-xs text-gray-500">'
        f'<span>Steps: 0</span><span>Screens: 0</span><span>Bugs: 0</span>'
        f'</div>'
        f'<button hx-post="/api/qa/stop/{run_id}" hx-swap="none" '
        f'class="mt-2 text-xs text-accent hover:underline">Stop</button>'
        f'</div>'
    )


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
        "report_path": run.report_path,
        "error": run.error_message,
        "started_at": run.started_at,
    })


@router.post("/qa/stop/{run_id}")
async def stop_qa_test(run_id: str) -> JSONResponse:
    """Stop a running QA test."""
    state = _get_state()
    if run_id not in state.test_runs:
        return JSONResponse({"error": "Test not found"}, status_code=404)

    run = state.test_runs[run_id]
    run.status = "stopped"
    # Cancel the background task if still running
    if run.task and not run.task.done():
        run.task.cancel()
    return JSONResponse({"status": "stopped"})


@router.post("/settings/api-key")
async def set_api_key(api_key: str = Form("")) -> HTMLResponse:
    """Save or clear the Anthropic API key."""


    state = _get_state()
    if api_key and api_key.startswith("sk-"):
        state.anthropic_api_key = api_key
        return HTMLResponse(
            '<div class="flex items-center gap-2 mb-3">'
            '<span class="text-success">&#10004;</span>'
            '<span class="text-success font-bold">Pro mode active</span>'
            '</div>'
            '<p class="text-gray-500 text-sm">API key saved. AI-powered exploration is now enabled.</p>'
            '<p class="text-gray-500 text-xs mt-1">Reload the QA Test page to see Pro mode.</p>'
        )
    state.anthropic_api_key = None
    return HTMLResponse(
        '<p class="text-gray-400 text-sm mb-3">'
        'API key removed. Using deterministic exploration.'
        '</p>'
        '<p class="text-gray-500 text-xs">Reload this page to re-add a key.</p>'
    )


@router.get("/qa/history")
async def qa_history() -> JSONResponse:
    """Return past QA runs from DB (or current in-memory runs if no DB)."""
    state = _get_state()
    if state.db is not None:
        runs = await state.db.load_runs()
        return JSONResponse({"runs": runs})
    return JSONResponse({"runs": [
        {"run_id": k, "status": v.status, "apk_name": v.apk_name}
        for k, v in state.test_runs.items()
    ]})


@router.get("/qa/report/{run_id}", response_model=None)
async def get_qa_report(run_id: str, format: str = "html") -> Response:
    """Download QA report. format=html (default) or json."""
    state = _get_state()
    run = state.test_runs.get(run_id)
    if not run:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    if format == "json" and run.report_path:
        path = Path(run.report_path)
        if path.exists():
            return FileResponse(str(path), media_type="application/json")
    if run.html_report_path:
        path = Path(run.html_report_path)
        if path.exists():
            return FileResponse(str(path), media_type="text/html")
    return JSONResponse({"error": "Report not available"}, status_code=404)
