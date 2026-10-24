"""036: historia 2011–2016 de la cuenta de socio del Condominio LSC (socio 3). Sergio, 24/10/2026: «Sí, cargar en
socio 3», valuada como Sergio y Lucy (antes del 16/03/2020: 100% US$ al dólar BNA de la fecha).

Universo, una sola vez cada operación (matriz única `matriz_financiacion_condominio_036.run`):
- A. 61 filas de «Aportes de Capital Directores / Depositos 1» ($733.781, aportes del Condominio según Sergio):
  Haber (a favor del Condominio); la devolución del préstamo 2016 va al Debe.
- B. Pagos directos que el Condominio hizo por Giamigli (Movs «Compra Giamigli» EF, 105 filas), por el importe del pago
  vigente, salvo: el pago 290 (cheque de la avena, ya es la fila 14 de A), los pagados por Lucy sin reintegro
  (88, 315, 503, 561: ya están en socio 2) y las filas sin un pago único (quedan listadas, no se cargan).
No toca la cuenta corriente del contacto 549 (lado bancario), cajas, pagos ni otros socios. Inspección por defecto.
"""

import argparse
import json
from datetime import date, datetime
from decimal import Decimal

from scripts.matriz_financiacion_condominio_036 import run as matriz
from scripts.rastrear_15_pagos_condominio_036 import OUT
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado

RULE = "socio3-historia-condominio-2011-2016-036"
ORIGEN = "CondominioHist036"
LUCY = {88, 315, 503, 561}


def _fecha(x) -> date:
    return date.fromisoformat(str(x)[:10])


def plan() -> dict:
    m = matriz()
    pagos = {p["id"]: p for e in m["operaciones"] for p in e.get("pagosVigentes", [])}
    filas = []
    for e in m["operaciones"]:
        if not e["clave"].startswith("APORTE-F"):
            continue
        imp = Decimal(str(e["importeFuente"]))
        filas.append({"origen": "A", "id": int(e["clave"][8:]), "fecha": _fecha(e["fecha"]), "lado": "haber" if imp > 0 else "debe",
                      "importe": abs(imp), "motivo": f"Condominio LSC — aporte {e['referencia']}"[:255], "medio": "Planilla aportes"})
    excluidas, ambiguas = [], []
    for f in m["filasEF"]:
        if len(f["pagos"]) != 1:
            ambiguas.append(f)
            continue
        pid = f["pagos"][0]
        if pid == 290 or pid in LUCY:
            excluidas.append({"pago": pid, "motivo": "ya en planilla (fila 14)" if pid == 290 else "pagado por Lucy (socio 2)"})
            continue
        p = pagos.get(pid)
        if p is None:
            ambiguas.append({**f, "motivo": "pago no vigente"})
            continue
        filas.append({"origen": "B", "id": pid, "fecha": _fecha(p["fecha"]), "lado": "haber", "importe": Decimal(str(p["importe"])),
                      "motivo": f"Condominio LSC — pago directo de gasto de Giamigli (pago efectivo {pid}, Movs fila {f['fila']})",
                      "medio": "Pago directo"})
    ids = [(x["origen"], x["id"]) for x in filas]
    assert len(ids) == len(set(ids))
    haber = sum(x["importe"] for x in filas if x["lado"] == "haber")
    debe = sum(x["importe"] for x in filas if x["lado"] == "debe")
    return {"filas": filas, "excluidas": excluidas, "ambiguas": ambiguas, "haber": haber, "debe": debe,
            "cantidad": {"A": sum(x["origen"] == "A" for x in filas), "B": sum(x["origen"] == "B" for x in filas)}}


def _socios():
    return fetch_all("SELECT IdSocio, COUNT(*) n, SUM(Importe) i, SUM(ImporteUSD) u, SUM(ImporteKgCarne) k FROM dbo.MovimientosCuentaSocio "
                     "WHERE Anulada=0 GROUP BY IdSocio ORDER BY IdSocio")


def run(aplicar=False):
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        n = fetch_all("SELECT COUNT(*) n FROM dbo.MovimientosCuentaSocio WHERE Origen=? AND Anulada=0", (ORIGEN,))[0]["n"]
        return {"estado": "ya_aplicado_sin_escrituras", "asientos": n}
    p = plan()
    for x in p["filas"]:
        v = a_fecha(x["importe"], x["fecha"])
        # Magnitudes positivas: el Tipo (Devolucion/AsignacionGasto) da el signo, como en el resto de la tabla.
        x["usd"], x["kg"] = Decimal(str(v["importeUSD"])), Decimal(str(v["importeKgCarne"]))
    res = {"estado": "inspeccion", "cantidad": p["cantidad"], "haber": p["haber"], "debe": p["debe"],
           "neto": p["haber"] - p["debe"], "usdNeto": sum(x["usd"] * (1 if x["lado"] == "debe" else -1) for x in p["filas"]),
           "excluidas": p["excluidas"], "ambiguas": p["ambiguas"]}
    if not aplicar:
        return res
    res["backup"] = backup_verificado("socio3_historia_condominio_036")
    log = OUT / f"socio3-historia-{datetime.now():%Y%m%d-%H%M%S}.json"
    log.write_text(json.dumps({**res, "filas": p["filas"]}, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    antes = _socios()
    stmts = [("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario) "
              "VALUES (3,?,?,?,?,?,?,?,?,?,'Claude036')",
              ("Devolucion" if x["lado"] == "haber" else "AsignacionGasto", x["importe"], x["usd"], x["kg"], x["fecha"].isoformat(), ORIGEN,
               x["id"] if x["origen"] == "B" else -x["id"], x["medio"], x["motivo"])) for x in p["filas"]]
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES (?,'aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (RULE, json.dumps({"informe": str(log), "nota": "IdOrigen negativo = fila de la planilla Depositos 1; positivo = IdPagoEfectivo"}),
                   res["backup"], f"Socio 3: {len(p['filas'])} asientos históricos 2011-2016 (aportes de planilla y pagos directos), neto {res['neto']}.")))
    execute_write_transaction(stmts)
    despues = _socios()
    assert [x for x in antes if x["IdSocio"] != 3] == [x for x in despues if x["IdSocio"] != 3], "Cambió otro socio"
    res.update(estado="aplicado", informe=str(log), socio3Antes=[x for x in antes if x["IdSocio"] == 3],
               socio3Despues=[x for x in despues if x["IdSocio"] == 3])
    log.write_text(json.dumps({**res, "filas": p["filas"]}, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(ap.parse_args().aplicar), default=str, ensure_ascii=False, indent=1))
