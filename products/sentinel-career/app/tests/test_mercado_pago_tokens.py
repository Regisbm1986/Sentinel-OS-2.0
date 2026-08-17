from backend.app.services.mercado_pago import (
    AccessTokenStatus,
    sanitize_access_token,
)


def test_sanitize_access_token_absent_returns_absent_status():
    token, status = sanitize_access_token(None, environment="homolog")

    assert token is None
    assert status == AccessTokenStatus.ABSENT


def test_sanitize_access_token_placeholder_detected():
    token, status = sanitize_access_token("sandbox-token", environment="homolog")

    assert token is None
    assert status == AccessTokenStatus.PLACEHOLDER


def test_sanitize_access_token_sandbox_pattern_allowed_in_homolog():
    sandbox_token = "TEST-1234567890-000000-0123456789abcdef0123456789abcdef-123456"

    token, status = sanitize_access_token(sandbox_token, environment="homolog")

    assert token == sandbox_token
    assert status == AccessTokenStatus.SANDBOX


def test_sanitize_access_token_sandbox_disallowed_in_production():
    sandbox_token = "TEST-1234567890-000000-0123456789abcdef0123456789abcdef-123456"

    token, status = sanitize_access_token(sandbox_token, environment="production")

    assert token is None
    assert status == AccessTokenStatus.SANDBOX_DISALLOWED


def test_sanitize_access_token_production_token_allowed_in_production(monkeypatch):
    production_token = "APP_USR-0123456789abcdef0123456789abcdef"

    token, status = sanitize_access_token(production_token, environment="production")

    assert token == production_token
    assert status == AccessTokenStatus.PRODUCTION


def test_sanitize_access_token_production_disallowed_in_homolog():
    production_token = "APP_USR-0123456789abcdef0123456789abcdef"

    token, status = sanitize_access_token(production_token, environment="homolog")

    assert token is None
    assert status == AccessTokenStatus.PRODUCTION_DISALLOWED


def test_sanitize_access_token_invalid_test_pattern():
    token, status = sanitize_access_token("TEST-invalid", environment="homolog")

    assert token is None
    assert status == AccessTokenStatus.INVALID_FORMAT


def test_sanitize_access_token_falls_back_to_env(monkeypatch):
    sandbox_token = "TEST-1234567890-000000-0123456789abcdef0123456789abcdef-123456"
    monkeypatch.setenv("ENVIRONMENT", "homolog")

    token, status = sanitize_access_token(sandbox_token)

    assert token == sandbox_token
    assert status == AccessTokenStatus.SANDBOX
