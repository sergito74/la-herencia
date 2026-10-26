"""Aplicar devolución en 20 certificados de retención de IVA Granos (Cargill 2020-2022).
Suma total de devolución: $558.997,32 (igual a su importe retenido).
Respaldo verificado, transacción, auditoría e invariantes.
"""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import _assert_target_is_wc, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT = Path(__file__).resolve().parents[2]
EVIDENCIA = ROOT / "backups/arca-continuacion-20261025"
REGLA = "arca-iva-devoluciones-cargill-20-036"
USUARIO = "Gemini036"

IDS_RETENCION = [
    291, 292, 293, 294, 295, 296, 297, 299, 301, 302,
    303, 304, 305, 306, 307, 308, 309, 310, 311, 312,
]


def run(aplicar: bool = False):
    _assert_target_is_wc()
    EVIDENCIA.mkdir(parents=True, exist_ok=True)

    certs = read(
        f"SELECT rig.IdRetencion, rig.IdLiquidacion, rig.[Nro Certificado], rig.[Importe Retenido] "
        f"FROM dbo.[Retenciones IVA Granos] rig WHERE rig.IdRetencion IN ({','.join(str(i) for i in IDS_RETENCION)}) "
        f"ORDER BY rig.IdRetencion"
    )
    if len(certs) != len(IDS_RETENCION):
        raise ValueError(f"Esperados {len(IDS_RETENCION)} certificados, hallados {len(certs)}")

    total_devolucion = sum(D(str(c["Importe Retenido"])) for c in certs)
    if total_devolucion != D("558997.32"):
        raise ValueError(f"Suma esperada 558997.32, hallada {total_devolucion}")

    plan = {
        "regla": REGLA,
        "usuario": USUARIO,
        "cantidad": len(certs),
        "total": total_devolucion,
        "certificados": [
            {
                "idRetencion": c["IdRetencion"],
                "idLiquidacion": c["IdLiquidacion"],
                "nroCertificado": c["Nro Certificado"],
                "importe": str(c["Importe Retenido"]),
            }
            for c in certs
        ],
    }

    if not aplicar:
        (EVIDENCIA / "iva-cargill-20-plan.json").write_text(
            json.dumps(plan, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"estado": "inspeccion", "plan": plan}

    respaldo = backup_verificado("arca_iva_devoluciones_cargill_036")

    with reconciliation_transaction():
        from src.db.connection import _reconciliation_connection
        cur = _reconciliation_connection.get().cursor()
        before = control(cur)

        for c in certs:
            cur.execute(
                "UPDATE dbo.[Retenciones IVA Granos] SET [Importe Devolucion] = [Importe Retenido] WHERE IdRetencion = ?",
                c["IdRetencion"],
            )

        after = control(cur)

        # Invariantes:
        # Cajas y socios no cambian en nada
        if before["cajas"] != after["cajas"]:
            raise ValueError("Cambió una caja de efectivo")
        if before["socios"] != after["socios"]:
            raise ValueError("Cambió una cuenta de socio")

        # Cuentas de proveedores: únicamente la cuenta 119 aumenta su crédito en +558.997,32
        esperado_cuentas = dict(before["cuentas"])
        esperado_cuentas[119] = esperado_cuentas[119] + total_devolucion
        if dict(after["cuentas"]) != esperado_cuentas:
            raise ValueError(
                f"Cambio inesperado en cuentas: esperado 119={esperado_cuentas[119]}, actual={dict(after['cuentas'])[119]}"
            )

        resultado = {
            "estado": "aplicado",
            "respaldo": respaldo,
            "cantidad": len(certs),
            "totalDevolucion": total_devolucion,
            "saldoAntes119": dict(before["cuentas"])[119],
            "saldoDespues119": dict(after["cuentas"])[119],
        }

        cur.execute(
            "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
            "VALUES (?,'aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
            REGLA,
            json.dumps(resultado, default=str, ensure_ascii=False),
            USUARIO,
            USUARIO,
            respaldo,
            f"IVA Granos: 20 certificados Cargill (2020-2022) con devolución aplicada por {total_devolucion}.",
        )

    (EVIDENCIA / "iva-cargill-20-aplicado.json").write_text(
        json.dumps(resultado, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))

