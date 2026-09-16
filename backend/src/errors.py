"""Basic error handling for the API.

Never logs credentials, connection strings, or personal/business data —
only exception types and generic context, per constitution "Data and
Security Constraints".
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("la_herencia.api")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning("ValueError on %s", request.url.path)
        return JSONResponse(status_code=400, content={"detail": "Solicitud invalida"})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error on %s: %s", request.url.path, type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Error interno"})
