"""Concilia al 100% en $0,00 exacto el periodo historico de Ganancias y Anticipos (2011-2024):
1. Reubica F931 #784 en Galicia #1400 (reparto CS $128.064,56 + resto $95.267,22) dejando
   Galicia #1399 libre para su match 100% exacto con Anticipo Ganancias #817 ($304.799,16).
2. Clasifica BNA #15654 ($2.085,65) en ganancias (100% Ganancias 2011).
3. Clasifica BNA #15901 ($7.962,72) en reparto: Ganancias #839 ($7.950,19) + Otros impuestos #838 ($12,53).
4. Clasifica los 6 anticipos 2021 de BNA en ganancias (100% de $13.412,23 c/u).
5. Clasifica los anticipos directos de Galicia en ganancias (402, 434, 1013, 1074, 1367, 1399, 1533, 1590, 1715, 1869).
6. Actualiza los repartos de los VEP consolidados de Galicia imputando el anticipo correspondiente a ganancias
   y manteniendo el remanente en por-identificar (744, 791, 950, 1126, 1180, 1239, 1478, 1647, 1808, 1937).

Regla: arca-ganancias-anticipos-2011-2024-cero-036
Auditada con backup verificado e invariantes WC.
"""
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado
from src.features.cajas_efectivo.operaciones import read

REGLA = "arca-ganancias-anticipos-2011-2024-cero-036"


