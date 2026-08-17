import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from backend.auth.exceptions import InvalidCredentials
from backend.auth.models import User

_ALGORITHM = "HS256"


_SECRET_BYTES: Optional[bytes] = None


def _load_secret() -> bytes:
    secret = (
        os.getenv("JWT_SECRET")
        or os.getenv("SENTINEL_JWT_SECRET")
        or os.getenv("SENTINEL_SECRET_KEY")
    )
    if not secret:
        raise RuntimeError(
            "JWT secret not configured. Set JWT_SECRET or SENTINEL_JWT_SECRET before issuing tokens."
        )
    return secret.encode()


def _get_secret_bytes() -> bytes:
    global _SECRET_BYTES
    if _SECRET_BYTES is None:
        _SECRET_BYTES = _load_secret()
    return _SECRET_BYTES


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: bytes) -> bytes:
    return hmac.new(_get_secret_bytes(), message, hashlib.sha256).digest()


def _build_token(payload: Dict[str, Any]) -> str:
    header = {"alg": _ALGORITHM, "typ": "JWT"}
    header_segment = _b64encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    payload_segment = _b64encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    signing_input = f"{header_segment}.{payload_segment}".encode()
    signature_segment = _b64encode(_sign(signing_input))
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _parse_token(token: str) -> Dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise InvalidCredentials("Invalid token format") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode()
    expected_signature = _sign(signing_input)
    provided_signature = _b64decode(signature_segment)

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise InvalidCredentials("Invalid token signature")

    try:
        payload: Dict[str, Any] = json.loads(_b64decode(payload_segment).decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidCredentials("Invalid token payload") from exc

    return payload


def create_access_token(user: User, exp: int = 60 * 15) -> str:
    payload = {
        "sub": user.id,
        "email": user.email,
        "exp": int(time.time() + exp),
        "plan": getattr(user, "plan", "FREE"),
        "type": "access",
    }
    return _build_token(payload)


def create_refresh_token(user: User, exp: int = 60 * 60 * 24 * 7) -> str:
    payload = {
        "sub": user.id,
        "exp": int(time.time() + exp),
        "type": "refresh",
    }
    return _build_token(payload)


def validate_token(token: str) -> Dict[str, Any]:
    payload = _parse_token(token)
    expires_at = payload.get("exp")
    if not isinstance(expires_at, (int, float)):
        raise InvalidCredentials("Token expiration missing")
    if expires_at < time.time():
        raise InvalidCredentials("Token expired")
    return payload


def _reset_cached_secret_for_tests() -> None:  # pragma: no cover - used in tests
    global _SECRET_BYTES
    _SECRET_BYTES = None
