"""036: reconstrucción de la caja Giamigli 2011–13/07/2015 (Sergio 25/10/2026).

La planilla de caja solo registra egresos antes del 14/07/2015; el libro cerraba con un ingreso «NO identificados» de
$144.350,52 (mov. 1947). Se agregan, cada uno una sola vez:
- Ingresos: cobros en efectivo de Pagos efectivo (forma 8 «Efectivo» de cobro, más el cobro 408 de $20.000 en efectivo)
  que no estaban en el libro.
- Egresos: depósitos de ese efectivo en el BNA (10640, 10990, 11076, 11533 identificados; 11245/11272 Pastorino y
  10509/10857 caja, probables, OK de Sergio).
- Egresos: 54 pagos en efectivo a Marcelo Sierra (cuenta Blue, parte en negro del sueldo, ene-2011 a jun-2015): «1. Adelante».
- Ingresos: 7 cheques propios BNA «COBRADO POR CAJA» sin contacto (efectivo para la caja): «5. Ok, adelante».
El ingreso no identificado 1947 pasa a ser el remanente, de modo que el saldo al 13/07/2015 y el saldo final no cambian.
Fuera de la caja: cheque 18505 (cuenta Sucesión) ↔ depósito 10431 (apertura cuenta Giamigli, 30/03/2012) = traspaso
interno, aporte de la Sucesión; cheque 11350 $2.000 (07/05/2014) = retiro de Sergio → socio 1 y contacto 5670.
Pendiente con Sergio: pagos 2137, 363, 1563, 2638, 708 (quedan dentro del remanente). Inspección por defecto.
"""

import argparse
import json
from datetime import date
from decimal import Decimal

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado

RULE = "caja-giamigli-reconstruccion-2011-2015-036"
USUARIO = "Sergio (036, reconstrucción caja 2011-2015 25/10/2026)"
REMANENTE = 1947
DEPOSITOS = {10640: "identificado (cobro 408)", 10990: "identificado (cobros 449+451)", 11076: "identificado (cobro 477)",
             11533: "identificado (cobros 696+697+698)", 11245: "probable (cobro Pastorino 551)",
             11272: "probable (cobro Pastorino 560)", 10509: "probable (efectivo de caja)", 10857: "probable (caja, transferencia)"}
CHEQUES = (9868, 9913, 9938, 9939, 10044, 10084, 10249)
RETIRO_BNA = 11350
CUENTA = {"Blue": "B", "White": "White"}


def plan():
    en_libro = "NOT EXISTS (SELECT 1 FROM dbo.MovimientosCajaEfectivo m WHERE m.IdPagoEfectivo=p.IdPagoEfectivo AND m.Anulada=0)"
    cobros = fetch_all(f"""SELECT p.IdPagoEfectivo id, CONVERT(date,p.Fecha) f, -p.[Importe imputado] i, p.Cuenta, c.[Razon Social] r
        FROM dbo.[Pagos efectivo] p LEFT JOIN dbo.Contactos c ON c.IdContacto=p.IdContacto
        WHERE p.Fecha<'2015-07-14' AND p.[Importe imputado]<0 AND (p.IdFormaPago=8 OR p.IdPagoEfectivo=408) AND {en_libro}""")
    sierra = fetch_all(f"""SELECT p.IdPagoEfectivo id, CONVERT(date,p.Fecha) f, p.[Importe imputado] i, p.Cuenta FROM dbo.[Pagos efectivo] p
        WHERE p.IdContacto=374 AND p.Caja='La Herencia' AND p.IdFormaPago=3 AND p.[Importe imputado]>0 AND p.Fecha<'2015-07-14' AND {en_libro}""")
    bna = {b["id"]: b for b in fetch_all(
        "SELECT IdMovimientoBNA id, CONVERT(date,[Fecha / Hora Mov#]) f, [Nro# Comprobante] n, Importe i, ISNULL(IdContacto,0) c FROM dbo.[Movimientos BNA] "
        "WHERE IdMovimientoBNA IN (%s)" % ",".join(map(str, (*DEPOSITOS, *CHEQUES, RETIRO_BNA))))}
    ya = {r["Detalle"] for r in fetch_all("SELECT Detalle FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA' AND Anulada=0 AND Detalle LIKE 'BNA %'")}
    filas = []
    for c in cobros:
        filas.append({"f": c["f"], "concepto": f"Cobro en efectivo {c['r']}", "detalle": f"Pago efectivo {c['id']} (cobro)",
                      "imp": Decimal(str(c["i"])), "cuenta": CUENTA.get(c["Cuenta"], "White"), "pago": c["id"]})
    for s in sierra:
        filas.append({"f": s["f"], "concepto": "Marcelo Sierra", "detalle": f"Sueldo, parte en efectivo (Access cuenta {s['Cuenta']}, pago {s['id']})",
                      "imp": -Decimal(str(s["i"])), "cuenta": CUENTA.get(s["Cuenta"], "B"), "pago": s["id"]})
    for i, nota in DEPOSITOS.items():
        b = bna[i]
        assert Decimal(str(b["i"])) > 0 and b["c"] == 0, i
        det = f"BNA {i} depósito del efectivo de caja, {nota}"
        if det not in ya:
            filas.append({"f": b["f"], "concepto": "Depósito en BNA", "detalle": det, "imp": -Decimal(str(b["i"])), "cuenta": "White", "pago": None})
    for i in CHEQUES:
        b = bna[i]
        assert Decimal(str(b["i"])) < 0 and b["c"] == 0, i
        det = f"BNA {i} cheque propio {int(b['n'])} cobrado por caja"
        if det not in ya:
            filas.append({"f": b["f"], "concepto": "Cheque propio cobrado por caja", "detalle": det, "imp": -Decimal(str(b["i"])), "cuenta": "White", "pago": None})
    neto = sum(f["imp"] for f in filas)
    rem = fetch_all("SELECT Importe FROM dbo.MovimientosCajaEfectivo WHERE IdMovimiento=? AND Anulada=0", (REMANENTE,))[0]["Importe"]
    return filas, neto, Decimal(str(rem)), bna[RETIRO_BNA]


