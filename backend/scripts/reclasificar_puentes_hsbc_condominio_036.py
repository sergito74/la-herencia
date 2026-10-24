"""Corrige medio de48 pagos y retira96 representaciones ficticias de efectivo.

--preparar genera insumos de solo lectura. Inspección por defecto.
--aplicar requiere evidencia del extractor HSBC, respaldo y transacción validada.
"""

import argparse
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from scripts.corregir_easy_cooperativa_condominio_036 import rows
from scripts.matriz_financiacion_condominio_036 import run as matrix
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection
from src.db.connection import reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado

OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"
RULE = "condominio-48-debitos-pares-caja-036"


def preparar():
    report = matrix()
    ids = [
        p
        for r in report["operaciones"]
        if r["tipo"]
        in (
            "puente_caja_pendiente_validar_origen",
            "debito_bancario_documentado",
            "tarjeta_documentada",
        )
        for p in r["pagos"]
    ]
    assert len(ids) == len(set(ids)) == 68
    marks = ",".join("?" for _ in ids)
    payments = read(
        "SELECT p.IdPagoEfectivo id,p.Fecha fecha,p.[Importe imputado] importe,"
        "p.IdFormaPago medio,p.IdContacto contacto,p.IdOperacion operacion,c.[Razon Social] nombre "
        "FROM dbo.[Pagos efectivo] p LEFT JOIN dbo.Contactos c ON c.IdContacto=p.IdContacto "
        f"WHERE p.IdPagoEfectivo IN ({marks}) ORDER BY p.Fecha,p.IdPagoEfectivo",
        tuple(ids),
    )
    operations = [p["operacion"] for p in payments]
    documents = read(
        "SELECT IdDeuda,IdContacto,Fecha,IdOperacion,[Nro Documento] numero,"
        f"[Documento Original] pdf FROM dbo.Compras WHERE IdOperacion IN ({marks})",
        tuple(operations),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in (
        ("puentes-68-pagos.json", payments),
        ("puentes-68-documentos.json", documents),
    ):
        (OUT / name).write_text(
            json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return {
        "estado": "preparado_solo_lectura",
        "pagos": len(payments),
        "documentos": len(documents),
    }


def active(c):
    return rows(
        c,
        "SELECT Caja,COUNT_BIG(*) n,SUM(Importe) saldo FROM "
        "dbo.vw_MovimientosCajaEfectivoOperativos WHERE Anulada=0 GROUP BY Caja ORDER BY Caja",
    )


def run(aplicar=False):
    _assert_target_is_wc()
    if read(
        "SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)
    ):
        return {"estado": "ya_aplicado_sin_escrituras"}
    evidence_path = OUT / "puentes-68-hsbc-verificado.json"
    report = json.loads(evidence_path.read_text(encoding="utf-8"))
    good = [r for r in report["matriz"] if r["estado"] == "debito_comercio_unico"]
    assert len(good) == 48
    assert sum(Decimal(r["pago"]["importe"]) for r in good) == Decimal("10318.06")
    bridges = read(
        "SELECT * FROM dbo.MovimientosCajaEfectivo WHERE "
        "Concepto='Aporte Condominio LSC (pago directo)'"
    )
    plans = []
    for r in good:
        p = read("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=?", (r["pago"]["id"],))[0]
        assert p["IdFormaPago"] == 3 and p["Caja"] == "Condominio"
        assert p["Importe imputado"] == Decimal(r["pago"]["importe"])
        assert str(p["Fecha"])[:10] == r["pago"]["fecha"][:10]
        assert r["evidencia"]["debitoExplicito"] and r["evidencia"]["comercioCoincide"]
        assert 0 <= r["evidencia"]["dias"] <= 5
        for src in r["evidencia"]["fuentes"]:
            assert hashlib.sha256(Path(src["pdf"]).read_bytes()).hexdigest() == src["sha256"]
        legs = read(
            "SELECT * FROM dbo.MovimientosCajaEfectivo WHERE IdPagoEfectivo=?",
            (p["IdPagoEfectivo"],),
        )
        assert len(legs) == 1
        leg = legs[0]
        matches = [
            b
            for b in bridges
            if re.search(rf"egreso mov\. {leg['IdMovimiento']}\)", b["Detalle"] or "")
        ]
        assert len(matches) == 1
        bridge = matches[0]
        assert bridge["Importe"] == -leg["Importe"] == p["Importe imputado"]
        for item in (leg, bridge):
            assert item["Caja"] == "GiamigliSA" and not item["Anulada"]
            assert item["IdOperacionCaja"] is None
        plans.append({"pago": p, "egreso": leg, "puente": bridge, "banco": r["evidencia"]})
    assert len({x[k]["IdMovimiento"] for x in plans for k in ("egreso", "puente")}) == 96
    result = {"estado": "inspeccion", "planes": plans, "evidencia": str(evidence_path)}
    if not aplicar:
        return {
            "estado": "inspeccion",
            "pagos": len(plans),
            "importe": "10318.06",
            "renglonesCaja": 96,
        }
    result["backupVerificado"] = backup_verificado("condominio_48_debitos_036")
    log = OUT / f"reclasificacion-48-{datetime.now():%Y%m%d-%H%M%S}.json"

    def save():
        log.write_text(
            json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    save()
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()
            before, active_before = control(c), active(c)
            for item in plans:
                p = item["pago"]
                assert (
                    rows(
                        c,
                        "SELECT * FROM dbo.[Pagos efectivo] WITH (UPDLOCK,HOLDLOCK) "
                        "WHERE IdPagoEfectivo=?",
                        (p["IdPagoEfectivo"],),
                    )[0]
                    == p
                )
                c.execute(
                    "UPDATE dbo.[Pagos efectivo] SET IdFormaPago=10 WHERE IdPagoEfectivo=?",
                    p["IdPagoEfectivo"],
                )
                for kind in ("egreso", "puente"):
                    old = item[kind]
                    assert (
                        rows(
                            c,
                            "SELECT * FROM dbo.MovimientosCajaEfectivo WITH (UPDLOCK,HOLDLOCK) "
                            "WHERE IdMovimiento=?",
                            (old["IdMovimiento"],),
                        )[0]
                        == old
                    )
                    note = (
                        old["Detalle"] or ""
                    ) + f" | Debito HSBC; pago{p['IdPagoEfectivo']} vigente; reclasificacion036."
                    assert len(note) <= 255
                    c.execute(
                        "UPDATE dbo.MovimientosCajaEfectivo SET Anulada=1,Detalle=? WHERE IdMovimiento=?",
                        note,
                        old["IdMovimiento"],
                    )
            after, active_after = control(c), active(c)
            assert before == after, "Cambió algún saldo, cantidad bruta o socio"
            assert [(x["Caja"], x["saldo"]) for x in active_before] == [
                (x["Caja"], x["saldo"]) for x in active_after
            ]
            counts_before = {r["Caja"]: r["n"] for r in active_before}
            counts_after = {r["Caja"]: r["n"] for r in active_after}
            assert counts_after == {
                k: v - (96 if k == "GiamigliSA" else 0) for k, v in counts_before.items()
            }
            result.update(
                controlesAntes=before,
                controlesDespues=after,
                cajaActivaAntes=active_before,
                cajaActivaDespues=active_after,
            )
            c.execute(
                "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,"
                "UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,"
                "'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
                RULE,
                json.dumps(
                    {"informe": str(log), "pagos": [x["pago"]["IdPagoEfectivo"] for x in plans]}
                ),
                result["backupVerificado"],
                "48 pagos debitados HSBC; medio3 a10. 96 filas caja anuladas con historia; saldos y socios intactos.",
            )
        result["estado"] = "aplicado"
    except Exception as exc:
        result.update(estado="revertido", error=str(exc))
        save()
        raise
    save()
    return {"estado": result["estado"], "informe": str(log), "backup": result["backupVerificado"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preparar", action="store_true")
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    if args.preparar and args.aplicar:
        parser.error("Preparar y aplicar son fases separadas")
    print(
        json.dumps(
            preparar() if args.preparar else run(args.aplicar), default=str, ensure_ascii=False
        )
    )
