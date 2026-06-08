"""Application error types and FastAPI exception handlers.

Every error response shares the same JSON shape: ``{"error": "...", "detail": ...}``
so the frontend can handle failures uniformly.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, handled application errors."""

    status_code = 500

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404


class ValidationError(AppError):
    status_code = 400


class UpstreamError(AppError):
    """A dependency (LLM, vector store) failed."""

    status_code = 502


class DependencyUnavailableError(AppError):
    """A required optional dependency is not installed/configured."""

    status_code = 503


def _describe_validation_error(err: dict) -> str:
    """Render one pydantic validation error as 'field: message'."""
    loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
    field = ".".join(loc) or "(request)"
    return f"{field}: {err.get('msg', 'invalid')}"


def _json_error(status: int, error: str, detail: object | None = None) -> JSONResponse:
    body: dict[str, object] = {"error": error}
    if detail is not None:
        body["detail"] = detail
    return JSONResponse(status_code=status, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that normalise all error responses."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("AppError: %s", exc.message)
        else:
            logger.info("AppError (%s): %s", exc.status_code, exc.message)
        return _json_error(exc.status_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # exc.errors() may embed exception objects (in ``ctx``); jsonable_encoder
        # coerces them into JSON-safe values.
        errors = exc.errors()
        summary = "; ".join(_describe_validation_error(e) for e in errors)
        logger.warning("Request validation failed: %s", summary or "unknown")
        message = (
            f"Request validation failed - {summary}"
            if summary
            else "Request validation failed"
        )
        return _json_error(400, message, jsonable_encoder(errors))

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _json_error(exc.status_code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return _json_error(500, "Internal server error")
