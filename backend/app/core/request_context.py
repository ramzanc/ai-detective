from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"

_MAX_ID_LENGTH = 128

_request_id: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)

_trace_id: ContextVar[str | None] = ContextVar(
    "trace_id",
    default=None,
)


def new_request_id() -> str:
    return str(uuid4())


def new_trace_id() -> str:
    return uuid4().hex


def normalize_external_id(value: str | None) -> str | None:
    """
    Accept a caller-provided correlation ID only when it is safe to use.

    Control characters are rejected because these values will eventually
    appear in structured logs and tracing metadata.
    """

    if value is None:
        return None

    value = value.strip()

    if not value or len(value) > _MAX_ID_LENGTH:
        return None

    if not value.isprintable():
        return None

    return value


def set_request_id(value: str) -> Token[str | None]:
    return _request_id.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def get_request_id() -> str | None:
    return _request_id.get()


def set_trace_id(value: str) -> Token[str | None]:
    return _trace_id.set(value)


def reset_trace_id(token: Token[str | None]) -> None:
    _trace_id.reset(token)


def get_trace_id() -> str | None:
    return _trace_id.get()
