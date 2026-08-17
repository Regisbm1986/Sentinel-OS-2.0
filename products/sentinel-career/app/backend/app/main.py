import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlencode, urlparse, urljoin
from io import BytesIO
import re
from zipfile import ZipFile, BadZipFile

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from backend.app.services.oauth_providers import (
    OAuthExchangeError,
    OAuthUser,
    google_oauth_client,
)
from backend.app.services.oauth_state import (
    OAuthStateData,
    OAuthStateResult,
    oauth_state_store,
)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Form, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from xml.etree import ElementTree as ET

from backend.app.api.career_health import calculate_career_health
from backend.app.services.azure_ai import (
    AzureAIError,
    analyze_linkedin_profile,
    generate_cv_analysis,
    search_jobs_suggestions,
)
from backend.linkedin.validator import (
    extract_linkedin_handle,
    normalize_linkedin_url,
)
from backend.app.services.mercado_pago import (
    AccessTokenStatus,
    MercadoPagoError,
    MercadoPagoPayment,
    evaluate_integration as evaluate_mercadopago,
    fetch_payment,
    normalize_payment_status,
    sanitize_access_token,
    validate_webhook_signature,
)
from backend.auth import auth as auth_module
from backend.auth.auth import login_user, register_user
from backend.auth.exceptions import (
    InvalidCredentials,
    InactiveUserError,
    UserExistsError,
)
from backend.database.user_repository import (
    get_user_by_email,
    get_user_by_id,
    list_users,
    update_last_login,
    update_user_plan,
)
from backend.gpt.client import get_default_deployment, has_azure_openai_credentials

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

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MERCADOPAGO_STATE_PATH = DATA_DIR / "mercadopago_webhooks.json"

CAREER_HEALTH_HISTORY_PATHS = [
    PROJECT_ROOT / "career_health_history.json",
    PROJECT_ROOT / "products" / "sentinel-career" / "app" / "data" / "career_health_history.json",
]

print(f"[ENV] .env carregado de {ENV_PATH}", flush=True)


def _get_env_value(*keys: str) -> Optional[str]:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def _is_placeholder_env_value(
    value: str,
    *,
    invalid_values: Set[str],
    invalid_prefixes: tuple[str, ...],
) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True
    if normalized in {candidate.lower() for candidate in invalid_values}:
        return True
    return any(normalized.startswith(prefix.lower()) for prefix in invalid_prefixes)


def _get_mercadopago_access_token() -> Optional[str]:
    raw_token = _get_env_value("MERCADOPAGO_ACCESS_TOKEN")
    token, status = sanitize_access_token(raw_token, environment=os.getenv("ENVIRONMENT"))

    if token is not None:
        if status == AccessTokenStatus.UNKNOWN:
            print(
                "[MERCADOPAGO] Token configurado com formato não reconhecido. Prosseguindo com cautela.",
                flush=True,
            )
        return token

    if status == AccessTokenStatus.ABSENT:
        return None

    messages = {
        AccessTokenStatus.PLACEHOLDER: "[MERCADOPAGO] Token configurado aparenta ser placeholder. Integração desativada.",
        AccessTokenStatus.INVALID_FORMAT: "[MERCADOPAGO] Token configurado possui formato inválido. Integração desativada.",
        AccessTokenStatus.SANDBOX_DISALLOWED: "[MERCADOPAGO] Token sandbox configurado, mas ambiente é de produção. Integração desativada.",
        AccessTokenStatus.PRODUCTION_DISALLOWED: "[MERCADOPAGO] Token de produção configurado, mas ambiente não é produção. Integração desativada.",
    }

    message = messages.get(status)
    if message:
        print(message, flush=True)

    return None


def _has_valid_mercadopago_credentials() -> bool:
    return _get_mercadopago_access_token() is not None


def _require_oauth_client_id(provider: str, *keys: str) -> str:
    candidate = _get_env_value(*keys)
    joined = " ou ".join(keys)
    if not candidate:
        print(f"[OAUTH][{provider}] Variáveis ausentes: {joined}", flush=True)
        raise HTTPException(status_code=503, detail=f"{provider} OAuth não configurado: defina {joined}.")

    if _is_placeholder_env_value(
        candidate,
        invalid_values=_OAUTH_INVALID_VALUES,
        invalid_prefixes=_OAUTH_INVALID_PREFIXES,
    ):
        print(f"[OAUTH][{provider}] Valor inválido configurado em {joined}.", flush=True)
        raise HTTPException(
            status_code=503,
            detail=f"{provider} OAuth não configurado: forneça credenciais válidas em {joined}.",
        )

    return candidate


