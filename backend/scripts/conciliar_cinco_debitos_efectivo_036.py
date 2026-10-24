"""036: cinco tickets de combustible que dicen «Efectivo» con débito HSBC del Condominio (Sergio, 24/10/2026:
«Débito del Condominio»: vale el extracto bancario; el ticket «Efectivo» es un error de la estación).

Mismo tratamiento que los diez débitos con centavos (regla condominio-diez-debitos-centavos-036):
- pago existente: medio 3 → 10 (débito) e importe = débito HSBC; no se crea otro pago;
- diferencia entre factura y débito como componente documental en AjustesCuentaCorriente (036-CENT-P{id});
- par histórico de caja Giamigli (egreso ficticio + «Aporte Condominio LSC (pago directo)») anulado, con nota;
- aplicaciones: una sola a la factura propia por el mínimo entre factura y débito (se anulan los cruces de centavos).
Débitos leídos del «Extracto Banco» de Movimientos Condominios.xlsx (operación explícita, comercio OPESSA); Codex
verificó que coinciden con los PDF HSBC (contradicciones-clasificacion-banco.json). Inspección por defecto.
"""

import argparse
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from scripts.corregir_easy_cooperativa_condominio_036 import rows
from scripts.reclasificar_puentes_hsbc_condominio_036 import active
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado

RULE = "condominio-cinco-debitos-ticket-efectivo-036"
OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"
# pago: (operación HSBC, fila del extracto, débito HSBC). La factura se lee de WC.
DEBITOS = {
    14: ("095313", 18, "122.81"),
    40: ("103113", 185, "173.75"),
    362: ("136332", 958, "93.71"),
    530: ("129042", 1134, "362.55"),
    660: ("174398", 1787, "510.13"),
}


def _plan():
    extracto = {x["fila"]: x for x in json.loads((OUT / "contradicciones-clasificacion-banco.json").read_text(encoding="utf-8"))}
    bridges = read("SELECT * FROM dbo.MovimientosCajaEfectivo WHERE Concepto='Aporte Condominio LSC (pago directo)'")
    plans = []
    for pid, (op, fila, banco) in DEBITOS.items():
        banco = Decimal(banco)
        e = extracto[fila]["valores"]
        assert "COMPRA TARJETA DE DEBITO" in e[1] and op in e[1] and "OPESSA" in e[1] and Decimal(str(e[6])) == banco
        p = read("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?", (pid,))[0]
        assert p["IdFormaPago"] == 3 and p["Caja"] == "Condominio"
        doc = read("SELECT c.IdDeuda,c.[Nro Documento] numero,t.ImporteDocumento FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento t "
                   "ON t.IdDeuda=c.IdDeuda WHERE c.IdOperacion=?", (p["IdOperacion"],))
        assert len(doc) == 1
        fiscal = Decimal(str(round(doc[0]["ImporteDocumento"], 2)))
        dias = (datetime.fromisoformat(str(e[0])[:10]) - datetime.fromisoformat(str(p["Fecha"])[:10])).days
        assert abs(banco - fiscal) <= Decimal("0.02") and 0 <= dias <= 5
        legs = read("SELECT * FROM dbo.MovimientosCajaEfectivo WHERE IdPagoEfectivo=?", (pid,))
        assert len(legs) == 1
        pair = legs + [x for x in bridges if re.search(rf"egreso mov\. {legs[0]['IdMovimiento']}\)", x["Detalle"] or "")]
        assert len(pair) == 2 and pair[1]["Importe"] == -pair[0]["Importe"] == p["Importe imputado"]
        assert all(not x["Anulada"] and x["Caja"] == "GiamigliSA" and x["IdOperacionCaja"] is None for x in pair)
        apps = read("SELECT * FROM dbo.AplicacionesPago WHERE OrigenMovimiento='efectivo' AND IdMovimientoOrigen=? AND Anulada=0 ORDER BY IdAplicacion", (pid,))
        assert not read("SELECT IdAjuste FROM dbo.AjustesCuentaCorriente WHERE Motivo LIKE ?", (f"036-CENT-P{pid}:%",))
        delta = banco - fiscal
        motivo = (f"036-CENT-P{pid}: FC{doc[0]['numero']} total{fiscal}; débito HSBC Condominio op{op} {banco}; ticket dice Efectivo "
                  f"(error de estación, Sergio 24/10/2026); diferencia {abs(delta)} documental, sin aporte nuevo.")
        assert len(motivo) <= 255
        plans.append({"pago": p, "factura": doc[0], "fiscal": fiscal, "banco": banco, "delta": delta, "motivo": motivo,
                      "parCaja": pair, "aplicacionesAntes": apps, "aplicar": min(fiscal, banco)})
    return plans


