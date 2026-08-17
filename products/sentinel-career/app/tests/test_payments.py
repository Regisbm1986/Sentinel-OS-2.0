
import hashlib
import hmac
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.main import app
from backend.app.services.mercado_pago import MercadoPagoPayment


@pytest.fixture
def authenticated_user(monkeypatch):
    dummy_user = SimpleNamespace(id="user-123", email="user@example.com", is_active=True)
    monkeypatch.setattr(main_module, "_require_authenticated_user", lambda request: dummy_user)
    monkeypatch.setattr(main_module, "_is_authenticated", lambda request: True)
    return dummy_user


def test_checkout_requires_authentication():
    client = TestClient(app)
    response = client.post("/api/payments/checkout", json={"plan_id": "pro"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["Location"].startswith("/login?next=%2Fapi%2Fpayments%2Fcheckout")


def test_checkout_rejects_unknown_plan(authenticated_user):
    client = TestClient(app)
    response = client.post("/api/payments/checkout", json={"plan_id": "invalid"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Plano Mercado Pago inválido"


def test_checkout_requires_access_token(monkeypatch, authenticated_user):
    client = TestClient(app)
    monkeypatch.setattr(main_module, "_get_env_value", lambda *keys: None)
    response = client.post("/api/payments/checkout", json={"plan_id": "pro"})
    assert response.status_code == 503
    assert response.json()["detail"] == "MERCADOPAGO_ACCESS_TOKEN não configurado"


def test_checkout_creates_preference(monkeypatch, authenticated_user):
    client = TestClient(app)

    def fake_get_env_value(*keys: str):
        if "MERCADOPAGO_ACCESS_TOKEN" in keys:
            return "live-token"
        return None

    monkeypatch.setattr(main_module, "_get_env_value", fake_get_env_value)
    monkeypatch.setenv("MERCADOPAGO_PAYER_EMAIL", "checkout-billing@example.com")
    monkeypatch.delenv("MERCADOPAGO_RETURN_URL", raising=False)
    monkeypatch.delenv("MERCADOPAGO_WEBHOOK_URL", raising=False)

    captured = {}

    class FakePreference:
        def __init__(self):
            self.created_payload = None

        def create(self, data):
            self.created_payload = data
            return {"response": {"id": "pref-123", "init_point": "https://checkout.example/redirect"}}

    class FakeSDK:
        def __init__(self, token):
            self.token = token
            self.preference_service = FakePreference()

        def preference(self):
            return self.preference_service

    def fake_sdk(token: str):
        instance = FakeSDK(token)
        captured["instance"] = instance
        return instance

    monkeypatch.setattr(main_module, "mercadopago", SimpleNamespace(SDK=fake_sdk))

    response = client.post("/api/payments/checkout", json={"plan_id": "pro"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mercadopago"
    assert payload["plan"]["id"] == "pro"
    assert payload["plan"]["price"] == main_module.MERCADO_PAGO_PLANS["pro"]["price"]
    assert payload["init_point"].startswith("https://checkout.example/")

    sdk_instance = captured["instance"]
    assert sdk_instance.token == "live-token"
    created = sdk_instance.preference_service.created_payload
    assert created["metadata"]["plan_id"] == "pro"
    assert created["metadata"]["user_id"] == authenticated_user.id
    assert created["metadata"]["user_email"] == authenticated_user.email
    assert created["items"][0]["title"] == main_module.MERCADO_PAGO_PLANS["pro"]["title"]
    assert created["payer"]["email"] == "checkout-billing@example.com"
    assert created["external_reference"].startswith("career:pro:")
    assert created["metadata"]["external_reference"] == created["external_reference"]


def _signed_payload(secret: str, payload: dict) -> tuple[bytes, str]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
    return body, f"sha1={signature}"


def test_webhook_processes_payment_and_applies_plan(monkeypatch, tmp_path):
    client = TestClient(app)

    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "super-secret")
    monkeypatch.setattr(main_module, "_get_mercadopago_access_token", lambda: "token-123")

    state_path = tmp_path / "state.json"
    monkeypatch.setattr(main_module, "MERCADOPAGO_STATE_PATH", state_path, raising=False)

    applied_calls = {}

    def fake_update_user_plan(user_id: str, plan: str):
        applied_calls["plan"] = (user_id, plan)

    def fake_get_user_by_id(user_id: str):
        return SimpleNamespace(id=user_id, plan="FREE")

    monkeypatch.setattr(main_module, "update_user_plan", fake_update_user_plan, raising=False)
    monkeypatch.setattr(main_module, "get_user_by_id", fake_get_user_by_id, raising=False)

    payment = MercadoPagoPayment(
        payment_id="pay-123",
        status="approved",
        status_detail="approved",
        transaction_amount=Decimal("39.90"),
        currency_id="BRL",
        external_reference="career:pro:user-456:token",
        metadata={"plan_id": "pro", "user_id": "user-456", "user_email": "buyer@example.com"},
        payer_email="buyer@example.com",
        date_created="2026-08-01T12:00:00Z",
        date_approved="2026-08-01T12:01:00Z",
        preference_id="pref-789",
    )

    monkeypatch.setattr(main_module, "fetch_payment", lambda token, pid: payment, raising=False)

    payload = {"id": "evt-123", "action": "payment.updated", "data": {"id": "pay-123"}}
    body, signature = _signed_payload("super-secret", payload)

    response = client.post(
        "/api/checkout/mercadopago/webhook",
        data=body,
        headers={"X-Hub-Signature": signature, "Content-Type": "application/json"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["normalized_status"] == "approved"
    assert data["plan_applied"] is True
    assert data["already_processed"] is False
    assert applied_calls["plan"] == ("user-456", "PRO")

    response_duplicate = client.post(
        "/api/checkout/mercadopago/webhook",
        data=body,
        headers={"X-Hub-Signature": signature, "Content-Type": "application/json"},
    )

    assert response_duplicate.status_code == 202
    duplicate_data = response_duplicate.json()
    assert duplicate_data["already_processed"] is True
    assert duplicate_data["plan_applied"] is False


def test_webhook_rejects_invalid_signature(monkeypatch):
    client = TestClient(app)

    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "secret-key")

    payload = {"id": "evt-1", "type": "payment", "data": {"id": "pay-1"}}
    body = json.dumps(payload).encode("utf-8")

    response = client.post(
        "/api/checkout/mercadopago/webhook",
        data=body,
        headers={"X-Hub-Signature": "sha1=deadbeef", "Content-Type": "application/json"},
    )

    assert response.status_code == 401