def _require_oauth_secret(provider: str, *keys: str) -> str:
    candidate = _get_env_value(*keys)
    joined = " ou ".join(keys)
    if not candidate:
        print(f"[OAUTH][{provider}] Segredo ausente: {joined}", flush=True)
        raise HTTPException(status_code=503, detail=f"{provider} OAuth não configurado: defina {joined}.")

    if _is_placeholder_env_value(
        candidate,
        invalid_values=_OAUTH_INVALID_VALUES,
        invalid_prefixes=_OAUTH_INVALID_PREFIXES,
    ):
        print(f"[OAUTH][{provider}] Valor inválido configurado em {joined}.", flush=True)
        raise HTTPException(
            status_code=503,
            detail=f"{provider} OAuth não configurado: forneça segredo válido em {joined}.",
        )

    return candidate


def _has_oauth_configuration(*keys: str) -> bool:
    candidate = _get_env_value(*keys)
    if not candidate:
        return False
    if _is_placeholder_env_value(
        candidate,
        invalid_values=_OAUTH_INVALID_VALUES,
        invalid_prefixes=_OAUTH_INVALID_PREFIXES,
    ):
        return False
    return True


def _mask_env_value(value: Optional[str]) -> str:
    if not value:
        return "ausente"
    prefix = value[:4]
    return f"presente ({prefix}...)" if len(value) > 4 else f"presente ({prefix})"


def _load_mercadopago_event_state() -> dict[str, Any]:
    if not MERCADOPAGO_STATE_PATH.exists():
        return {
            "payments": {},
        }
    try:
        with MERCADOPAGO_STATE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        print(f"[MERCADOPAGO][state] Falha ao ler estado persistido: {exc}", flush=True)
        return {
            "payments": {},
        }

    payments = data.get("payments") if isinstance(data, dict) else {}
    if not isinstance(payments, dict):
        payments = {}
    return {
        "payments": payments,
    }


def _save_mercadopago_event_state(state: dict[str, Any]) -> None:
    payload = {"payments": state.get("payments", {})}
    try:
        with MERCADOPAGO_STATE_PATH.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
    except Exception as exc:
        print(f"[MERCADOPAGO][state] Falha ao salvar estado: {exc}", flush=True)


def _record_mercadopago_event(
    payment: MercadoPagoPayment,
    *,
    event_id: Optional[str],
    action: Optional[str],
    normalized_status: str,
) -> tuple[bool, dict[str, Any]]:
    state = _load_mercadopago_event_state()
    payments = state.setdefault("payments", {})

    existing = payments.get(payment.payment_id)
    history = []
    if isinstance(existing, dict):
        raw_history = existing.get("history")
        if isinstance(raw_history, list):
            history = [item for item in raw_history if isinstance(item, dict)]

    already_processed = False
    if event_id and any(entry.get("event_id") == event_id for entry in history):
        already_processed = True

    if already_processed:
        return True, existing if isinstance(existing, dict) else {}

    received_at = datetime.now(timezone.utc).isoformat()

    history.append(
        {
            "event_id": event_id,
            "action": action,
            "normalized_status": normalized_status,
            "status": payment.status,
            "status_detail": payment.status_detail,
            "received_at": received_at,
        }
    )

    record = {
        "payment_id": payment.payment_id,
        "normalized_status": normalized_status,
        "status": payment.status,
        "status_detail": payment.status_detail,
        "external_reference": payment.external_reference,
        "metadata": payment.metadata,
        "transaction_amount": str(payment.transaction_amount) if payment.transaction_amount is not None else None,
        "currency_id": payment.currency_id,
        "payer_email": payment.payer_email,
        "date_created": payment.date_created,
        "date_approved": payment.date_approved,
        "preference_id": payment.preference_id,
        "last_event_id": event_id,
        "updated_at": received_at,
        "history": history,
    }

    payments[payment.payment_id] = record
    _save_mercadopago_event_state(state)
    return False, record


def _map_payment_plan_id(plan_id: Optional[str]) -> Optional[str]:
    if not plan_id:
        return None
    normalized = plan_id.strip().lower()
    mapping = {
        "pro": "PRO",
        "premium": "PREMIUM",
        "enterprise": "MASTER",
    }
    return mapping.get(normalized)


def _update_legacy_user_plan_cache(user_id: str, plan_code: str) -> None:
    for legacy in auth_module.USERS_DB.values():
        if getattr(legacy, "id", None) == user_id:
            setattr(legacy, "plan", plan_code)


def _apply_user_plan_change(user_id: Optional[str], plan_code: Optional[str]) -> bool:
    if not user_id or not plan_code:
        return False

    applied = False
    try:
        update_user_plan(user_id, plan_code)
        applied = True
    except RuntimeError as exc:
        print(f"[MERCADOPAGO][plan] Falha ao atualizar plano no banco: {exc}", flush=True)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[MERCADOPAGO][plan] Erro inesperado ao atualizar plano: {exc}", flush=True)

    try:
        user_obj = get_user_by_id(user_id)
    except RuntimeError:
        user_obj = None

    if user_obj is not None:
        setattr(user_obj, "plan", plan_code)
        applied = True

    _update_legacy_user_plan_cache(user_id, plan_code)

    if applied:
        AUTO_APPLY_USAGE.pop(user_id, None)

    return applied

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
MERCADO_PAGO_PLANS = {
    "pro": {"price": 39.90, "title": "Sentinel Career PRO"},
    "enterprise": {"price": 79.90, "title": "Sentinel Career ENTERPRISE"},
}

