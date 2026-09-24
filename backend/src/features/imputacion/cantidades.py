"""Reconstrucción conservadora de cantidades para corridas sin snapshot físico."""

from collections import defaultdict
from decimal import Decimal


def cantidades_coincidentes(guardadas: list[dict], calculadas: list[dict]) -> dict[int, dict]:
    """Relaciona una corrida completa solo si destinos e importes coinciden.

    No convierte importes en cantidades ni modifica la corrida. Una corrección,
    diferencia de conteo o duplicados con cantidades distintas invalida toda la
    coincidencia. El resultado indica cantidades reconstruidas del cálculo
    actual; no prueba cuál fue el consumo histórico al aprobar la corrida.
    """
    if not guardadas or len(guardadas) != len(calculadas):
        return {}
    if len({f.get("idCorrida") for f in guardadas}) != 1:
        return {}
    if len({f.get("idDetalleCompra") for f in guardadas}) != 1:
        return {}
    if any(f.get("origen") != "Insumo" or f.get("estado") == "RequiereIntervencion" for f in guardadas):
        return {}
    if any(f.get("cantidad") is None for f in calculadas):
        return {}

    def clave(f: dict) -> tuple:
        destino = tuple(f.get(k) for k in (
            "idOrdenTrabajo", "idLote", "idCultivo", "idCampania", "idCentroCosto", "esGanaderia",
        ))
        return (*destino, Decimal(str(f["importe"])))

    anteriores: dict[tuple, list[dict]] = defaultdict(list)
    actuales: dict[tuple, list[dict]] = defaultdict(list)
    for f in guardadas:
        anteriores[clave(f)].append(f)
    for f in calculadas:
        actuales[clave(f)].append(f)
    if anteriores.keys() != actuales.keys():
        return {}

    resultado = {}
    for destino, filas in anteriores.items():
        nuevas = actuales[destino]
        if len(filas) != len(nuevas):
            return {}
        cantidades = {(Decimal(str(f["cantidad"])), f.get("unidad")) for f in nuevas}
        if len(cantidades) != 1:
            return {}
        cantidad, unidad = cantidades.pop()
        for fila in filas:
            resultado[fila["idPropuesta"]] = {"cantidad": float(cantidad), "unidad": unidad}
    return resultado
