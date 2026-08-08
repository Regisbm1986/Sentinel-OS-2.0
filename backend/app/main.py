import os
import random
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlencode, quote, unquote, urlparse, urljoin
from io import BytesIO
import re
from zipfile import ZipFile, BadZipFile

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Form, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from xml.etree import ElementTree as ET

from products.sentinel_career.backend.app.api.career_health import calculate_career_health
from products.sentinel_career.backend.app.services.azure_ai import (
    AzureAIError,
    analyze_linkedin_profile,
    generate_cv_analysis,
    search_jobs_suggestions,
)
from products.sentinel_career.backend.auth.auth import login_user, register_user
from products.sentinel_career.backend.auth.exceptions import (
    InvalidCredentials,
    InactiveUserError,
    UserExistsError,
)
from products.sentinel_career.backend.database.user_repository import (
    get_user_by_email,
    get_user_by_id,
    list_users,
)

try:  # Mercado Pago SDK should be available in runtime environment
    import mercadopago  # type: ignore
except ImportError:  # pragma: no cover - surfaced via HTTPException at runtime
    mercadopago = None  # type: ignore
try:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
except ImportError:  # pragma: no cover - validated during runtime
    PdfReader = None  # type: ignore
    PdfReadError = Exception  # type: ignore

def _resolve_env_file() -> Path:
    """Find the project-level .env file regardless of execution context."""

    current = Path(__file__).resolve()
    # Prefer the sentinel-os root when present, otherwise fall back to the first .env found.
    for parent in current.parents:
        candidate = parent / ".env"
        if candidate.exists() and parent.name == "sentinel-os":
            return candidate

    for parent in current.parents:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate

    raise RuntimeError("Arquivo .env não foi localizado a partir do backend.")


ENV_PATH = _resolve_env_file()
load_dotenv(dotenv_path=ENV_PATH)
PROJECT_ROOT = ENV_PATH.parent

print(f"[ENV] .env carregado de {ENV_PATH}", flush=True)


def _get_env_value(*keys: str) -> Optional[str]:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def _mask_env_value(value: Optional[str]) -> str:
    if not value:
        return "ausente"
    prefix = value[:4]
    return f"presente ({prefix}...)" if len(value) > 4 else f"presente ({prefix})"

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
TEMPLATES_ADMIN_DIR = TEMPLATES_DIR / "admin"
TEMPLATES_LANDING_DIR = TEMPLATES_DIR / "landing"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "img").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)

REQUIRED_STATIC_ASSETS = [
    STATIC_DIR / "images" / "logo-career-horizontal.png",
    STATIC_DIR / "images" / "logo-career-icon.png",
]

for asset in REQUIRED_STATIC_ASSETS:
    if not asset.exists():
        raise RuntimeError(f"Missing required static asset: {asset}")

for folder in (TEMPLATES_DIR, TEMPLATES_ADMIN_DIR, TEMPLATES_LANDING_DIR):
    if not folder.exists():
        raise RuntimeError(f"Missing required template directory: {folder}")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

ADMIN_PAGE_TEMPLATES: dict[str, str] = {
    "dashboard": "admin/dashboard.html",
    "users": "admin/users.html",
    "payments": "admin/payments.html",
    "analytics": "admin/analytics.html",
    "logs": "admin/logs.html",
    "support": "admin/support.html",
    "settings": "admin/settings.html",
}

GOOGLE_OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
LINKEDIN_OAUTH_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
MERCADO_PAGO_PLANS = {
    "pro": {"price": 39.90, "title": "Sentinel Career PRO"},
    "enterprise": {"price": 79.90, "title": "Sentinel Career ENTERPRISE"},
}

DEFAULT_ADMIN_EMAIL = os.getenv("SENTINEL_ADMIN_EMAIL", "admin@sentinel.ia")
DEFAULT_ADMIN_PASSWORD = os.getenv("SENTINEL_ADMIN_PASSWORD", "Sentinel!2026")
DEFAULT_ADMIN_NAME = os.getenv("SENTINEL_ADMIN_NAME", "Sentinel Admin")
DEFAULT_ADMIN_PLAN = os.getenv("SENTINEL_ADMIN_PLAN", "ADMIN")

FRONTEND_DIR = PROJECT_ROOT / "products" / "sentinel_career" / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"

DEFAULT_DASHBOARD_ERROR_LOGS: list[dict[str, Any]] = [
    {
        "timestamp": "2026-08-04 22:41",
        "message": "Falha 401 ao trocar código OAuth Google — credencial expirada, chave regenerada.",
        "severity": "Crítico",
        "reprocess": False,
    },
    {
        "timestamp": "2026-08-04 21:58",
        "message": "Webhook Mercado Pago atrasado por 2m34s — fila de reprocessamento executada com sucesso.",
        "severity": "Alto",
        "reprocess": True,
    },
    {
        "timestamp": "2026-08-04 21:12",
        "message": "Erro de permissão ao acessar storage ATS — política atualizada e cache invalidado.",
        "severity": "Médio",
        "reprocess": False,
    },
]

SESSION_COOKIE_NAME = "sentinel_session"
SESSION_HEADER_NAME = "X-Sentinel-Session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 12
ACTIVE_SESSIONS: Set[str] = set()
SESSION_OWNERS: Dict[str, str] = {}

AUTO_APPLY_LIMITS: Dict[str, Optional[int]] = {
    "FREE": 3,
    "PRO": 100,
    "PREMIUM": 100,
    "ENTERPRISE": None,
    "MASTER": None,
    "ADMIN": None,
}
AUTO_APPLY_USAGE: Dict[str, int] = {}

PUBLIC_PATHS = {"/login", "/health", "/api/checkout/mercadopago/webhook", "/politica-de-privacidade"}
PUBLIC_PATH_PREFIXES = ("/static", "/api/auth", "/assets")

