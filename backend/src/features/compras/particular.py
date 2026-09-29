"""Detección y cálculo del patrón "compra particular" (008/009, corregido
2026-09-26 — casos reales "2JM", "ACA Bolivar", "Cumo Store"): una compra
con una línea negativa ("Compra particular", "Compra particular Sergio",
"Devolución compra particular"...) que descuenta de su propio total la
parte que en realidad es un gasto personal pagado con medios de la
empresa (tarjeta, efectivo).

La línea negativa NO tiene que netear la compra a $0: puede ser un
descuento parcial (ej. una compra de $13.521 con una línea "Compra
particular Lucy" de -$6.080,51 deja $7.440,50 de deuda real con el
proveedor, y $6.080,51 de gasto personal) — caso agregado 2026-09-26 al
extender `cuentas_socios` (021) a splits parciales, no solo compras
100% personales.

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
    línea negativa, es decir lo que realmente cobró el proveedor/la
    tarjeta) — usado por `tarjetas_resumenes` para conciliar contra el
    monto real del resumen, sin importar si el descuento fue total o
    parcial. `None` si la compra no tiene ninguna línea "particular"
    (no es candidata)."""
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


def importe_personal_compra_particular(id_compra: int) -> float | None:
    """Importe personal de una compra "particular": el valor absoluto de
    la línea negativa en sí (no el total reconstruido) — lo que hay que
    asignarle al socio. Coincide con `importe_bruto_compra_particular`
    cuando la compra queda neteada a $0 (100% personal), pero es distinto
    cuando queda un remanente de deuda real con el proveedor (split
    parcial): ese remanente es de la empresa, no del socio, y no debe
    sumarse a lo que se le asigna. `None` si no es una compra "particular"."""
    fila = fetch_one(
        f"""
        SELECT pa.cp AS cp
        FROM dbo.vw_Compras_ImporteDocumento w
        {APLICA_PARTICULAR_JOIN}
        WHERE w.IdDeuda = ?
        """,
        (id_compra,),
    )
    if fila is None or float(fila["cp"] or 0) == 0:
        return None
    return round(abs(float(fila["cp"])), 2)
