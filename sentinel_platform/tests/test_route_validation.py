from fastapi.testclient import TestClient

import sentinel_platform.backend.api.main as api_main


def test_generated_route_returns_ok_for_existing_module_route():
    client = TestClient(api_main.app)

    response = client.get("/api/")

    assert response.status_code == 200
    assert response.json() == {"module": "beef", "status": "ok"}


def test_generated_route_health_path_still_works():
    client = TestClient(api_main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
