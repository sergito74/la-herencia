"""Conciliación de una línea de consumo (pesos) contra uno o más documentos.

Los documentos de Compras pueden estar en dólares y el resumen de la tarjeta
siempre viene en pesos, así que los importes nunca coinciden directamente. Al
saldar la cuenta, además, una línea puede cubrir varios documentos a la vez
(Factura + Nota de Crédito + Nota de Débito; las NC ya vienen con importe
negativo). Este módulo es puro (sin base de datos):

- `calcular_imputacion`: dada una línea y un conjunto de documentos, reparte el
  importe de la línea entre ellos. Con documentos en dólares despeja el tipo de
  cambio implícito (el que hace que la suma de todo cierre con la línea) y lo
  compara con el tipo de cambio propio de los documentos.
- `sugerir`: busca qué combinaciones de documentos concilian la línea.
"""

from __future__ import annotations

from itertools import combinations

# Misma tolerancia que la conciliación de pagos (research.md §5).
TOLERANCIA_PESOS = 0.10
# Desvío máximo entre el tipo de cambio implícito y el de los documentos para
# darlo por "aproximado": el resumen se liquida con la cotización de la tarjeta,
# que no es la del día en que se cargó el documento. Calibrado con los vínculos
# reales ya cargados que saldan una cuenta en dólares: 12 de 18 tienen desvío
# 0%, 17 de 18 quedan dentro del 2% (el resto son cuotas/pagos parciales, con
# desvíos de 58% a 99%). Subir la tolerancia solo agrega falsos positivos: con un
# tipo de cambio libre, muchas combinaciones "cierran" por casualidad.
TOLERANCIA_TC = 0.02
MAX_DOCS_SUGERENCIA = 18
MAX_TAMANO_COMBINACION = 4


def _es_dolar(doc: dict) -> bool:
    return doc.get("moneda") == "Dolares"


def _tc(doc: dict) -> float:
    return float(doc.get("tipoDeCambio") or 0)


def importe_pesos(doc: dict) -> float:
    """Importe del documento pesificado con su propio tipo de cambio (el que
    tenía al cargarlo)."""
    importe = float(doc.get("importeOriginal") or 0)
    if _es_dolar(doc) and _tc(doc) > 0:
        return round(importe * _tc(doc), 2)
    return round(importe, 2)


def calcular_imputacion(importe_linea: float, docs: list[dict]) -> dict:
    """Reparte `importe_linea` entre `docs`.

    Devuelve `imputados` ({idCompra: importe en pesos}), `diferencia` (línea −
    total imputado), y para documentos en dólares `tcImplicito`, `tcReferencia`
    (promedio de los TC de los documentos, ponderado por importe) y `desvioTc`.
    `estado`: "exacta" (sin dólares y dentro de $0,10), "aproximada" (con
    dólares y desvío de TC dentro de la tolerancia) o "parcial". `diferencia`
    se calcula contra el importe completo de los documentos, aun en un pago
    parcial (`pagoParcial`), para poder mostrarla.
    """
    importe_linea = round(float(importe_linea), 2)
    usd = [d for d in docs if _es_dolar(d)]
    ars = [d for d in docs if not _es_dolar(d)]
    suma_ars = sum(float(d.get("importeOriginal") or 0) for d in ars)
    suma_usd = sum(float(d.get("importeOriginal") or 0) for d in usd)

    resultado: dict = {"tcImplicito": None, "tcReferencia": None, "desvioTc": None}
    imputados: dict[int, float] = {}

    tc_implicito = None
    if usd and abs(suma_usd) > 1e-9:
        candidato = (importe_linea - suma_ars) / suma_usd
        if candidato > 0:
            tc_implicito = candidato

    if tc_implicito is None:
        # Sin dólares, o sin forma de despejar el tipo de cambio: se pesifica
        # cada documento con su propio TC y la diferencia queda expuesta.
        for d in docs:
            imputados[d["idCompra"]] = importe_pesos(d)
    else:
        for d in ars:
            imputados[d["idCompra"]] = round(float(d.get("importeOriginal") or 0), 2)
        for d in usd:
            imputados[d["idCompra"]] = round(float(d.get("importeOriginal") or 0) * tc_implicito, 2)
        # El redondeo por documento no debe romper el cierre exacto con la línea.
        resto = round(importe_linea - sum(imputados.values()), 2)
        if resto:
            mayor = max(usd, key=lambda d: abs(float(d.get("importeOriginal") or 0)))
            imputados[mayor["idCompra"]] = round(imputados[mayor["idCompra"]] + resto, 2)

        pesos_ref = sum(abs(float(d.get("importeOriginal") or 0)) for d in usd if _tc(d) > 0)
        if pesos_ref > 0:
            referencia = (
                sum(abs(float(d.get("importeOriginal") or 0)) * _tc(d) for d in usd if _tc(d) > 0) / pesos_ref
            )
            resultado["tcReferencia"] = round(referencia, 4)
            resultado["desvioTc"] = round(tc_implicito / referencia - 1, 4)
        resultado["tcImplicito"] = round(tc_implicito, 4)

    diferencia = round(importe_linea - sum(imputados.values()), 2)
    if usd and tc_implicito is not None:
        desvio = resultado["desvioTc"]
        estado = "aproximada" if desvio is not None and abs(desvio) <= TOLERANCIA_TC else "parcial"
    else:
        estado = "exacta" if not usd and abs(diferencia) <= TOLERANCIA_PESOS else "parcial"

    # Un único documento en pesos que no coincide con la línea: la línea paga
    # una parte (cuota o pago parcial) y se imputa su importe, como siempre.
    pago_parcial = not usd and len(docs) == 1 and estado == "parcial"
    if pago_parcial:
        imputados = {docs[0]["idCompra"]: importe_linea}

    resultado.update(
        {
            "pagoParcial": pago_parcial,
            "imputados": [{"idCompra": k, "importeImputado": v} for k, v in imputados.items()],
            "diferencia": diferencia,
            "estado": estado,
        }
    )
    return resultado


def sugerir(importe_linea: float, docs: list[dict], top: int = 5) -> list[dict]:
    """Combinaciones de `docs` (los más cercanos en fecha primero) que concilian
    la línea, de mejor a peor: exactas antes que aproximadas, luego menos
    documentos, luego menor diferencia/desvío. Menos documentos va antes que
    menor desvío a propósito: con un tipo de cambio libre casi cualquier
    conjunto "cierra" dentro de la tolerancia, y sumar un documento ajeno podría
    bajar el desvío por casualidad."""
    candidatos = [d for d in docs if float(d.get("importeOriginal") or 0) != 0][:MAX_DOCS_SUGERENCIA]
    encontradas: list[tuple[int, float, int, dict]] = []
    for tamano in range(1, min(MAX_TAMANO_COMBINACION, len(candidatos)) + 1):
        for combo in combinations(candidatos, tamano):
            calculo = calcular_imputacion(importe_linea, list(combo))
            if calculo["estado"] == "parcial":
                continue
            error = abs(calculo["desvioTc"]) if calculo["estado"] == "aproximada" else abs(calculo["diferencia"])
            orden_estado = 0 if calculo["estado"] == "exacta" else 1
            encontradas.append(
                (orden_estado, error, tamano, {"idsCompra": [d["idCompra"] for d in combo], **calculo})
            )
    encontradas.sort(key=lambda t: (t[0], t[2], t[1]))
    return [t[3] for t in encontradas[:top]]
