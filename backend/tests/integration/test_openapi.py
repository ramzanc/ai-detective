from fastapi.testclient import TestClient


def test_openapi_document_contains_expected_contract(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    document = response.json()

    assert document["info"] == {
        "title": "AI Detective API",
        "version": "0.1.0",
    }

    assert "/health/live" in document["paths"]
    assert "/health/ready" in document["paths"]

    assert document["paths"]["/health/live"]["get"]["tags"] == ["health"]


def test_docs_can_be_disabled() -> None:
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app

    application = create_app(
        Settings(
            environment="production",
            debug=False,
            docs_enabled=False,
        )
    )

    with TestClient(
        application,
        raise_server_exceptions=False,
    ) as client:
        openapi_response = client.get("/openapi.json")
        docs_response = client.get("/docs")

    assert openapi_response.status_code == 404
    assert docs_response.status_code == 404
