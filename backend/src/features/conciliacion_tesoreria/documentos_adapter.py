"""Adaptación de identidades/saldos al motor puro existente de Tarjetas."""

from src.features.tarjetas_resumenes import conciliacion_documentos as motor


def _preparar(docs: list[dict]) -> list[dict]:
    keys = [(d["origen"], d["idOrigen"]) for d in docs]
    if not 1 <= len(docs) <= 20 or len(set(keys)) != len(keys):
        raise ValueError("Elegí de 1 a 20 documentos, sin repetir.")
    if sum(float(d["saldoPendiente"]) for d in docs) <= 0:
        raise ValueError("La selección debe tener un importe neto positivo.")
    # Saldo ya convertido a pesos. Mantener la marca USD solo para que el
    # motor conserve su tolerancia; TC=1 evita convertir el saldo dos veces.
    return [
        dict(
            d, idCompra=i + 1, idImpuesto=None, importeOriginal=d["saldoPendiente"], tipoDeCambio=1
        )
        for i, d in enumerate(docs)
    ]


def _publico(result: dict, docs: list[dict]) -> dict:
    result = dict(result)
    result["imputados"] = [
        dict(
            origen=docs[i["idCompra"] - 1]["origen"],
            idOrigen=docs[i["idCompra"] - 1]["idOrigen"],
            importeImputado=i["importeImputado"],
        )
        for i in result["imputados"]
    ]
    # No mostrar TC sintético como si fuera una cotización financiera.
    for key in ("tcImplicito", "tcReferencia", "desvioTc"):
        result[key] = None
    if "idsCompra" in result:
        result["documentos"] = [
            {k: docs[i - 1][k] for k in ("origen", "idOrigen")} for i in result.pop("idsCompra")
        ]
    return result


def calcular(importe: float, docs: list[dict]) -> dict:
    prepared = _preparar(docs)
    result = _publico(motor.calcular_imputacion(importe, prepared), docs)
    if all(abs(motor.importe_pesos(d) - d["saldoPendiente"]) < 0.005 for d in docs):
        originals = [dict(d, idCompra=i + 1, idImpuesto=None) for i, d in enumerate(docs)]
        hints = motor.calcular_imputacion(importe, originals)
        for key in ("tcImplicito", "tcReferencia", "desvioTc"):
            result[key] = hints.get(key)
    return result


def sugerencias(importe: float, docs: list[dict]) -> list[dict]:
    if not docs:
        return []
    docs = docs[: motor.MAX_DOCS_SUGERENCIA]
    if sum(d["saldoPendiente"] for d in docs) <= 0:
        return []
    return [_publico(r, docs) for r in motor.sugerir(importe, _preparar(docs))]
