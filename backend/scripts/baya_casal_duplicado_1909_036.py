"""Neutraliza el pago histórico duplicado1909 sin tocar tarjeta ni bancos.

Reversión atómica del importe original y sus cinco aplicaciones mediante
--revertir ID. Reversión genérica035 bloqueada para esta regla.
"""
import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.db.connection import _assert_target_is_wc, fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.auditoria_cuentas.correcciones import REGLA_EFECTIVO_DUPLICADO
from src.features.vinculos.backup import backup_verificado

USER = "Sergio (correccion autorizada Baya Casal 036)"
IDS = [15644, 15645, 15646, 15647, 15648]
ROOT = Path(__file__).resolve().parents[2] / "backups/baya-conciliacion-20261019"
AMOUNT = Decimal("471336.79")
MOTIVO = "Pago historico AgroNacion duplicado por consumo5917/vinculo5577; conservar tarjeta y bancos, retirar credito1909"


def state():
    return {
        "efectivo": fetch_all("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?", (1909,)),
        "aplicaciones": fetch_all("SELECT * FROM dbo.AplicacionesPago WHERE OrigenMovimiento=? AND IdMovimientoOrigen=? ORDER BY IdAplicacion", ("efectivo", 1909)),
        "tarjeta": fetch_all("SELECT * FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdVinculo=?", (5577,)),
        "consumo": fetch_all("SELECT * FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdLineaConsumo=?", (5917,)),
        "bancos": fetch_all("SELECT * FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA IN (?,?) ORDER BY IdMovimientoBNA", (18215, 18216)),
        "pagosResumen": fetch_all("SELECT * FROM dbo.Tarjetas_Resumenes_Pagos WHERE IdResumen=? ORDER BY IdPago", (651,)),
        "saldoBase": fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"],
        "movimiento1909": fetch_all("SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE Origen=? AND IdOrigen=?", ("Pagos efectivo", 1909)),
    }


def save(path, data):
    path.write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def unchanged_real_payments(before, after):
    for key in ("tarjeta", "consumo", "bancos", "pagosResumen"):
        assert before[key] == after[key], f"Cambio inesperado en{key}"


def apply():
    before = state()
    previous = fetch_all("SELECT IdCorreccion,Estado FROM dbo.AuditoriaCorrecciones WHERE Regla=? ORDER BY IdCorreccion DESC", (REGLA_EFECTIVO_DUPLICADO,))
    if previous and previous[0]["Estado"] == "aplicada":
        assert before["efectivo"][0]["Importe imputado"] == 0 and not before["movimiento1909"]
        assert all(r["Anulada"] for r in before["aplicaciones"])
        print("Ya aplicada, correccion:", previous[0]["IdCorreccion"])
        return
    row = before["efectivo"][0]
    assert row["IdContacto"] == 226 and row["IdFormaPago"] == 18 and Decimal(str(row["Importe imputado"])) == AMOUNT
    active = [r for r in before["aplicaciones"] if not r["Anulada"]]
    assert [r["IdAplicacion"] for r in active] == IDS
    assert abs(sum(Decimal(str(r["ImporteAplicado"])) for r in active) - AMOUNT) < Decimal("0.001")
    assert before["tarjeta"][0]["IdCompra"] == 2143512802 and Decimal(str(before["tarjeta"][0]["ImporteImputado"])) == AMOUNT
    backup = backup_verificado("baya-duplicado1909-036")
    path = ROOT / f"duplicado1909-{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    audit = {"respaldo": backup, "motivo": MOTIVO, "antes": before}
    save(path, audit)
    params = json.dumps({"idPagoEfectivo": 1909, "idContacto": 226, "importeAnterior": str(AMOUNT), "idsAplicacion": IDS, "auditoriaArchivo": str(path), "antes": before}, default=str, ensure_ascii=False)
    with reconciliation_transaction():
        assert state() == before, "Cambio concurrente: no sobrescribir"
        result = execute_write_transaction([
            ("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) OUTPUT INSERTED.IdCorreccion VALUES (?,'aplicada',?,?,?,SYSDATETIME(),?,?)",
             (REGLA_EFECTIVO_DUPLICADO, params, USER, USER, backup, json.dumps({"pago": 1909, "importe": str(AMOUNT), "aplicaciones": IDS}))),
            ("UPDATE dbo.[Pagos efectivo] SET [Importe imputado]=0 WHERE IdPagoEfectivo=? AND IdContacto=? AND [Importe imputado]=?", (1909, 226, AMOUNT)),
            ("UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion=?,FechaAnulacion=SYSUTCDATETIME() WHERE OrigenMovimiento=? AND IdMovimientoOrigen=? AND Anulada=0", (MOTIVO, USER, "efectivo", 1909)),
        ])
        after = state()
        unchanged_real_payments(before, after)
        assert not after["movimiento1909"] and all(r["Anulada"] for r in after["aplicaciones"])
        assert after["efectivo"][0] == {**row, "Importe imputado": 0.0}
        assert abs(Decimal(str(after["saldoBase"])) - Decimal(str(before["saldoBase"])) + AMOUNT) < Decimal("0.001")
        execute_write_transaction([("INSERT INTO dbo.AuditoriaCorreccionesCuentas (IdCorreccion,IdContacto,Tildada,SaldoAntes,SaldoDespues,IdsAplicacion,Detalle) VALUES (?,?,1,?,?,?,?)", (result[0], 226, before["saldoBase"], after["saldoBase"], json.dumps(IDS), MOTIVO + "; reversion completa mediante script especifico, no generica"))])
        audit.update(idCorreccion=result[0], despues=after)
        save(path, audit)
    assert state() == after
    print("Correccion:", result[0], "Respaldo verificado:", backup)
    print("Importe neutralizado:", AMOUNT, "Aplicaciones anuladas:", IDS)
    print("Tarjeta y bancos sin cambios. Auditoria:", path)


