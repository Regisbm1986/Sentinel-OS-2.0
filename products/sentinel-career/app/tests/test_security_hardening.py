import base64
import hashlib
import json
import importlib
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret-key")
from backend.app import main as app_module
from backend.auth import auth as auth_module
from backend.auth.exceptions import InvalidCredentials
from backend.auth.jwt_manager import create_access_token, validate_token
from backend.auth.models import User


client = TestClient(app_module.app)


def _b64decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def test_jwt_signature_validation():
    user = User(id="user-1", name="Tester", email="tester@example.com", password_hash="", plan="FREE")

    token = create_access_token(user, exp=60)
    payload = validate_token(token)
    assert payload["sub"] == "user-1"

    header_segment, payload_segment, signature_segment = token.split(".")
    tampered_payload = json.loads(_b64decode(payload_segment).decode())
    tampered_payload["sub"] = "other-user"
    tampered_segment = base64.urlsafe_b64encode(
        json.dumps(tampered_payload, separators=(",", ":"), ensure_ascii=False).encode()
    ).decode().rstrip("=")
    tampered_token = f"{header_segment}.{tampered_segment}.{signature_segment}"

    with pytest.raises(InvalidCredentials):
        validate_token(tampered_token)


def test_password_hashing_pbkdf2():
    hashed = auth_module.hash_password("Sup3rSecret!")
    assert hashed.startswith("pbkdf2$")
    assert auth_module.verify_password("Sup3rSecret!", hashed)
    assert not auth_module.verify_password("wrong-pass", hashed)


def test_password_verify_legacy_hash():
    legacy_hash = hashlib.sha256("legacy-pass".encode()).hexdigest()
    assert auth_module.verify_password("legacy-pass", legacy_hash)
    assert not auth_module.verify_password("invalid", legacy_hash)


def test_jwt_requires_secret(monkeypatch):
    import backend.auth.jwt_manager as jwt_module

    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("SENTINEL_JWT_SECRET", raising=False)
    monkeypatch.delenv("SENTINEL_SECRET_KEY", raising=False)
    jwt_module._reset_cached_secret_for_tests()

    user = User(id="user-2", name="Tester", email="tester@example.com", password_hash="", plan="FREE")
    with pytest.raises(RuntimeError):
        jwt_module.create_access_token(user)

    monkeypatch.setenv("JWT_SECRET", "restored-secret")
    jwt_module._reset_cached_secret_for_tests()
    token = jwt_module.create_access_token(user)
    payload = jwt_module.validate_token(token)
    assert payload["sub"] == "user-2"


def _set_upload_limit(limit: int):
    original_limit = app_module.MAX_RESUME_UPLOAD_SIZE_BYTES
    app_module.MAX_RESUME_UPLOAD_SIZE_BYTES = limit
    return original_limit


def test_resume_parse_rejects_large_file():
    original_limit = _set_upload_limit(1024)
    app_module.PUBLIC_PATHS.add("/api/resume/parse")
    try:
        response = client.post(
            "/api/resume/parse",
            files={"file": ("resume.pdf", b"a" * 2048, "application/pdf")},
        )
    finally:
        app_module.PUBLIC_PATHS.discard("/api/resume/parse")
        app_module.MAX_RESUME_UPLOAD_SIZE_BYTES = original_limit

    assert response.status_code == 413
    assert "limite" in response.json()["detail"].lower()


def test_resume_parse_accepts_small_text():
    original_limit = _set_upload_limit(1024)
    app_module.PUBLIC_PATHS.add("/api/resume/parse")
    try:
        response = client.post(
            "/api/resume/parse",
            files={"file": ("resume.txt", b"Resumo profissional", "text/plain")},
        )
    finally:
        app_module.PUBLIC_PATHS.discard("/api/resume/parse")
        app_module.MAX_RESUME_UPLOAD_SIZE_BYTES = original_limit

    assert response.status_code == 200
    payload = response.json()
    assert "Resumo profissional" in payload["text"]

def test_session_cookie_flags_secure():
    client = TestClient(app_module.app)

    auth_module.USERS_DB.clear()
    auth_module.SESSIONS.clear()
    auth_module.REFRESH_TOKENS.clear()

    auth_module.register_user("Cookie", "cookie@sentinel.ai", "sentinelsecret", plan="PRO")

    response = client.post(
        "/login",
        data={"email": "cookie@sentinel.ai", "password": "sentinelsecret"},
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}
    set_cookie = response.headers.get("set-cookie", "")
    assert app_module.SESSION_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "samesite=lax" in set_cookie.lower()


def test_session_cookie_insecure_flag_toggle(monkeypatch):
    monkeypatch.setenv("SENTINEL_SESSION_COOKIE_SECURE", "0")
    import backend.app.main as main_module

    importlib.reload(main_module)

    test_client = TestClient(main_module.app)
    auth_module.USERS_DB.clear()
    auth_module.SESSIONS.clear()
    auth_module.REFRESH_TOKENS.clear()
    auth_module.register_user("Dev", "dev@sentinel.ai", "devpass123", plan="PRO")

    response = test_client.post(
        "/login",
        data={"email": "dev@sentinel.ai", "password": "devpass123"},
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}
    header_value = response.headers.get("set-cookie", "")
    assert "Secure" not in header_value
    assert "HttpOnly" in header_value
    assert "samesite=lax" in header_value.lower()

    monkeypatch.delenv("SENTINEL_SESSION_COOKIE_SECURE", raising=False)
    importlib.reload(main_module)
