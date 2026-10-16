"""Reparto de la cantidad total de un insumo entre los lotes de la orden.

FR-003 (corregido 2026-09-22, hallazgo orden heredada #185/153): el usuario
carga la cantidad TOTAL de insumo a usar (dato real del plan del ingeniero
agrónomo, ej. "260 litros de Glifosato") y la dosis/ha de cada lote — la
cantidad que le toca a cada lote NO es dosis × superficie en valor absoluto,
sino ese producto usado como PESO para repartir proporcionalmente el total
entre los lotes. Verificado contra los datos migrados: en la orden heredada
#185, la cantidad histórica de cada lote es exactamente
`TotalAplicado × (dosisHa_lote × superficie_lote) / Σ(dosisHa × superficie)`
(coincide hasta el 4º decimal en los 10 lotes de SILICONADO ARN EBC) — nunca
dosis × superficie directo, que da un número distinto.

FR-004: el total repartido entre lotes más lo devuelto a stock debe coincidir
siempre con la cantidad total cargada; al ser un reparto proporcional del
propio total, esto se cumple por construcción salvo ruido de redondeo.
"""

from __future__ import annotations

EPS = 1e-4


def repartir_total(cantidad_total: float, distribuciones: list[dict]) -> list[dict]:
    """Devuelve `distribuciones` con `cantidadAsignada` agregado a cada fila:
    `cantidad_total` repartido en proporción al peso `dosisHa × superficie` de
    cada lote con `aplicar=True`. Un lote con dosis 0 (no requiere el insumo)
    o `aplicar=False` recibe 0."""
    pesos = [float(d["dosisHa"]) * float(d["superficie"]) if d.get("aplicar", True) else 0.0 for d in distribuciones]
    peso_total = sum(pesos)
    cantidades = [round(float(cantidad_total) * peso / peso_total, 4) if peso_total > 0 else 0.0 for peso in pesos]
    if peso_total > 0:
        # Cada parte se redondea a 4 decimales; el residuo (ej. 16 repartido da 15,9998)
        # va al lote con más cantidad para que el reparto cierre exacto contra el total.
        mayor = max(range(len(cantidades)), key=lambda i: cantidades[i])
        cantidades[mayor] = round(cantidades[mayor] + float(cantidad_total) - sum(cantidades), 4)
    return [{**d, "cantidadAsignada": c} for d, c in zip(distribuciones, cantidades)]


def _num(v: float) -> str:
    """Formato local para mensajes: miles con punto, decimales con coma, sin ceros de más."""
    texto = f"{v:,.4f}".rstrip("0").rstrip(".")
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def validar_cierre(
    cantidad_total: float,
    distribuciones_repartidas: list[dict],
    devoluciones: list[float] | None = None,
    producto: str | None = None,
    unidad: str | None = None,
) -> None:
    """Lanza ValueError si `cantidad_total` no cierra contra `cantidadAsignada`
    de cada lote (ya repartida por `repartir_total`) + lo devuelto a stock."""
    repartido = sum(float(d["cantidadAsignada"]) for d in distribuciones_repartidas)
    devuelto = sum(devoluciones or [])
    diferencia = round(float(cantidad_total) - repartido - devuelto, 4)
    if abs(diferencia) > EPS:
        u = f" {unidad}" if unidad else ""
        nombre = f"«{producto}»" if producto else "Un insumo"
        detalle = f"{_num(repartido)}{u} entre los lotes" + (f" y {_num(devuelto)}{u} devueltos" if devuelto else "")
        raise ValueError(
            [
                f"{nombre}: la cantidad total a aplicar ({_num(cantidad_total)}{u}) no coincide con lo repartido "
                f"({detalle}); faltan {_num(diferencia)}{u}." if diferencia > 0 else
                f"{nombre}: lo repartido ({detalle}) supera la cantidad total a aplicar ({_num(cantidad_total)}{u}) "
                f"en {_num(-diferencia)}{u}. Revisá la cantidad total o las dosis de los lotes."
            ]
        )