def _saldos():
    return fetch_all("SELECT SUM(Importe) s, SUM(CASE WHEN Fecha<'2015-07-14' THEN Importe END) s1507 FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA' AND Anulada=0")[0]


def run(aplicar=False):
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    filas, neto, rem, ret = plan()
    nuevo = rem - neto
    grupos = {}
    for f in filas:
        g = grupos.setdefault(f["concepto"] if not f["concepto"].startswith("Cobro") else "Cobros en efectivo", [0, Decimal(0)])
        g[0] += 1
        g[1] += f["imp"]
    res = {"estado": "inspeccion", "grupos": {k: [v[0], str(v[1])] for k, v in grupos.items()}, "neto": str(neto),
           "remanenteAntes": str(rem), "remanenteNuevo": str(nuevo), "retiroSergio": ret}
    if not aplicar:
        return res
    res["backup"] = backup_verificado("caja_giamigli_reconstruccion_2011_2015_036")
    antes = _saldos()
    st = [("INSERT INTO dbo.MovimientosCajaEfectivo (Caja,Fecha,Concepto,Detalle,Importe,Cuenta,IdPagoEfectivo,Usuario) VALUES ('GiamigliSA',?,?,?,?,?,?,?)",
           (str(f["f"]), f["concepto"], f["detalle"], f["imp"], f["cuenta"], f["pago"], USUARIO)) for f in filas]
    st.append(("UPDATE dbo.MovimientosCajaEfectivo SET Importe=?, Concepto=? WHERE IdMovimiento=?",
               (nuevo, "Ingresos 2011–jul-2015 NO identificados (remanente tras reconstrucción 25/10/2026)", REMANENTE)))
    # Retiro de Sergio: contacto 5670 en el banco y Debe en su cuenta de socio.
    f = date.fromisoformat(str(ret["f"]))
    v = a_fecha(Decimal("2000"), f)
    st += [("UPDATE dbo.[Movimientos BNA] SET IdContacto=5670, Contacto='Sergio Giamberardini (socio)' WHERE IdMovimientoBNA=? AND ISNULL(IdContacto,0)=0", (RETIRO_BNA,)),
           ("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario) "
            "VALUES (1,'AsignacionGasto',2000,?,?,?,'Banco Nacion',?,'Banco Nación',?,'Claude036')",
            (Decimal(str(v["importeUSD"])), Decimal(str(v["importeKgCarne"])), f.isoformat(), RETIRO_BNA,
             "Sergio Giamberardini — Retiro con cheque Giamigli cobrado por caja (BNA 11350); Movs Condominio 18/05/2014 «Retiro Sergio» (Sergio 25/10/2026)"))]
    st.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
               "VALUES (?,'aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
               (RULE, json.dumps({**res["grupos"], "traspasoSucesion": [18505, 10431], "retiro": RETIRO_BNA,
                                  "pendientes": [2137, 363, 1563, 2638, 708]}, default=str), res["backup"],
                f"Caja Giamigli 2011-2015: {len(filas)} movimientos, neto {neto}; remanente no identificado {rem} → {nuevo}. Retiro Sergio BNA 11350.")))
    execute_write_transaction(st)
    despues = _saldos()
    assert abs(Decimal(str(antes["s"])) - Decimal(str(despues["s"]))) < Decimal("0.01"), "cambió el saldo final"
    assert abs(Decimal(str(antes["s1507"])) - Decimal(str(despues["s1507"]))) < Decimal("0.01"), "cambió el saldo al 13/07/2015"
    res.update(estado="aplicado", saldos=despues)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(ap.parse_args().aplicar), default=str, ensure_ascii=False, indent=1))
