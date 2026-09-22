"""FastAPI app entrypoint. Mounts feature routers.

Read-only module (constitution principle II, FR-010): only GET endpoints
are registered anywhere under /api.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.errors import register_error_handlers
from src.features.arrendamientos.router import router as arrendamientos_router
from src.features.compras.router import router as compras_router
from src.features.contactos.router import router as contactos_router
from src.features.cuentas_corrientes.router import router as cuentas_corrientes_router
from src.features.documentos.router import router as documentos_router
from src.features.impuestos.router import router as impuestos_router
from src.features.ordenes.router import router as ordenes_router
from src.features.remitos.router import router as remitos_router
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
    description="API de solo lectura sobre SQL Server LaHerencia.",
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
)

app.include_router(arrendamientos_router)
app.include_router(compras_router)
app.include_router(contactos_router)
app.include_router(cuentas_corrientes_router)
app.include_router(documentos_router)
app.include_router(impuestos_router)
app.include_router(remitos_router)
app.include_router(ordenes_router)
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
