"""Business errors with a machine-readable code.

The two frontends are bilingual, so they translate `code`; `message` is English for
logs and developers. Every error response has the same shape:

    {"error": {"code": "category_has_products", "message": "...", "details": {...}}}

Request validation errors (wrong types, missing fields, bad phone pattern) keep
FastAPI's standard 422 body with `detail`.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT


class InvalidRequestError(AppError):
    """The request is well formed but breaks a business rule."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    body: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details:
        body["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content={"error": body})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
