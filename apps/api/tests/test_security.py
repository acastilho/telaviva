import json
import logging

from fastapi.testclient import TestClient
from pytest import LogCaptureFixture

from app.config import Settings
from app.main import app
from app.security import RateLimiter

client = TestClient(app)


def test_wildcard_cors_is_rejected_with_credentials() -> None:
    try:
        Settings(api_cors_origins=["*"])
    except ValueError as error:
        assert "API_CORS_ORIGINS" in str(error)
    else:
        raise AssertionError("wildcard CORS origin should be rejected")


def test_security_headers_and_request_id_are_added() -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "request123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_invalid_request_id_is_replaced() -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "bad request id"})

    assert response.headers["x-request-id"] != "bad request id"
    assert len(response.headers["x-request-id"]) == 32


def test_cors_allows_configured_origin_and_rejects_unknown_origin() -> None:
    allowed = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    rejected = client.options(
        "/auth/login",
        headers={"Origin": "https://attacker.invalid", "Access-Control-Request-Method": "POST"},
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_oversized_and_malformed_content_length_are_rejected() -> None:
    oversized = client.post(
        "/auth/login", content=b"{}", headers={"Content-Length": "1048577"}
    )
    malformed = client.post(
        "/auth/login", content=b"{}", headers={"Content-Length": "invalid"}
    )

    assert oversized.status_code == 413
    assert malformed.status_code == 413


def test_rate_limiter_enforces_window_and_recovers() -> None:
    limiter = RateLimiter()

    assert limiter.allow("client:auth", limit=2, window=10, now=10)
    assert limiter.allow("client:auth", limit=2, window=10, now=11)
    assert not limiter.allow("client:auth", limit=2, window=10, now=12)
    assert limiter.allow("client:auth", limit=2, window=10, now=21)


def test_structured_logs_exclude_credentials(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="telaviva.security"):
        response = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "do-not-log-this"},
            headers={"Authorization": "Bearer do-not-log-token"},
        )

    assert response.status_code == 401
    text = caplog.text
    assert "do-not-log-this" not in text
    assert "do-not-log-token" not in text
    records = [json.loads(record.message) for record in caplog.records]
    assert any(record["event"] == "security_audit" for record in records)
