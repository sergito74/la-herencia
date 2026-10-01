"""Validación al guardar un vínculo (031, FR-012): cuenta todas las vías.
Un exceso de más del 2% sobre el total del documento se rechaza; dentro
del 2% se permite con advertencia."""

from __future__ import annotations

from src.features.vinculos import fuente
from src.formatting import formatear_moneda
from src.features.vinculos.cadenas import TOLERANCIA


class ExcesoVinculo(ValueError):
    """El vínculo dejaría el documento más de un 2% por encima de su total (422)."""


def evaluar(total: float, pagado: float, nuevo: float, etiqueta: str) -> str | None:
    """Pura: devuelve advertencia, None, o lanza `ExcesoVinculo`."""
    exceso = round(pagado + nuevo - abs(total), 2)
    if exceso <= 1.0:
        return None
    if exceso > max(1.0, abs(total) * TOLERANCIA):
        raise ExcesoVinculo(
            f"El vínculo deja {etiqueta} imputado por {formatear_moneda(pagado + nuevo)} sobre su total ({formatear_moneda(abs(total))})."
        )
    return f"{etiqueta} queda {formatear_moneda(exceso)} por encima de su total (dentro del 2% de tolerancia)."


def verificar_documentos(nuevos: list[dict], total_de) -> list[str]:
    """`nuevos`: [{tipoDocumento, idDocumento, importe}] en pesos.
    `total_de(tipo, id)`: total del documento en pesos."""
    claves = [(n["tipoDocumento"], n["idDocumento"]) for n in nuevos]
    pagado = fuente.pagado_de_documentos(claves)
    acumulado: dict[tuple, float] = {}
    advertencias = []
    for n, clave in zip(nuevos, claves):
        acumulado[clave] = acumulado.get(clave, 0.0) + float(n["importe"])
        adv = evaluar(total_de(*clave), pagado[clave], acumulado[clave], f"El documento {clave[0]} #{clave[1]}")
        if adv:
            advertencias.append(adv)
    return advertencias
