"""Clasificación de las cuentas contra la referencia del Access — 035 (research D4, FR-001/FR-002).

Funciones puras sobre lo que carga `datos.cargar()`. La diferencia de una cuenta
(`saldo WC al corte − saldo Access`) se descompone exactamente en componentes:

  fuentes-no-contadas  filas de WC cuyo origen el Access no tenía en la cuenta corriente (tarjetas, ventas, ...)
  reasignacion         filas movidas de contacto con `ReasignacionesContacto`
  datos-posteriores    filas que solo existen en WC y son posteriores a lo último que el Access tenía de ese origen
  correccion-importe   la misma fila con otro importe (correcciones deliberadas, ej. signo de retenciones)
  otros                el resto: lo que nadie explicó todavía
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

TOLERANCIA_USD_RELATIVA = 0.005  # 0,5 % (tolerancia del FIFO); en dólares nunca se usa el umbral de pesos
EXCEPCIONES = {
    "otros", "aplicacion-fuera-de-plazo", "doble-descuento-tarjeta", "nota-sin-imputar", "impuesto-sin-boleta",
    "movimiento-sin-contacto", "sobrepago", "contacto-duplicado", "falta-documento",
}
CAUSAS = (
    "coincide", "coincide-causa-conocida", "diferencia-menor-umbral", "fuera-de-plazo-decidido",
    "aplicacion-fuera-de-plazo", "doble-descuento-tarjeta", "nota-sin-imputar", "impuesto-sin-boleta",
    "movimiento-sin-contacto", "sobrepago", "contacto-duplicado", "falta-documento", "sin-referencia", "otros",
)
COMPONENTES = ("fuentes-no-contadas", "reasignacion", "datos-posteriores", "correccion-importe", "otros")


def _dia(valor) -> date | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.fromisoformat(str(valor)[:19]).date()


def _neto(fila: dict) -> float:
    return float(fila["Credito"] or 0) - float(fila["Deuda"] or 0)


def descomponer(filas_wc: list[dict], filas_ref: list[dict], origenes_ref: set[str], reasignados: set[tuple],
                max_fecha_ref: dict[str, date], claves_ref_globales: set[tuple]) -> dict[str, float]:
    """Descompone la diferencia (WC − Access) de UNA cuenta en componentes que suman la diferencia exacta."""
    wc: dict[tuple, float] = defaultdict(float)
    ref: dict[tuple, float] = defaultdict(float)
    fecha_wc: dict[tuple, date | None] = {}
    for f in filas_wc:
        k = (f["Origen"], int(f["IdOrigen"]))
        wc[k] += _neto(f)
        fecha_wc[k] = _dia(f.get("Fecha"))
    for f in filas_ref:
        ref[(f["Origen"], int(f["IdOrigen"]))] += _neto(f)

    comp = {c: 0.0 for c in COMPONENTES}
    for k in set(wc) | set(ref):
        delta = wc.get(k, 0.0) - ref.get(k, 0.0)
        if abs(delta) < 0.005:
            continue
        origen = k[0]
        if origen not in origenes_ref:
            comp["fuentes-no-contadas"] += delta
        elif k in reasignados:
            comp["reasignacion"] += delta
        elif k in wc and k not in ref:
            if k not in claves_ref_globales and (fecha_wc.get(k) is None or fecha_wc[k] > max_fecha_ref.get(origen, date.min)):
                comp["datos-posteriores"] += delta
            else:
                comp["otros"] += delta  # la fila existía en el Access con otro contacto y nadie lo registró
        elif k in wc and k in ref:
            comp["correccion-importe"] += delta
        else:
            comp["otros"] += delta  # estaba en el Access y ya no está en la cuenta
    return {c: round(v, 2) for c, v in comp.items()}


def _coincide(diferencia: float, referencia: float, moneda: str, umbral: float) -> bool:
    if moneda == "Dolares":
        return abs(diferencia) <= max(0.01, abs(referencia) * TOLERANCIA_USD_RELATIVA)
    return abs(diferencia) < umbral


def clasificar_cuenta(id_contacto: int, razon_social: str | None, moneda: str, saldo_wc: float, saldo_ref: float | None,
                      componentes: dict[str, float] | None, umbral: float, documentada: dict | None = None) -> dict:
    cuenta = {"idContacto": id_contacto, "razonSocial": razon_social, "moneda": moneda,
              "saldoSistema": round(saldo_wc, 2), "saldoAccess": None if saldo_ref is None else round(saldo_ref, 2),
              "diferencia": None, "sinExplicar": 0.0, "componentes": componentes or {}, "causa": "sin-referencia"}
    if saldo_ref is None:
        return cuenta
    diferencia = round(saldo_wc - saldo_ref, 2)
    cuenta["diferencia"] = diferencia
    if abs(diferencia) < 0.005:
        cuenta["causa"] = "coincide"
        return cuenta
    if _coincide(diferencia, saldo_ref, moneda, umbral):
        cuenta["causa"] = "diferencia-menor-umbral"
        return cuenta
    sin_explicar = (componentes or {}).get("otros", 0.0)
    cuenta["sinExplicar"] = round(sin_explicar, 2)
    cuenta["causa"] = "coincide-causa-conocida" if _coincide(sin_explicar, saldo_ref, moneda, umbral) else "otros"
    if cuenta["causa"] == "otros" and documentada is not None and _coincide(diferencia - documentada["importeRef"], saldo_ref, moneda, umbral):
        # Sergio documentó esta diferencia: mientras siga siendo la misma no es una excepción
        cuenta["causa"] = "coincide-causa-conocida"
        cuenta["documentada"] = documentada["motivo"]
    return cuenta


def clasificar_cuentas(datos: dict, parametros: dict) -> list[dict]:
    """`datos` (ver `datos.cargar`): saldos, filas WC y de referencia por contacto, razones sociales, monedas, etc."""
    umbral = float(parametros["umbralPesos"])
    excluidos = datos.get("excluidos", set())
    cuentas = []
    contactos = (set(datos["saldoRef"]) | {c for c, v in datos["saldoWc"].items() if abs(v) >= umbral}) - excluidos
    for c in sorted(contactos):
        ref = datos["saldoRef"].get(c)
        comp = None
        if ref is not None:
            comp = descomponer(datos["filasWc"].get(c, []), datos["filasRef"].get(c, []), datos["origenesRef"],
                               datos["reasignados"], datos["maxFechaRef"], datos["clavesRef"])
        cuentas.append(clasificar_cuenta(c, datos["razon"].get(c), datos["moneda"].get(c, "Pesos"),
                                         float(datos["saldoWc"].get(c, 0.0)), ref, comp, umbral,
                                         datos.get("documentadas", {}).get(c)))
    return cuentas


def agregar_hallazgos(cuentas: list[dict], hallazgos: list[dict]) -> None:
    """Suma a cada cuenta sus hallazgos de imputaciones (plazo, doble descuento, ...) como causas adicionales."""
    por_contacto: dict[int, list[dict]] = defaultdict(list)
    for h in hallazgos:
        por_contacto[h["idContacto"]].append(h)
    for c in cuentas:
        lista = por_contacto.get(c["idContacto"], [])
        c["hallazgos"] = len(lista)
        c["causasExtra"] = sorted({h["causa"] for h in lista})
        c["_importesExtra"] = defaultdict(float)
        for h in lista:
            c["_importesExtra"][h["causa"]] += float(h.get("importe") or 0)


def resumen(cuentas: list[dict]) -> dict:
    grupos: dict[str, dict] = {}
    for c in cuentas:
        g = grupos.setdefault(c["causa"], {"causa": c["causa"], "cuentas": 0, "importe": 0.0, "excepcion": c["causa"] in EXCEPCIONES})
        g["cuentas"] += 1
        g["importe"] += abs(c["diferencia"] or 0.0)
    for g in grupos.values():
        g["importe"] = round(g["importe"], 2)
    coinciden = sum(1 for c in cuentas if c["causa"] in ("coincide", "coincide-causa-conocida", "diferencia-menor-umbral"))
    orden = {c: i for i, c in enumerate(CAUSAS)}
    extras: dict[str, dict] = {}
    for c in cuentas:
        for causa in c.get("causasExtra", []):
            g = extras.setdefault(causa, {"causa": causa, "cuentas": 0, "importe": 0.0, "excepcion": causa in EXCEPCIONES, "adicional": True})
            g["cuentas"] += 1
            g["importe"] += abs(c.get("_importesExtra", {}).get(causa, 0.0))
    for g in extras.values():
        g["importe"] = round(g["importe"], 2)
    for g in grupos.values():
        g["adicional"] = False
    todas = sorted(grupos.values(), key=lambda g: orden.get(g["causa"], 99)) + sorted(extras.values(), key=lambda g: orden.get(g["causa"], 99))
    return {"totalCuentas": len(cuentas), "coinciden": coinciden, "conDiferencia": len(cuentas) - coinciden, "causas": todas}
