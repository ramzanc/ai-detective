from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        environment="test",
        debug=False,
        docs_enabled=True,
    )


@pytest.fixture
def application(
    test_settings: Settings,
) -> FastAPI:
    return create_app(test_settings)


@pytest.fixture
def client(
    application: FastAPI,
) -> Iterator[TestClient]:
    with TestClient(
        application,
        raise_server_exceptions=False,
    ) as test_client:
        yield test_client
