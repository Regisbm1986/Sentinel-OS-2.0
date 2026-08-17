from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.main import app
from backend.app.services.mercado_pago import (
    MercadoPagoRecord,
    MercadoPagoSummary,
)


def test_admin_dashboard_metrics_uses_data_sources(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(main_module, "_is_authenticated", lambda request: True)
    monkeypatch.setattr(main_module, "has_azure_openai_credentials", lambda: True)
    monkeypatch.setattr(main_module, "_has_oauth_configuration", lambda *keys: True)
    monkeypatch.setattr(main_module, "_get_mercadopago_access_token", lambda: "live-token")

    sample_users = [
        SimpleNamespace(
            id="u1",
            name="Alice",
            email="alice@example.com",
            plan="PRO",
            last_login="2026-08-10T10:30:00+00:00",
            is_active=True,
        ),
        SimpleNamespace(
            id="u2",
            name="Bruno",
            email="bruno@example.com",
            plan="FREE",
            last_login=None,
            is_active=False,
        ),
    ]
    monkeypatch.setattr(main_module, "list_users", lambda limit=None: sample_users)
    summary = MercadoPagoSummary(
        status="configured",
        availability="available",
        detail=None,
        total_confirmed=Decimal("109.40"),
        confirmed_count=2,
        last_payment_at="2026-08-05T10:00:00+00:00",
        payments=[
            MercadoPagoRecord(
                payment_id="p1",
                status="approved",
                amount=Decimal("59.90"),
                created_at="2026-08-05T10:00:00+00:00",
                payer_email="alice@example.com",
            ),
            MercadoPagoRecord(
                payment_id="p2",
                status="approved",
                amount=Decimal("49.50"),
                created_at="2026-08-04T00:23:58+00:00",
                payer_email="bruno@example.com",
            ),
        ],
    )
    monkeypatch.setattr(main_module, "evaluate_mercadopago", lambda token, environment=None: summary)

    response = client.get("/api/admin/dashboard/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["users_total"] == 2
    assert data["integrations"]["azure_openai"] == "configured"
    card = data["integrations"]["mercado_pago"]
    assert card["status"] == "configured"
    assert card["confirmed_total"] == "R$ 109,40"
    assert card["confirmed_count"] == 2
    assert data["revenue_caption"] == "2 pagamentos confirmados"


def test_admin_dashboard_metrics_without_mercadopago(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(main_module, "_is_authenticated", lambda request: True)
    monkeypatch.setattr(main_module, "list_users", lambda limit=None: [])
    monkeypatch.setattr(main_module, "has_azure_openai_credentials", lambda: False)
    monkeypatch.setattr(main_module, "_has_oauth_configuration", lambda *keys: False)
    summary = MercadoPagoSummary(
        status="not_configured",
        availability=None,
        detail="Credenciais do Mercado Pago ausentes.",
        total_confirmed=Decimal("0"),
        confirmed_count=0,
        last_payment_at=None,
        payments=[],
    )
    monkeypatch.setattr(main_module, "evaluate_mercadopago", lambda token, environment=None: summary)

    response = client.get("/api/admin/dashboard/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["integrations"]["azure_openai"] == "not_configured"
    card = data["integrations"]["mercado_pago"]
    assert card["status"] == "not_configured"
    assert card["detail"] == "Credenciais do Mercado Pago ausentes."
    assert card["confirmed_total"] == "R$ 0,00"
    assert data["revenue_caption"] == "Nenhum pagamento confirmado"


def test_admin_dashboard_displays_career_health_history(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(main_module, "_is_authenticated", lambda request: True)
    monkeypatch.setattr(
        main_module,
        "_build_dashboard_context",
        lambda: {
            "app_status": {"status": "online", "checked_at": "10/08/2026 12:00 UTC"},
            "users": [],
            "integrations": {
                "azure_openai": "configured",
                "google_oauth": "configured",
                "linkedin_oauth": "configured",
                "mercado_pago": {
                    "status": "configured",
                    "availability": "available",
                    "detail": None,
                    "confirmed_total": "R$ 0,00",
                    "confirmed_count": 0,
                    "last_payment": "Sem dados",
                },
            },
            "mercadopago_payments": [],
            "revenue_caption": "Nenhum pagamento confirmado",
            "career_health_history": [
                {
                    "timestamp": "2026-08-05T09:00:00+00:00",
                    "career_health": 84,
                    "status": "GOOD",
                    "recommendations": ["Fortalecer networking"],
                }
            ],
            "logs": [],
        },
    )

    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    html = response.text
    assert "Career Health" in html
    assert "Fortalecer networking" in html


def test_admin_dashboard_contains_career_cta(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(main_module, "_is_authenticated", lambda request: True)
    monkeypatch.setattr(
        main_module,
        "_build_dashboard_context",
        lambda: {
            "app_status": {"status": "online", "checked_at": "10/08/2026 12:00 UTC"},
            "users": [],
            "integrations": {
                "azure_openai": "not_configured",
                "google_oauth": "not_configured",
                "linkedin_oauth": "not_configured",
                "mercado_pago": {
                    "status": "not_configured",
                    "availability": None,
                    "detail": "Integração Mercado Pago não configurada",
                    "confirmed_total": "R$ 0,00",
                    "confirmed_count": 0,
                    "last_payment": "Sem dados",
                },
            },
            "mercadopago_payments": [],
            "revenue_caption": "Nenhum pagamento confirmado",
            "career_health_history": [],
            "logs": [],
        },
    )

    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    html = response.text
    assert "Integração Mercado Pago não configurada." in html
    assert "Sem usuários cadastrados neste momento." in html