"""Detección y cálculo del patrón "compra particular" (008/009, corregido
2026-09-26 — casos reales "2JM", "ACA Bolivar", "Cumo Store"): una compra
con una línea negativa ("Compra particular", "Compra particular Sergio",
"Devolución compra particular"...) que la netea a $0 en su propio total.

Fuente única de esta lógica, reutilizada por `tarjetas_resumenes`
(candidatos de conciliación de resumen) y `cuentas_socios` (021, candidatas
a asignar a un socio) — no duplicar esta consulta en un segundo lugar
(021-cuentas-socios, research.md §3 / tasks.md T006-T007).

La línea negativa puede cargarse de dos formas (`Precio Unitario` negativo
o `Cantidad` negativa — mismo efecto sobre el total, solo cambia qué
factor es negativo): el filtro compara el SUBTOTAL de la línea, no un
factor en particular, para reconocer ambas.
"""

from __future__ import annotations

from src.db.connection import fetch_one

# Fragmento SQL reusable: la consulta que lo incluya debe tener un alias
# `w` con una columna `IdDeuda` (la Compra) en el FROM/JOIN previo — ver
# `tarjetas_resumenes/repository.py` para el patrón de uso en listados
# (uno por proveedor/contacto, no fila por fila).
APLICA_PARTICULAR_JOIN = """
    OUTER APPLY (
        SELECT ISNULL(SUM(dc.Cantidad * dc.[Precio Unitario] * (1 + ISNULL(dc.IVA, 0) / 100.0)), 0) AS cp
        FROM dbo.Det_Compras dc
        WHERE dc.IdCompra = w.IdDeuda
          AND dc.Cantidad * dc.[Precio Unitario] < 0
          AND dc.[Producto/Servicio] LIKE '%particular%'
    ) pa
"""


def importe_bruto_compra_particular(id_compra: int) -> float | None:
    """Importe bruto de una compra "particular" (el total antes de la
    línea negativa que la netea a $0), o `None` si la compra no tiene
    ninguna línea "particular" (no es candidata)."""
    fila = fetch_one(
        f"""
        SELECT w.ImporteDocumento - pa.cp AS bruto, pa.cp AS cp
        FROM dbo.vw_Compras_ImporteDocumento w
        {APLICA_PARTICULAR_JOIN}
        WHERE w.IdDeuda = ?
        """,
        (id_compra,),
    )
    if fila is None or float(fila["cp"] or 0) == 0:
        return None
    return round(float(fila["bruto"]), 2)
