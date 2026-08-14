from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_liveness_reports_process_is_alive(
    client: TestClient,
) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
    }


def test_readiness_reports_ready_after_startup(
    client: TestClient,
) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
    }


def test_liveness_does_not_depend_on_readiness(
    application: FastAPI,
) -> None:
    application.state.ready = False

    with TestClient(
        application,
        raise_server_exceptions=False,
    ) as client:
        application.state.ready = False

        live_response = client.get("/health/live")
        ready_response = client.get("/health/ready")

    assert live_response.status_code == 200
    assert live_response.json() == {
        "status": "alive",
    }

    assert ready_response.status_code == 503
    assert ready_response.json() == {
        "status": "not_ready",
    }


def test_health_response_contains_correlation_headers(
    client: TestClient,
) -> None:
    response = client.get("/health/live")

    assert response.headers["X-Request-ID"]
    assert response.headers["X-Trace-ID"]


def test_valid_caller_request_id_is_preserved(
    client: TestClient,
) -> None:
    response = client.get(
        "/health/live",
        headers={
            "X-Request-ID": "frontend-request-123",
            "X-Trace-ID": "frontend-trace-456",
        },
    )

    assert response.headers["X-Request-ID"] == "frontend-request-123"
    assert response.headers["X-Trace-ID"] == "frontend-trace-456"
