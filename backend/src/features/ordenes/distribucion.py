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
    return [
        {**d, "cantidadAsignada": round(float(cantidad_total) * peso / peso_total, 4) if peso_total > 0 else 0.0}
        for d, peso in zip(distribuciones, pesos)
    ]


def validar_cierre(cantidad_total: float, distribuciones_repartidas: list[dict], devoluciones: list[float] | None = None) -> None:
    """Lanza ValueError si `cantidad_total` no cierra contra `cantidadAsignada`
    de cada lote (ya repartida por `repartir_total`) + lo devuelto a stock."""
    repartido = sum(float(d["cantidadAsignada"]) for d in distribuciones_repartidas)
    devuelto = sum(devoluciones or [])
    diferencia = round(float(cantidad_total) - repartido - devuelto, 4)
    if abs(diferencia) > EPS:
        raise ValueError(
            [
                f"El total del insumo ({cantidad_total:g}) no cierra contra lo repartido entre lotes "
                f"({repartido:g}) más lo devuelto ({devuelto:g}): diferencia de {diferencia:g}."
            ]
        )