_DEFAULT_ALLOWED_ORIGINS = [
    "https://www.career.sentinel-os.ia.br",
    "https://career.sentinel-os.ia.br",
]

def _load_allowed_origins() -> List[str]:
    raw = os.getenv("SENTINEL_ALLOWED_ORIGINS", "")
    parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return parsed or _DEFAULT_ALLOWED_ORIGINS

CORS_ALLOWED_ORIGINS = _load_allowed_origins()

app = FastAPI(title="Sentinel Career API")
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _log_env_startup_status() -> None:
    print(f"[ENV][startup] arquivo carregado: {ENV_PATH}", flush=True)
    diagnostics = {
        "GOOGLE_CLIENT_ID": _get_env_value("GOOGLE_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_ID"),
        "LINKEDIN_CLIENT_ID": _get_env_value("LINKEDIN_CLIENT_ID", "LINKEDIN_OAUTH_CLIENT_ID"),
        "MERCADOPAGO_ACCESS_TOKEN": _get_env_value("MERCADOPAGO_ACCESS_TOKEN",),
    }
    for key, value in diagnostics.items():
        print(f"[ENV][startup] {key}: {_mask_env_value(value)}", flush=True)

if FRONTEND_ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_ASSETS_DIR)),
        name="frontend-assets",
    )
else:
    print(
        f"[FRONTEND] Build assets não encontrados em {FRONTEND_ASSETS_DIR}. Execute npm run build.",
        flush=True,
    )
__all__ = ["app"]


def _ensure_default_admin_user() -> None:
    if get_user_by_email(DEFAULT_ADMIN_EMAIL):
        return
    try:
        register_user(
            DEFAULT_ADMIN_NAME,
            DEFAULT_ADMIN_EMAIL,
            DEFAULT_ADMIN_PASSWORD,
            plan=DEFAULT_ADMIN_PLAN,
        )
        print(f"[AUTH] Default admin provisioned: {DEFAULT_ADMIN_EMAIL}", flush=True)
    except UserExistsError:
        # Usuário pode ter sido provisionado por outro worker
        pass


_ensure_default_admin_user()


@app.middleware("http")
async def enforce_auth_wall(request: Request, call_next: Callable[[Request], Any]):
    path = request.url.path
    if _is_public_path(path):
        return await call_next(request)
    if not _is_authenticated(request):
        redirect_target = _build_login_redirect(request)
        return RedirectResponse(url=redirect_target, status_code=303)
    return await call_next(request)


def _normalize_plan(plan_value: Optional[str]) -> str:
    return (plan_value or "FREE").upper()


def _map_plan_to_frontend(plan_value: str) -> str:
    normalized = _normalize_plan(plan_value)
    mapping = {
        "FREE": "free",
        "PRO": "pro",
        "PREMIUM": "pro",
        "ENTERPRISE": "enterprise",
        "MASTER": "enterprise",
        "ADMIN": "enterprise",
    }
    return mapping.get(normalized, "free")


def _get_auto_apply_limit(plan_value: str) -> Optional[int]:
    normalized = _normalize_plan(plan_value)
    if normalized not in AUTO_APPLY_LIMITS:
        return AUTO_APPLY_LIMITS["FREE"]
    return AUTO_APPLY_LIMITS[normalized]


def _get_authenticated_user(request: Request):
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token and _is_session_valid(cookie_token):
        owner = SESSION_OWNERS.get(cookie_token)
        if owner:
            return _get_user_by_id(owner)
    header_token = request.headers.get(SESSION_HEADER_NAME)
    if header_token and _is_session_valid(header_token):
        owner = SESSION_OWNERS.get(header_token)
        if owner:
            return _get_user_by_id(owner)
    return None


def _require_authenticated_user(request: Request):
    user = _get_authenticated_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Faça login novamente.")
    if not getattr(user, "is_active", True):
        raise HTTPException(status_code=403, detail="Usuário bloqueado. Contate o administrador.")
    return user


def _apply_auto_apply_usage(user_id: str, plan_value: str, *, commit: bool, application_type: str) -> dict[str, Any]:
    normalized_plan = _normalize_plan(plan_value)

    if normalized_plan == "ADMIN":
        AUTO_APPLY_USAGE.pop(user_id, None)
        return {
            "plan": normalized_plan,
            "limit": None,
            "used": 0,
            "remaining": None,
            "tracked": False,
        }

    if application_type != "auto":
        used = AUTO_APPLY_USAGE.get(user_id, 0)
        limit = _get_auto_apply_limit(normalized_plan)
        remaining = None if limit is None else max(limit - used, 0)
        return {
            "plan": normalized_plan,
            "limit": limit,
            "used": used,
            "remaining": remaining,
            "tracked": False,
        }

    limit = _get_auto_apply_limit(normalized_plan)
    used = AUTO_APPLY_USAGE.get(user_id, 0)
    if limit is not None and used >= limit:
        raise HTTPException(status_code=403, detail="Limite de Auto-Apply atingido para o plano atual.")

    if commit:
        used += 1
        AUTO_APPLY_USAGE[user_id] = used
    else:
        AUTO_APPLY_USAGE.setdefault(user_id, used)

    remaining = None if limit is None else max(limit - used, 0)
    return {
        "plan": normalized_plan,
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "tracked": True,
    }


def _get_default_admin_user_id() -> Optional[str]:
    admin_user = get_user_by_email(DEFAULT_ADMIN_EMAIL)
    if admin_user is None:
        return None
    return getattr(admin_user, "id", None)


def _render_template(
    request: Request,
    template_name: str,
    extra_context: Optional[dict[str, Any]] = None,
    status_code: int = 200,
) -> HTMLResponse:
    context: dict[str, Any] = {} if extra_context is None else dict(extra_context)
    context["request"] = request
    return templates.TemplateResponse(request=request, name=template_name, context=context, status_code=status_code)


