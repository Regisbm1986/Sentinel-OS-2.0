import os
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_CANONICAL_URL", "https://career.sentinel-os.ia.br")
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "valid-google-client"
os.environ["GOOGLE_CLIENT_SECRET"] = "valid-google-secret"
os.environ["LINKEDIN_OAUTH_CLIENT_ID"] = "valid-linkedin-client"
os.environ["LINKEDIN_CLIENT_SECRET"] = "valid-linkedin-secret"
os.environ.setdefault("SENTINEL_CANONICAL_URL", "https://career.sentinel-os.ia.br")

from products.sentinel_career.backend.app import main as app_module
from products.sentinel_career.backend.app.services.oauth_providers import OAuthUser


@pytest.fixture(autouse=True)
def reset_oauth_state():
    app_module.oauth_state_store._states.clear()  # type: ignore[attr-defined]
    app_module.auth_module.USERS_DB.clear()
    app_module.auth_module._LEGACY_USERS_BY_ID.clear()  # type: ignore[attr-defined]
    yield
    app_module.oauth_state_store._states.clear()  # type: ignore[attr-defined]
    app_module.auth_module.USERS_DB.clear()
    app_module.auth_module._LEGACY_USERS_BY_ID.clear()  # type: ignore[attr-defined]


@pytest.fixture
def client():
    return TestClient(app_module.app)


def _extract_state_data(authorization_url: str) -> tuple[str, str]:
    parsed = urlparse(authorization_url)
    query = parse_qs(parsed.query)
    state = query["state"][0]
    nonce = query["nonce"][0]
    return state, nonce


def test_google_login_returns_authorize_url_with_state_and_nonce(client):
    response = client.get("/api/auth/google/login", params={"next": "/admin/dashboard"})

    assert response.status_code == 200
    payload = response.json()

    authorization_url = payload["authorization_url"]
    parsed = urlparse(authorization_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert query["client_id"][0] == "valid-google-client"
    assert query["state"][0]
    assert query["nonce"][0]
    assert query["redirect_uri"][0] == "https://career.sentinel-os.ia.br/api/auth/google/callback"
    assert "openid" in query["scope"][0]


def test_google_callback_creates_user_and_sets_session(client, monkeypatch):
    login_response = client.get("/api/auth/google/login")
    state_value, _ = _extract_state_data(login_response.json()["authorization_url"])

    monkeypatch.setattr(
        app_module.google_oauth_client,
        "exchange_code",
        lambda **_: {"access_token": "token-123", "id_token": "id-123"},
    )
    monkeypatch.setattr(
        app_module.google_oauth_client,
        "fetch_userinfo",
        lambda _: {"email": "oauth-user@example.com", "email_verified": True, "name": "OAuth User"},
    )
    monkeypatch.setattr(
        app_module.google_oauth_client,
        "build_user",
        lambda **_: OAuthUser(
            provider="google",
            subject="sub-123",
            email="oauth-user@example.com",
            email_verified=True,
            name="OAuth User",
            picture=None,
        ),
    )

    response = client.get(
        "/api/auth/google/callback",
        params={"code": "auth-code", "state": state_value},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == app_module.DEFAULT_POST_LOGIN_ROUTE
    assert app_module.SESSION_COOKIE_NAME in response.cookies
    assert "oauth-user@example.com" in app_module.auth_module.USERS_DB


def test_google_callback_rejects_invalid_state(client):
    response = client.get(
        "/api/auth/google/callback",
        params={"code": "auth-code", "state": "tampered"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "inválido" in response.json()["detail"]


def test_linkedin_oauth_routes_removed(client):
    login_response = client.get("/api/auth/linkedin/login")
    callback_response = client.get(
        "/api/auth/linkedin/callback",
        params={"code": "auth-code", "state": "irrelevant"},
        follow_redirects=False,
    )

    assert login_response.status_code == 404
    assert callback_response.status_code == 404


def test_google_oauth_route_remains_available(client):
    response = client.get("/api/auth/google/login")

    assert response.status_code == 200
    assert "authorization_url" in response.json()


def test_oauth_state_cannot_be_reused(client, monkeypatch):
    login_response = client.get("/api/auth/google/login")
    state_value, _ = _extract_state_data(login_response.json()["authorization_url"])

    monkeypatch.setattr(
        app_module.google_oauth_client,
        "exchange_code",
        lambda **_: {"access_token": "token-123", "id_token": "id-123"},
    )
    monkeypatch.setattr(
        app_module.google_oauth_client,
        "fetch_userinfo",
        lambda _: {"email": "reuse@example.com", "email_verified": True, "name": "Reuse"},
    )
    monkeypatch.setattr(
        app_module.google_oauth_client,
        "build_user",
        lambda **_: OAuthUser(
            provider="google",
            subject="reuse",
            email="reuse@example.com",
            email_verified=True,
            name="Reuse",
            picture=None,
        ),
    )

    first = client.get(
        "/api/auth/google/callback",
        params={"code": "auth-code", "state": state_value},
        follow_redirects=False,
    )

    assert first.status_code == 302

    second = client.get(
        "/api/auth/google/callback",
        params={"code": "auth-code", "state": state_value},
        follow_redirects=False,
    )

    assert second.status_code == 400
    assert "inválido" in second.json()["detail"]
