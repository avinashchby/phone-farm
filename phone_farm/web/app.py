"""FastAPI web application for Phone Farm dashboard."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from phone_farm.web import api as api_module
from phone_farm.web.state import AppState

TEMPLATE_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Phone Farm", version="0.1.0")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

state = AppState()
state.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

# Wire up API routes with shared state
api_module._state = state
app.include_router(api_module.router)


@app.get("/", response_class=HTMLResponse)
async def qa_test_page(request: Request) -> HTMLResponse:
    """QA Test home page."""
    return templates.TemplateResponse(
        request, "qa_test.html",
        {"active_tab": "qa", "state": state},
    )


@app.get("/phones", response_class=HTMLResponse)
async def phones_page(request: Request) -> HTMLResponse:
    """Phones management page."""
    return templates.TemplateResponse(
        request, "phones.html",
        {"active_tab": "phones", "state": state},
    )


@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request) -> HTMLResponse:
    """Reports page."""
    return templates.TemplateResponse(
        request, "reports.html",
        {"active_tab": "reports", "state": state},
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    """Settings page."""
    return templates.TemplateResponse(
        request, "settings.html",
        {"active_tab": "settings", "state": state},
    )


@app.get("/api/health/html", response_class=HTMLResponse)
async def health_html() -> HTMLResponse:
    """HTMX partial: health check results as HTML."""
    from phone_farm.doctor import Doctor

    doc = Doctor()
    results = await doc.check_all()
    html = ""
    for r in results:
        icon = "&#10004;" if r.ok else "&#10008;"
        color = "text-success" if r.ok else "text-accent"
        html += (
            f'<div class="flex justify-between py-2 border-b border-border">'
            f'<span class="{color}">{icon} {r.name}</span>'
            f'<span class="text-gray-500 text-sm">{r.message}</span></div>'
        )
    return HTMLResponse(html)


@app.get("/api/phones/grid", response_class=HTMLResponse)
async def phones_grid(request: Request) -> HTMLResponse:
    """HTMX partial: phone grid cards."""
    html_parts = []
    for phone in state.phones.values():
        resp = templates.TemplateResponse(
            request, "partials/phone_card.html",
            {"phone": phone},
        )
        html_parts.append(resp.body.decode())
    # Add phone button
    html_parts.append(
        '<div class="bg-card border border-border rounded-lg p-3 text-center opacity-50 '
        'cursor-pointer hover:opacity-100 transition" hx-post="/api/phones/boot" hx-swap="none">'
        '<div class="bg-border h-32 rounded mb-2 flex items-center justify-center">'
        '<span class="text-2xl">+</span></div><div>Add Phone</div></div>'
    )
    return HTMLResponse("".join(html_parts))