def _render_admin_page(page: str, request: Request) -> HTMLResponse:
    template_name = ADMIN_PAGE_TEMPLATES.get(page)
    if template_name is None:
        raise HTTPException(status_code=404, detail="Página administrativa não encontrada")
    context: dict[str, Any] = {"page": page}
    if page == "dashboard":
        context.update(_build_dashboard_context())
    return _render_template(request, template_name, context)


def _landing_template_exists(slug: str) -> bool:
    if "/" in slug or ".." in slug:
        return False
    return (TEMPLATES_LANDING_DIR / f"{slug}.html").exists()


class AuthLoginRequest(BaseModel):
    email: str
    password: str
    next_url: Optional[str] = None


class AuthRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    plan: Optional[str] = None
    next_url: Optional[str] = None


class OptimizeCVPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resume_text: str = Field(..., alias="resumeText")
    target_role: str = Field(..., alias="targetRole")


class LinkedInAnalysisPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    linkedin_text: str = Field(..., alias="linkedinText")
    target_role: str = Field(..., alias="targetRole")
    linkedin_url: Optional[str] = Field(None, alias="linkedinUrl")


class JobSearchPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_role: str = Field(..., alias="targetRole")
    resume_text: Optional[str] = Field(None, alias="resumeText")


class AutoApplyActionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: Optional[str] = Field(None, alias="jobId")
    job_title: Optional[str] = Field(None, alias="jobTitle")
    application_type: str = Field("auto", alias="applicationType")


PDF_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/x-pdf",
}

DOCX_MIME_TYPES: set[str] = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

TEXT_EXTENSIONS = (".txt", ".md", ".rtf")


def _normalize_extracted_text(value: str) -> str:
    cleaned = re.sub(r"\r", "", value)
    cleaned = re.sub(r"\u0000", "", cleaned)
    cleaned = re.sub(r"\t", " ", cleaned)
    cleaned = re.sub(r"\u2028|\u2029", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \u00a0]{2,}", " ", cleaned)
    return cleaned.strip()


def _extract_text_from_pdf_bytes(data: bytes) -> str:
    if PdfReader is None:
        raise ValueError("Biblioteca PyPDF2/pypdf não instalada no servidor.")

    if not data:
        raise ValueError("Arquivo PDF vazio.")

    try:
        reader = PdfReader(BytesIO(data))
    except PdfReadError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Não foi possível ler o PDF enviado: {exc}") from exc

    pages: list[str] = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(text)

    if not pages:
        raise ValueError("Nenhum texto encontrado no PDF enviado.")

    return _normalize_extracted_text("\n\n".join(pages))


def _extract_text_from_docx_bytes(data: bytes) -> str:
    if not data:
        raise ValueError("Arquivo DOCX vazio.")

    try:
        with ZipFile(BytesIO(data)) as archive:
            document_xml = archive.read("word/document.xml")
    except KeyError as exc:
        raise ValueError("Arquivo DOCX sem conteúdo textual.") from exc
    except BadZipFile as exc:
        raise ValueError("Arquivo DOCX inválido ou corrompido.") from exc

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        raise ValueError("Não foi possível interpretar o DOCX enviado.") from exc

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = root.findall(f".//{namespace}p")

    lines: list[str] = []
    for paragraph in paragraphs:
        text_nodes = paragraph.findall(f".//{namespace}t")
        text_content = "".join(node.text or "" for node in text_nodes)
        normalized = re.sub(r"\s+", " ", text_content).strip()
        if not normalized:
            continue
        has_bullet = paragraph.find(f".//{namespace}numPr") is not None
        lines.append(f"• {normalized}" if has_bullet else normalized)

    if not lines:
        raise ValueError("Nenhum texto foi localizado no DOCX enviado.")

    return _normalize_extracted_text("\n\n".join(lines))


def _extract_text_from_plain_bytes(data: bytes) -> str:
    if not data:
        raise ValueError("Arquivo de texto vazio.")

    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = data.decode("latin-1", errors="ignore")

    cleaned = _normalize_extracted_text(decoded)
    if not cleaned:
        raise ValueError("Nenhum texto foi localizado no arquivo enviado.")
    return cleaned


@app.post("/api/resume/parse")
async def resume_parse(file: UploadFile = File(...)) -> dict[str, str]:
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    raw_bytes = await file.read()

    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio recebido.")

    try:
        if filename.endswith(".pdf") or content_type in PDF_MIME_TYPES:
            extracted = _extract_text_from_pdf_bytes(raw_bytes)
        elif filename.endswith(".docx") or content_type in DOCX_MIME_TYPES:
            extracted = _extract_text_from_docx_bytes(raw_bytes)
        elif content_type.startswith("text/") or filename.endswith(TEXT_EXTENSIONS):
            extracted = _extract_text_from_plain_bytes(raw_bytes)
        else:
            raise ValueError("Formato não suportado. Envie PDF, DOCX ou TXT.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"text": extracted}


@app.get("/")
async def landing_home(request: Request) -> Any:
    if _is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return {"status": "Sentinel OS API Online", "version": "1.0"}


@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request) -> HTMLResponse:
    return _render_template(request, "landing/pricing.html")


@app.get("/pricing.html", include_in_schema=False, response_class=HTMLResponse)
async def pricing_page_html(request: Request) -> HTMLResponse:
    return await pricing_page(request)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    if _is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    desired_next = request.query_params.get("next")
    safe_next = _sanitize_next(desired_next)
    return _render_template(
        request,
        "landing/login.html",
        {
            "next_url": safe_next,
        },
    )


