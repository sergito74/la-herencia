"""Búsqueda global Ctrl+K (spec 051 US4): solo lectura. Busca contactos, compras por número, productos, lotes y
órdenes de trabajo; las pantallas y acciones las arma el frontend."""
from __future__ import annotations

import re

from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_all

router = APIRouter(prefix="/api/buscar", tags=["buscar"])


def buscar(q: str) -> list[dict]:
    q = q.strip()
    if len(q) < 2:
        return []
    like = f"%{q}%"
    digitos = re.sub(r"\D", "", q)
    out: list[dict] = []
    for c in fetch_all("SELECT TOP 6 IdContacto AS id, [Razon Social] AS n, [Tipo Contacto] AS t FROM dbo.Contactos "
                       "WHERE [Razon Social] LIKE ? ORDER BY CASE WHEN [Razon Social] LIKE ? THEN 0 ELSE 1 END, [Razon Social]",
                       (like, f"{q}%")):
        out.append({"tipo": "Contactos", "titulo": c["n"], "subtitulo": c["t"] or "", "idContacto": c["id"]})
    if digitos and len(digitos) >= 3:
        for c in fetch_all("SELECT TOP 6 c.IdDeuda AS id, c.[Nro Documento] AS nro, c.[Tipo documento] AS td, c.Fecha AS f, co.[Razon Social] AS p "
                           "FROM dbo.Compras c LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto "
                           "WHERE REPLACE(REPLACE(c.[Nro Documento], '-', ''), ' ', '') LIKE ? ORDER BY c.Fecha DESC", (f"%{digitos}%",)):
            out.append({"tipo": "Compras", "titulo": f"{c['td'] or 'Factura'} {c['nro']}", "subtitulo": f"{c['p'] or ''} · {str(c['f'])[:10]}",
                        "idCompra": c["id"]})
    for p in fetch_all("SELECT TOP 5 IdProducto AS id, Producto AS n, TipoProducto AS t FROM dbo.vw_ProductosBase WHERE Producto LIKE ? "
                       "AND IdProducto IN (SELECT IdFormulado FROM dbo.Remitos_Detalles UNION SELECT IdProducto FROM dbo.Ordenes_Trabajo_Insumos) "
                       "ORDER BY Producto", (like,)):
        out.append({"tipo": "Productos", "titulo": p["n"].strip(), "subtitulo": p["t"] or "", "idProducto": int(p["id"])})
    for l in fetch_all("SELECT TOP 4 IdLote AS id, [Numero Lote] AS n, Superficie AS s FROM dbo.Lotes WHERE [Numero Lote] LIKE ? ORDER BY [Numero Lote]",
                       (f"{q}%",)):
        out.append({"tipo": "Lotes", "titulo": f"Lote {l['n']}", "subtitulo": f"{float(l['s'] or 0):.1f} ha".replace(".", ","), "idLote": l["id"]})
    if q.isdigit() and len(q) <= 5:  # un número corto es una orden: va primero
        ordenes = []
        for o in fetch_all("SELECT TOP 3 o.IdOrdenTrabajo AS id, o.FechaPedido AS f, o.Estado AS e, t.Labor AS l FROM dbo.Ordenes_Trabajo o "
                           "LEFT JOIN dbo.[Tipo Labores] t ON t.IdLabor = o.IdTipoLabor WHERE CAST(o.IdOrdenTrabajo AS varchar(10)) LIKE ? "
                           "ORDER BY o.IdOrdenTrabajo DESC", (f"{digitos}%",)):
            ordenes.append({"tipo": "Órdenes", "titulo": f"Orden {o['id']} · {o['l'] or ''}", "subtitulo": f"{str(o['f'])[:10]} · {o['e']}", "idOrden": o["id"]})
        out = ordenes + out
    return out


@router.get("")
async def buscar_endpoint(q: str = Query("", max_length=80)) -> list[dict]:
    return await run_in_threadpool(buscar, q)
