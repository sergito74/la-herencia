"""FastAPI app entrypoint. Mounts feature routers.

Feature routers may expose reads and task-scoped writes to the development
database WC. The shared connection layer prevents writes to the protected
official database during development.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.tokens import verificar_token
from src.errors import register_error_handlers
from src.features.auth.router import COOKIE_NAME
from src.features.auth.router import router as auth_router
from src.features.arrendamientos.router import router as arrendamientos_router
from src.features.compras.router import router as compras_router
from src.features.contactos.router import router as contactos_router
from src.features.cuentas_corrientes.router import router as cuentas_corrientes_router
from src.features.documentos.router import router as documentos_router
from src.features.imputacion.router import router as imputacion_router
from src.features.impuestos.router import router as impuestos_router
from src.features.ordenes.router import router as ordenes_router
from src.features.planificacion.router import router as planificacion_router
from src.features.remitos.router import router as remitos_router
from src.features.resultado_cultivo.router import router as resultado_cultivo_router
from src.features.remitos.stock_router import router as stock_router
from src.features.remuneraciones.router import router as remuneraciones_router
from src.features.sesion.router import router as sesion_router
from src.features.tarjetas.router import router as tarjetas_router
from src.features.tarjetas_cuotas.router import router as tarjetas_cuotas_router
from src.features.tarjetas_resumenes.router import router as tarjetas_resumenes_router
from src.features.tesoreria.router import router as tesoreria_router
from src.features.ventas_granos.router import router as ventas_granos_router
from src.features.ventas_hacienda.router import router as ventas_hacienda_router

app = FastAPI(
    title="La Herencia API",
    description="API de La Herencia sobre SQL Server WC.",
    version="0.1.0",
)

register_error_handlers(app)

# El frontend Next.js corre en un origen distinto (localhost:3000/3001) en
# desarrollo. Sin esto, el navegador bloquea toda llamada a /api/* por
# CORS aunque el backend responda 200 — nunca se detectó porque las
# verificaciones previas usaban curl (mismo origen que el servidor) en
# vez de un fetch real desde el navegador. GET (lectura, mayoría de la
# API) + PATCH/POST/PUT/DELETE (escrituras reales, siempre acotadas a `WC`
# — ver `execute_write`/`_assert_target_is_wc` en `src/db/connection.py`).
# PUT/DELETE quedaron afuera de la lista original (agregados recién en
# 006-carga-compras) — el navegador bloqueaba su preflight (OPTIONS) en
# silencio, sin llegar nunca al backend, por eso la edición/eliminación de
# compras fallaba con un error genérico sin detalle (2026-09-17).
_allowed_origins = os.environ.get(
    "LA_HERENCIA_CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "PATCH", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Endpoints exentos de autenticación (016-autenticacion, FR-001): el propio
# login, el chequeo de salud del launcher y la documentación automática
# (no exponen datos de WC).
_AUTH_EXEMPT_PATHS = {"/api/auth/login", "/health", "/docs", "/openapi.json"}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Exige una sesión válida en toda la API salvo `_AUTH_EXEMPT_PATHS`.

    Además rechaza con 403 las escrituras (POST/PUT/PATCH/DELETE) de
    usuarios con rol `Lectura` (FR-006), sin llegar a invocar el endpoint.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in _AUTH_EXEMPT_PATHS:
            return await call_next(request)

        token = request.cookies.get(COOKIE_NAME)
        payload = verificar_token(token) if token else None
        if payload is None:
            return JSONResponse(status_code=401, content={"detail": "Sesión inválida o expirada"})

        if request.method in _WRITE_METHODS and payload.get("rol") == "Lectura":
            return JSONResponse(status_code=403, content={"detail": "Rol de solo lectura"})

        request.state.usuario = payload
        return await call_next(request)


app.add_middleware(AuthMiddleware)

app.include_router(auth_router)
app.include_router(arrendamientos_router)
app.include_router(compras_router)
app.include_router(contactos_router)
app.include_router(cuentas_corrientes_router)
app.include_router(documentos_router)
app.include_router(imputacion_router)
app.include_router(impuestos_router)
app.include_router(remitos_router)
app.include_router(ordenes_router)
app.include_router(planificacion_router)
app.include_router(resultado_cultivo_router)
app.include_router(stock_router)
app.include_router(remuneraciones_router)
app.include_router(sesion_router)
app.include_router(tarjetas_router)
app.include_router(tarjetas_cuotas_router)
app.include_router(tarjetas_resumenes_router)
app.include_router(tesoreria_router)
app.include_router(ventas_granos_router)
app.include_router(ventas_hacienda_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
