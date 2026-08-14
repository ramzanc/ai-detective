from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app.api.errors import register_exception_handlers
from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.request_context import (
    REQUEST_ID_HEADER,
    TRACE_ID_HEADER,
    new_request_id,
    new_trace_id,
    normalize_external_id,
    reset_request_id,
    reset_trace_id,
    set_request_id,
    set_trace_id,
)


def create_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """
        Own application startup and shutdown resources.
        """

        app.state.settings = settings
        app.state.ready = False

        # Perform mandatory startup initialization above this line.

        app.state.ready = True

        try:
            yield
        finally:
            app.state.ready = False
            # Close shared resources here in reverse startup order.

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    docs_url = "/docs" if resolved_settings.docs_enabled else None
    redoc_url = "/redoc" if resolved_settings.docs_enabled else None
    openapi_url = "/openapi.json" if resolved_settings.docs_enabled else None

    app = FastAPI(
        title=resolved_settings.application_name,
        version=resolved_settings.application_version,
        debug=resolved_settings.debug,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=create_lifespan(resolved_settings),
    )

    app.state.settings = resolved_settings
    app.state.ready = False

    register_exception_handlers(app)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next) -> Response:
        request_id = (
            normalize_external_id(request.headers.get(REQUEST_ID_HEADER))
            or new_request_id()
        )

        trace_id = (
            normalize_external_id(request.headers.get(TRACE_ID_HEADER))
            or new_trace_id()
        )

        request.state.request_id = request_id
        request.state.trace_id = trace_id

        request_token = set_request_id(request_id)
        trace_token = set_trace_id(trace_id)

        try:
            response = await call_next(request)
        finally:
            reset_trace_id(trace_token)
            reset_request_id(request_token)

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[TRACE_ID_HEADER] = trace_id

        return response

    app.include_router(health_router)
    app.include_router(api_v1_router, prefix=resolved_settings.api_v1_prefix)

    return app


app = create_app()
