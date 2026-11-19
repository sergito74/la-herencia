"""Inversiones (plazos fijos y FCI Fima) — solo lectura (19/11/2026, modelo C aprobado por Sergio).

Análisis: specs/036-revision-sistematica-cuentas/analisis-inversiones-fci-plazo-fijo-20261119.md (con adendas).
Diseño: specs/051-experiencia-uso-moderna/diseno-inversiones-20261119.md.

- Plazo fijo BNA: constitución y acreditación con el mismo número de comprobante. Los certificados en papel de 2016 se
  cobraban por caja y entraban como "DEP.EFECTIVO" (adenda 3): esos pares están fijos abajo, con su respaldo.
- Plazo fijo Galicia: sin comprobante; se aparea cada constitución con la primera acreditación posterior que la supere
  (la renovación automática capitaliza: el de $ 4.500.000 volvió como $ 9.257.546,87, certificado 809259034553).
- FCI Fima: rendimiento por mes = saldo del extracto − saldo anterior − suscripciones + rescates.
- Ejercicio económico: del 01/04 al 31/03. Rubro "Resultados financieros", Adm. General.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from src.db.connection import fetch_all

# Certificados en papel del BNA de 2016, cobrados por caja como "DEP.EFECTIVO" (adenda 3 del análisis).
PARES_BNA_MANUALES = {12021: 12178, 17483: 12263}
_FIMA = Path(__file__).resolve().parents[1] / "flujo_caja" / "fima_posiciones.json"


def _d(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def ejercicio(f: date) -> str:
    """Ejercicio económico 01/04–31/03, rotulado por sus años (ej. "2025/26")."""
    inicio = f.year if f.month >= 4 else f.year - 1
    return f"{inicio}/{str(inicio + 1)[-2:]}"


def plazos_fijos() -> list[dict]:
    bna = fetch_all(
        "SELECT IdMovimientoBNA AS id, [Fecha / Hora Mov#] AS fecha, [Nro# Comprobante] AS comp, Concepto AS concepto, "
        "Importe AS importe FROM dbo.[Movimientos BNA] WHERE Concepto LIKE '%FIJO%' OR IdMovimientoBNA IN (?, ?) "
        "ORDER BY [Fecha / Hora Mov#], IdMovimientoBNA", tuple(PARES_BNA_MANUALES.values()))
    por_id = {m["id"]: m for m in bna}
    salida, usados = [], set()
    for m in bna:
        if m["importe"] >= 0 or m["id"] in usados:
            continue
        vuelta = None
        if m["id"] in PARES_BNA_MANUALES:
            vuelta = por_id.get(PARES_BNA_MANUALES[m["id"]])
        else:
            vuelta = next((x for x in bna if x["importe"] > 0 and x["comp"] == m["comp"] and x["id"] not in usados
                           and _d(x["fecha"]) >= _d(m["fecha"])), None)
        usados.add(m["id"])
        if vuelta:
            usados.add(vuelta["id"])
        salida.append(_par("Plazo fijo Nación", m, vuelta, "bna"))
    gal = fetch_all(
        "SELECT IdMovimiento AS id, Fecha AS fecha, [Descripción] AS concepto, ISNULL([Créditos],0) - ISNULL([Débitos],0) AS importe "
        "FROM dbo.[Movimientos Galicia] WHERE [Descripción] LIKE '%Plazo Fijo%' ORDER BY Fecha, IdMovimiento")
    usados = set()
    for m in gal:
        if m["importe"] >= 0:
            continue
        vuelta = next((x for x in gal if x["importe"] > abs(m["importe"]) and x["id"] not in usados
                       and _d(x["fecha"]) > _d(m["fecha"])), None)
        if vuelta:
            usados.add(vuelta["id"])
        salida.append(_par("Plazo fijo Galicia", m, vuelta, "galicia"))
    return sorted(salida, key=lambda p: p["constitucion"], reverse=True)


def _par(cuenta: str, ida: dict, vuelta: dict | None, medio: str = "") -> dict:
    capital = round(abs(float(ida["importe"])), 2)
    p = {"cuenta": cuenta, "medio": medio, "idIda": ida["id"], "idVuelta": vuelta["id"] if vuelta else None, "constitucion": _d(ida["fecha"]).isoformat(), "capital": capital,
         "vencimiento": None, "cobrado": None, "rendimiento": None, "dias": None, "tna": None, "estado": "vigente"}
    if vuelta:
        cobrado = round(float(vuelta["importe"]), 2)
        dias = max(1, (_d(vuelta["fecha"]) - _d(ida["fecha"])).days)
        p.update(vencimiento=_d(vuelta["fecha"]).isoformat(), cobrado=cobrado, rendimiento=round(cobrado - capital, 2),
                 dias=dias, tna=round((cobrado / capital - 1) * 365 / dias * 100, 2), estado="cobrado")
    elif (date.today() - _d(ida["fecha"])).days > 400:
        p["estado"] = "revisar"  # inversión abierta hace más de 400 días: falta su vuelta
    return p


def fima() -> list[dict]:
    """Un renglón por extracto mensual del Fima, con su rendimiento."""
    if not _FIMA.exists():
        return []
    pos = sorted(json.load(open(_FIMA, encoding="utf-8")).values(), key=lambda x: x["fecha"])
    movs = fetch_all("SELECT Fecha AS fecha, ISNULL([Débitos],0) AS susc, ISNULL([Créditos],0) AS resc "
                     "FROM dbo.[Movimientos Galicia] WHERE [Descripción] LIKE '%Fima%'")
    salida, anterior, desde = [], 0.0, date(2000, 1, 1)
    for x in pos:
        hasta = date.fromisoformat(x["fecha"])
        susc = sum(float(m["susc"]) for m in movs if desde < _d(m["fecha"]) <= hasta)
        resc = sum(float(m["resc"]) for m in movs if desde < _d(m["fecha"]) <= hasta)
        saldo = float(x["saldo"])
        salida.append({"periodo": x["periodo"], "fecha": x["fecha"], "saldoAnterior": round(anterior, 2),
                       "suscripciones": round(susc, 2), "rescates": round(resc, 2), "saldo": round(saldo, 2),
                       "rendimiento": round(saldo - anterior - susc + resc, 2)})
        anterior, desde = saldo, hasta
    return salida


def resumen() -> dict:
    pfs, meses = plazos_fijos(), fima()
    por_ejercicio: dict[str, dict] = defaultdict(lambda: {"plazoFijoNacion": 0.0, "plazoFijoGalicia": 0.0, "fima": 0.0})
    for p in pfs:
        if p["rendimiento"] is not None:
            clave = "plazoFijoNacion" if "Nación" in p["cuenta"] else "plazoFijoGalicia"
            por_ejercicio[ejercicio(date.fromisoformat(p["vencimiento"]))][clave] += p["rendimiento"]
    for m in meses:
        por_ejercicio[ejercicio(date.fromisoformat(m["fecha"]))]["fima"] += m["rendimiento"]
    ejercicios = [{"ejercicio": k, **{a: round(b, 2) for a, b in v.items()}, "total": round(sum(v.values()), 2)}
                  for k, v in sorted(por_ejercicio.items())]
    vigentes = [p for p in pfs if p["estado"] == "vigente"]
    saldo_fima = meses[-1]["saldo"] if meses else 0.0
    actual = ejercicio(date.today())
    return {
        "invertido": round(saldo_fima + sum(p["capital"] for p in vigentes), 2),
        "fimaSaldo": saldo_fima, "fimaFecha": meses[-1]["fecha"] if meses else None,
        "rendimientoEjercicio": next((e["total"] for e in ejercicios if e["ejercicio"] == actual), 0.0),
        "ejercicioActual": actual,
        "proximoVencimiento": None,  # los plazos fijos vigentes no traen fecha de vencimiento en el banco
        "plazosFijosVigentes": vigentes,
        "revisar": [p for p in pfs if p["estado"] == "revisar"],
        "plazosFijos": pfs, "fima": meses, "ejercicios": ejercicios,
    }
