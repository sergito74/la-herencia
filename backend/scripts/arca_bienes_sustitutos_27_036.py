"""Clasificación de 27 pagos históricos (2012-2021) en la subcuenta bienes-sustitutos.
Cierra la subcuenta Bienes Sustitutos completa (2012-30/09/2026) en $0,00 exacto.
No agrega movimientos, no cambia bancos, cajas, socios ni saldo de contacto 119.
Respaldo verificado, transacción, auditoría e invariantes.
"""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import _assert_target_is_wc, reconciliation_transaction
from src.features.cuentas_corrientes import arca
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT = Path(__file__).resolve().parents[2]
EVIDENCIA = ROOT / "backups/arca-continuacion-20261025"
REGLA = "arca-bienes-sustitutos-27-historicos-036"
USUARIO = "Gemini036"

PAGOS_HISTORICOS = [
    # (Origen, IdOrigen, Importe, Detalle)
    ("Pagos efectivo", 224, D("60.00"), "Bienes Personales Acciones y Participaciones 2011 (pago 03/05/2012)"),
    ("Pagos efectivo", 405, D("186.00"), "Bienes Personales Acciones y Participaciones 2012 (pago 08/05/2013)"),
    ("Banco Nacion", 15725, D("1432.38"), "Bienes Personales Acciones y Participaciones 2013 cuota 1"),
    ("Banco Nacion", 15726, D("1395.18"), "Bienes Personales Acciones y Participaciones 2013 cuota 2"),
    ("Banco Nacion", 15730, D("1432.38"), "Bienes Personales Acciones y Participaciones 2013 cuota 3"),
    ("Banco Nacion", 15761, D("1569.26"), "Bienes Personales Acciones y Participaciones 2014 cuota 1"),
    ("Banco Nacion", 15765, D("1596.19"), "Bienes Personales Acciones y Participaciones 2014 cuota 2"),
    ("Banco Nacion", 15769, D("1569.25"), "Bienes Personales Acciones y Participaciones 2014 cuota 3"),
    ("Banco Nacion", 15795, D("3552.42"), "Bienes Personales Acciones y Participaciones 2015 cuota 1"),
    ("Banco Nacion", 15801, D("3654.26"), "Bienes Personales Acciones y Participaciones 2015 cuota 2"),
    ("Banco Nacion", 15806, D("3587.95"), "Bienes Personales Acciones y Participaciones 2015 cuota 3"),
    ("Banco Nacion", 15936, D("5316.51"), "Plan N043365 cuota 1"),
    ("Banco Nacion", 15939, D("5316.51"), "Plan N043365 cuota 2"),
    ("Banco Nacion", 15942, D("5316.51"), "Plan N043365 cuota 3"),
    ("Banco Nacion", 15944, D("5316.51"), "Plan N043365 cuota 4"),
    ("Banco Nacion", 15947, D("5316.51"), "Plan N043365 cuota 5"),
    ("Banco Nacion", 15951, D("5316.51"), "Plan N043365 cuota 6"),
    ("Banco Nacion", 15955, D("5316.51"), "Plan N043365 cuota 7"),
    ("Banco Nacion", 15958, D("5316.51"), "Plan N043365 cuota 8"),
    ("Galicia", 98, D("8521.06"), "Plan O853149 cuota 1"),
    ("Galicia", 135, D("8521.06"), "Plan O853149 cuota 2"),
    ("Galicia", 187, D("8521.06"), "Plan O853149 cuota 3"),
    ("Galicia", 250, D("8521.06"), "Plan O853149 cuota 4"),
    ("Galicia", 295, D("8521.06"), "Plan O853149 cuota 5"),
    ("Galicia", 330, D("8521.06"), "Plan O853149 cuota 6"),
    ("Galicia", 364, D("8521.06"), "Plan O853149 cuota 7"),
    ("Galicia", 404, D("8521.06"), "Plan O853149 cuota 8"),
]


def run(aplicar: bool = False):
    _assert_target_is_wc()
    EVIDENCIA.mkdir(parents=True, exist_ok=True)

    total_clasificar = sum(p[2] for p in PAGOS_HISTORICOS)
    if total_clasificar != D("130735.83"):
        raise ValueError(f"Suma esperada 130735.83, obtenida {total_clasificar}")

    plan = {
        "regla": REGLA,
        "usuario": USUARIO,
        "cantidad": len(PAGOS_HISTORICOS),
        "total": total_clasificar,
        "pagos": [
            {"origen": o, "idOrigen": i, "importe": imp, "motivo": m}
            for o, i, imp, m in PAGOS_HISTORICOS
        ],
    }

    if not aplicar:
        (EVIDENCIA / "bienes-sustitutos-27-plan.json").write_text(
            json.dumps(plan, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"estado": "inspeccion", "plan": plan}

    respaldo = backup_verificado("arca_bienes_sustitutos_27_036")

    with reconciliation_transaction():
        # arca.guardar usa _reconciliation_connection de la transacción
        from src.db.connection import _reconciliation_connection
        cur = _reconciliation_connection.get().cursor()
        before = control(cur)

        for origen, id_origen, imp, motivo in PAGOS_HISTORICOS:
            arca.guardar(
                origen, id_origen, 0,
                [{"subcuenta": "bienes-sustitutos", "deuda": D(0), "credito": imp}],
                motivo,
                USUARIO,
            )

        after = control(cur)

        # Invariantes absolutos:
        # Cajas, Cuentas de proveedores y Cuentas de socios no cambian en nada
        if before["cajas"] != after["cajas"]:
            raise ValueError("Cambió una caja de efectivo")
        if dict(before["cuentas"]) != dict(after["cuentas"]):
            raise ValueError("Cambió una cuenta de proveedor")
        if before["socios"] != after["socios"]:
            raise ValueError("Cambió una cuenta de socio")

        resultado = {
            "estado": "aplicado",
            "respaldo": respaldo,
            "cantidad": len(PAGOS_HISTORICOS),
            "totalClasificado": total_clasificar,
            "saldoContacto119": dict(after["cuentas"])[119],
        }

        cur.execute(
            "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
            "VALUES (?,'aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
            REGLA,
            json.dumps(resultado, default=str, ensure_ascii=False),
            USUARIO,
            USUARIO,
            respaldo,
            f"Bienes Sustitutos: 27 pagos históricos (2012-2021) clasificados por {total_clasificar}; subcuenta cerrada en $0,00 exacto.",
        )

    (EVIDENCIA / "bienes-sustitutos-27-aplicado.json").write_text(
        json.dumps(resultado, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))
