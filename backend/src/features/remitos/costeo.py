"""Costo unitario de un renglón de remito a partir de las facturas vinculadas.

El remito no lleva precio: el costo sale de los renglones de factura (Compras)
vinculados renglón por renglón (`tblRemitoCompra`), incluyendo notas de crédito y
de débito que se hayan vinculado al mismo renglón para corregir el precio.

Para cada vínculo el costo por unidad, en la moneda del documento, es:

- el **precio unitario** de la factura/NC/ND, cuando la cantidad de la línea de
  compra coincide con lo remitido en total a esa línea (±5%): en el 92% de los
  vínculos reales la cantidad de la factura y la del remito están en la misma
  unidad aunque la columna «Unidad» de la factura casi siempre esté vacía;
- si no coinciden (por ejemplo la factura dice 1 bidón y el remito 15 litros), el
  **subtotal de la línea prorrateado** entre lo remitido a ella.

Cuentas separadas por moneda: una nota de crédito o de débito emitida en pesos
sólo corrige el precio promedio de los vínculos en pesos de ese renglón; una
emitida en dólares sólo corrige el promedio en dólares (con su propio tipo de
cambio). Nunca se mezcla un ND en dólares con una factura en pesos ni viceversa.
El costo final del renglón es el promedio ponderado por cantidad entre las
cuentas de cada moneda, ya convertidas a pesos.
"""

from __future__ import annotations

from collections import defaultdict

TOLERANCIA_CANTIDAD = 0.05
EPS = 1e-9


def costo_unitario_renglon(vinculos: list[dict], cantidad_renglon: float) -> tuple[float | None, str, float]:
    """`vinculos`: uno por cada fila de `tblRemitoCompra` del renglón (factura, nota
    de crédito o de débito), con `cantidadRemitida`, `cantidadCompra`,
    `precioUnitario`, `moneda`, `tipoDeCambio` y `sumaRemitidaLineaCompra` (lo
    remitido en total, desde todos los remitos, a esa línea de compra).

    Devuelve `(costo por unidad del remito o None, estado, cantidad vinculada)`, con
    estado «pendiente» (sin factura), «parcial» (vinculado menos que lo remitido) o
    «completo».
    """
    # Una cuenta por moneda: los ND/NC en pesos sólo afectan el promedio en pesos,
    # los emitidos en dólares sólo afectan el promedio en dólares.
    cuentas: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "cantidad": 0.0, "tc_total": 0.0, "tc_cantidad": 0.0})
    for v in vinculos:
        cant = float(v["cantidadRemitida"] or 0)
        if cant <= EPS:
            continue
        compra = float(v.get("cantidadCompra") or 0)
        suma = float(v.get("sumaRemitidaLineaCompra") or 0)
        precio = float(v.get("precioUnitario") or 0)
        if compra > EPS and abs(compra - suma) <= TOLERANCIA_CANTIDAD * compra:
            unitario = precio
        elif suma > EPS:
            unitario = precio * compra / suma
        else:
            unitario = precio
        moneda = v.get("moneda") or "Pesos"
        cuenta = cuentas[moneda]
        cuenta["total"] += unitario * cant
        cuenta["cantidad"] += cant
        if moneda == "Dolares":
            tc = float(v.get("tipoDeCambio") or 0)
            cuenta["tc_total"] += tc * cant
            cuenta["tc_cantidad"] += cant

    total_pesos = 0.0
    cantidad_vinculada = 0.0
    for moneda, cuenta in cuentas.items():
        if cuenta["cantidad"] <= EPS:
            continue
        promedio = cuenta["total"] / cuenta["cantidad"]
        if moneda == "Dolares":
            tc_promedio = cuenta["tc_total"] / cuenta["tc_cantidad"] if cuenta["tc_cantidad"] > EPS else 0.0
            promedio = promedio * tc_promedio
        total_pesos += promedio * cuenta["cantidad"]
        cantidad_vinculada += cuenta["cantidad"]

    if cantidad_vinculada <= EPS:
        return None, "pendiente", 0.0
    estado = "completo" if cantidad_vinculada >= float(cantidad_renglon) - 0.005 else "parcial"
    return total_pesos / cantidad_vinculada, estado, cantidad_vinculada
