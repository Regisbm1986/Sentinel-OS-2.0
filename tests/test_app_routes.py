from fastapi.testclient import TestClient

from products.sentinel_career.backend.app.main import app
from products.sentinel_career.backend.auth.auth import USERS_DB, SESSIONS, REFRESH_TOKENS, register_user


def test_root_route_serves_landing_page():
    client = TestClient(app)

    USERS_DB.clear()
    SESSIONS.clear()
    REFRESH_TOKENS.clear()
    register_user("QA", "qa@sentinel.ai", "qa-password", plan="ADMIN")

    login_response = client.post(
        "/login",
        data={"email": "qa@sentinel.ai", "password": "qa-password"},
        follow_redirects=False,
    )
    assert login_response.status_code in {302, 303}

    response = client.get("/")

    assert response.status_code == 200
    assert "Sentinel Career | Login" in response.text
    assert "name=\"email\"" in response.text
