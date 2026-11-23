from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    def __init__(
        self,
        status_code: int = 500,
        title: str = "Internal Server Error",
        detail: str = "An unexpected error occurred.",
        type_: str = "about:blank",
        instance: str | None = None,
        errors: Any = None,
    ):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type = type_
        self.instance = instance
        self.errors = errors
        super().__init__(detail)


def rfc7807_error_response(
    status_code: int,
    title: str,
    detail: str,
    type_: str = "about:blank",
    instance: str | None = None,
    errors: Any = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        content["instance"] = instance
    if errors is not None:
        content["invalid_params"] = errors

    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={"Content-Type": "application/problem+json"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return rfc7807_error_response(
            status_code=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            type_=exc.type,
            instance=str(request.url),
            errors=exc.errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return rfc7807_error_response(
            status_code=exc.status_code,
            title="HTTP Error",
            detail=str(exc.detail),
            instance=str(request.url),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return rfc7807_error_response(
            status_code=422,
            title="Unprocessable Entity",
            detail="Request validation failed.",
            type_="https://tools.ietf.org/html/rfc4918#section-11.2",
            instance=str(request.url),
            errors=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return rfc7807_error_response(
            status_code=500,
            title="Internal Server Error",
            detail=str(exc) if app.debug else "An unexpected error occurred.",
            instance=str(request.url),
        )