def revert(correction_id):
    rows = fetch_all("SELECT Estado,Regla,Parametros FROM dbo.AuditoriaCorrecciones WHERE IdCorreccion=?", (correction_id,))
    assert len(rows) == 1 and rows[0]["Estado"] == "aplicada" and rows[0]["Regla"] == REGLA_EFECTIVO_DUPLICADO
    p = json.loads(rows[0]["Parametros"])
    assert p["idPagoEfectivo"] == 1909 and p["idContacto"] == 226 and p["idsAplicacion"] == IDS
    before = state()
    assert before["efectivo"][0]["IdContacto"] == 226 and before["efectivo"][0]["Importe imputado"] == 0
    assert [r["IdAplicacion"] for r in before["aplicaciones"]] == IDS and all(r["Anulada"] and r["MotivoAnulacion"] == MOTIVO for r in before["aplicaciones"])
    backup = backup_verificado("revertir-baya1909-036")
    with reconciliation_transaction():
        assert state() == before
        execute_write_transaction([
            ("UPDATE dbo.[Pagos efectivo] SET [Importe imputado]=? WHERE IdPagoEfectivo=? AND IdContacto=? AND [Importe imputado]=0", (AMOUNT, 1909, 226)),
            ("UPDATE dbo.AplicacionesPago SET Anulada=0,MotivoAnulacion=NULL,UsuarioAnulacion=NULL,FechaAnulacion=NULL WHERE OrigenMovimiento=? AND IdMovimientoOrigen=? AND Anulada=1 AND MotivoAnulacion=?", ("efectivo", 1909, MOTIVO)),
            ("UPDATE dbo.AuditoriaCorrecciones SET Estado='revertida',UsuarioReversion=?,FechaReversion=SYSDATETIME() WHERE IdCorreccion=? AND Estado='aplicada'", (USER, correction_id)),
        ])
        after = state()
        unchanged_real_payments(before, after)
        assert Decimal(str(after["efectivo"][0]["Importe imputado"])) == AMOUNT and all(not r["Anulada"] for r in after["aplicaciones"])
        assert abs(Decimal(str(after["saldoBase"])) - Decimal(str(before["saldoBase"])) - AMOUNT) < Decimal("0.001")
        save(ROOT / f"reversion1909-{datetime.now():%Y%m%d_%H%M%S_%f}.json", {"idCorreccion": correction_id, "respaldo": backup, "antes": before, "despues": after})
    assert state() == after
    print("Reversion completa:", correction_id, "Respaldo:", backup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--revertir", type=int)
    args = parser.parse_args()
    _assert_target_is_wc()
    revert(args.revertir) if args.revertir is not None else apply()
