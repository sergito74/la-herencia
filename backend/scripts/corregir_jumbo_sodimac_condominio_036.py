"""Originales y pago Jumbo respaldado en HSBC. Sin pagos nuevos ni ajuste de cierre."""

import argparse
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from scripts.corregir_easy_cooperativa_condominio_036 import rows
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection
from src.db.connection import reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado

OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"
RULE = "condominio-originales-jumbo-sodimac-036"
JUMBO, SODIMAC = 1892320260, -575570518


def state(q):
    return {
        "compras": q("SELECT * FROM dbo.Compras WHERE IdDeuda IN (?,?)", (JUMBO, SODIMAC)),
        "detalle": q(
            "SELECT * FROM dbo.Det_Compras WHERE IdCompra IN (?,?) ORDER BY IdDetalleCompra",
            (JUMBO, SODIMAC),
        ),
        "totales": q(
            "SELECT IdDeuda,ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda IN (?,?)",
            (JUMBO, SODIMAC),
        ),
        "pago": q("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo IN (31,88)"),
        "fichas": q("SELECT * FROM dbo.RevisionFichas WHERE IdContacto IN (60,91)"),
    }


def run(aplicar=False):
    _assert_target_is_wc()
    before = state(read)
    totals = {r["IdDeuda"]: round(r["ImporteDocumento"], 2) for r in before["totales"]}
    if read(
        "SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)
    ):
        assert totals == {JUMBO: Decimal("511.79"), SODIMAC: Decimal("624.29")}
        return {"estado": "ya_aplicado_sin_escrituras"}
    assert totals == {JUMBO: Decimal("355.99"), SODIMAC: Decimal("571.92")}
    assert len(before["detalle"]) == 4
    assert {r["IdPagoEfectivo"]: r["Importe imputado"] for r in before["pago"]} == {
        31: Decimal("356"),
        88: Decimal("571.92"),
    }
    # Reproduce el bloque del resumen incluyendo continuación entre páginas.
    coverage = json.loads((OUT / "puentes-68-hsbc-verificado.json").read_text(encoding="utf-8"))[
        "cobertura"
    ]
    bank = []
    for src in coverage:
        text = Path(src["extraido"]).read_text(encoding="utf-8")
        lines = text.splitlines()
        current, page = None, None
        for i, line in enumerate(lines):
            if line.startswith("PAGINA "):
                page = int(line.split()[1])
            if re.match(r"\d\d-[A-Z]{3}", line):
                current = line[:6]
            if "- COMPRA 46885 511.79" not in line:
                continue
            assert current == "12-DIC" and "2011" in src["pdf"]
            block = "\n".join(lines[i : i + 12])
            assert "OPERACION: 246885" in block and "JUMBO PACHECO" in block
            assert "TARJETA DE DEBITO" in block
            assert hashlib.sha256(Path(src["pdf"]).read_bytes()).hexdigest() == src["sha256"]
            bank.append({**src, "pagina": page, "operacion": "246885", "fecha": "2011-12-12"})
    assert bank, "Falta respaldo bancario Jumbo"
    sources = []
    for c in before["compras"]:
        p = Path(c["Documento Original"].split("#")[0])
        sources.append({"pdf": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    leg = read("SELECT * FROM dbo.MovimientosCajaEfectivo WHERE IdPagoEfectivo=31")
    assert len(leg) == 1
    bridges = read(
        "SELECT * FROM dbo.MovimientosCajaEfectivo WHERE Concepto='Aporte Condominio LSC (pago directo)'"
    )
    bridge = [
        b for b in bridges if f"egreso mov. {leg[0]['IdMovimiento']})" in (b["Detalle"] or "")
    ]
    assert len(bridge) == 1 and bridge[0]["Importe"] == -leg[0]["Importe"] == Decimal("356")
    pair = leg + bridge
    assert all(not x["Anulada"] and x["IdOperacionCaja"] is None for x in pair)
    result = {
        "estado": "inspeccion",
        "antes": before,
        "parCaja": pair,
        "bancoJumbo": bank,
        "fuentes": sources,
    }
    if not aplicar:
        return {
            "estado": "inspeccion",
            "objetivo": "Jumbo511.79 factura y pago; Sodimac624.29 solo factura",
        }
    result["backupVerificado"] = backup_verificado("condominio_jumbo_sodimac_036")
    log = OUT / f"jumbo-sodimac-{datetime.now():%Y%m%d-%H%M%S}.json"

    def save():
        log.write_text(
            json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    save()
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()

            def q(sql, params=()):
                return rows(c, sql, params)

            assert state(q) == before
            control_before = control(c)
            # Clasificación de los renglones de la propia factura, General/No Aplica.
            fields = "IdCompra,Cantidad,[Producto/Servicio],IdFormulado,IdCentroCostos,IdDestino,IdRubro,[IdCampaña],Campaña,[Precio Unitario],IVA,[Ajuste financiero]"
            extras = [
                ("Mantecol", 1, 16.36, 21),
                ("Turron Georgalos", 1, 11.49, 21),
                ("Turron Arcor", 1, 4.13, 21),
                ("Mani Arcor", 1, 6.78, 21),
                ("Budin Bagley", 2, 9.75, 21),
                ("Pan Arcor", 1, 16.52, 21),
                ("Sidra Real neto5 unidades", 5, 9.082, 21),
                ("Ajuste IVA del ticket", 1, 0.01, 0),
            ]
            for name, qty, price, iva in extras:
                c.execute(
                    f"INSERT INTO dbo.Det_Compras ({fields}) SELECT IdCompra,?,?,IdFormulado,"
                    "IdCentroCostos,IdDestino,IdRubro,[IdCampaña],Campaña,?,?,0 "
                    "FROM dbo.Det_Compras WHERE IdDetalleCompra=1416796626",
                    qty,
                    name,
                    price,
                    iva,
                )
            c.execute("UPDATE dbo.Compras SET [Ingresos Brutos]=10.36 WHERE IdDeuda=?", JUMBO)
            c.execute(
                f"INSERT INTO dbo.Det_Compras ({fields}) SELECT IdCompra,2,'C TUBO según ticket',"
                "IdFormulado,IdCentroCostos,IdDestino,IdRubro,[IdCampaña],Campaña,20.62,21,0 "
                "FROM dbo.Det_Compras WHERE IdDetalleCompra=127521507"
            )
            c.execute("UPDATE dbo.Compras SET [Ingresos Brutos]=29.49 WHERE IdDeuda=?", SODIMAC)
            c.execute(
                "UPDATE dbo.[Pagos efectivo] SET IdFormaPago=10,[Importe imputado]=511.79 WHERE IdPagoEfectivo=31"
            )
            for old in pair:
                assert (
                    q(
                        "SELECT * FROM dbo.MovimientosCajaEfectivo WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimiento=?",
                        (old["IdMovimiento"],),
                    )[0]
                    == old
                )
                note = (
                    old["Detalle"] or ""
                ) + " | Pago31 vigente: HSBC511.79; reclasificacion documental036."
                assert len(note) <= 255
                c.execute(
                    "UPDATE dbo.MovimientosCajaEfectivo SET Anulada=1,Detalle=? WHERE IdMovimiento=?",
                    note,
                    old["IdMovimiento"],
                )
            c.execute(
                "UPDATE dbo.RevisionFichas SET Estado='esperando-evidencia',Nota=CONCAT(Nota,?),"
                "UsuarioActualiza='Codex036',FechaActualiza=SYSDATETIME() WHERE IdContacto IN (60,91)",
                " | 24/10/2026 revisión puntual Condominio: originales Jumbo511.79/Sodimac624.29. "
                "Jumbo débito HSBC comprobado; falta titular/resumen Sodimac. No es deuda externa nueva.",
            )
            after = state(q)
            assert {r["IdDeuda"]: round(r["ImporteDocumento"], 2) for r in after["totales"]} == {
                JUMBO: Decimal("511.79"),
                SODIMAC: Decimal("624.29"),
            }
            control_after = control(c)
            assert control_before["cajas"] == control_after["cajas"]
            assert control_before["socios"] == control_after["socios"]
            old_cc = dict(control_before["cuentas"])
            new_cc = dict(control_after["cuentas"])
            assert {k: v for k, v in old_cc.items() if k not in (60, 91)} == {
                k: v for k, v in new_cc.items() if k not in (60, 91)
            }
            olds = {r["IdDeuda"]: r["ImporteDocumento"] for r in before["totales"]}
            news = {r["IdDeuda"]: r["ImporteDocumento"] for r in after["totales"]}
            assert new_cc[60] - old_cc[60] == Decimal("155.79") - (news[JUMBO] - olds[JUMBO])
            assert new_cc[91] - old_cc[91] == olds[SODIMAC] - news[SODIMAC]
            assert next(r for r in after["pago"] if r["IdPagoEfectivo"] == 88) == next(
                r for r in before["pago"] if r["IdPagoEfectivo"] == 88
            )
            result.update(
                despues=after, controlesAntes=control_before, controlesDespues=control_after
            )
            c.execute(
                "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,"
                "FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),"
                "'Codex036',SYSDATETIME(),?,?)",
                RULE,
                json.dumps({"informe": str(log)}),
                result["backupVerificado"],
                "Originales Jumbo/Sodimac; pago31 igual a HSBC511.79. Sin pago nuevo ni socio.",
            )
        result["estado"] = "aplicado"
    except Exception as exc:
        result.update(estado="revertido", error=str(exc))
        save()
        raise
    save()
    return {"estado": result["estado"], "informe": str(log), "backup": result["backupVerificado"]}


def reclasificar_tarjeta(aplicar=False):
    from scripts.rastrear_15_pagos_condominio_036 import LSC, workbook, fingerprint

    _assert_target_is_wc()
    rule = "condominio-sodimac88-tarjeta-036"
    if read(
        "SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (rule,)
    ):
        return {"estado": "ya_aplicado_sin_escrituras"}
    source = LSC / "Movimientos LSC.xlsx"
    row = workbook(source, "Movs")[354]
    assert str(row[0])[:10] == "2012-02-29" and row[5] == "TJC"
    assert row[4] == "Compra Giamigli" and Decimal(str(row[8])) == Decimal("571.92")
    assert "Sodimac" in row[2]
    p = read("SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=88")[0]
    assert p["IdFormaPago"] == 3 and p["Caja"] == "Condominio"
    assert p["Importe imputado"] == Decimal("571.92") and p["IdOperacion"] == 265
    leg = read("SELECT * FROM dbo.MovimientosCajaEfectivo WHERE IdPagoEfectivo=88")
    assert len(leg) == 1
    bridges = read(
        "SELECT * FROM dbo.MovimientosCajaEfectivo WHERE Concepto='Aporte Condominio LSC (pago directo)'"
    )
    bridge = [
        b for b in bridges if f"egreso mov. {leg[0]['IdMovimiento']})" in (b["Detalle"] or "")
    ]
    assert len(bridge) == 1 and bridge[0]["Importe"] == -leg[0]["Importe"] == Decimal("571.92")
    pair = leg + bridge
    assert all(not x["Anulada"] and x["IdOperacionCaja"] is None for x in pair)
    result = {
        "estado": "inspeccion",
        "pagoAntes": p,
        "cajaAntes": pair,
        "fuente": fingerprint(source),
        "fila": 355,
        "nota": "Movs TJC y original Tarjeta Bancaria; titular/resumen pendientes. No aumentar pago.",
    }
    if not aplicar:
        return {"estado": "inspeccion_tarjeta", "pago": 88, "medioNuevo": 20}
    result["backupVerificado"] = backup_verificado("condominio_sodimac_tarjeta_036")
    log = OUT / f"sodimac-tarjeta-{datetime.now():%Y%m%d-%H%M%S}.json"
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()
            before = control(c)
            assert (
                rows(
                    c,
                    "SELECT * FROM dbo.[Pagos efectivo] WITH (UPDLOCK,HOLDLOCK) WHERE IdPagoEfectivo=88",
                )[0]
                == p
            )
            c.execute("UPDATE dbo.[Pagos efectivo] SET IdFormaPago=20 WHERE IdPagoEfectivo=88")
            for old in pair:
                assert (
                    rows(
                        c,
                        "SELECT * FROM dbo.MovimientosCajaEfectivo WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimiento=?",
                        (old["IdMovimiento"],),
                    )[0]
                    == old
                )
                note = (
                    old["Detalle"] or ""
                ) + " | Pago88 vigente por tarjeta; original y Movs355 TJC; reclasificacion036."
                assert len(note) <= 255
                c.execute(
                    "UPDATE dbo.MovimientosCajaEfectivo SET Anulada=1,Detalle=? WHERE IdMovimiento=?",
                    note,
                    old["IdMovimiento"],
                )
            assert before == control(c)
            c.execute(
                "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,"
                "FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),"
                "'Codex036',SYSDATETIME(),?,?)",
                rule,
                json.dumps({"informe": str(log)}),
                result["backupVerificado"],
                "Sodimac88: medio3 a20; par ficticio de caja anulado, pago571.92 y saldos intactos.",
            )
        result["estado"] = "aplicado"
    except Exception as exc:
        result.update(estado="revertido", error=str(exc))
        log.write_text(
            json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        raise
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"estado": "aplicado", "informe": str(log), "backup": result["backupVerificado"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--reclasificar-tarjeta", action="store_true")
    args = parser.parse_args()
    action = reclasificar_tarjeta if args.reclasificar_tarjeta else run
    print(json.dumps(action(args.aplicar), default=str, ensure_ascii=False))