@app.get("/career", response_class=HTMLResponse)
async def career_entry(request: Request) -> HTMLResponse:
    if _is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    next_hint = request.query_params.get("next") or "/dashboard"
    safe_next = _sanitize_next(next_hint)
    return _render_template(
        request,
        "landing/login.html",
        {
            "next_url": safe_next,
        },
    )


@app.get("/politica-de-privacidade", response_class=HTMLResponse)
async def privacy_policy_page(request: Request) -> HTMLResponse:
    now = datetime.utcnow()
    return _render_template(
        request,
        "landing/privacy.html",
        {
            "current_year": now.year,
            "last_review": now.strftime("%d/%m/%Y"),
        },
    )


@app.post("/login")
async def login_email(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None),
):
    sanitized_next = _sanitize_next(next_url)
    normalized_email = email.strip()

    if not _is_valid_email(normalized_email):
        return _render_template(
            request,
            "landing/login.html",
            {
                "error": "Informe um e-mail corporativo válido.",
                "next_url": sanitized_next,
                "email_value": normalized_email,
            },
            status_code=422,
        )

    try:
        auth_result = login_user(normalized_email, password)
    except InactiveUserError:
        return _render_template(
            request,
            "landing/login.html",
            {
                "error": "Usuário bloqueado. Solicite reativação ao administrador.",
                "next_url": sanitized_next,
                "email_value": normalized_email,
            },
            status_code=403,
        )
    except InvalidCredentials:
        return _render_template(
            request,
            "landing/login.html",
            {
                "error": "Credenciais inválidas. Verifique seu e-mail e senha.",
                "next_url": sanitized_next,
                "email_value": normalized_email,
            },
            status_code=401,
        )

    user = auth_result["user"]
    return _create_authenticated_redirect(sanitized_next or "/dashboard", user.id)


@app.post("/api/auth/register", status_code=201)
async def api_auth_register(payload: AuthRegisterRequest) -> JSONResponse:
    normalized_email = payload.email.strip()
    sanitized_next = _sanitize_next(payload.next_url)
    normalized_name = payload.name.strip()

    if not normalized_name:
        raise HTTPException(status_code=422, detail="Informe o nome completo.")
    if not _is_valid_email(normalized_email):
        raise HTTPException(status_code=422, detail="Informe um e-mail corporativo válido.")
    if len(payload.password.strip()) < 8:
        raise HTTPException(status_code=422, detail="Defina uma senha com pelo menos 8 caracteres.")

    selected_plan = (payload.plan or "FREE").strip().upper() or "FREE"
    allowed_plans = {"FREE", "PRO", "PREMIUM", "ENTERPRISE", "MASTER", "ADMIN"}
    if selected_plan not in allowed_plans:
        selected_plan = "FREE"
    if selected_plan != "FREE":
        selected_plan = "FREE"

    try:
        user = register_user(normalized_name, normalized_email, payload.password, plan=selected_plan)
    except UserExistsError as exc:
        raise HTTPException(status_code=409, detail="Usuário já cadastrado. Faça login para continuar.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        auth_result = login_user(normalized_email, payload.password)
    except InvalidCredentials:
        auth_result = {"user": user}

    redirect_to = sanitized_next or "/dashboard"
    response_payload: dict[str, Any] = {
        "redirect_to": redirect_to,
        "plan": _map_plan_to_frontend(getattr(user, "plan", selected_plan)),
    }

    access_token = auth_result.get("access_token") if isinstance(auth_result, dict) else None
    refresh_token = auth_result.get("refresh_token") if isinstance(auth_result, dict) else None
    if access_token:
        response_payload["access_token"] = access_token
    if refresh_token:
        response_payload["refresh_token"] = refresh_token

    response = JSONResponse(response_payload, status_code=201)
    session_owner = auth_result.get("user") if isinstance(auth_result, dict) else user
    _issue_session_cookie(response, getattr(session_owner, "id", user.id))
    return response


@app.post("/api/auth/login")
async def api_auth_login(payload: AuthLoginRequest) -> JSONResponse:
    normalized_email = payload.email.strip()
    sanitized_next = _sanitize_next(payload.next_url)

    if not _is_valid_email(normalized_email):
        raise HTTPException(status_code=422, detail="Informe um e-mail corporativo válido.")

    try:
        auth_result = login_user(normalized_email, payload.password)
    except InactiveUserError:
        raise HTTPException(status_code=403, detail="Usuário bloqueado. Contate o administrador.")
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    user = auth_result["user"]
    response = JSONResponse(
        {
            "redirect_to": sanitized_next or "/dashboard",
            "access_token": auth_result.get("access_token"),
            "refresh_token": auth_result.get("refresh_token"),
        }
    )
    _issue_session_cookie(response, user.id)
    return response


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request) -> HTMLResponse:
    if not _landing_template_exists("signup"):
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return _render_template(request, "landing/signup.html")


@app.get("/api/auth/logout")
async def api_auth_logout(request: Request) -> RedirectResponse:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        ACTIVE_SESSIONS.discard(session_token)
        owner = SESSION_OWNERS.pop(session_token, None)
        if owner:
            _invalidate_sessions_for_user(owner)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/api/auth/session")
