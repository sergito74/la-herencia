"""Conciliación de una línea de consumo (pesos) contra uno o más documentos.

El resumen de la tarjeta viene en pesos y los documentos de Compras pueden estar
en dólares. Un documento en dólares se pesifica con su propio tipo de cambio, y
la diferencia de cambio con la cotización de la tarjeta se documenta con una
Nota de Crédito/Débito de ajuste (`Ajusta Tipo Cambio`) asociada a la factura:
la conciliación cierra **exacta en pesos** con la factura pesificada más esas
notas (las NC ya vienen con importe negativo, así que se suma con signo). Una
línea puede requerir varios documentos, incluso de proveedores distintos.

Módulo puro (sin base de datos):

- `calcular_imputacion`: reparte la línea entre los documentos y dice si cierra.
- `sugerir`: busca qué combinaciones de documentos cierran exacto con la línea.
"""

from __future__ import annotations

from itertools import combinations

TOLERANCIA_PESOS = 0.10
# Con documentos en dólares hay una conversión de por medio (la tarjeta y el
# documento redondean por separado): en los vínculos reales ya cargados que saldan
# una cuenta en dólares, las diferencias de redondeo llegan a $0,68.
TOLERANCIA_PESOS_USD = 1.00
MAX_DOCS_SUGERENCIA = 18
MAX_TAMANO_COMBINACION = 4


def _es_dolar(doc: dict) -> bool:
    return doc.get("moneda") == "Dolares"


def _tc(doc: dict) -> float:
    return float(doc.get("tipoDeCambio") or 0)


def importe_pesos(doc: dict) -> float:
    """Importe del documento en pesos. Un documento en dólares se pesifica con su
    propio tipo de cambio, redondeando antes el importe a centavos de dólar: el
    total guardado en Compras se arma multiplicando cantidades, precios e IVA y
    trae más decimales que la factura impresa."""
    importe = float(doc.get("importeOriginal") or 0)
    if _es_dolar(doc) and _tc(doc) > 0:
        return round(round(importe, 2) * _tc(doc), 2)
    return round(importe, 2)


def tolerancia(docs: list[dict]) -> float:
    return TOLERANCIA_PESOS_USD if any(_es_dolar(d) for d in docs) else TOLERANCIA_PESOS


def _usd(doc: dict) -> float:
    return round(float(doc.get("importeOriginal") or 0), 2)


def _tc_implicito(importe_linea: float, docs: list[dict]) -> float | None:
    """Tipo de cambio que haría cerrar la línea si los documentos en dólares se
    cobraran a otra cotización — solo una pista de cuánto ajuste faltaría."""
    usd = [d for d in docs if _es_dolar(d)]
    suma_usd = sum(_usd(d) for d in usd)
    if not usd or abs(suma_usd) < 1e-9:
        return None
    suma_ars = sum(importe_pesos(d) for d in docs if not _es_dolar(d))
    candidato = (importe_linea - suma_ars) / suma_usd
    return candidato if candidato > 0 else None


