import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.document_errors import DocumentProcessingError

logger = logging.getLogger("akshara_backend")


def error_payload(code: str, message: str, details: Dict[str, Any] | None = None) -> dict:
    return {"success": False, "error": {"code": code, "message": message, "details": details or {}}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DocumentProcessingError)
    async def document_error_handler(request: Request, exc: DocumentProcessingError):
        return JSONResponse(status_code=exc.status_code, content=error_payload(exc.code, exc.message))

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        code_by_status = {400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 413: "FILE_TOO_LARGE", 415: "UNSUPPORTED_MEDIA_TYPE", 422: "VALIDATION_ERROR", 503: "SERVICE_UNAVAILABLE"}
        code = code_by_status.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request could not be processed."
        return JSONResponse(status_code=exc.status_code, content=error_payload(code, message))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        details = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "Invalid value"), "type": e.get("type", "value_error")} for e in exc.errors()]
        return JSONResponse(status_code=422, content=error_payload("VALIDATION_ERROR", "Request validation failed.", {"issues": details}))

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled API error for %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=error_payload("INTERNAL_ERROR", "An unexpected server error occurred."))