DEFAULT_ADMIN_EMAIL = os.getenv("SENTINEL_ADMIN_EMAIL")
DEFAULT_ADMIN_PASSWORD = os.getenv("SENTINEL_ADMIN_PASSWORD")
DEFAULT_ADMIN_NAME = os.getenv("SENTINEL_ADMIN_NAME")
DEFAULT_ADMIN_PLAN = os.getenv("SENTINEL_ADMIN_PLAN")

FRONTEND_DIR = PROJECT_ROOT / "products" / "sentinel-career" / "app" / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"

CANONICAL_DOMAIN = "career.sentinel-os.ia.br"
DEFAULT_POST_LOGIN_ROUTE = "/admin/dashboard"

SESSION_COOKIE_NAME = "sentinel_session"
SESSION_HEADER_NAME = "X-Sentinel-Session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 12
ACTIVE_SESSIONS: Set[str] = set()
SESSION_OWNERS: Dict[str, str] = {}


def _resolve_max_upload_size() -> int:
    raw = os.getenv("SENTINEL_RESUME_MAX_BYTES")
    if raw is None:
        return 5 * 1024 * 1024
    try:
        parsed = int(raw)
    except ValueError:
        return 5 * 1024 * 1024
    return max(parsed, 256_000)


MAX_RESUME_UPLOAD_SIZE_BYTES = _resolve_max_upload_size()
ALLOWED_TEXT_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/rtf",
    "application/rtf",
}


def _resolve_cookie_secure_flag() -> bool:
    raw = os.getenv("SENTINEL_SESSION_COOKIE_SECURE")
    if raw is None:
        return True
    normalized = raw.strip().lower()
    if normalized in {"0", "false", "no"}:
        return False
    if normalized in {"1", "true", "yes"}:
        return True
    return True

AUTO_APPLY_LIMITS: Dict[str, Optional[int]] = {
    "FREE": 3,
    "PRO": 100,
    "PREMIUM": 100,
    "ENTERPRISE": None,
    "MASTER": None,
    "ADMIN": None,
}
AUTO_APPLY_USAGE: Dict[str, int] = {}

PUBLIC_PATHS = {
    "/",
    "/login",
    "/health",
    "/api/checkout/mercadopago/webhook",
    "/politica-de-privacidade",
    "/diretrizes",
    "/termos",
    "/termos-de-uso",
}
PUBLIC_PATH_PREFIXES = ("/static", "/api/auth", "/assets")

SESSION_COOKIE_SECURE = _resolve_cookie_secure_flag()

_DEFAULT_ALLOWED_ORIGINS = [
    "https://www.career.sentinel-os.ia.br",
    "https://career.sentinel-os.ia.br",
]

_OAUTH_INVALID_VALUES = {
    "homolog-linkedin-client",
    "homolog-google-client",
    "example-client",
    "placeholder",
    "dummy",
    "test",
}
_OAUTH_INVALID_PREFIXES = (
    "homolog-",
    "sandbox-",
    "test-",
    "dummy-",
    "placeholder-",
    "example-",
)

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


def _require_plan(user: Any, allowed: set[str], feature: str) -> str:
    plan = _normalize_plan(getattr(user, "plan", "FREE"))
    if plan not in allowed:
        raise HTTPException(status_code=403, detail=f"O recurso {feature} não está disponível no plano {plan}.")
    return plan


def _generate_checkout_reference(plan_id: str, user: Optional[Any]) -> str:
    sanitized_plan = plan_id.strip().lower() if plan_id else "unknown"
    user_fragment = getattr(user, "id", None) if user is not None else None
    if not user_fragment:
        user_fragment = "anonymous"
    fragment = str(user_fragment).replace(":", "-").replace(" ", "-")
    token = secrets.token_hex(6)
    return f"career:{sanitized_plan}:{fragment}:{token}"


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
    if not DEFAULT_ADMIN_EMAIL:
        return None
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
    target_role: Optional[str] = Field(None, alias="targetRole")


class LinkedInAnalysisPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    linkedin_text: str = Field(..., alias="linkedinText")
    target_role: Optional[str] = Field(None, alias="targetRole")
    linkedin_url: Optional[str] = Field(None, alias="linkedinUrl")


class JobSearchPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_role: Optional[str] = Field(None, alias="targetRole")
    resume_text: Optional[str] = Field(None, alias="resumeText")


class AutoApplyActionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: Optional[str] = Field(None, alias="jobId")
    job_title: Optional[str] = Field(None, alias="jobTitle")
    application_type: str = Field("auto", alias="applicationType")


class AzureApplyAssetsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_title: str = Field(..., alias="jobTitle")
    company: Optional[str] = None
    resume_text: Optional[str] = Field(None, alias="resumeText")
    target_role: Optional[str] = Field(None, alias="targetRole")


PDF_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/x-pdf",
}

DOCX_MIME_TYPES: set[str] = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

TEXT_EXTENSIONS = (".txt", ".md", ".rtf")


def _resolve_resume_kind(filename: str, content_type: str) -> str:
    lower_name = (filename or "").lower()
    lowered_type = (content_type or "").lower()
    if lower_name.endswith(".pdf") or lowered_type in PDF_MIME_TYPES:
        return "pdf"
    if lower_name.endswith(".docx") or lowered_type in DOCX_MIME_TYPES:
        return "docx"
    if lower_name.endswith(TEXT_EXTENSIONS) or lowered_type in ALLOWED_TEXT_MIME_TYPES:
        return "text"
    raise ValueError("Formato não suportado. Envie PDF, DOCX ou TXT.")


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

    if len(raw_bytes) > MAX_RESUME_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite de upload permitido.")

    try:
        kind = _resolve_resume_kind(filename, content_type)
        if kind == "pdf":
            extracted = _extract_text_from_pdf_bytes(raw_bytes)
        elif kind == "docx":
            extracted = _extract_text_from_docx_bytes(raw_bytes)
        else:
            extracted = _extract_text_from_plain_bytes(raw_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"text": extracted}


@app.get("/")
async def landing_home(request: Request) -> Any:
    if _is_authenticated(request):
        return RedirectResponse(url=DEFAULT_POST_LOGIN_ROUTE, status_code=303)
    now = datetime.utcnow()
    return _render_template(
        request,
        "landing/home.html",
        {
            "current_year": now.year,
        },
    )


@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request) -> HTMLResponse:
    return _render_template(request, "landing/pricing.html")


@app.get("/pricing.html", include_in_schema=False, response_class=HTMLResponse)
async def pricing_page_html(request: Request) -> HTMLResponse:
    return await pricing_page(request)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    if _is_authenticated(request):
        return RedirectResponse(url=DEFAULT_POST_LOGIN_ROUTE, status_code=303)
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
        return RedirectResponse(url=DEFAULT_POST_LOGIN_ROUTE, status_code=303)
    next_hint = request.query_params.get("next") or DEFAULT_POST_LOGIN_ROUTE
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


@app.get("/diretrizes", response_class=HTMLResponse)
async def guidelines_page(request: Request) -> HTMLResponse:
    now = datetime.utcnow()
    return _render_template(
        request,
        "landing/guidelines.html",
        {
            "current_year": now.year,
            "last_review": now.strftime("%d/%m/%Y"),
        },
    )


@app.get("/termos", response_class=HTMLResponse)
@app.get("/termos-de-uso", response_class=HTMLResponse)
async def terms_page(request: Request) -> HTMLResponse:
    now = datetime.utcnow()
    return _render_template(
        request,
        "landing/terms.html",
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
    return _create_authenticated_redirect(sanitized_next or DEFAULT_POST_LOGIN_ROUTE, user.id)


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

    redirect_to = sanitized_next or DEFAULT_POST_LOGIN_ROUTE
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
            "redirect_to": sanitized_next or DEFAULT_POST_LOGIN_ROUTE,
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


@app.get("/api/azure/status")
async def azure_status() -> dict[str, Any]:
    configured = has_azure_openai_credentials()

    return {
        "configured": configured,
        "deployment": get_default_deployment() if configured else None,
        "modules": {
            "resume": configured,
            "linkedin": configured,
            "jobs": configured,
        },
    }


@app.post("/api/azure/optimize-cv")
async def azure_optimize_cv(payload: OptimizeCVPayload, request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    plan = _require_plan(user, {"FREE", "PRO", "PREMIUM", "ENTERPRISE", "MASTER", "ADMIN"}, "ATS de currículo")

    if not has_azure_openai_credentials():
        raise HTTPException(status_code=503, detail="Integração com Azure OpenAI não configurada.")

    try:
        return generate_cv_analysis(payload.resume_text, payload.target_role)
    except AzureAIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail="Azure OpenAI indisponível no momento.") from exc


@app.post("/api/azure/analyze-linkedin")
async def azure_analyze_linkedin(payload: LinkedInAnalysisPayload, request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    plan = _normalize_plan(getattr(user, "plan", "FREE"))
    _require_plan(user, {"PRO", "PREMIUM", "ENTERPRISE", "MASTER", "ADMIN"}, "ATS do LinkedIn")

    if not has_azure_openai_credentials():
        raise HTTPException(status_code=503, detail="Integração com Azure OpenAI não configurada.")

    normalized_linkedin_url: Optional[str] = None
    raw_linkedin_url = (payload.linkedin_url or "").strip()
    if raw_linkedin_url:
        normalized_linkedin_url = normalize_linkedin_url(raw_linkedin_url)
        if not normalized_linkedin_url:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Não reconhecemos esse link como um perfil do LinkedIn. "
                    "Use um endereço no formato https://www.linkedin.com/in/seu-usuario."
                ),
            )

    try:
        return analyze_linkedin_profile(payload.linkedin_text, payload.target_role, normalized_linkedin_url)
    except AzureAIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail="Azure OpenAI indisponível no momento.") from exc


