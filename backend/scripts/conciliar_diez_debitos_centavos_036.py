"""Diez tickets y débitos HSBC: banco exacto y componente no bancario explícito.

No usa tolerancia para aplicar: importes de tarjeta leídos del original y hash
verificado. No identifica el patrimonio del vuelto/complemento ni crea aportes.
"""

import argparse
import hashlib
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

RULE = "condominio-diez-debitos-centavos-036"
OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"
# Total fiscal y cobro por Visa débito, revisados en el original, no inferidos.
TICKETS = {
    516: ("183.99", "184.00"), 562: ("178.91", "178.92"),
    604: ("255.51", "255.52"), 611: ("173.72", "173.73"),
    625: ("194.19", "194.18"), 715: ("230.13", "230.12"),
    725: ("202.54", "202.53"), 733: ("200.80", "200.78"),
    739: ("280.74", "280.73"), 752: ("230.02", "230.00"),
}


def run(apply=False):
    _assert_target_is_wc()
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        for identifier, (fiscal, bank) in TICKETS.items():
            p = read("SELECT [Importe imputado] importe,IdFormaPago medio FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?", (identifier,))[0]
            assert p == {"importe": Decimal(bank), "medio": 10}
            adjustment = read("SELECT Lado,Importe FROM dbo.AjustesCuentaCorriente WHERE Motivo LIKE ?", (f"036-CENT-P{identifier}:%",))
            delta = Decimal(bank) - Decimal(fiscal)
            assert adjustment == [{"Lado": "Deuda" if delta > 0 else "Credito", "Importe": abs(delta)}]
        return {"estado": "ya_aplicado_sin_escrituras"}
    evidence = json.loads((OUT / "diez-debitos-centavos-revision.json").read_text(encoding="utf-8"))
    originals = {x["pago"]: x for x in json.loads((OUT / "destinatarios/revision.json").read_text(encoding="utf-8"))}
    assert {x["pago"]["id"] for x in evidence} == set(TICKETS)
    bridges = read("SELECT * FROM dbo.MovimientosCajaEfectivo WHERE Concepto='Aporte Condominio LSC (pago directo)'")
    plans = []
    for e in evidence:
        identifier = e["pago"]["id"]
        fiscal, bank = (Decimal(x) for x in TICKETS[identifier])
        tx = e["evidencia"]
        assert Decimal(tx["importe"]) == bank and tx["debitoExplicito"] and tx["comercioCoincide"]
        assert 0 <= tx["dias"] <= 5
        for src in [originals[identifier], *tx["fuentes"]]:
            assert hashlib.sha256(Path(src["pdf"]).read_bytes()).hexdigest() == src["sha256"]
        p = read("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?", (identifier,))[0]
        assert p["Importe imputado"] == fiscal and p["IdFormaPago"] == 3 and p["Caja"] == "Condominio" and p["IdContacto"] == 30
        docs = read("SELECT c.*,t.ImporteDocumento FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento t ON t.IdDeuda=c.IdDeuda WHERE c.IdOperacion=?", (p["IdOperacion"],))
        assert len(docs) == 1 and round(docs[0]["ImporteDocumento"], 2) == fiscal
        assert not read("SELECT IdAplicacion FROM dbo.AplicacionesPago WHERE OrigenMovimiento='PagosEfectivo' AND IdMovimientoOrigen=? AND Anulada=0", (identifier,))
        assert not read("SELECT IdAjuste FROM dbo.AjustesCuentaCorriente WHERE Motivo LIKE ?", (f"036-CENT-P{identifier}:%",))
        legs = read("SELECT * FROM dbo.MovimientosCajaEfectivo WHERE IdPagoEfectivo=?", (identifier,))
        assert len(legs) == 1
        matches = [x for x in bridges if re.search(rf"egreso mov\. {legs[0]['IdMovimiento']}\)", x["Detalle"] or "")]
        assert len(matches) == 1 and matches[0]["Importe"] == -legs[0]["Importe"] == fiscal
        pair = legs + matches
        assert all(not x["Anulada"] and x["Caja"] == "GiamigliSA" and x["IdOperacionCaja"] is None for x in pair)
        delta = bank - fiscal
        label = "vuelto" if delta > 0 else "complemento Su pago"
        note = f"036-CENT-P{identifier}: FC{docs[0]['Nro Documento']} total{fiscal}; Visa HSBC{bank}; {label}{abs(delta)} documentado. Origen/destino patrimonial del componente no identificado; sin aporte nuevo."
        assert len(note) <= 255
        plans.append({"pago": p, "banco": tx, "original": originals[identifier], "compra": docs[0], "parCaja": pair, "importeBanco": bank, "componente": abs(delta), "lado": "Deuda" if delta > 0 else "Credito", "motivo": note})
    assert sum(x["importeBanco"] for x in plans) == Decimal("2130.51")
    result = {"estado": "inspeccion", "planes": plans}
    if not apply:
        return {"estado": "inspeccion", "pagos": 10, "banco": "2130.51", "ajustesDocumentales": 10, "filasCajaAAnular": 20}
    result["backup"] = backup_verificado("condominio_diez_centavos_036")
    log = OUT / f"diez-centavos-{datetime.now():%Y%m%d-%H%M%S}.json"
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()
            before, active_before = control(c), active(c)
            for plan in plans:
                p = plan["pago"]
                assert rows(c, "SELECT * FROM dbo.[Pagos efectivo] WITH (UPDLOCK,HOLDLOCK) WHERE IdPagoEfectivo=?", (p["IdPagoEfectivo"],))[0] == p
                assert not rows(c, "SELECT IdAplicacion FROM dbo.AplicacionesPago WITH (UPDLOCK,HOLDLOCK) WHERE OrigenMovimiento='PagosEfectivo' AND IdMovimientoOrigen=? AND Anulada=0", (p["IdPagoEfectivo"],))
                c.execute("UPDATE dbo.[Pagos efectivo] SET IdFormaPago=10,[Importe imputado]=? WHERE IdPagoEfectivo=?", plan["importeBanco"], p["IdPagoEfectivo"])
                c.execute("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) VALUES (30,?,?,?,?, 'Codex036')", p["Fecha"], plan["lado"], plan["componente"], plan["motivo"])
                for old in plan["parCaja"]:
                    assert rows(c, "SELECT * FROM dbo.MovimientosCajaEfectivo WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimiento=?", (old["IdMovimiento"],))[0] == old
                    note = (old["Detalle"] or "") + f" | Pago{p['IdPagoEfectivo']} vigente por HSBC; componente ticket aparte036."
                    assert len(note) <= 255
                    c.execute("UPDATE dbo.MovimientosCajaEfectivo SET Anulada=1,Detalle=? WHERE IdMovimiento=?", note, old["IdMovimiento"])
            after, active_after = control(c), active(c)
            assert before == after, "Cambió saldo/contacto/caja/socio o cantidad bruta."
            assert [(x["Caja"], x["saldo"]) for x in active_before] == [(x["Caja"], x["saldo"]) for x in active_after]
            assert sum(x["n"] for x in active_before) - sum(x["n"] for x in active_after) == 20
            result["controlAntes"], result["controlDespues"] = before, after
            c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps({"informe": str(log)}), result["backup"], "10 pagos HSBC exactos2130,51 y10 componentes de ticket;20 filas caja anuladas, saldos y socios intactos.")
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
