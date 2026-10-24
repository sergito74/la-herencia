"""Repara aplicaciones en origen real 'efectivo'; no modifica pagos ni saldos."""

import argparse
import json
from datetime import datetime
from decimal import Decimal

from scripts.conciliar_diez_debitos_centavos_036 import OUT, TICKETS
from scripts.corregir_easy_cooperativa_condominio_036 import rows
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado

RULE = "condominio-aplicaciones-diez-centavos-036"


def validate(q):
    for pid, (fiscal, bank) in TICKETS.items():
        doc = q("SELECT IdDeuda FROM dbo.Compras WHERE IdOperacion=(SELECT IdOperacion FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?)", (pid,))[0]["IdDeuda"]
        apps = q("SELECT IdDocumentoAplicado,ImporteAplicado FROM dbo.AplicacionesPago WHERE OrigenMovimiento='efectivo' AND IdMovimientoOrigen=? AND Anulada=0", (pid,))
        assert apps == [{"IdDocumentoAplicado": doc, "ImporteAplicado": min(Decimal(fiscal), Decimal(bank))}]


def run(apply=False):
    _assert_target_is_wc()
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        validate(read)
        return {"estado": "ya_aplicado_sin_escrituras"}
    changes = []
    for pid, (fiscal, bank) in TICKETS.items():
        doc = read("SELECT IdDeuda FROM dbo.Compras WHERE IdOperacion=(SELECT IdOperacion FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?)", (pid,))[0]["IdDeuda"]
        apps = read("SELECT * FROM dbo.AplicacionesPago WHERE OrigenMovimiento='efectivo' AND IdMovimientoOrigen=? AND Anulada=0 ORDER BY IdAplicacion", (pid,))
        target = min(Decimal(fiscal), Decimal(bank))
        correct = [a for a in apps if a["IdDocumentoAplicado"] == doc and a["ImporteAplicado"] == target]
        assert len(correct) <= 1
        changes.append({"pago": pid, "compra": doc, "importe": target, "antes": apps, "conservar": [a["IdAplicacion"] for a in correct]})
    result = {"estado": "inspeccion", "planes": changes}
    if not apply:
        return result
    result["backup"] = backup_verificado("aplicaciones_diez_centavos_036")
    log = OUT / f"aplicaciones-diez-centavos-{datetime.now():%Y%m%d-%H%M%S}.json"
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()
            before = control(c)
            for plan in changes:
                pid = plan["pago"]
                assert rows(c, "SELECT * FROM dbo.AplicacionesPago WITH (UPDLOCK,HOLDLOCK) WHERE OrigenMovimiento='efectivo' AND IdMovimientoOrigen=? AND Anulada=0 ORDER BY IdAplicacion", (pid,)) == plan["antes"]
                for old in plan["antes"]:
                    if old["IdAplicacion"] in plan["conservar"]:
                        continue
                    c.execute("UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion='Codex036',FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=?", "036: banco exacto y ticket propio; retira reparto cronológico de centavos o exceso sobre débito.", old["IdAplicacion"])
                if not plan["conservar"]:
                    c.execute("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) VALUES ('efectivo',?,'CompraDeuda',?,?,SYSDATETIME(),'Codex036',0,'manual',?)", pid, plan["compra"], plan["importe"], "036: cobroVisa documentado aplicado solo al ticket propio. Vuelto/complemento en AjustesCuentaCorriente; no repartir a otras facturas.")
            validate(lambda sql, params=(): rows(c, sql, params))
            assert before == control(c)
            c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps({"informe": str(log)}), result["backup"], "Corrige control de origen: efectivo es nombre real. Diez aplicaciones al ticket propio sin superar banco; no cambios de saldos.")
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
