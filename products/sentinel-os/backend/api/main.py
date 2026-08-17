import importlib
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.api.control import (
    get_autonomous_status,
    get_goals,
    get_telemetry,
    get_workers,
    run_autonomous_cycle,
)
from sentinel_platform.backend.agents.autonomous_developer import AutonomousDeveloper
from sentinel_platform.backend.agents.orchestrator import Orchestrator
from sentinel_platform.backend.agents.task_queue import TaskQueue
from sentinel_platform.backend.agents.worker_selector import WorkerSelector
from sentinel_platform.backend.telemetry.execution_telemetry import ExecutionTelemetry
from sentinel_platform.backend.core.config import PROJECT_ROOT
from backend.dashboard.operations_dashboard import (
    build_dashboard_snapshot,
    load_goals,
    load_queue_status,
    load_telemetry,
)


BACKEND_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BACKEND_DIR / "static"
TEMPLATES_DIR = BACKEND_DIR / "templates"

ROUTES_DIR = Path(__file__).resolve().parent / "routes"
MODULE_PREFIX = "backend.api.routes"


app = FastAPI(
    title="Sentinel OS API",
    version="2.0.0"
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    return {
        "status": "online",
        "framework": "Sentinel OS",
        "version": "2.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/autonomous/run")
def autonomous_run():
    return run_autonomous_cycle(
        project_root=PROJECT_ROOT,
        developer_cls=AutonomousDeveloper,
        orchestrator_cls=Orchestrator,
    )


@app.get("/autonomous/status")
def autonomous_status():
    return get_autonomous_status(task_queue_cls=TaskQueue)


@app.get("/telemetry")
def telemetry():
    return get_telemetry(telemetry_cls=ExecutionTelemetry)


@app.get("/workers")
def workers():
    return get_workers(worker_selector_cls=WorkerSelector)


@app.get("/goals")
def goals():
    return get_goals(project_root=PROJECT_ROOT, developer_cls=AutonomousDeveloper)



def _base_context(**kwargs):
    context = {"current_year": datetime.utcnow().year}
    context.update(kwargs)
    return context


def _compute_dashboard_metrics(snapshot):
    telemetry_entries = snapshot.get("telemetry", [])
    positive = sum(
        1
        for entry in telemetry_entries
        if entry.get("status") in {"running", "completed", "success", "submitted"}
    )

    if telemetry_entries:
        score = 70 + int((positive / max(len(telemetry_entries), 1)) * 25)
    else:
        score = 72

    capabilities = snapshot.get("capabilities", [])
    subscription_status = "Enterprise ativo" if any(
        capability.get("status") == "active" for capability in capabilities
    ) else "Trial em avaliação"

    queue_status = snapshot.get("queue_status", {})

    return {
        "active_workers": len(snapshot.get("workers", [])),
        "ats_score": min(score, 99),
        "subscription_status": subscription_status,
        "pending_tasks": queue_status.get("queue_length", 0),
    }


def _render_ats_page(request: Request, submission: SimpleNamespace | None = None):
    telemetry_entries = list(reversed(load_telemetry(project_root=PROJECT_ROOT)))
    queue_status = load_queue_status(project_root=PROJECT_ROOT)
    goals_list = load_goals(project_root=PROJECT_ROOT)

    context = _base_context(
        request=request,
        telemetry=telemetry_entries,
        queue_status=queue_status,
        goals=goals_list,
        submission=submission,
    )

    return templates.TemplateResponse(request, "ats.html", context)


@app.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request):
    snapshot = build_dashboard_snapshot(project_root=PROJECT_ROOT)
    context = _base_context(
        request=request,
        snapshot=snapshot,
        metrics=_compute_dashboard_metrics(snapshot),
    )

    return templates.TemplateResponse(request, "dashboard.html", context)


@app.get("/ats", response_class=HTMLResponse, name="ats_module")
def ats_module(request: Request):
    return _render_ats_page(request)


@app.post("/ats", response_class=HTMLResponse, name="ats_module_submit")
async def ats_module_submit(
    request: Request,
    candidate_name: str = Form(...),
    target_role: str = Form(...),
    notes: str = Form(""),
    resume: UploadFile | None = File(None),
):
    timestamp = datetime.utcnow().isoformat()
    task_payload = {
        "type": "ats_review",
        "candidate": candidate_name,
        "role": target_role,
        "notes": notes,
        "resume_filename": resume.filename if resume and resume.filename else None,
        "received_at": timestamp,
    }

    TaskQueue().add_task(task_payload)

    ExecutionTelemetry(log_path=PROJECT_ROOT / "backend" / "telemetry" / "execution_log.json").log_execution(
        goal=f"ATS triage for {candidate_name}",
        task=task_payload,
        worker="ats-ingestion",
        start_time=timestamp,
        end_time=timestamp,
        status="submitted",
    )

    submission = SimpleNamespace(
        candidate_name=candidate_name,
        target_role=target_role,
    )

    return _render_ats_page(request, submission=submission)


def register_routes(app, routes_dir=ROUTES_DIR, module_prefix=MODULE_PREFIX):
    for route_file in sorted(routes_dir.glob("*.py")):
        if route_file.name.startswith("__") or route_file.name == "main.py":
            continue

        module_name = f"{module_prefix}.{route_file.stem}"
        module = importlib.import_module(module_name)
        router = getattr(module, "router", None)

        if router is not None:
            app.include_router(router, prefix="/api")

    return app


register_routes(app)

# Rota de redirecionamento/proxy para o Pricing do Career
from fastapi.responses import RedirectResponse

@app.get("/pricing")
async def pricing_page_redirect():
    return RedirectResponse(url="/career/pricing", status_code=303)

# --- INTEGRAÇÃO COM SENTINEL CAREER ---
try:
    from products.sentinel_career.backend.app.main import app as career_app
    app.mount("/career", career_app)
    print("Módulo Sentinel Career montado com sucesso em /career")
except Exception as e:
    print(f"Erro ao montar o Sentinel Career: {e}")