def calcular_imputacion(importe_linea: float, docs: list[dict]) -> dict:
    """Reparte `importe_linea` entre `docs`.

    `imputados`: importe en pesos de cada documento. `diferencia`: línea − suma.
    `estado`: "exacta" (dentro de $0,10, o $1,00 si hay dólares) o "parcial". Un único documento en pesos
    que no coincide es un pago parcial (`pagoParcial`, ej. una cuota) y se imputa
    el importe de la línea. Si hay documentos en dólares y no cierra, `tcImplicito`
    y `desvioTc` orientan sobre cuánto ajuste de cambio faltaría.
    """
    importe_linea = round(float(importe_linea), 2)
    imputados = {d["idCompra"]: importe_pesos(d) for d in docs}
    diferencia = round(importe_linea - sum(imputados.values()), 2)
    estado = "exacta" if abs(diferencia) <= tolerancia(docs) else "parcial"

    resultado: dict = {"tcImplicito": None, "tcReferencia": None, "desvioTc": None}
    usd = [d for d in docs if _es_dolar(d)]
    if usd and estado == "parcial":
        implicito = _tc_implicito(importe_linea, docs)
        base = sum(abs(_usd(d)) for d in usd if _tc(d) > 0)
        if implicito is not None and base > 0:
            referencia = sum(abs(_usd(d)) * _tc(d) for d in usd if _tc(d) > 0) / base
            resultado["tcImplicito"] = round(implicito, 4)
            resultado["tcReferencia"] = round(referencia, 4)
            resultado["desvioTc"] = round(implicito / referencia - 1, 4)

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
    """Combinaciones de `docs` (los más cercanos en fecha primero) cuya suma en
    pesos cierra exacto con la línea: primero las de menos documentos, luego la
    menor diferencia."""
    importe_linea = round(float(importe_linea), 2)
    candidatos = [d for d in docs if float(d.get("importeOriginal") or 0) != 0][:MAX_DOCS_SUGERENCIA]
    pesos = [importe_pesos(d) for d in candidatos]
    encontradas: list[tuple[int, float, tuple[int, ...]]] = []
    for tamano in range(1, min(MAX_TAMANO_COMBINACION, len(candidatos)) + 1):
        for idx in combinations(range(len(candidatos)), tamano):
            diferencia = abs(importe_linea - sum(pesos[i] for i in idx))
            if diferencia <= tolerancia([candidatos[i] for i in idx]):
                encontradas.append((tamano, diferencia, idx))
    encontradas.sort()
    return [
        {
            "idsCompra": [candidatos[i]["idCompra"] for i in idx],
            **calcular_imputacion(importe_linea, [candidatos[i] for i in idx]),
        }
        for _, _, idx in encontradas[:top]
    ]


_MAX_ASIGNACIONES = 200_000


def repartir(lineas: list[dict], docs: list[dict]) -> dict:
    """Propone cómo repartir varias líneas (`idLinea`, `importe`) entre varios
    documentos: primero busca una asignación exacta con cada documento entero en
    una sola línea; si no existe, llena las líneas en orden partiendo documentos
    (las notas de crédito van enteras a la primera línea). Es solo una propuesta:
    el usuario puede editar los importes antes de guardar."""
    from itertools import product

    pesos = [importe_pesos(d) for d in docs]
    importes = [round(float(l["importe"]), 2) for l in lineas]
    n_l, n_d = len(lineas), len(docs)

    def diferencias(asignado: list[float]) -> list[float]:
        return [round(importes[i] - asignado[i], 2) for i in range(n_l)]

    reparto: list[dict] | None = None
    if n_l and n_d and n_l**n_d <= _MAX_ASIGNACIONES:
        for asignacion in product(range(n_l), repeat=n_d):
            sumas = [0.0] * n_l
            for d, li in enumerate(asignacion):
                sumas[li] += pesos[d]
            if all(abs(importes[i] - sumas[i]) <= tolerancia([docs[d] for d in range(n_d) if asignacion[d] == i]) for i in range(n_l)):
                reparto = [
                    {"idLinea": lineas[li]["idLinea"], "idCompra": docs[d]["idCompra"], "importe": pesos[d]}
                    for d, li in enumerate(asignacion)
                ]
                break

    if reparto is None:
        reparto = []
        falta = importes[:]
        for d in range(n_d):
            if pesos[d] < 0:
                reparto.append({"idLinea": lineas[0]["idLinea"], "idCompra": docs[d]["idCompra"], "importe": pesos[d]})
                falta[0] = round(falta[0] - pesos[d], 2)
        for d in range(n_d):
            resto = pesos[d]
            if resto <= 0:
                continue
            for i in range(n_l):
                if resto <= 0.005:
                    break
                usar = resto if i == n_l - 1 else min(resto, max(falta[i], 0.0))
                if usar > 0.005:
                    reparto.append({"idLinea": lineas[i]["idLinea"], "idCompra": docs[d]["idCompra"], "importe": round(usar, 2)})
                    falta[i] = round(falta[i] - usar, 2)
                    resto = round(resto - usar, 2)

    asignado = [
        round(sum(r["importe"] for r in reparto if r["idLinea"] == l["idLinea"]), 2) for l in lineas
    ]
    return {"reparto": reparto, "diferencias": dict(zip((l["idLinea"] for l in lineas), diferencias(asignado)))}