def run(apply=False):
    _assert_target_is_wc()
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        for pid, (_, _, banco) in DEBITOS.items():
            assert read("SELECT [Importe imputado] importe,IdFormaPago medio FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?", (pid,))[0] == {
                "importe": Decimal(banco), "medio": 10}
        return {"estado": "ya_aplicado_sin_escrituras"}
    plans = _plan()
    resumen = [{"pago": x["pago"]["IdPagoEfectivo"], "factura": x["fiscal"], "pagoAntes": x["pago"]["Importe imputado"], "banco": x["banco"],
                "componente": x["delta"], "aplicacionesAntes": [(a["IdDocumentoAplicado"], a["ImporteAplicado"]) for a in x["aplicacionesAntes"]]}
               for x in plans]
    result = {"estado": "inspeccion", "resumen": resumen, "planes": plans}
    if not apply:
        return {"estado": "inspeccion", "resumen": resumen}
    result["backup"] = backup_verificado("condominio_cinco_debitos_036")
    log = OUT / f"cinco-debitos-{datetime.now():%Y%m%d-%H%M%S}.json"
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()
            before, active_before = control(c), active(c)
            for plan in plans:
                p = plan["pago"]
                pid = p["IdPagoEfectivo"]
                assert rows(c, "SELECT * FROM dbo.[Pagos efectivo] WITH (UPDLOCK,HOLDLOCK) WHERE IdPagoEfectivo=?", (pid,))[0] == p
                assert rows(c, "SELECT * FROM dbo.AplicacionesPago WITH (UPDLOCK,HOLDLOCK) WHERE OrigenMovimiento='efectivo' AND "
                               "IdMovimientoOrigen=? AND Anulada=0 ORDER BY IdAplicacion", (pid,)) == plan["aplicacionesAntes"]
                c.execute("UPDATE dbo.[Pagos efectivo] SET IdFormaPago=10,[Importe imputado]=? WHERE IdPagoEfectivo=?", plan["banco"], pid)
                if plan["delta"]:
                    c.execute("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) VALUES (?,?,?,?,?,'Claude036')",
                              p["IdContacto"], p["Fecha"], "Deuda" if plan["delta"] > 0 else "Credito", abs(plan["delta"]), plan["motivo"])
                for old in plan["parCaja"]:
                    assert rows(c, "SELECT * FROM dbo.MovimientosCajaEfectivo WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimiento=?", (old["IdMovimiento"],))[0] == old
                    note = (old["Detalle"] or "") + f" | Pago{pid} débito HSBC Condominio; anulado036."
                    assert len(note) <= 255
                    c.execute("UPDATE dbo.MovimientosCajaEfectivo SET Anulada=1,Detalle=? WHERE IdMovimiento=?", note, old["IdMovimiento"])
                for a in plan["aplicacionesAntes"]:
                    c.execute("UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion='Claude036',FechaAnulacion=SYSDATETIME() "
                              "WHERE IdAplicacion=?", "036: pago corregido a débito HSBC; una aplicación a la factura propia.", a["IdAplicacion"])
                c.execute("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,"
                          "Fecha,Usuario,Anulada,Origen,NotaConciliacion) VALUES ('efectivo',?,'CompraDeuda',?,?,SYSDATETIME(),'Claude036',0,'manual',?)",
                          pid, plan["factura"]["IdDeuda"], plan["aplicar"], "036: débito HSBC del Condominio aplicado solo a su ticket.")
            after, active_after = control(c), active(c)
            assert before["cajas"] == after["cajas"] and before["socios"] == after["socios"]
            # Solo pueden moverse los proveedores de estos pagos, y solo por diferencias de factura sin componente.
            otros = {x["pago"]["IdContacto"] for x in plans}
            assert [x for x in before["cuentas"] if x[0] not in otros] == [x for x in after["cuentas"] if x[0] not in otros]
            assert [(x["Caja"], x["saldo"]) for x in active_before] == [(x["Caja"], x["saldo"]) for x in active_after]
            assert sum(x["n"] for x in active_before) - sum(x["n"] for x in active_after) == 10
            result["controlAntes"], result["controlDespues"] = before, after
            c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                      "VALUES (?,'aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)", RULE, json.dumps({"informe": str(log)}),
                      result["backup"], "5 tickets «Efectivo» con débito HSBC Condominio: medio 10, importe banco, componentes 036-CENT, 10 filas de caja anuladas.")
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
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=1))
