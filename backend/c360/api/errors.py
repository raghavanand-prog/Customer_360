"""Typed error envelope (§16.5, §16.7)."""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def _envelope(request: Request, code: str, message: str, details: dict | None = None) -> dict:
    request_id = getattr(request.state, "request_id", "unknown")
    return {"error": {"code": code, "message": message, "request_id": request_id, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=_envelope(request, exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope(request, "validation_error", "Request validation failed", {"errors": exc.errors()}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        code_map = {401: "unauthenticated", 403: "insufficient_role", 404: "not_found", 429: "rate_limited"}
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(request, code_map.get(exc.status_code, "http_error"), str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(request, "internal_error", "An unexpected error occurred."),
        )
