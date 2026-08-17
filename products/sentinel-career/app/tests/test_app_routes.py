from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.main import app
from backend.auth.auth import USERS_DB, SESSIONS, REFRESH_TOKENS


def test_root_route_serves_public_homepage():
    client = TestClient(app)

    USERS_DB.clear()
    SESSIONS.clear()
    REFRESH_TOKENS.clear()

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers.get("location") is None
    assert "Sentinel Career" in response.text
    assert "orientação" in response.text or "orientacao" in response.text
    assert "análise de currículos" in response.text or "analise de curriculos" in response.text
    assert "/politica-de-privacidade" in response.text
    assert "/diretrizes" in response.text
    assert "/termos" in response.text


def test_root_homepage_mentions_google_login():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "login com Google" in response.text


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
    assert "Painel Administrativo" in response.text
    assert "Azure OpenAI não configurado" in response.text or "Azure OpenAI" in response.text
    assert "Integração Mercado Pago não configurada." in response.text
    assert "Sem usuários cadastrados neste momento." in response.text
