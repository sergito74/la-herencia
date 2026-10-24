"""Corrige importes documentados y créditosLucy; aplicaciones ajenas sin inventar."""

import argparse
import hashlib
import json
from datetime import datetime
from decimal import Decimal

from scripts.corregir_easy_cooperativa_condominio_036 import rows
from scripts.lucy_tres_tarjetas_condominio_036 import OUT
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado
from pathlib import Path

RULE = "lucy-importes-fiscales-easy-coop-036"
TARGETS = {503: Decimal("2253.03"), 561: Decimal("1361.54")}


def active_lucy(q):
    return q("SELECT SUM(Importe) pesos,SUM(ImporteUSD) usd,SUM(ImporteKgCarne) kg FROM dbo.MovimientosCuentaSocio WHERE IdSocio=2 AND Anulada=0")[0]


def run(apply=False):
    _assert_target_is_wc()
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        for pid, amount in TARGETS.items():
            assert read("SELECT [Importe imputado] importe FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?", (pid,))[0]["importe"] == amount
            credit = read("SELECT Importe FROM dbo.MovimientosCuentaSocio WHERE Origen='PagosEfectivo' AND IdOrigen=? AND IdSocio=2 AND Anulada=0", (pid,))
            assert credit == [{"Importe": amount}]
        return {"estado": "ya_aplicado_sin_escrituras"}
    plans = []
    for pid, amount in TARGETS.items():
        p = read("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?", (pid,))[0]
        credit = read("SELECT * FROM dbo.MovimientosCuentaSocio WHERE Origen='PagosEfectivo' AND IdOrigen=? AND Anulada=0", (pid,))
        assert len(credit) == 1 and credit[0]["IdSocio"] == 2 and credit[0]["Tipo"] == "Devolucion"
        assert credit[0]["Importe"] == p["Importe imputado"] == (Decimal("2253.04") if pid == 503 else Decimal("1250.97"))
        doc = read("SELECT c.*,t.ImporteDocumento FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento t ON t.IdDeuda=c.IdDeuda WHERE c.IdOperacion=?", (p["IdOperacion"],))[0]
        assert round(doc["ImporteDocumento"], 2) == amount
        source = Path(doc["Documento Original"].split("#")[0])
        apps = read("SELECT * FROM dbo.AplicacionesPago WHERE OrigenMovimiento='efectivo' AND IdMovimientoOrigen=? AND Anulada=0 ORDER BY IdAplicacion", (pid,))
        plans.append({"pago": p, "credito": credit[0], "compra": doc, "importe": amount, "valuacion": a_fecha(amount, p["Fecha"].date()), "aplicaciones": apps, "pdf": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    displaced = read("SELECT * FROM dbo.AplicacionesPago WHERE IdAplicacion=12052 AND Anulada=0")
    assert len(displaced) == 1 and displaced[0]["OrigenMovimiento"] == "bna" and displaced[0]["IdMovimientoOrigen"] == 14405 and displaced[0]["ImporteAplicado"] == Decimal("1317.93")
    result = {"estado": "inspeccion", "planes": plans, "bnaDesplazada": displaced, "nota": "Coop tarjeta2253,03; Easy tarjeta1362 menos vuelto0,46 =1361,54. Lucy titular sin reintegro confirmado. No atribuir vuelto a caja empresa."}
    if not apply:
        return result
    result["backup"] = backup_verificado("lucy_easy_coop_importes_036")
    log = OUT / f"lucy-easy-coop-{datetime.now():%Y%m%d-%H%M%S}.json"
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()
            def q(sql, params=()):
                return rows(c, sql, params)
            before, lucy_before = control(c), active_lucy(q)
            for plan in plans:
                p, old, amount = plan["pago"], plan["credito"], plan["importe"]
                assert q("SELECT * FROM dbo.[Pagos efectivo] WITH (UPDLOCK,HOLDLOCK) WHERE IdPagoEfectivo=?", (p["IdPagoEfectivo"],))[0] == p
                assert q("SELECT * FROM dbo.MovimientosCuentaSocio WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimiento=?", (old["IdMovimiento"],))[0] == old
                assert q("SELECT * FROM dbo.AplicacionesPago WITH (UPDLOCK,HOLDLOCK) WHERE OrigenMovimiento='efectivo' AND IdMovimientoOrigen=? AND Anulada=0 ORDER BY IdAplicacion", (p["IdPagoEfectivo"],)) == plan["aplicaciones"]
                c.execute("UPDATE dbo.[Pagos efectivo] SET [Importe imputado]=? WHERE IdPagoEfectivo=?", amount, p["IdPagoEfectivo"])
                c.execute("UPDATE dbo.MovimientosCuentaSocio SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion='Codex036',FechaAnulacion=SYSDATETIME() WHERE IdMovimiento=?", "Importe corregido según ticket original; reemplazo con mismo origen. Sin reintegroLucy confirmado porSergio.", old["IdMovimiento"])
                note = f"Pago{p['IdPagoEfectivo']} por tarjetaLucy, sin reintegro; total fiscal{amount}. Corrige asiento{old['IdMovimiento']} sin duplicar gasto/pago."
                if p["IdPagoEfectivo"] == 561:
                    note += " Visa1362 menos vuelto0,46."
                v = plan["valuacion"]
                c.execute("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) VALUES (2,'Devolucion',?,?,?,?,'PagosEfectivo',?,'Tarjeta Lucy',?,'Codex036',0)", amount, v["importeUSD"], v["importeKgCarne"], p["Fecha"], p["IdPagoEfectivo"], note)
                for app in plan["aplicaciones"]:
                    c.execute("UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion='Codex036',FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=?", "Ticket pagado porLucy: reemplazo deFIFO/parcial por importe fiscal íntegro a su factura.", app["IdAplicacion"])
                c.execute("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) VALUES ('efectivo',?,'CompraDeuda',?,?,SYSDATETIME(),'Codex036',0,'manual','Original tarjetaLucy y confirmación sin reintegro; importe neto fiscal, sin duplicar pago.')", p["IdPagoEfectivo"], plan["compra"]["IdDeuda"], amount)
            assert q("SELECT * FROM dbo.AplicacionesPago WITH (UPDLOCK,HOLDLOCK) WHERE IdAplicacion=12052 AND Anulada=0") == displaced
            c.execute("UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion='Codex036',FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=12052", "FIFO asignabaBNA14405 a factura2253,03 pagada íntegra porLucy. Importe1317,93 queda disponible para conciliar otros documentos; no deuda nueva.")
            after, lucy_after = control(c), active_lucy(q)
            assert before["cajas"] == after["cajas"]
            assert [x for x in before["cuentas"] if x[0] not in (22, 29)] == [x for x in after["cuentas"] if x[0] not in (22, 29)]
            for contact, delta in [(22, Decimal("-0.01")), (29, Decimal("110.57"))]:
                assert next(x[1] for x in after["cuentas"] if x[0] == contact) - next(x[1] for x in before["cuentas"] if x[0] == contact) == delta
            assert [x for x in before["socios"] if x[0] != 2] == [x for x in after["socios"] if x[0] != 2]
            assert lucy_after["pesos"] - lucy_before["pesos"] == Decimal("110.56") and lucy_after["kg"] == lucy_before["kg"]
            result["antes"], result["despues"] = before, after
            c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps({"informe": str(log)}), result["backup"], "Easy1361,54 yCoop2253,03: pagos existentes ycréditosLucy corregidos; aplicaciones a ticket propio; BNA liberado1317,93 pendiente, no deuda.")
        result["estado"] = "aplicado"
    except Exception:
        result["estado"] = "revertido"
        raise
    finally:
        log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"estado": result["estado"], "informe": str(log), "backup": result["backup"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False))
