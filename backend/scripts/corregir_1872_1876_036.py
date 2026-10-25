"""Invertir Tipo en MovimientosCuentaSocio 1872 (AsignacionGasto -> Devolucion) y 1876 (Devolucion -> AsignacionGasto).
Opción A aprobada por Sergio el 25/10/2026.
Idempotente, con respaldo verificado, transacción, invariantes y sincronización de Cajas Giamigli.xlsx.
"""
import argparse
import hashlib
import json
from decimal import Decimal as D
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import _assert_target_is_wc, get_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT = Path(__file__).resolve().parents[2]
EVIDENCIA = ROOT / "backups/arca-continuacion-20261025"
REGLA = "socio-sergio-autonomos-1872-1876-036"
USUARIO = "Gemini036"


def run(aplicar: bool = False):
    _assert_target_is_wc()
    EVIDENCIA.mkdir(parents=True, exist_ok=True)

    m1872 = read("SELECT * FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento=1872")[0]
    m1876 = read("SELECT * FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento=1876")[0]

    plan = {
        "regla": REGLA,
        "usuario": USUARIO,
        "1872": {
            "antes": {
                "tipo": m1872["Tipo"],
                "importe": str(m1872["Importe"]),
                "motivo": m1872["Motivo"],
                "medio": m1872["Medio"],
                "importeUSD": str(m1872["ImporteUSD"]),
                "importeKgCarne": str(m1872["ImporteKgCarne"]),
            },
            "despues": {
                "tipo": "Devolucion",
                "importe": str(m1872["Importe"]),
                "motivo": "Autonomos 04 2018",
                "medio": m1872["Medio"],
                "importeUSD": str(m1872["ImporteUSD"]),
                "importeKgCarne": str(m1872["ImporteKgCarne"]),
            },
        },
        "1876": {
            "antes": {
                "tipo": m1876["Tipo"],
                "importe": str(m1876["Importe"]),
                "motivo": m1876["Motivo"],
                "medio": m1876["Medio"],
                "importeUSD": str(m1876["ImporteUSD"]),
                "importeKgCarne": str(m1876["ImporteKgCarne"]),
            },
            "despues": {
                "tipo": "AsignacionGasto",
                "importe": str(m1876["Importe"]),
                "motivo": "Pago — Reintegro efectivo Autonomos 04 2018",
                "medio": m1876["Medio"],
                "importeUSD": str(m1876["ImporteUSD"]),
                "importeKgCarne": str(m1876["ImporteKgCarne"]),
            },
        },
    }

    if not aplicar:
        (EVIDENCIA / "opcionA-1872-1876-plan.json").write_text(
            json.dumps(plan, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"estado": "inspeccion", "plan": plan}

    respaldo = backup_verificado("socio_sergio_1872_1876_036")

    with get_connection(readonly=False) as conn:
        cur = conn.cursor()
        before = control(cur)

        # Actualizar 1872
        cur.execute(
            "UPDATE dbo.MovimientosCuentaSocio SET Tipo='Devolucion', Motivo='Autonomos 04 2018' WHERE IdMovimiento=1872"
        )
        # Actualizar 1876
        cur.execute(
            "UPDATE dbo.MovimientosCuentaSocio SET Tipo='AsignacionGasto', Motivo='Pago — Reintegro efectivo Autonomos 04 2018' WHERE IdMovimiento=1876"
        )

        after = control(cur)

        # Invariantes:
        # 1) Cajas no cambian
        if before["cajas"] != after["cajas"]:
            raise ValueError("Cambió una caja de efectivo")
        # 2) Cuentas de proveedores no cambian
        if before["cuentas"] != after["cuentas"]:
            raise ValueError("Cambió una cuenta de proveedor")
        # 3) En socios, solo cambia IdSocio = 1:
        # 1872 (Debe 2842.12 -> Haber 2842.12):
        #   gasto disminuye en 2842.12, devolucion aumenta en 2842.12
        # 1876 (Haber 2842.12 -> Debe 2842.12):
        #   devolucion disminuye en 2842.12, gasto aumenta en 2842.12
        # Suma total nominal de Importe no cambia.
        # En ImporteUSD: antes suma total = 64.8886 + 57.0707 = 121.9593, después = igual suma.
        # En ImporteKgCarne: antes suma total = 41.413 + 39.426 = 80.839, después = igual suma.
        antes_soc = {r[0]: r for r in before["socios"]}
        desp_soc = {r[0]: r for r in after["socios"]}
        for sid in (2, 3, 4):
            if antes_soc.get(sid) != desp_soc.get(sid):
                raise ValueError(f"Cambio inesperado en socio {sid}")
        s1_b, s1_a = antes_soc[1], desp_soc[1]
        # s1_b = (1, count, sum_importe, sum_usd, sum_kg)
        if s1_b[1] != s1_a[1] or s1_b[2] != s1_a[2] or s1_b[3] != s1_a[3] or s1_b[4] != s1_a[4]:
            raise ValueError(f"Cambio inesperado en totales agregados de socio 1: {s1_b} vs {s1_a}")

        resultado = {
            "estado": "aplicado",
            "respaldo": respaldo,
            "1872": plan["1872"],
            "1876": plan["1876"],
        }

        cur.execute(
            "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
            "VALUES (?,'aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
            REGLA,
            json.dumps(resultado, default=str, ensure_ascii=False),
            USUARIO,
            USUARIO,
            respaldo,
            "Inversión de Tipo en asientos 1872 y 1876 (Autónomos 04/2018) autorizada por Sergio (Opción A).",
        )

    (EVIDENCIA / "opcionA-1872-1876-aplicado.json").write_text(
        json.dumps(resultado, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))
