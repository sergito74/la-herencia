"""Corrige dos enlaces documentales verificados visualmente; sin cambios contables."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts.corregir_easy_cooperativa_condominio_036 import rows
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import (
    _assert_target_is_wc,
    _reconciliation_connection,
    reconciliation_transaction,
)
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado

RULE = "condominio-enlaces-pdf-375-568-036"
OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"
FIXES = (
    (2143509653, "2904-00006359", "20132201_YPFNordelta.pdf", "20130122_YPFNordelta.pdf"),
    (2143510007, "2566-00184029", "20140314_EESSSaladillo.pdf", "20140404_EEESSaladillo.pdf"),
)


def run(apply=False):
    _assert_target_is_wc()
    changes = []
    for identifier, number, old_name, new_name in FIXES:
        row = read("SELECT * FROM dbo.Compras WHERE IdDeuda=?", (identifier,))[0]
        assert row["Nro Documento"] == number
        original = row["Documento Original"]
        source = Path(original.split("#")[0]).with_name(new_name)
        assert source.is_file()
        target = original.replace(old_name, new_name)
        changes.append({
            "antes": row, "nuevo": target, "pdf": str(source),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        })
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        assert all(x["antes"]["Documento Original"] == x["nuevo"] for x in changes)
        return {"estado": "ya_aplicado_sin_escrituras"}
    assert all(x["antes"]["Documento Original"] != x["nuevo"] for x in changes)
    if not apply:
        return {"estado": "inspeccion", "cambios": changes}
    result = {"cambios": changes, "backup": backup_verificado("condominio_enlaces_pdf_036")}
    log = OUT / f"enlaces-pdf-{datetime.now():%Y%m%d-%H%M%S}.json"
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        with reconciliation_transaction():
            cursor = _reconciliation_connection.get().cursor()
            before = control(cursor)
            for change in changes:
                old = change["antes"]
                current = rows(cursor, "SELECT * FROM dbo.Compras WITH (UPDLOCK,HOLDLOCK) WHERE IdDeuda=?", (old["IdDeuda"],))[0]
                assert current == old
                cursor.execute("UPDATE dbo.Compras SET [Documento Original]=? WHERE IdDeuda=?", change["nuevo"], old["IdDeuda"])
                after = rows(cursor, "SELECT * FROM dbo.Compras WHERE IdDeuda=?", (old["IdDeuda"],))[0]
                # SQL Server cambia su marca de versión automáticamente al actualizar.
                expected = {**old, "Documento Original": change["nuevo"]}
                assert {k: v for k, v in after.items() if k != "SSMA_TimeStamp"} == {
                    k: v for k, v in expected.items() if k != "SSMA_TimeStamp"
                }
            assert before == control(cursor)
            cursor.execute(
                "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
                RULE, json.dumps({"informe": str(log)}), result["backup"],
                "Solo enlaces PDF de compras vinculadas a pagos375/568. Sin cambios financieros.",
            )
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
