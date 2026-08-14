from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import ResourceNotFoundError


def test_unknown_route_uses_standard_error_envelope(
    client: TestClient,
) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404

    payload = response.json()

    assert payload["error"]["code"] == "route_not_found"
    assert payload["error"]["message"] == "Not Found"
    assert payload["error"]["details"] is None
    assert payload["error"]["request_id"]
    assert payload["error"]["request_id"] == response.headers["X-Request-ID"]


def test_application_error_uses_standard_envelope(
    application: FastAPI,
) -> None:
    @application.get("/test/not-found")
    async def test_not_found() -> None:
        raise ResourceNotFoundError(
            "Evidence 'missing_watch' was not found",
            details={
                "evidence_id": "missing_watch",
            },
        )

    with TestClient(
        application,
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/test/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "resource_not_found",
            "message": ("Evidence 'missing_watch' was not found"),
            "details": {
                "evidence_id": "missing_watch",
            },
            "request_id": response.headers["X-Request-ID"],
        }
    }


def test_validation_error_uses_standard_envelope(
    application: FastAPI,
) -> None:
    @application.get("/test/validation")
    async def test_validation(limit: int) -> dict[str, int]:
        return {
            "limit": limit,
        }

    with TestClient(
        application,
        raise_server_exceptions=False,
    ) as client:
        response = client.get(
            "/test/validation",
            params={
                "limit": "not-an-integer",
            },
        )

    assert response.status_code == 422

    payload = response.json()

    assert payload["error"]["code"] == "request_validation_failed"
    assert payload["error"]["details"][0]["path"] == "query.limit"
    assert payload["error"]["request_id"]


def test_unexpected_error_does_not_leak_stack_trace(
    application: FastAPI,
) -> None:
    @application.get("/test/crash")
    async def test_crash() -> None:
        secret_internal_value = "culprit-is-maya"
        raise RuntimeError(secret_internal_value)

    with TestClient(
        application,
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/test/crash")

    assert response.status_code == 500

    payload = response.json()
    response_text = response.text

    assert payload["error"]["code"] == "internal_server_error"
    assert payload["error"]["message"] == "An unexpected error occurred"
    assert payload["error"]["details"] is None
    assert payload["error"]["request_id"]

    assert "culprit-is-maya" not in response_text
    assert "RuntimeError" not in response_text
    assert "Traceback" not in response_text
