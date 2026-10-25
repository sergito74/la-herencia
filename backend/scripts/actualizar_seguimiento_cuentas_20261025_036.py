"""Actualiza notas de revisión AFIP/Criado con la evidencia de esta tanda.

Usa el servicio de fichas y su historial, sin cerrar cuentas ni cambiar dinero.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, reconciliation_transaction, execute_write_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.revision_cuentas import fichas
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _reconciliation_connection

RULE = "seguimiento-cuentas-20261025-036"
NOTAS = {
    119: "25/10/2026: incorporados 6 F931 (oct-dic2025 y jun-ago2026), $6.869.246,62, con originales. Cinco coinciden con pagos existentes. Dic2025: obligación $1.311.952,66 confirmada por PDF y aviso; Galicia2991 $1.548.334,45 es candidato sin conciliar (dif.$236.381,79). Saldo contable +$5.739.479,41, no crédito fiscal ARCA confirmado. Faltan otras obligaciones, planes, retenciones y estado ARCA; no cerrar ni aplicar FIFO global. Evidencia: continuacion-cuentas-20261025.md.",
    210: "Balance25-26: pendiente NC reclamada20/10 por $2.665.608,21 y débito eCheq125 $884.932,61 de octubre. Saldo -$3.550.540,34. Transferencia Galicia2104 $275.500 del16/09/2024 RESUELTA: inscripción Art.60 Directorio, DPPJ5668; no volver a cargar ni consultar. Consulta25/10: NC no hallada entre PDFs actuales ni correo reciente revisado. Estado esperando-evidencia; no registrar NC ni débito sin respaldo. Detalle: continuacion-cuentas-20261025.md.",
}


def run(aplicar=False):
    _assert_target_is_wc()
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    previo = read("SELECT * FROM dbo.RevisionFichas WHERE IdContacto IN (119,210) ORDER BY IdContacto")
    if not aplicar:
        return {"estado": "inspeccion", "notas": NOTAS}
    backup = backup_verificado("seguimiento_cuentas_20261025_036")
    path = Path(__file__).resolve().parents[2] / "backups/continuacion-cuentas-20261025" / f"seguimiento-{datetime.now():%Y%m%d-%H%M%S}.json"
    result = {"antes": previo, "notas": NOTAS, "backup": backup, "estado": "respaldado"}
    path.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    with reconciliation_transaction():
        c = _reconciliation_connection.get().cursor()
        if read("SELECT * FROM dbo.RevisionFichas WHERE IdContacto IN (119,210) ORDER BY IdContacto") != previo:
            raise ValueError("Otra persona cambió las fichas")
        before = control(c)
        for id_, nota in NOTAS.items():
            fichas.cambiar_estado(id_, {"estado": "esperando-evidencia", "nota": nota}, "Codex036")
        if control(c) != before:
            raise ValueError("Cambió un saldo al actualizar notas")
        result.update(estado="aplicado", despues=read("SELECT * FROM dbo.RevisionFichas WHERE IdContacto IN (119,210) ORDER BY IdContacto"))
        execute_write_transaction([(
            "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
            "VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
            (RULE, json.dumps(result, default=str, ensure_ascii=False), backup, "Seguimiento AFIP/Criado actualizado; sin cambios financieros ni cierres."),
        )])
    path.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"estado": "aplicado", "backup": backup, "snapshot": str(path)}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(p.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))
