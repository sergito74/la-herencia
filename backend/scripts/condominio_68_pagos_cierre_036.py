"""036: cierre de los 68 pagos «puente» del Condominio LSC 2011–2014 y corrección de los cheques del camión.

Respuestas de Sergio (25/10/2026):
- A. Los comprobantes a nombre de la Sucesión / consumidor final (13, 14, 15, 16, 18, 75) son gastos de Giamigli: la
  Sucesión fue la etapa previa del negocio, antes de la S.A.
- B. Los 5 combustibles con ticket «Efectivo» y débito HSBC exacto (14, 40, 362, 530, 660) se pagaron con el débito.
- C. El efectivo de los pagos 177, 331 y 360 lo puso Lucy (socio 2), sin reintegro.
- D. Los cheques de la planilla por $3.134 son los Maignal 122750-52 de $3.143 depositados en BNA (10626/10668/10721);
  los asientos 2990, 2991 y 2993 del socio 3 pasan a $3.143 con su US$ recalculado.

Universo: backups/condominio-15-medios-036/puentes-68-pagos.json. Medio 10 (débito HSBC del Condominio) → Haber del
socio 3; medio 3 (efectivo de Lucy) → Haber del socio 2; Sodimac 88 (tarjeta de Lucy) ya está en el socio 2.
Sin tocar pagos, caja, bancos ni contactos. Inspección por defecto.
"""

import argparse
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado

RULE = "condominio-68-pagos-cierre-036"
BASE = Path(__file__).resolve().parents[2] / "backups" / "condominio-15-medios-036"
SUCESION = {13, 14, 15, 16, 18, 75}
CHEQUES = {2990: 10626, 2991: 10668, 2993: 10721}


def plan():
    ids = [p["id"] for p in json.loads((BASE / "puentes-68-pagos.json").read_text(encoding="utf-8"))]
    q = ",".join(map(str, ids))
    pagos = fetch_all(f"SELECT p.IdPagoEfectivo id, p.Fecha f, p.[Importe imputado] imp, p.IdFormaPago medio, c.[Razon Social] c "
                      f"FROM dbo.[Pagos efectivo] p LEFT JOIN dbo.Contactos c ON c.IdContacto=p.IdContacto WHERE p.IdPagoEfectivo IN ({q})")
    ya = {(r["IdSocio"], r["IdOrigen"]) for r in fetch_all(
        f"SELECT IdSocio, IdOrigen FROM dbo.MovimientosCuentaSocio WHERE Anulada=0 AND IdOrigen IN ({q}) "
        "AND Origen IN ('CondominioHist036','PagosEfectivo')")}
    filas, omitidos = [], []
    for p in sorted(pagos, key=lambda x: x["id"]):
        fecha = date.fromisoformat(str(p["f"])[:10])
        imp = Decimal(str(p["imp"])).quantize(Decimal("0.01"))
        if p["medio"] == 10:
            nota = " Comprobante a nombre de la Sucesión (etapa previa de Giamigli)." if p["id"] in SUCESION else ""
            fila = {"socio": 3, "origen": "CondominioHist036", "medio": "Débito HSBC Condominio",
                    "motivo": f"Condominio LSC — pago con débito HSBC del Condominio de gasto de Giamigli ({p['c']}, pago efectivo {p['id']}).{nota}"}
        elif p["medio"] == 3:
            fila = {"socio": 2, "origen": "PagosEfectivo", "medio": "Efectivo",
                    "motivo": f"{p['c']}: pago {p['id']} en efectivo puesto por Lucy, sin reintegro (Sergio 25/10/2026)."}
        else:
            omitidos.append({"pago": p["id"], "medio": p["medio"], "motivo": "tarjeta de Lucy, ya en socio 2" if p["id"] == 88 else "medio no previsto"})
            continue
        if (fila["socio"], p["id"]) in ya:
            omitidos.append({"pago": p["id"], "motivo": "ya cargado"})
            continue
        v = a_fecha(imp, fecha)
        filas.append({**fila, "id": p["id"], "fecha": fecha, "importe": imp,
                      "usd": Decimal(str(v["importeUSD"])), "kg": Decimal(str(v["importeKgCarne"]))})
    cheques = []
    for mov, bna in CHEQUES.items():
        r = fetch_all("SELECT IdMovimiento, Fecha, Importe FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento=? AND Anulada=0 AND IdSocio=3", (mov,))
        b = fetch_all("SELECT Importe FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA=? AND IdContacto=549", (bna,))
        assert r and b and Decimal(str(b[0]["Importe"])) == Decimal("3143"), (mov, bna)
        if Decimal(str(r[0]["Importe"])) == Decimal("3143"):
            continue
        v = a_fecha(Decimal("3143"), date.fromisoformat(str(r[0]["Fecha"])[:10]))
        cheques.append({"mov": mov, "bna": bna, "usd": Decimal(str(v["importeUSD"])), "kg": Decimal(str(v["importeKgCarne"]))})
    return filas, omitidos, cheques


def _saldos():
    return fetch_all("SELECT IdSocio, COUNT(*) n, SUM(CASE WHEN Tipo='Devolucion' THEN -Importe ELSE Importe END) i, "
                     "SUM(CASE WHEN Tipo='Devolucion' THEN -ImporteUSD ELSE ImporteUSD END) u FROM dbo.MovimientosCuentaSocio "
                     "WHERE Anulada=0 GROUP BY IdSocio ORDER BY IdSocio")


def run(aplicar=False):
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    filas, omitidos, cheques = plan()
    res = {"estado": "inspeccion",
           "socio3": {"n": sum(f["socio"] == 3 for f in filas), "importe": sum(f["importe"] for f in filas if f["socio"] == 3)},
           "socio2": {"n": sum(f["socio"] == 2 for f in filas), "importe": sum(f["importe"] for f in filas if f["socio"] == 2)},
           "cheques3143": cheques, "omitidos": omitidos}
    if not aplicar:
        return res
    res["backup"] = backup_verificado("condominio_68_pagos_cierre_036")
    antes = _saldos()
    log = BASE / f"condominio-68-cierre-{datetime.now():%Y%m%d-%H%M%S}.json"
    st = [("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario) "
           "VALUES (?,'Devolucion',?,?,?,?,?,?,?,?,'Claude036')",
           (f["socio"], f["importe"], f["usd"], f["kg"], f["fecha"].isoformat(), f["origen"], f["id"], f["medio"], f["motivo"][:255]))
          for f in filas]
    st += [("UPDATE dbo.MovimientosCuentaSocio SET Importe=3143, ImporteUSD=?, ImporteKgCarne=?, "
            "Motivo=LEFT(Motivo + ? ,255) WHERE IdMovimiento=? AND Importe=3134",
            (c["usd"], c["kg"], f" (cheque Maignal $3.143, BNA {c['bna']}; planilla decía 3.134)", c["mov"])) for c in cheques]
    st.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
               "VALUES (?,'aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
               (RULE, json.dumps({"informe": str(log)}), res["backup"],
                f"68 pagos Condominio: {res['socio3']['n']} al socio 3, {res['socio2']['n']} a Lucy; {len(cheques)} cheques 3134→3143.")))
    execute_write_transaction(st)
    despues = _saldos()
    assert [x for x in antes if x["IdSocio"] not in (2, 3)] == [x for x in despues if x["IdSocio"] not in (2, 3)], "Cambió otro socio"
    res.update(estado="aplicado", antes=antes, despues=despues, informe=str(log))
    log.write_text(json.dumps({**res, "filas": filas}, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(ap.parse_args().aplicar), default=str, ensure_ascii=False, indent=1))
