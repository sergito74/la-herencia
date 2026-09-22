"""Stock de insumos por capas FIFO (primero entra, primero sale) — lógica pura.

Cada entrada (renglón de remito o sobrante de un ajuste) es una **capa** con su
cantidad y su costo unitario en pesos, en la unidad base del producto. Toda
salida (consumo de una orden de trabajo, baja o faltante de un ajuste) consume
primero las capas más antiguas.

Es un FIFO sobre cantidades acumuladas, igual que el stock heredado
(`vw_ExistenciaProductos` suma todas las entradas y resta todas las salidas sin
mirar fechas): la unidad n-ésima que sale toma el costo de la unidad n-ésima
que entró. Las capas se ordenan por fecha y luego por orden de carga.

Si una capa todavía no tiene factura vinculada su costo es `None` («costo
pendiente»): las salidas que la consumen quedan marcadas como provisorias y se
recalculan solas cuando se vincula la factura, porque este cálculo se rehace
siempre desde los datos. Si las salidas superan lo que entró, el excedente es
`sin_cobertura` (stock negativo) y no se valoriza.
"""

from __future__ import annotations

from dataclasses import dataclass, field

EPS = 1e-9


@dataclass
class Capa:
    id: str
    fecha: object
    cantidad: float
    costo_unitario: float | None
    orden: int = 0
    restante: float = field(init=False)

    def __post_init__(self) -> None:
        self.restante = float(self.cantidad)


@dataclass
class Salida:
    id: str
    fecha: object
    cantidad: float
    tipo: str = "salida"
    orden: int = 0


def asignar_fifo(capas: list[Capa], salidas: list[Salida]) -> dict:
    """Asigna cada salida a las capas más antiguas disponibles.

    Devuelve:
    - `consumos[salida_id]`: `items` (capa, cantidad, costo unitario), `costo` (de lo
      valorizado), `cantidad_costo_pendiente`, `sin_cobertura` y `provisoria`.
    - `restantes[capa_id]`: lo que queda de cada capa.
    - `existencia` (puede ser negativa), `valor` (de lo que queda con costo conocido)
      y `cantidad_costo_pendiente` (de lo que queda sin costo).
    """
    capas_ord = sorted(capas, key=lambda c: (c.fecha, c.orden))
    for c in capas_ord:
        c.restante = float(c.cantidad)
    consumos: dict[str, dict] = {}
    puntero = 0
    for s in sorted(salidas, key=lambda x: (x.fecha, x.orden)):
        falta = float(s.cantidad)
        items: list[dict] = []
        costo = 0.0
        pendiente = 0.0
        while falta > EPS and puntero < len(capas_ord):
            capa = capas_ord[puntero]
            if capa.restante <= EPS:
                puntero += 1
                continue
            toma = min(capa.restante, falta)
            capa.restante -= toma
            falta -= toma
            items.append({"capa": capa.id, "cantidad": toma, "costo_unitario": capa.costo_unitario})
            if capa.costo_unitario is None:
                pendiente += toma
            else:
                costo += toma * capa.costo_unitario
        sin_cobertura = falta if falta > EPS else 0.0
        consumos[s.id] = {
            "tipo": s.tipo,
            "items": items,
            "costo": round(costo, 2),
            "cantidad_costo_pendiente": pendiente,
            "sin_cobertura": sin_cobertura,
            "provisoria": pendiente > EPS,
        }
    restantes = {c.id: c.restante for c in capas_ord}
    sobrante = sum(c.restante for c in capas_ord)
    deuda = sum(v["sin_cobertura"] for v in consumos.values())
    valor = sum(c.restante * c.costo_unitario for c in capas_ord if c.costo_unitario is not None)
    pendiente_stock = sum(c.restante for c in capas_ord if c.costo_unitario is None and c.restante > EPS)
    return {
        "consumos": consumos,
        "restantes": restantes,
        "existencia": round(sobrante - deuda, 6),
        "valor": round(valor, 2),
        "cantidad_costo_pendiente": pendiente_stock,
    }
