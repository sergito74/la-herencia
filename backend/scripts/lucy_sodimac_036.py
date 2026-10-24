"""Sergio24/10/2026: Lucy pagó total fiscal Sodimac, sin reintegro."""

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from scripts.corregir_easy_cooperativa_condominio_036 import rows
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado

RULE = "lucy-sodimac-total-confirmado-036"
OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"


def run(apply=False):
    _assert_target_is_wc()
    p = read("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=88")[0]
    existing = read("SELECT * FROM dbo.MovimientosCuentaSocio WHERE Origen='PagosEfectivo' AND IdOrigen=88 AND Anulada=0")
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        assert p["Importe imputado"] == Decimal("624.29")
        assert len(existing) == 1 and existing[0]["IdSocio"] == 2 and existing[0]["Importe"] == Decimal("624.29")
        return {"estado": "ya_aplicado_sin_escrituras"}
    assert not existing
    assert not read("SELECT IdMovimiento FROM dbo.MovimientosCuentaSocio WHERE IdSocio=2 AND (CONVERT(date,Fecha)=? OR Importe IN (571.92,624.29))", (p["Fecha"].date(),))
    assert p["Importe imputado"] == Decimal("571.92") and p["IdFormaPago"] == 20 and p["IdContacto"] == 91 and p["IdOperacion"] == 265
    fiscal = read("SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=-575570518")[0]["ImporteDocumento"]
    assert round(fiscal, 2) == Decimal("624.29")
    v = a_fecha(Decimal("624.29"), p["Fecha"].date())
    result = {"estado": "inspeccion", "pagoAntes": p, "fiscal": fiscal, "valuacion": v, "confirmacion": "Sergio24/10/2026: tarjetaLucy, pagó factura624,29, no reintegrado; detalleGeneral sin particular."}
    if not apply:
        return result
    result["backup"] = backup_verificado("lucy_sodimac_036")
    log = OUT / f"lucy-sodimac-{datetime.now():%Y%m%d-%H%M%S}.json"
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()
            before = control(c)
            assert rows(c, "SELECT * FROM dbo.[Pagos efectivo] WITH (UPDLOCK,HOLDLOCK) WHERE IdPagoEfectivo=88")[0] == p
            assert not rows(c, "SELECT IdMovimiento FROM dbo.MovimientosCuentaSocio WITH (UPDLOCK,HOLDLOCK) WHERE Origen='PagosEfectivo' AND IdOrigen=88 AND Anulada=0")
            c.execute("UPDATE dbo.[Pagos efectivo] SET [Importe imputado]=624.29 WHERE IdPagoEfectivo=88")
            c.execute("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) VALUES (2,'Devolucion',624.29,?,?,?,'PagosEfectivo',88,'Tarjeta Lucy',?,'Codex036',0)", v["importeUSD"], v["importeKgCarne"], p["Fecha"], "Sodimac2282-00000483: Lucy pagó total624,29 sin reintegro (Sergio24/10/2026). Pago88 corregido, sin pago nuevo.")
            after = control(c)
            assert before["cajas"] == after["cajas"]
            assert [x for x in before["cuentas"] if x[0] != 91] == [x for x in after["cuentas"] if x[0] != 91]
            assert next(x[1] for x in after["cuentas"] if x[0] == 91) - next(x[1] for x in before["cuentas"] if x[0] == 91) == Decimal("52.37")
            assert [x for x in before["socios"] if x[0] != 2] == [x for x in after["socios"] if x[0] != 2]
            old, new = (next(x for x in state["socios"] if x[0] == 2) for state in (before, after))
            assert new[1] == old[1] + 1 and new[2] - old[2] == Decimal("624.29") and new[3] - old[3] == v["importeUSD"] and new[4] == old[4]
            result["controlAntes"], result["controlDespues"] = before, after
            c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps({"informe": str(log)}), result["backup"], "Pago88 a624,29 y créditoLucy por total confirmado; no nuevos pagos/gastos ni caja.")
        result["estado"] = "aplicado"
    except Exception:
        result["estado"] = "revertido"
        raise
    finally:
        log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"estado": result["estado"], "informe": str(log), "backup": result["backup"], "valuacion": v}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False))
