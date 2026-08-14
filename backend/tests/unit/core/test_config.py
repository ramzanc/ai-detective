import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_local_settings_are_valid() -> None:
    settings = Settings(
        environment="local",
        debug=True,
    )

    assert settings.environment == "local"
    assert settings.debug is True
    assert settings.api_v1_prefix == "/api/v1"


def test_production_rejects_debug_mode() -> None:
    with pytest.raises(
        ValidationError,
        match="debug must be disabled",
    ):
        Settings(
            environment="production",
            debug=True,
        )


def test_api_prefix_must_start_with_slash() -> None:
    with pytest.raises(
        ValidationError,
        match="must start with",
    ):
        Settings(api_v1_prefix="api/v1")


def test_api_prefix_must_not_end_with_slash() -> None:
    with pytest.raises(
        ValidationError,
        match="must not end with",
    ):
        Settings(api_v1_prefix="/api/v1/")


def test_port_range_is_validated() -> None:
    with pytest.raises(ValidationError):
        Settings(port=70_000)
