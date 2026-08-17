from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Tuple

try:  # pragma: no cover - validated through tests with mocks
    import mercadopago  # type: ignore
except ImportError:  # pragma: no cover - surfaced via result.detail
    mercadopago = None  # type: ignore

_LOGGER = logging.getLogger(__name__)

# Mercado Pago sandbox tokens typically start with "TEST-" or "TEST_".
_PLACEHOLDER_PREFIXES: Tuple[str, ...] = (
    "sandbox",
    "sanbox",
    "dummy",
    "placeholder",
    "example",
    "homolog",
    "beta",
    "demo",
)
_PLACEHOLDER_VALUES = {
    "",
    "sandbox-token",
    "sanbox-token",
    "sandbox",
    "test",
    "dummy",
    "placeholder",
    "example",
    "token",
}

_SANDBOX_TOKEN_PATTERN = re.compile(
    r"^TEST-\d{10,}-\d{6}-[0-9a-f]{32}-\d{6,}$",
    re.IGNORECASE,
)
_PRODUCTION_TOKEN_PREFIXES = ("APP_USR-",)
_PRODUCTION_ENV_NAMES = {"prod", "production", "live"}


class AccessTokenStatus(Enum):
    ABSENT = "absent"
    PLACEHOLDER = "placeholder"
    INVALID_FORMAT = "invalid_format"
    SANDBOX = "sandbox"
    SANDBOX_DISALLOWED = "sandbox_disallowed"
    PRODUCTION = "production"
    PRODUCTION_DISALLOWED = "production_disallowed"
    UNKNOWN = "unknown"

_APPROVED_PAYMENT_STATUSES = {"approved", "authorized"}
_PENDING_PAYMENT_STATUSES = {"in_process", "pending", "in_mediation"}
_CANCELLED_PAYMENT_STATUSES = {"cancelled", "rejected", "charged_back"}
_REFUNDED_PAYMENT_STATUSES = {"refunded", "partially_refunded"}

_SUPPORTED_SIGNATURE_ALGORITHMS = {
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
}


class MercadoPagoError(RuntimeError):
    """Raised when the Mercado Pago service encounters an operational failure."""


@dataclass(slots=True)
class MercadoPagoRecord:
    payment_id: Optional[str]
    status: Optional[str]
    amount: Optional[Decimal]
    created_at: Optional[str]
    payer_email: Optional[str]


@dataclass(slots=True)
class MercadoPagoSummary:
    status: str
    availability: Optional[str]
    detail: Optional[str]
    total_confirmed: Decimal
    confirmed_count: int
    last_payment_at: Optional[str]
    payments: List[MercadoPagoRecord]


@dataclass(slots=True)
class MercadoPagoPayment:
    payment_id: str
    status: Optional[str]
    status_detail: Optional[str]
    transaction_amount: Optional[Decimal]
    currency_id: Optional[str]
    external_reference: Optional[str]
    metadata: Dict[str, Any]
    payer_email: Optional[str]
    date_created: Optional[str]
    date_approved: Optional[str]
    preference_id: Optional[str]


def _resolve_algorithm(signature_header: str) -> Tuple[str, Optional[str]]:
    if "=" not in signature_header:
        return "sha1", signature_header.strip() or None
    algorithm, _, signature = signature_header.partition("=")
    return algorithm.strip().lower(), signature.strip() or None


def _extract_signature(headers: Mapping[str, str]) -> Optional[str]:
    for key in ("x-mercadopago-signature", "x-hub-signature-256", "x-hub-signature"):
        for header_key, value in headers.items():
            if header_key.lower() == key:
                return value
    return None


def _normalize_environment(environment: Optional[str]) -> str:
    value = (environment or os.getenv("ENVIRONMENT") or "production").strip().lower()
    if value in {"prd", "prod"}:
        return "production"
    if value in {"homolog", "staging", "stage", "qa", "test", "sandbox", "development", "dev"}:
        return "homolog"
    return value or "production"


def _classify_token(token: Optional[str], environment: Optional[str]) -> Tuple[Optional[str], AccessTokenStatus]:
    normalized_env = _normalize_environment(environment)

    if token is None or not token.strip():
        return None, AccessTokenStatus.ABSENT

    token_stripped = token.strip()
    lowered = token_stripped.lower()

    if lowered in _PLACEHOLDER_VALUES:
        return None, AccessTokenStatus.PLACEHOLDER

    if lowered.startswith("test-"):
        if _SANDBOX_TOKEN_PATTERN.match(token_stripped):
            if normalized_env in _PRODUCTION_ENV_NAMES:
                return None, AccessTokenStatus.SANDBOX_DISALLOWED
            return token_stripped, AccessTokenStatus.SANDBOX
        return None, AccessTokenStatus.INVALID_FORMAT

    for prefix in _PLACEHOLDER_PREFIXES:
        if lowered.startswith(prefix):
            return None, AccessTokenStatus.PLACEHOLDER

    for prefix in _PRODUCTION_TOKEN_PREFIXES:
        if token_stripped.startswith(prefix):
            if normalized_env in _PRODUCTION_ENV_NAMES:
                return token_stripped, AccessTokenStatus.PRODUCTION
            return None, AccessTokenStatus.PRODUCTION_DISALLOWED

    return token_stripped, AccessTokenStatus.UNKNOWN


