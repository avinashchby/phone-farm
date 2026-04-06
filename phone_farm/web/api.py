"""REST API endpoints for Phone Farm dashboard."""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse

from phone_farm.config import load_config
from phone_farm.doctor import Doctor
from phone_farm.emulator import Emulator, run_cmd
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

    run_id = state.start_test_run(apk.filename, description)

    try:
        start_qa_background(state, run_id, apk_path)
    except RuntimeError as e:
        state.test_runs[run_id].status = "error"
        state.test_runs[run_id].error_message = str(e)
        return JSONResponse(
            {"run_id": run_id, "status": "error", "error": str(e)},
            status_code=500,
        )

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


@router.get("/qa/report/{run_id}", response_model=None)
async def get_qa_report(run_id: str):
    """Download the QA report JSON for a completed test."""
    state = _get_state()
    if run_id not in state.test_runs:
        return JSONResponse({"error": "Test not found"}, status_code=404)

    run = state.test_runs[run_id]
    if not run.report_path or not Path(run.report_path).exists():
        return JSONResponse({"error": "Report not ready"}, status_code=404)

    return FileResponse(
        run.report_path,
        media_type="application/json",
        filename=f"qa-report-{run_id}.json",
    )
