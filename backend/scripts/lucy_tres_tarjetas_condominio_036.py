"""Tres pagos existentes financiados por Lucy; confirmación de Sergio24/10/2026."""

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

RULE = "lucy-tres-tarjetas-historicas-036"
TARGETS = {315: ("Naldo", Decimal("1578")), 503: ("Cooperativa", Decimal("2253.04")), 561: ("Easy", Decimal("1250.97"))}
OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"


def run(apply=False):
    _assert_target_is_wc()
    entries = read("SELECT * FROM dbo.MovimientosCuentaSocio WHERE Origen='PagosEfectivo' AND IdOrigen IN (315,503,561) AND Anulada=0")
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        assert len(entries) == 3
        for entry in entries:
            expected = TARGETS[entry["IdOrigen"]][1]
            if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla='lucy-importes-fiscales-easy-coop-036' AND Estado='aplicada'"):
                expected = {315: Decimal("1578"), 503: Decimal("2253.03"), 561: Decimal("1361.54")}[entry["IdOrigen"]]
            assert entry["IdSocio"] == 2 and entry["Tipo"] == "Devolucion" and entry["Importe"] == expected
        return {"estado": "ya_aplicado_sin_escrituras"}
    assert not entries, "Ya existe representación de alguno de los pagos; revisar antes de sumar."
    sources = read("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo IN (315,503,561) ORDER BY IdPagoEfectivo")
    assert len(sources) == 3
    proposals = []
    for p in sources:
        identifier = p["IdPagoEfectivo"]
        name, amount = TARGETS[identifier]
        assert p["Importe imputado"] == amount and p["IdFormaPago"] == 20
        # Revisión de todas las filas, incluso anuladas: sin coincidencias individuales.
        possible = read("SELECT IdMovimiento FROM dbo.MovimientosCuentaSocio WHERE IdSocio=2 AND (CONVERT(date,Fecha)=? OR Importe=?)", (p["Fecha"].date(), amount))
        assert not possible, "Hay candidato en Lucy que requiere revisión."
        valuation = a_fecha(amount, p["Fecha"].date())
        note = f"{name}: pago{identifier} existente financiado por Lucy, sin reintegro (Sergio24/10/2026)."
        if identifier == 561:
            note += " Solo1250,97 registrados; diferencia fiscal110,57 pendiente."
        if identifier == 503:
            note += " Pago2253,04; fiscal2253,03, centavo pendiente."
        proposals.append({"pago": p, "valuacion": valuation, "motivo": note})
    result = {"estado": "inspeccion", "propuestas": proposals, "confirmacion": "Lucy titular de Naldo/Cooperativa/Easy; Giamigli no reintegró, Sergio24/10/2026."}
    if not apply:
        return result
    result["backup"] = backup_verificado("lucy_tres_tarjetas_036")
    log = OUT / f"lucy-tres-tarjetas-{datetime.now():%Y%m%d-%H%M%S}.json"
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()
            before = control(c)
            assert not rows(c, "SELECT IdMovimiento FROM dbo.MovimientosCuentaSocio WITH (UPDLOCK,HOLDLOCK) WHERE Origen='PagosEfectivo' AND IdOrigen IN (315,503,561) AND Anulada=0")
            for proposal in proposals:
                p = proposal["pago"]
                assert rows(c, "SELECT * FROM dbo.[Pagos efectivo] WITH (UPDLOCK,HOLDLOCK) WHERE IdPagoEfectivo=?", (p["IdPagoEfectivo"],))[0] == p
                v = proposal["valuacion"]
                c.execute("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) VALUES (2,'Devolucion',?,?,?,?,'PagosEfectivo',?,'Tarjeta Lucy',?,'Codex036',0)", p["Importe imputado"], v["importeUSD"], v["importeKgCarne"], p["Fecha"], p["IdPagoEfectivo"], proposal["motivo"])
            after = control(c)
            assert before["cajas"] == after["cajas"] and before["cuentas"] == after["cuentas"]
            assert [x for x in before["socios"] if x[0] != 2] == [x for x in after["socios"] if x[0] != 2]
            old = next(x for x in before["socios"] if x[0] == 2)
            new = next(x for x in after["socios"] if x[0] == 2)
            assert new[1] == old[1] + 3 and new[2] - old[2] == Decimal("5082.01")
            assert new[3] - old[3] == sum(x["valuacion"]["importeUSD"] for x in proposals)
            assert new[4] == old[4]
            result["controlAntes"], result["controlDespues"] = before, after
            c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps({"informe": str(log)}), result["backup"], "Tres pagos existentes a favor de Lucy5082,01; sin nuevos pagos/gastos ni cambios en Condominio.")
        result["estado"] = "aplicado"
    except Exception:
        result["estado"] = "revertido"
        raise
    finally:
        log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"estado": result["estado"], "informe": str(log), "backup": result["backup"], "importe": "5082.01", "usd": str(sum(x["valuacion"]["importeUSD"] for x in proposals))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False))