@app.post("/api/azure/search-jobs")
async def azure_search_jobs(payload: JobSearchPayload, request: Request) -> list[dict[str, Any]]:
    _require_authenticated_user(request)
    if not has_azure_openai_credentials():
        raise HTTPException(status_code=503, detail="Integração com Azure OpenAI não configurada.")
    try:
        return search_jobs_suggestions(payload.target_role, payload.resume_text)
    except AzureAIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail="Azure OpenAI indisponível no momento.") from exc


@app.post("/api/azure/auto-apply/validate")
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


@app.post("/api/azure/auto-apply/register")
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


@app.post("/api/azure/generate-apply-assets")
async def azure_generate_apply_assets(payload: AzureApplyAssetsRequest, request: Request) -> dict[str, Any]:
    user = _require_authenticated_user(request)
    _require_plan(user, {"PRO", "PREMIUM", "ENTERPRISE", "MASTER", "ADMIN"}, "cartas de apresentação")
    if not has_azure_openai_credentials():
        raise HTTPException(status_code=503, detail="Integração com Azure OpenAI não configurada.")

    target_role = payload.target_role or payload.job_title
    resume_text = payload.resume_text or ""

    try:
        analysis = generate_cv_analysis(resume_text, target_role)
    except AzureAIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail="Azure OpenAI indisponível no momento.") from exc

    cover_letter = analysis.get("mockCoverLetter") or ""
    if not cover_letter:
        company = payload.company or "sua empresa"
        cover_letter = (
            f"Prezados recrutadores da {company},\n\n"
            f"Gostaria de me candidatar à oportunidade '{payload.job_title}'. "
            "Com base na minha experiência e competências alinhadas ao cargo, estou disponível para uma conversa.\n\n"
            "Atenciosamente,\nSentinel Candidate"
        )

    return {
        "coverLetter": cover_letter,
        "keywords": analysis.get("keywords", []),
        "score": analysis.get("score"),
    }


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
async def admin_dashboard_metrics(request: Request) -> dict[str, Any]:
    _require_plan(_require_authenticated_user(request), {"ADMIN"}, "painel administrativo")
    context = _build_dashboard_context()
    integrations = context["integrations"]
    return {
        "app_status": context["app_status"],
        "integrations": integrations,
        "revenue_caption": context["revenue_caption"],
        "users_total": len(context["users"]),
    }


@app.get("/api/admin/dashboard/users")
async def admin_dashboard_users(request: Request) -> list[dict[str, Any]]:
    _require_plan(_require_authenticated_user(request), {"ADMIN"}, "painel administrativo")
    context = _build_dashboard_context()
    return context["users"]


@app.get("/api/admin/dashboard/logs")
async def admin_dashboard_logs(request: Request, limit: int = 10) -> list[dict[str, Any]]:
    _require_plan(_require_authenticated_user(request), {"ADMIN"}, "painel administrativo")
    logs = _load_recent_error_logs(limit=limit)
    return logs


@app.post("/api/admin/users/{user_id}/block")
async def block_admin_user(user_id: str, request: Request) -> dict[str, Any]:
    _require_plan(_require_authenticated_user(request), {"ADMIN"}, "gestão de usuários")
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
async def unblock_admin_user(user_id: str, request: Request) -> dict[str, Any]:
    _require_plan(_require_authenticated_user(request), {"ADMIN"}, "gestão de usuários")
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
        state_result = _issue_oauth_state("google", next_hint)
        authorize_url = _build_google_authorize_url(request, state_result)
    except HTTPException as exc:
        print(f"[OAUTH][google] Falha ao gerar login ({exc.status_code}): {exc.detail}", flush=True)
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[OAUTH][google] Erro inesperado ao montar login: {exc}", flush=True)
        raise HTTPException(status_code=500, detail="Erro ao preparar login com Google.") from exc
    return {"provider": "google", "authorization_url": authorize_url}