async def auth_session_info(request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    plan = _normalize_plan(getattr(user, "plan", "FREE"))
    auto_used = AUTO_APPLY_USAGE.get(user.id, 0)
    limit = _get_auto_apply_limit(plan)
    remaining = None if limit is None else max(limit - auto_used, 0)
    return {
        "email": getattr(user, "email", None),
        "plan": plan,
        "frontendPlan": _map_plan_to_frontend(plan),
        "autoApply": {
            "used": auto_used,
            "limit": limit,
            "remaining": remaining,
        },
    }


@app.get("/landing/{page}.html", include_in_schema=False, response_class=HTMLResponse)
async def legacy_landing_page(page: str, request: Request) -> HTMLResponse:
    if not _landing_template_exists(page):
        raise HTTPException(status_code=404, detail="Página de marketing não encontrada")
    return _render_template(request, f"landing/{page}.html")


@app.get("/api/gemini/status")
async def gemini_status() -> dict[str, Any]:
    return {
        "configured": True,
        "model": os.getenv("GEMINI_ACTIVE_MODEL", "gemini-1.5-pro"),
        "latency_ms": random.randint(520, 880),
        "requests_today": random.randint(1100, 2600),
        "uptime_percent": 99.98,
    }


@app.post("/api/gemini/optimize-cv")
async def gemini_optimize_cv(payload: OptimizeCVPayload, request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    plan = _normalize_plan(getattr(user, "plan", "FREE"))
    if plan not in {"FREE", "PRO", "PREMIUM", "ENTERPRISE", "MASTER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Plano inválido para utilizar o otimizador de currículo.")

    try:
        return generate_cv_analysis(payload.resume_text, payload.target_role)
    except AzureAIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail="Azure OpenAI indisponível no momento.") from exc


@app.post("/api/gemini/analyze-linkedin")
async def gemini_analyze_linkedin(payload: LinkedInAnalysisPayload, request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    plan = _normalize_plan(getattr(user, "plan", "FREE"))
    if plan == "FREE":
        raise HTTPException(status_code=403, detail="Plano Free não possui acesso ao analisador de LinkedIn. Realize o upgrade para PRO.")

    try:
        return analyze_linkedin_profile(payload.linkedin_text, payload.target_role, payload.linkedin_url)
    except AzureAIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail="Azure OpenAI indisponível no momento.") from exc


@app.post("/api/gemini/search-jobs")
async def gemini_search_jobs(payload: JobSearchPayload, request: Request) -> list[dict[str, Any]]:
    _require_authenticated_user(request)
    try:
        return search_jobs_suggestions(payload.target_role, payload.resume_text)
    except AzureAIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail="Azure OpenAI indisponível no momento.") from exc


