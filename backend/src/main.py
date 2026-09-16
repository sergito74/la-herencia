"""FastAPI app entrypoint. Mounts feature routers.

Read-only module (constitution principle II, FR-010): only GET endpoints
are registered anywhere under /api.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.errors import register_error_handlers
from src.features.arrendamientos.router import router as arrendamientos_router
from src.features.compras.router import router as compras_router
from src.features.cuentas_corrientes.router import router as cuentas_corrientes_router
from src.features.impuestos.router import router as impuestos_router
from src.features.remuneraciones.router import router as remuneraciones_router
from src.features.tesoreria.router import router as tesoreria_router
from src.features.ventas_hacienda.router import router as ventas_hacienda_router

app = FastAPI(
    title="La Herencia API",
    description="API de solo lectura sobre SQL Server LaHerencia.",
    version="0.1.0",
)

register_error_handlers(app)

app.include_router(arrendamientos_router)
app.include_router(compras_router)
app.include_router(cuentas_corrientes_router)
app.include_router(impuestos_router)
app.include_router(remuneraciones_router)
app.include_router(tesoreria_router)
app.include_router(ventas_hacienda_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