@app.get("/api/auth/google/callback", name="google_callback")
async def google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    if not code:
        raise HTTPException(status_code=400, detail="Parâmetro 'code' não informado")

    state_data = _validate_oauth_state("google", state)

    client_id = _require_oauth_client_id("Google", "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_CLIENT_ID")
    client_secret = _require_oauth_secret("Google", "GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_CLIENT_SECRET")

    redirect_uri = _resolve_oauth_redirect(
        "google",
        "/api/auth/google/callback",
        env_keys=("GOOGLE_OAUTH_REDIRECT_URI",),
        request=request,
        prefer_canonical=True,
    )

    try:
        token_payload = google_oauth_client.exchange_code(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
        userinfo = google_oauth_client.fetch_userinfo(token_payload["access_token"])
        oauth_user = google_oauth_client.build_user(
            id_token=token_payload["id_token"],
            userinfo=userinfo,
            client_id=client_id,
            expected_nonce=state_data.nonce,
        )
    except OAuthExchangeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    user = _sync_oauth_user(oauth_user)
    next_target = state_data.next_path or DEFAULT_POST_LOGIN_ROUTE
    return _create_authenticated_redirect(next_target, user.id)


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

    external_reference = _generate_checkout_reference(plan_id, user)
    preference_data["external_reference"] = external_reference
    preference_data["metadata"]["external_reference"] = external_reference

    if user is not None:
        preference_data["metadata"]["user_id"] = getattr(user, "id", None)
        preference_data["metadata"]["user_email"] = getattr(user, "email", None)
        user_plan = getattr(user, "plan", None)
        if user_plan:
            preference_data["metadata"]["user_plan"] = user_plan

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
async def mercadopago_webhook(request: Request) -> JSONResponse:
    raw_body = await request.body()
    if not raw_body:
        return JSONResponse({"status": "ignored", "reason": "empty_body"}, status_code=202)

    secret = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
    signature_valid, signature_reason = validate_webhook_signature(raw_body, request.headers, secret)
    if not signature_valid:
        raise HTTPException(status_code=401, detail=f"Assinatura inválida do webhook ({signature_reason}).")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Payload inválido recebido do Mercado Pago.") from exc

    action = payload.get("action") or payload.get("type")
    if action and "payment" not in str(action).lower():
        return JSONResponse(
            {
                "status": "ignored",
                "reason": "unsupported_action",
                "action": action,
            },
            status_code=202,
        )

    payment_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    payment_id = payment_data.get("id") or payload.get("id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="ID do pagamento ausente no payload do webhook.")

    access_token = _get_mercadopago_access_token()
    if not access_token:
        raise HTTPException(status_code=503, detail="MERCADOPAGO_ACCESS_TOKEN não configurado")

    try:
        payment = fetch_payment(access_token, str(payment_id))
    except MercadoPagoError as exc:
        print(f"[MERCADOPAGO][webhook] Falha ao consultar pagamento {payment_id}: {exc}", flush=True)
        raise HTTPException(status_code=502, detail="Erro ao consultar pagamento no Mercado Pago.") from exc

    normalized_status = normalize_payment_status(payment.status)

    event_id = payload.get("id")
    already_processed, stored_record = _record_mercadopago_event(
        payment,
        event_id=str(event_id) if event_id is not None else None,
        action=str(action) if action is not None else None,
        normalized_status=normalized_status,
    )

    metadata = payment.metadata or {}
    user_id = metadata.get("user_id")
    plan_code = _map_payment_plan_id(metadata.get("plan_id"))

    plan_applied = False
    if not already_processed and normalized_status == "approved":
        plan_applied = _apply_user_plan_change(user_id, plan_code)

    response_payload = {
        "status": "processed",
        "payment_id": payment.payment_id,
        "event_id": str(event_id) if event_id is not None else None,
        "action": action,
        "normalized_status": normalized_status,
        "raw_status": payment.status,
        "already_processed": already_processed,
        "plan_applied": plan_applied,
        "user_id": user_id,
        "plan_code": plan_code,
        "metadata": {key: metadata[key] for key in metadata if key in {"plan_id", "user_id", "user_email"}},
        "stored": stored_record,
    }

    print(
        "[MERCADOPAGO][webhook] Processado pagamento="
        f"{payment.payment_id} status={normalized_status} already_processed={already_processed} plan_applied={plan_applied}",
        flush=True,
    )

    return JSONResponse(response_payload, status_code=202)


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


def _get_oauth_state_base(provider: str) -> str:
    normalized = provider.lower()
    if normalized == "google":
        return (
            _get_env_value("GOOGLE_OAUTH_DEFAULT_STATE", "GOOGLE_DEFAULT_STATE")
            or "sentinel-career"
        )
    return "sentinel-career"


def _normalize_canonical_base_url() -> str:
    override = _get_env_value("SENTINEL_CANONICAL_URL", "SENTINEL_OAUTH_BASE_URL")
    candidate = override.strip() if override else f"https://{CANONICAL_DOMAIN}"
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = parsed.netloc or parsed.path
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return f"https://{host.strip('/')}"


def _build_canonical_oauth_url(path: str) -> str:
    base = _normalize_canonical_base_url()
    return urljoin(f"{base}/", path.lstrip("/"))


def _issue_oauth_state(provider: str, next_hint: Optional[str]) -> OAuthStateResult:
    base_state = _get_oauth_state_base(provider)
    return oauth_state_store.issue(provider, base_state, next_hint)


def _validate_oauth_state(provider: str, received_state: Optional[str]) -> OAuthStateData:
    base_state = _get_oauth_state_base(provider)
    try:
        return oauth_state_store.consume(provider, base_state, received_state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fluxo OAuth inválido ou expirado.")


def _load_json_records(*paths: Path) -> List[dict[str, Any]]:
    for path in paths:
        if path is None:
            continue
        try:
            with path.open("r", encoding="utf-8") as handler:
                payload = json.load(handler)
        except FileNotFoundError:
            continue
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"[ADMIN][data] Falha ao ler {path}: {exc}", flush=True)
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        print(f"[ADMIN][data] Conteúdo inesperado em {path}", flush=True)
        return []
    return []


def _load_career_health_history() -> List[dict[str, Any]]:
    return _load_json_records(*CAREER_HEALTH_HISTORY_PATHS)


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            # Assume UTC for historic data where timezone was omitted.
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _format_payments_caption(total_confirmed: int) -> str:
    if total_confirmed == 0:
        return "Nenhum pagamento confirmado"
    if total_confirmed == 1:
        return "1 pagamento confirmado"
    return f"{total_confirmed} pagamentos confirmados"


def _career_health_history_sort_key(entry: dict[str, Any]) -> float:
    timestamp_value = entry.get("timestamp") or entry.get("created_at")
    parsed = _parse_iso_datetime(timestamp_value)
    if parsed:
        return parsed.timestamp()
    return 0.0


def _prepare_career_health_history(history: List[dict[str, Any]], limit: int = 10) -> List[dict[str, Any]]:
    sorted_history = sorted(history, key=_career_health_history_sort_key, reverse=True)
    return sorted_history[:limit]


def _format_brl(amount: Any) -> str:
    if isinstance(amount, Decimal):
        normalized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        amount_text = f"{normalized:.2f}"
    else:
        try:
            amount_text = f"{float(amount):.2f}"
        except (TypeError, ValueError):
            amount_text = "0.00"
    integer_part, _, cents = amount_text.partition(".")
    try:
        integer_with_sep = f"{int(integer_part):,}".replace(",", ".")
    except ValueError:
        integer_with_sep = "0"
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
        return []

    try:
        with log_path.open("r", encoding="utf-8") as handler:
            lines = [line.strip() for line in handler.readlines() if line.strip()]
    except Exception as exc:  # pragma: no cover - I/O defensive
        print(f"[ADMIN][logs] Falha ao ler arquivo de logs: {exc}", flush=True)
        return []

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

    return entries


def _build_dashboard_context() -> dict[str, Any]:
    try:
        users = list(list_users())
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[ADMIN][dashboard] Falha ao carregar usuários: {exc}", flush=True)
        users = []

    sorted_users = sorted(
        users,
        key=lambda user: _timestamp_sort_key(getattr(user, "last_login", None)),
        reverse=True,
    )
    user_rows = [
        {
            "id": user.id,
            "name": getattr(user, "name", user.email),
            "email": getattr(user, "email", "?n/a"),
            "plan": getattr(user, "plan", "FREE"),
            "last_login": _humanize_timestamp(getattr(user, "last_login", None)),
            "is_active": getattr(user, "is_active", True),
        }
        for user in sorted_users[:8]
    ]

    azure_configured = has_azure_openai_credentials()
    google_configured = _has_oauth_configuration("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_CLIENT_ID")

    mercadopago_summary = evaluate_mercadopago(
        _get_env_value("MERCADOPAGO_ACCESS_TOKEN"),
        environment=os.getenv("ENVIRONMENT"),
    )
    last_payment_display = "Sem dados"
    if mercadopago_summary.last_payment_at:
        parsed_dt = _parse_iso_datetime(mercadopago_summary.last_payment_at)
        if parsed_dt:
            last_payment_display = parsed_dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M")

    revenue_caption = _format_payments_caption(mercadopago_summary.confirmed_count)

    mercadopago_card = {
        "status": mercadopago_summary.status,
        "availability": mercadopago_summary.availability,
        "detail": mercadopago_summary.detail,
        "confirmed_total": _format_brl(mercadopago_summary.total_confirmed),
        "confirmed_count": mercadopago_summary.confirmed_count,
        "last_payment": last_payment_display,
    }

    mercadopago_payments = [
        {
            "payment_id": record.payment_id or "—",
            "status": (record.status or "indefinido").upper(),
            "amount": _format_brl(record.amount) if record.amount is not None else "—",
            "created_at": _humanize_timestamp(record.created_at),
            "payer_email": record.payer_email or "—",
        }
        for record in mercadopago_summary.payments[:5]
    ]

    career_health_history = _prepare_career_health_history(_load_career_health_history())
    logs = _load_recent_error_logs()

    app_status = {
        "status": "online",
        "checked_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
    }

    integrations = {
        "azure_openai": "configured" if azure_configured else "not_configured",
        "google_oauth": "configured" if google_configured else "not_configured",
        "linkedin_ats": "configured" if azure_configured else "not_configured",
        "mercado_pago": mercadopago_card,
    }

    return {
        "app_status": app_status,
        "users": user_rows,
        "integrations": integrations,
        "mercadopago_payments": mercadopago_payments,
        "revenue_caption": revenue_caption,
        "career_health_history": career_health_history,
        "logs": logs,
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


def _resolve_oauth_redirect(
    provider: str,
    callback_path: str,
    *,
    env_keys: tuple[str, ...],
    request: Optional[Request],
    prefer_canonical: bool,
) -> str:
    override = _get_env_value(*env_keys)
    if override:
        return _ensure_callback_path(provider, override, callback_path)

    if prefer_canonical:
        canonical = _build_canonical_oauth_url(callback_path)
        return _ensure_callback_path(provider, canonical, callback_path)

    if request is None:
        raise HTTPException(status_code=500, detail="redirect_uri não pôde ser determinado.")

    dynamic = _build_absolute_url(callback_path, request)
    return _ensure_callback_path(provider, dynamic, callback_path)


def _build_google_authorize_url(request: Request, state_result: OAuthStateResult) -> str:
    client_id = _require_oauth_client_id("Google", "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_CLIENT_ID")

    callback_path = "/api/auth/google/callback"
    redirect_uri = _resolve_oauth_redirect(
        "google",
        callback_path,
        env_keys=("GOOGLE_OAUTH_REDIRECT_URI",),
        request=request,
        prefer_canonical=True,
    )

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": os.getenv("GOOGLE_OAUTH_SCOPE", "openid email profile"),
        "access_type": "offline",
        "prompt": os.getenv("GOOGLE_OAUTH_PROMPT", "consent"),
        "state": state_result.state_value,
        "nonce": state_result.nonce,
    }
    return f"{GOOGLE_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"



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


def _touch_last_login(user) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        update_last_login(user.id)
    except Exception as exc:
        print(f"[AUTH] Falha ao atualizar last_login para {user.email}: {exc}", flush=True)
    finally:
        user.last_login = now_iso


def _sync_oauth_user(oauth_user: OAuthUser):
    email = oauth_user.email.strip().lower()
    if not _is_valid_email(email):
        raise HTTPException(status_code=400, detail="E-mail inválido retornado pelo provedor OAuth.")

    try:
        existing = get_user_by_email(email)
    except Exception as exc:
        print(f"[OAUTH][{oauth_user.provider}] Falha ao consultar usuário {email}: {exc}", flush=True)
        existing = auth_module.USERS_DB.get(email)
    if not existing:
        existing = auth_module.USERS_DB.get(email)
    if existing:
        if not getattr(existing, "is_active", True):
            raise HTTPException(status_code=403, detail="Usuário bloqueado. Contate o administrador.")
        _touch_last_login(existing)
        return existing

    display_name = oauth_user.name or email.split("@", 1)[0]
    random_password = secrets.token_urlsafe(32)

    try:
        user = register_user(display_name, email, random_password, plan="FREE")
    except UserExistsError:
        try:
            user = get_user_by_email(email)
        except Exception as exc:
            print(f"[OAUTH][{oauth_user.provider}] Falha ao recuperar usuário existente {email}: {exc}", flush=True)
            user = auth_module.USERS_DB.get(email)
        if user is None:
            user = auth_module.USERS_DB.get(email)
        if user is None:
            raise HTTPException(status_code=500, detail="Falha ao sincronizar usuário OAuth.")
    except Exception as exc:
        print(f"[OAUTH][{oauth_user.provider}] Falha ao registrar usuário: {exc}", flush=True)
        raise HTTPException(status_code=502, detail="Erro ao registrar usuário OAuth.") from exc

    _touch_last_login(user)
    return user


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
    expires_at = int(time.time() + SESSION_MAX_AGE_SECONDS)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        max_age=SESSION_MAX_AGE_SECONDS,
        expires=expires_at,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
    )


def _create_authenticated_redirect(target: str, user_id: Optional[str] = None) -> RedirectResponse:
    safe_target = target or DEFAULT_POST_LOGIN_ROUTE
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


def _extract_next_from_state(state: Optional[str]) -> Optional[str]:
    return None