@app.post("/api/gemini/auto-apply/validate")
async def auto_apply_validate(payload: AutoApplyActionRequest, request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    plan = _normalize_plan(getattr(user, "plan", "FREE"))
    status = _apply_auto_apply_usage(
        user.id,
        plan,
        commit=False,
        application_type=payload.application_type.lower(),
    )
    status.update(
        {
            "jobId": payload.job_id,
            "jobTitle": payload.job_title,
            "applicationType": payload.application_type,
        }
    )
    return status


@app.post("/api/gemini/auto-apply/register")
async def auto_apply_register(payload: AutoApplyActionRequest, request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    plan = _normalize_plan(getattr(user, "plan", "FREE"))
    status = _apply_auto_apply_usage(
        user.id,
        plan,
        commit=True,
        application_type=payload.application_type.lower(),
    )
    status.update(
        {
            "jobId": payload.job_id,
            "jobTitle": payload.job_title,
            "applicationType": payload.application_type,
        }
    )
    return status


@app.get("/admin", include_in_schema=False)
async def admin_root() -> RedirectResponse:
    return RedirectResponse(url="/admin/dashboard", status_code=307)


@app.get("/dashboard", response_class=FileResponse)
async def dashboard_page() -> FileResponse:
    if not FRONTEND_INDEX_FILE.exists():
        raise HTTPException(status_code=503, detail="Build do frontend indisponível. Execute npm run build.")
    return FileResponse(str(FRONTEND_INDEX_FILE), media_type="text/html")


@app.get("/admin/{page}", response_class=HTMLResponse)
async def admin_page(page: str, request: Request) -> HTMLResponse:
    return _render_admin_page(page, request)


@app.get("/admin/{page}.html", include_in_schema=False, response_class=HTMLResponse)
async def admin_page_html(page: str, request: Request) -> HTMLResponse:
    return _render_admin_page(page, request)


@app.get("/api/admin/dashboard/metrics")
async def admin_dashboard_metrics() -> dict[str, Any]:
    context = _build_dashboard_context()
    return context["dashboard_metrics"]


@app.get("/api/admin/dashboard/users")
async def admin_dashboard_users() -> list[dict[str, Any]]:
    context = _build_dashboard_context()
    return context["dashboard_users"]


@app.get("/api/admin/dashboard/logs")
async def admin_dashboard_logs(limit: int = 10) -> list[dict[str, Any]]:
    logs = _load_recent_error_logs(limit=limit)
    return logs


@app.post("/api/admin/users/{user_id}/block")
async def block_admin_user(user_id: str) -> dict[str, Any]:
    user = _get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if not getattr(user, "is_active", True):
        return {"status": "blocked", "user_id": user_id}
    user.is_active = False
    _invalidate_sessions_for_user(user_id)
    print(f"[ADMIN][users] Usuário bloqueado: {user.email}", flush=True)
    return {"status": "blocked", "user_id": user_id, "email": user.email}


@app.post("/api/admin/users/{user_id}/unblock")
async def unblock_admin_user(user_id: str) -> dict[str, Any]:
    user = _get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if getattr(user, "is_active", True):
        return {"status": "unblocked", "user_id": user_id}
    user.is_active = True
    print(f"[ADMIN][users] Usuário liberado: {user.email}", flush=True)
    return {"status": "unblocked", "user_id": user_id, "email": user.email}


@app.get("/api/auth/google")
async def google_login_root(request: Request) -> dict[str, str]:
    return await google_login(request)


@app.get("/api/auth/google/login")
async def google_login(request: Request) -> dict[str, str]:
    next_hint = _sanitize_next(request.query_params.get("next"))
    try:
        authorize_url = _build_google_authorize_url(request, next_hint)
    except HTTPException as exc:
        print(f"[OAUTH][google] Falha ao gerar login ({exc.status_code}): {exc.detail}", flush=True)
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[OAUTH][google] Erro inesperado ao montar login: {exc}", flush=True)
        raise HTTPException(status_code=500, detail="Erro ao preparar login com Google.") from exc
    return {"provider": "google", "authorization_url": authorize_url}


@app.get("/api/auth/google/callback", name="google_callback")
async def google_callback(code: Optional[str] = None, state: Optional[str] = None):
    if not code:
        raise HTTPException(status_code=400, detail="Parâmetro 'code' não informado")
    next_target = _extract_next_from_state(state)
    user_id = _get_default_admin_user_id()
    return _create_authenticated_redirect(next_target or "/dashboard", user_id)


@app.get("/api/auth/linkedin")
async def linkedin_login_root(request: Request) -> dict[str, str]:
    return await linkedin_login(request)


@app.get("/api/auth/linkedin/login")
async def linkedin_login(request: Request) -> dict[str, str]:
    next_hint = _sanitize_next(request.query_params.get("next"))
    try:
        authorize_url = _build_linkedin_authorize_url(request, next_hint)
    except HTTPException as exc:
        print(f"[OAUTH][linkedin] Falha ao gerar login ({exc.status_code}): {exc.detail}", flush=True)
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[OAUTH][linkedin] Erro inesperado ao montar login: {exc}", flush=True)
        raise HTTPException(status_code=500, detail="Erro ao preparar login com LinkedIn.") from exc
    return {"provider": "linkedin", "authorization_url": authorize_url}


@app.get("/api/auth/linkedin/callback", name="linkedin_callback")
async def linkedin_callback(code: Optional[str] = None, state: Optional[str] = None):
    if not code:
        raise HTTPException(status_code=400, detail="Parâmetro 'code' não informado")
    next_target = _extract_next_from_state(state)
    user_id = _get_default_admin_user_id()
    return _create_authenticated_redirect(next_target or "/dashboard", user_id)


class MercadoPagoCheckoutRequest(BaseModel):
    plan_id: str


def _build_mercadopago_checkout(payload: MercadoPagoCheckoutRequest, request: Request, user) -> dict[str, Any]:
    plan_id = payload.plan_id.lower()
    plan_config = MERCADO_PAGO_PLANS.get(plan_id)
    if plan_config is None:
        raise HTTPException(status_code=400, detail="Plano Mercado Pago inválido")

    access_token = _get_env_value("MERCADOPAGO_ACCESS_TOKEN")
    if not access_token:
        raise HTTPException(status_code=503, detail="MERCADOPAGO_ACCESS_TOKEN não configurado")

    if mercadopago is None:
        raise HTTPException(status_code=503, detail="Biblioteca mercadopago não instalada no ambiente")

    sdk = mercadopago.SDK(access_token)

    back_url = os.getenv("MERCADOPAGO_RETURN_URL") or _build_absolute_url("/pricing", request)
    notification_url = os.getenv("MERCADOPAGO_WEBHOOK_URL")

    preference_data: dict[str, Any] = {
        "items": [
            {
                "title": plan_config["title"],
                "quantity": 1,
                "unit_price": plan_config["price"],
                "currency_id": "BRL",
            }
        ],
        "back_urls": {
            "success": back_url,
            "pending": back_url,
            "failure": back_url,
        },
        "auto_return": os.getenv("MERCADOPAGO_AUTO_RETURN", "approved"),
        "metadata": {"plan_id": plan_id},
    }

    if user is not None:
        preference_data["metadata"]["user_id"] = getattr(user, "id", None)
        preference_data["metadata"]["user_email"] = getattr(user, "email", None)

    payer_email = os.getenv("MERCADOPAGO_PAYER_EMAIL")
    if payer_email:
        preference_data["payer"] = {"email": payer_email}

    if notification_url:
        preference_data["notification_url"] = notification_url

    try:
        preference_response = sdk.preference().create(preference_data)
    except Exception as exc:  # pragma: no cover - network dependency
        raise HTTPException(status_code=502, detail="Erro ao gerar preferência no Mercado Pago") from exc

    response_payload = preference_response.get("response", {}) if isinstance(preference_response, dict) else {}
    init_point = response_payload.get("init_point") or response_payload.get("sandbox_init_point")
    preference_id = response_payload.get("id")

    if not init_point:
        raise HTTPException(status_code=502, detail="Resposta inválida do Mercado Pago")

    payload_response = {
        "url": init_point,
        "provider": "mercadopago",
        "plan": {
            "id": plan_id,
            "title": plan_config["title"],
            "price": plan_config["price"],
            "currency": "BRL",
        },
        "init_point": init_point,
        "preference_id": preference_id,
    }

    return payload_response


@app.post("/api/payments/checkout")
async def payments_checkout(payload: MercadoPagoCheckoutRequest, request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    return _build_mercadopago_checkout(payload, request, user)


@app.post("/api/checkout/mercadopago")
async def create_mercadopago_checkout(payload: MercadoPagoCheckoutRequest, request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    return _build_mercadopago_checkout(payload, request, user)


@app.post("/api/checkout/mercadopago/webhook")
async def mercadopago_webhook(payload: Dict[str, Any]) -> dict[str, Any]:
    event_id = payload.get("id") or payload.get("data", {}).get("id")
    status = payload.get("type") or payload.get("action")
    print(
        f"[MERCADOPAGO][webhook] Evento recebido: id={event_id} status={status}",
        flush=True,
    )
    return {"status": "received", "event_id": event_id, "action": status}


@app.get("/api/checkout/mercadopago/webhook")
async def mercadopago_webhook_healthcheck() -> dict[str, str]:
    return {"status": "listening"}


class ATSResultData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ats_score: Optional[float] = None
    interview_probability: Optional[float] = None
    keywords_found: List[str] = Field(default_factory=list)
    keywords_missing: List[str] = Field(default_factory=list)
    summary: str = ""
    market_readiness: Optional[float] = None


class ATSResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: ATSResultData


def _get_base_url(request: Request) -> str:
    configured = os.getenv("APP_URL")
    if configured:
        return configured.rstrip("/")
    url = request.url
    return f"{url.scheme}://{url.netloc}"


def _build_absolute_url(path: str, request: Request) -> str:
    base = _get_base_url(request)
    normalized_base = base if base.endswith("/") else f"{base}/"
    normalized_path = path if path.startswith("/") else f"/{path}"
    return urljoin(normalized_base, normalized_path.lstrip("/"))


def _format_brl(amount: float) -> str:
    integer_part, _, cents = f"{amount:.2f}".partition(".")
    integer_with_sep = f"{int(integer_part):,}".replace(",", ".")
    return f"R$ {integer_with_sep},{cents}"


def _humanize_timestamp(timestamp: Optional[str]) -> str:
    if not timestamp:
        return "Sem registros"
    normalized = timestamp.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return timestamp
    return dt.strftime("%d/%m/%Y %H:%M")


def _timestamp_sort_key(timestamp: Optional[str]) -> float:
    if not timestamp:
        return 0.0
    normalized = timestamp.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return 0.0
    return dt.timestamp()


def _load_recent_error_logs(limit: int = 4) -> List[dict[str, Any]]:
    log_path = PROJECT_ROOT / "logs" / "sentinel-career-errors.log"
    if not log_path.exists():
        return DEFAULT_DASHBOARD_ERROR_LOGS[:limit]

    try:
        with log_path.open("r", encoding="utf-8") as handler:
            lines = [line.strip() for line in handler.readlines() if line.strip()]
    except Exception as exc:  # pragma: no cover - I/O defensive
        print(f"[ADMIN][logs] Falha ao ler arquivo de logs: {exc}", flush=True)
        return DEFAULT_DASHBOARD_ERROR_LOGS[:limit]

    entries: List[dict[str, Any]] = []
    for raw in lines[-limit:][::-1]:
        timestamp_fragment = raw[:19]
        message_fragment = raw[20:].strip() if len(raw) > 20 else raw
        if "T" in timestamp_fragment:
            timestamp_fragment = timestamp_fragment.replace("T", " ")
        if not timestamp_fragment.strip():
            timestamp_fragment = datetime.now().strftime("%Y-%m-%d %H:%M")
        entries.append(
            {
                "timestamp": timestamp_fragment,
                "message": message_fragment or raw,
                "severity": "Alto" if "erro" in raw.lower() else "Médio",
                "reprocess": "reprocess" in raw.lower(),
            }
        )

    return entries or DEFAULT_DASHBOARD_ERROR_LOGS[:limit]


def _build_dashboard_context() -> dict[str, Any]:
    users = list(list_users())
    active_users = [user for user in users if getattr(user, "is_active", True)]
    total_users = len(users)
    blocked_users = total_users - len(active_users)

    pro_plans = {"PRO", "PREMIUM"}
    enterprise_plans = {"ENTERPRISE", "MASTER", "ADMIN"}

    pro_count = sum(1 for user in active_users if getattr(user, "plan", "").upper() in pro_plans)
    enterprise_count = sum(1 for user in active_users if getattr(user, "plan", "").upper() in enterprise_plans)

    revenue_total = (
        pro_count * MERCADO_PAGO_PLANS["pro"]["price"]
        + enterprise_count * MERCADO_PAGO_PLANS["enterprise"]["price"]
    )

    sync_time = os.getenv("MERCADOPAGO_LAST_SYNC", "há 4 minutos")
    last_event = os.getenv("MERCADOPAGO_LAST_EVENT", "6 minutos")
    ai_status = os.getenv("GEMINI_STATUS", "Operacional")
    ai_usage = os.getenv("GEMINI_USAGE_PERCENT", "92% SLA")
    ai_detail = os.getenv("GEMINI_USAGE_DETAIL", "Latência média 620 ms · 1,3k requisições em 24h")

    onboarding_pending = os.getenv("DASHBOARD_ONBOARDING_PENDING", "12")
    support_critical = os.getenv("DASHBOARD_SUPPORT_CRITICAL", "3")

    metrics = {
        "total_users": {
            "value": str(total_users),
            "caption": f"{len(active_users)} ativos · {blocked_users} bloqueados",
        },
        "active_subscriptions": {
            "value": str(pro_count + enterprise_count),
            "pro": str(pro_count),
            "enterprise": str(enterprise_count),
        },
        "revenue": {
            "value": _format_brl(revenue_total),
            "caption": f"Sincronizado com Mercado Pago · {sync_time}",
            "sync_time": sync_time,
            "last_event": last_event,
        },
        "ai_consumption": {
            "value": ai_usage,
            "status": ai_status,
            "detail": ai_detail,
        },
        "onboarding": {
            "pending": onboarding_pending,
            "caption": "Convites aguardando validação de identidade.",
        },
        "support": {
            "critical": support_critical,
            "caption": "Escalonamento automático para o time SRE.",
        },
    }

    sorted_users = sorted(users, key=lambda user: _timestamp_sort_key(getattr(user, "last_login", None)), reverse=True)
    user_rows = [
        {
            "id": user.id,
            "name": getattr(user, "name", user.email),
            "email": getattr(user, "email", "?n/a"),
            "plan": getattr(user, "plan", "FREE"),
            "last_login": _humanize_timestamp(getattr(user, "last_login", None)),
            "is_active": getattr(user, "is_active", True),
        }
        for user in sorted_users[:6]
    ]

    logs = _load_recent_error_logs()

    return {
        "dashboard_metrics": metrics,
        "dashboard_users": user_rows,
        "dashboard_logs": logs,
    }


def _ensure_callback_path(provider: str, callback_url: str, expected_path: str) -> str:
    parsed = urlparse(callback_url)
    if parsed.path != expected_path:
        print(
            f"[OAUTH][{provider}] redirect_uri mismatch: expected {expected_path}, got {parsed.path}",
            flush=True,
        )
        raise HTTPException(status_code=500, detail="Configuração de redirect_uri inválida.")
    if not parsed.scheme or not parsed.netloc:
        print(f"[OAUTH][{provider}] redirect_uri incompleto: {callback_url}", flush=True)
        raise HTTPException(status_code=500, detail="redirect_uri incompleto para OAuth.")
    return callback_url


def _build_google_authorize_url(request: Request, next_hint: Optional[str] = None) -> str:
    client_id = _get_env_value("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google OAuth não configurado")

    base_state = os.getenv("GOOGLE_OAUTH_DEFAULT_STATE") or os.getenv("GOOGLE_DEFAULT_STATE") or "sentinel-career"
    state_value = _encode_state_with_next(base_state, next_hint)

    callback_path = "/api/auth/google/callback"
    redirect_uri = _ensure_callback_path("google", _build_absolute_url(callback_path, request), callback_path)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": os.getenv("GOOGLE_OAUTH_SCOPE", "openid email profile"),
        "access_type": "offline",
        "prompt": os.getenv("GOOGLE_OAUTH_PROMPT", "consent"),
        "state": state_value,
    }
    return f"{GOOGLE_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


def _build_linkedin_authorize_url(request: Request, next_hint: Optional[str] = None) -> str:
    client_id = _get_env_value("LINKEDIN_OAUTH_CLIENT_ID", "LINKEDIN_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="LinkedIn OAuth não configurado")

    base_state = os.getenv("LINKEDIN_OAUTH_DEFAULT_STATE") or os.getenv("LINKEDIN_DEFAULT_STATE") or "sentinel-career"
    state_value = _encode_state_with_next(base_state, next_hint)

    callback_path = "/api/auth/linkedin/callback"
    redirect_uri = _ensure_callback_path("linkedin", _build_absolute_url(callback_path, request), callback_path)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": os.getenv("LINKEDIN_OAUTH_SCOPE", "r_liteprofile r_emailaddress"),
        "state": state_value,
    }
    return f"{LINKEDIN_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/career-health/calculate")
async def calculate_career_health_endpoint(payload: ATSResultRequest):
    try:
        result = calculate_career_health(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Erro interno do servidor") from exc

    if result is None:
        raise HTTPException(status_code=500, detail="Resposta vazia do serviço de cálculo")

    if result.get("status") == "ERROR":
        recommendations = result.get("recommendations")
        detail = (
            recommendations[0]
            if isinstance(recommendations, list) and recommendations
            else "Erro ao calcular o Career Health"
        )
        raise HTTPException(status_code=422, detail=detail)

    return result


def _is_public_path(path: str) -> bool:
    normalized = path.rstrip("/") or "/"
    if normalized in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _build_login_redirect(request: Request) -> str:
    target_path = request.url.path
    if target_path == "/login":
        return "/login"
    full_target = target_path
    if request.url.query:
        full_target = f"{target_path}?{request.url.query}"
    return f"/login?{urlencode({'next': full_target})}"


def _sanitize_next(raw_value: Optional[str]) -> Optional[str]:
    if not raw_value:
        return None
    raw_value = raw_value.strip()
    if not raw_value.startswith("/") or raw_value.startswith("//"):
        return None
    return raw_value


def _is_valid_email(email: str) -> bool:
    email = email.strip()
    if "@" not in email or email.endswith("@"):
        return False
    local_part, _, domain = email.partition("@")
    return bool(local_part and "." in domain)


def _invalidate_sessions_for_user(user_id: str) -> None:
    tokens_to_remove = [token for token, owner in SESSION_OWNERS.items() if owner == user_id]
    for token in tokens_to_remove:
        ACTIVE_SESSIONS.discard(token)
        SESSION_OWNERS.pop(token, None)


def _issue_session_cookie(response: Response, user_id: Optional[str] = None) -> None:
    session_token = secrets.token_urlsafe(32)
    ACTIVE_SESSIONS.add(session_token)
    if user_id:
        SESSION_OWNERS[session_token] = user_id
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
    )


def _create_authenticated_redirect(target: str, user_id: Optional[str] = None) -> RedirectResponse:
    safe_target = target or "/dashboard"
    response = RedirectResponse(url=safe_target, status_code=302)
    _issue_session_cookie(response, user_id)
    return response


def _get_user_by_id(user_id: str):
    return get_user_by_id(user_id)


def _is_session_valid(token: str) -> bool:
    if token not in ACTIVE_SESSIONS:
        return False
    owner = SESSION_OWNERS.get(token)
    if not owner:
        return True
    user = _get_user_by_id(owner)
    if user is None or not getattr(user, "is_active", True):
        _invalidate_sessions_for_user(owner)
        return False
    return True


def _is_authenticated(request: Request) -> bool:
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token and _is_session_valid(cookie_token):
        return True
    header_token = request.headers.get(SESSION_HEADER_NAME)
    return bool(header_token and _is_session_valid(header_token))


def _encode_state_with_next(base_state: str, next_hint: Optional[str]) -> str:
    if not next_hint:
        return base_state
    encoded_next = quote(next_hint, safe="/?:=&%")
    return f"{base_state}|next={encoded_next}"


def _extract_next_from_state(state: Optional[str]) -> Optional[str]:
    if not state or "|next=" not in state:
        return None
    _, _, encoded = state.partition("|next=")
    try:
        decoded = unquote(encoded)
    except Exception:
        return None
    return _sanitize_next(decoded)
