from fastapi.testclient import TestClient

from app.main import app


def test_health():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "telaviva-api"


def test_platform_contract():
    response = TestClient(app).get("/api/platform")

    assert response.status_code == 200
    assert response.json()["roles"] == ["ADMIN", "CREATOR", "VIEWER"]