def sanitize_access_token(token: Optional[str], *, environment: Optional[str] = None) -> Tuple[Optional[str], AccessTokenStatus]:
    """Validate and sanitize a Mercado Pago access token for the given environment."""

    return _classify_token(token, environment)


def validate_webhook_signature(
    raw_body: bytes,
    headers: Mapping[str, str],
    secret: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Validate Mercado Pago webhook signature using the provided secret.

    Returns a tuple ``(is_valid, diagnostic)`` where ``diagnostic`` is ``None``
    when the signature is valid or absent, otherwise describes the failure.
    """

    if not secret:
        return True, None

    signature_header = _extract_signature(headers)
    if not signature_header:
        return False, "missing_signature"

    algorithm, signature = _resolve_algorithm(signature_header)
    if not signature:
        return False, "invalid_signature_format"

    hash_constructor = _SUPPORTED_SIGNATURE_ALGORITHMS.get(algorithm)
    if hash_constructor is None:
        return False, "unsupported_signature_algorithm"

    expected = hmac.new(secret.encode("utf-8"), raw_body, hash_constructor).hexdigest()
    if hmac.compare_digest(expected, signature):
        return True, None

    # Some integrations may send JSON dumps with reordered keys. Attempt a
    # deterministic encoding fallback before rejecting to reduce false negatives.
    try:
        parsed = json.loads(raw_body.decode("utf-8"))
    except Exception:
        parsed = None

    if parsed is not None:
        canonical_body = json.dumps(parsed, separators=(",", ":"), sort_keys=True).encode("utf-8")
        expected_canonical = hmac.new(secret.encode("utf-8"), canonical_body, hash_constructor).hexdigest()
        if hmac.compare_digest(expected_canonical, signature):
            return True, None

    return False, "signature_mismatch"


def normalize_payment_status(raw_status: Optional[str]) -> str:
    if not raw_status:
        return "unknown"
    normalized = raw_status.strip().lower()
    if normalized in _APPROVED_PAYMENT_STATUSES:
        return "approved"
    if normalized in _PENDING_PAYMENT_STATUSES:
        return "pending"
    if normalized in _REFUNDED_PAYMENT_STATUSES:
        return "refunded"
    if normalized in _CANCELLED_PAYMENT_STATUSES:
        return "cancelled"
    if normalized == "in_mediation":
        return "pending"
    if normalized == "charged_back":
        return "cancelled"
    return "unknown"


def _get_payment_body(token: str, payment_id: str) -> Dict[str, Any]:
    if mercadopago is None:
        raise MercadoPagoError("SDK mercadopago não está instalado no ambiente.")

    try:
        sdk = mercadopago.SDK(token)
    except Exception as exc:  # pragma: no cover - defensive
        raise MercadoPagoError(f"Falha ao inicializar SDK do Mercado Pago: {exc}") from exc

    try:
        response: Dict[str, Any] = sdk.payment().get(payment_id)
    except Exception as exc:  # pragma: no cover - network/SDK failure
        raise MercadoPagoError(f"Erro ao consultar pagamento {payment_id}: {exc}") from exc

    status_code = response.get("status")
    if status_code != 200:
        message = response.get("response", {}).get("message") if isinstance(response.get("response"), dict) else None
        raise MercadoPagoError(
            f"Falha ao consultar pagamento {payment_id}: status {status_code} - {message or 'sem detalhes'}"
        )

    body = response.get("response")
    if not isinstance(body, dict):
        raise MercadoPagoError("Resposta inválida ao consultar pagamento.")
    return body


def fetch_payment(token: str, payment_id: str) -> MercadoPagoPayment:
    body = _get_payment_body(token, payment_id)

    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    payer_email = _extract_email(body)

    return MercadoPagoPayment(
        payment_id=str(body.get("id")) if body.get("id") is not None else payment_id,
        status=body.get("status"),
        status_detail=body.get("status_detail"),
        transaction_amount=_parse_decimal(body.get("transaction_amount")),
        currency_id=body.get("currency_id"),
        external_reference=body.get("external_reference"),
        metadata=metadata,
        payer_email=payer_email,
        date_created=_normalize_timestamp(body.get("date_created")),
        date_approved=_normalize_timestamp(body.get("date_approved")),
        preference_id=body.get("preference_id"),
    )


def evaluate_integration(token: Optional[str], *, limit: int = 10, environment: Optional[str] = None) -> MercadoPagoSummary:
    """Evaluate Mercado Pago integration state using the official SDK.

    The return value always includes a configuration status (``status``) and a
    data availability status (``availability``). The availability value is
    ``None`` when the integration is not configured. Possible values:

    - status: ``configured`` or ``not_configured``
    - availability: ``available``, ``no_data`` or ``query_failed``
    """

    sanitized_token, status = sanitize_access_token(token, environment=environment)

    if sanitized_token is None:
        if status == AccessTokenStatus.ABSENT:
            detail = "Credenciais do Mercado Pago ausentes."
        elif status == AccessTokenStatus.PLACEHOLDER:
            detail = "Credenciais do Mercado Pago aparentam ser placeholders."
        elif status == AccessTokenStatus.INVALID_FORMAT:
            detail = "Formato do token do Mercado Pago inválido."
        elif status == AccessTokenStatus.SANDBOX_DISALLOWED:
            detail = "Token Sandbox não é permitido no ambiente de produção."
        elif status == AccessTokenStatus.PRODUCTION_DISALLOWED:
            detail = "Token de produção não é permitido no ambiente de homologação."
        else:
            detail = "Credenciais do Mercado Pago inválidas ou ausentes."
        return MercadoPagoSummary(
            status="not_configured",
            availability=None,
            detail=detail,
            total_confirmed=Decimal("0"),
            confirmed_count=0,
            last_payment_at=None,
            payments=[],
        )

    token = sanitized_token

    if mercadopago is None:
        return MercadoPagoSummary(
            status="configured",
            availability="query_failed",
            detail="SDK mercadopago não está instalado no ambiente.",
            total_confirmed=Decimal("0"),
            confirmed_count=0,
            last_payment_at=None,
            payments=[],
        )

    try:
        sdk = mercadopago.SDK(token)
    except Exception as exc:  # pragma: no cover - defensive fallback
        _LOGGER.error("[MERCADOPAGO] Falha ao instanciar SDK: %s", exc)
        return MercadoPagoSummary(
            status="configured",
            availability="query_failed",
            detail="Não foi possível inicializar a SDK do Mercado Pago.",
            total_confirmed=Decimal("0"),
            confirmed_count=0,
            last_payment_at=None,
            payments=[],
        )

    try:
        response: Dict[str, Any] = sdk.payment().search(
            filters={
                "sort": "date_created",
                "criteria": "desc",
                "status": "approved",
                "limit": limit,
            }
        )
    except Exception as exc:  # pragma: no cover - network failures mocked in tests
        _LOGGER.error("[MERCADOPAGO] Erro ao consultar pagamentos: %s", exc)
        return MercadoPagoSummary(
            status="configured",
            availability="query_failed",
            detail="Erro ao consultar a API do Mercado Pago.",
            total_confirmed=Decimal("0"),
            confirmed_count=0,
            last_payment_at=None,
            payments=[],
        )

    http_status = response.get("status")
    body = response.get("response") or {}

    if http_status != 200:
        message = body.get("message") or "Falha ao consultar o Mercado Pago."
        _LOGGER.warning("[MERCADOPAGO] Consulta retornou status %s: %s", http_status, message)
        return MercadoPagoSummary(
            status="configured",
            availability="query_failed",
            detail=str(message),
            total_confirmed=Decimal("0"),
            confirmed_count=0,
            last_payment_at=None,
            payments=[],
        )

    results = body.get("results") or []
    payments: List[MercadoPagoRecord] = []
    total_confirmed = Decimal("0")
    confirmed_count = 0
    latest_timestamp: Optional[datetime] = None

    for entry in results:
        payment_id = str(entry.get("id")) if entry.get("id") is not None else None
        status = entry.get("status")
        amount_value = _parse_decimal(entry.get("transaction_amount"))
        created_at = _normalize_timestamp(entry.get("date_created"))
        payer_email = _extract_email(entry)

        payments.append(
            MercadoPagoRecord(
                payment_id=payment_id,
                status=status,
                amount=amount_value,
                created_at=created_at,
                payer_email=payer_email,
            )
        )

        if status and status.lower() in _APPROVED_PAYMENT_STATUSES and amount_value is not None:
            total_confirmed += amount_value
            confirmed_count += 1
            latest_candidate = _parse_datetime(entry.get("date_approved") or entry.get("date_created"))
            if latest_candidate and (latest_timestamp is None or latest_candidate > latest_timestamp):
                latest_timestamp = latest_candidate

    if not payments:
        return MercadoPagoSummary(
            status="configured",
            availability="no_data",
            detail="Nenhum pagamento aprovado retornado pelo Mercado Pago.",
            total_confirmed=Decimal("0"),
            confirmed_count=0,
            last_payment_at=None,
            payments=[],
        )

    latest_str = latest_timestamp.isoformat().replace("+00:00", "Z") if latest_timestamp else None

    return MercadoPagoSummary(
        status="configured",
        availability="available",
        detail=None,
        total_confirmed=total_confirmed,
        confirmed_count=confirmed_count,
        last_payment_at=latest_str,
        payments=payments,
    )


def _parse_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):  # pragma: no cover - sanitisation fallback
        return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _normalize_timestamp(value: Any) -> Optional[str]:
    dt = _parse_datetime(value)
    if dt is None:
        return None
    return dt.isoformat().replace("+00:00", "Z")


def _extract_email(entry: Dict[str, Any]) -> Optional[str]:
    payer = entry.get("payer") if isinstance(entry, dict) else None
    if isinstance(payer, dict):
        email = payer.get("email")
        if isinstance(email, str) and email.strip():
            return email.strip()
    return None