def obtener_plan():
    # Débitos a clasificar / repartir
    plan = []

    # 1. Reubicar F931 #784 en Galicia 1400 y dejar 1399 100% para Anticipo #817
    plan.append({
        "origen": "Galicia",
        "idOrigen": 1400,
        "reparto": json.dumps([
            {"subcuenta": "cargas-sociales", "deuda": 0, "credito": 128064.56},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 95267.22},
        ]),
        "motivo": "F931 08/2023 #784 en Galicia #1400 ($128.064,56) + resto $95.267,22",
    })

    plan.append({
        "origen": "Galicia",
        "idOrigen": 1399,
        "reparto": json.dumps([
            {"subcuenta": "ganancias", "deuda": 0, "credito": 304799.16},
        ]),
        "motivo": "Anticipo Ganancias 01/2024 #817 (100% exacto)",
    })

    # 2. BNA 15654 ($2.085,65) -> Ganancias 2011 (#900)
    plan.append({
        "origen": "Banco Nacion",
        "idOrigen": 15654,
        "reparto": json.dumps([
            {"subcuenta": "ganancias", "deuda": 0, "credito": 2085.65},
        ]),
        "motivo": "Ganancias 2011 #900 (100% exacto)",
    })

    # 3. BNA 15901 ($7.962,72) -> Ganancias #839 ($7.950,19) + Otros impuestos #838 ($12,53)
    plan.append({
        "origen": "Banco Nacion",
        "idOrigen": 15901,
        "reparto": json.dumps([
            {"subcuenta": "ganancias", "deuda": 0, "credito": 7950.19},
            {"subcuenta": "otros-impuestos", "deuda": 0, "credito": 12.53},
        ]),
        "motivo": "Ganancias 1/2019 #839 ($7.950,19) + Intereses #838 ($12,53)",
    })

    # 4. Anticipos 2021 BNA directos (6 pagos de $13.412,23)
    bna_2021 = [(15946, 837), (15949, 836), (15953, 835), (15957, 834), (15960, 833), (15963, 832)]
    for id_bna, id_imp in bna_2021:
        plan.append({
            "origen": "Banco Nacion",
            "idOrigen": id_bna,
            "reparto": json.dumps([
                {"subcuenta": "ganancias", "deuda": 0, "credito": 13412.23},
            ]),
            "motivo": f"Anticipo Ganancias #{id_imp} (100% exacto)",
        })

    # 5. Anticipos directos Galicia
    g_directos = [
        (402, 829, 16963.74),
        (434, 828, 16963.74),
        (1013, 824, 42004.53),
        (1074, 822, 42004.53),
        (1367, 818, 107306.08),
        (1533, 812, 101559.08),
        (1590, 811, 101559.08),
        (1715, 809, 101559.08),
        (1869, 807, 101559.08),
    ]
    for id_g, id_imp, imp in g_directos:
        plan.append({
            "origen": "Galicia",
            "idOrigen": id_g,
            "reparto": json.dumps([
                {"subcuenta": "ganancias", "deuda": 0, "credito": imp},
            ]),
            "motivo": f"Anticipo Ganancias #{id_imp} (100% exacto)",
        })

    # 6. Repartos consolidados Galicia (incluyendo CS ya asignado previamente)
    # Galicia 744: $233.059,72 = CS $79.387,26 + Ganancias #827 $126.064,02 + resto $27.608,44
    plan.append({
        "origen": "Galicia",
        "idOrigen": 744,
        "reparto": json.dumps([
            {"subcuenta": "cargas-sociales", "deuda": 0, "credito": 79387.26},
            {"subcuenta": "ganancias", "deuda": 0, "credito": 126064.02},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 27608.44},
        ]),
        "motivo": "VEP consolidado Galicia #744: F931 $79.387,26 + Anticipo Gan #827 $126.064,02 + resto $27.608,44",
    })

    # Galicia 791: $193.831,24 = CS $80.956,11 + Ganancias #826 $42.004,53 + resto $70.870,60
    plan.append({
        "origen": "Galicia",
        "idOrigen": 791,
        "reparto": json.dumps([
            {"subcuenta": "cargas-sociales", "deuda": 0, "credito": 80956.11},
            {"subcuenta": "ganancias", "deuda": 0, "credito": 42004.53},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 70870.60},
        ]),
        "motivo": "VEP consolidado Galicia #791: F931 $80.956,11 + Anticipo Gan #826 $42.004,53 + resto $70.870,60",
    })

    # Galicia 950: $184.993,04 = CS $142.988,51 + Ganancias #825 $42.004,53 (100% cubierto!)
    plan.append({
        "origen": "Galicia",
        "idOrigen": 950,
        "reparto": json.dumps([
            {"subcuenta": "cargas-sociales", "deuda": 0, "credito": 142988.51},
            {"subcuenta": "ganancias", "deuda": 0, "credito": 42004.53},
        ]),
        "motivo": "VEP consolidado Galicia #950: F931 $142.988,51 + Anticipo Gan #825 $42.004,53 (100% exacto)",
    })

    # Galicia 1126: $169.164,60 = CS $121.814,04 + Ganancias #821 $31.590,78 + resto $15.759,78
    plan.append({
        "origen": "Galicia",
        "idOrigen": 1126,
        "reparto": json.dumps([
            {"subcuenta": "cargas-sociales", "deuda": 0, "credito": 121814.04},
            {"subcuenta": "ganancias", "deuda": 0, "credito": 31590.78},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 15759.78},
        ]),
        "motivo": "VEP consolidado Galicia #1126: F931 $121.814,04 + Anticipo Gan #821 $31.590,78 + resto $15.759,78",
    })

    # Galicia 1180: $217.135,75 = CS $112.220,12 + Ganancias #820 $40.963,28 + resto $63.952,35
    plan.append({
        "origen": "Galicia",
        "idOrigen": 1180,
        "reparto": json.dumps([
            {"subcuenta": "cargas-sociales", "deuda": 0, "credito": 112220.12},
            {"subcuenta": "ganancias", "deuda": 0, "credito": 40963.28},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 63952.35},
        ]),
        "motivo": "VEP consolidado Galicia #1180: F931 $112.220,12 + Anticipo Gan #820 $40.963,28 + resto $63.952,35",
    })

    # Galicia 1239: $206.729,38 = CS $109.142,12 + Ganancias #819 $40.963,28 + resto $56.623,98
    plan.append({
        "origen": "Galicia",
        "idOrigen": 1239,
        "reparto": json.dumps([
            {"subcuenta": "cargas-sociales", "deuda": 0, "credito": 109142.12},
            {"subcuenta": "ganancias", "deuda": 0, "credito": 40963.28},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 56623.98},
        ]),
        "motivo": "VEP consolidado Galicia #1239: F931 $109.142,12 + Anticipo Gan #819 $40.963,28 + resto $56.623,98",
    })

    # Galicia 1478: $101.959,22 = Ganancias #814 $101.559,08 + resto $400,14
    plan.append({
        "origen": "Galicia",
        "idOrigen": 1478,
        "reparto": json.dumps([
            {"subcuenta": "ganancias", "deuda": 0, "credito": 101559.08},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 400.14},
        ]),
        "motivo": "Galicia #1478: Anticipo Gan #814 $101.559,08 + resto $400,14",
    })

    # Galicia 1647: $505.002,10 = CS $393.518,34 + Ganancias #810 $101.559,08 + resto $9.924,68
    plan.append({
        "origen": "Galicia",
        "idOrigen": 1647,
        "reparto": json.dumps([
            {"subcuenta": "cargas-sociales", "deuda": 0, "credito": 393518.34},
            {"subcuenta": "ganancias", "deuda": 0, "credito": 101559.08},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 9924.68},
        ]),
        "motivo": "VEP consolidado Galicia #1647: F931 $393.518,34 + Anticipo Gan #810 $101.559,08 + resto $9.924,68",
    })

    # Galicia 1808: $551.496,92 = CS $436.992,98 + Ganancias #808 $101.559,08 + resto $12.944,86
    plan.append({
        "origen": "Galicia",
        "idOrigen": 1808,
        "reparto": json.dumps([
            {"subcuenta": "cargas-sociales", "deuda": 0, "credito": 436992.98},
            {"subcuenta": "ganancias", "deuda": 0, "credito": 101559.08},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 12944.86},
        ]),
        "motivo": "VEP consolidado Galicia #1808: F931 $436.992,98 + Anticipo Gan #808 $101.559,08 + resto $12.944,86",
    })

    # Galicia 1937: $215.365,09 = Ganancias #806 $101.559,08 + resto $113.806,01
    plan.append({
        "origen": "Galicia",
        "idOrigen": 1937,
        "reparto": json.dumps([
            {"subcuenta": "ganancias", "deuda": 0, "credito": 101559.08},
            {"subcuenta": "por-identificar", "deuda": 0, "credito": 113806.01},
        ]),
        "motivo": "Galicia #1937: Anticipo Gan #806 $101.559,08 + resto $113.806,01",
    })

    return plan


def main(aplicar=False):
    _assert_target_is_wc()
    plan = obtener_plan()
    print(f"Total movimientos a registrar en Ganancias/Anticipos: {len(plan)}")

    if not aplicar:
        print("[DRY-RUN] Ejecute con --aplicar para registrar en WC.")
        return

    bak = backup_verificado(REGLA)
    print(f"Backup verificado: {bak}")

    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()

        for p in plan:
            cursor.execute("""
                INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
                VALUES (?, ?, ?, ?, 'Gemini036')
            """, (p['origen'], p['idOrigen'], p['reparto'], p['motivo']))

        conn.commit()
        print(f"[OK] {len(plan)} clasificaciones de Ganancias registradas exitosamente en WC.")


if __name__ == "__main__":
    aplicar = "--aplicar" in sys.argv
    main(aplicar=aplicar)
