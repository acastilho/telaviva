from fastapi.testclient import TestClient

from app.main import app, get_health_checker


class HealthyChecker:
    async def check(self) -> dict[str, str]:
        return {"database": "up", "redis": "up"}


class UnhealthyChecker:
    async def check(self) -> dict[str, str]:
        raise ConnectionError("unavailable")


client = TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_liveness() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_when_dependencies_are_available() -> None:
    app.dependency_overrides[get_health_checker] = HealthyChecker
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "services": {"database": "up", "redis": "up"},
    }


def test_readiness_when_dependency_is_unavailable() -> None:
    app.dependency_overrides[get_health_checker] = UnhealthyChecker
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Infrastructure dependency unavailable"}
