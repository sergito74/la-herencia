"""Clasifica los 24 abonos de BNA (2016-2021) que corresponden a reintegros de IVA Granos
por un total de $688.395,43, calzando con las devoluciones de certificados de granos pre-2021.

Regla: arca-iva-24-reintegros-bna-036
Auditada con backup verificado e invariantes WC.
"""
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

REGLA = "arca-iva-24-reintegros-bna-036"

REINTEGROS_BNA = [
    (15815, 2424.49, "Reintegro IVA Granos BNA #15815: cancela cert #3"),
    (15819, 9705.73, "Reintegro IVA Granos BNA #15819: cancela certs #4, #5"),
    (15826, 5950.10, "Reintegro IVA Granos BNA #15826: cancela certs #1, #2"),
    (15833, 11590.06, "Reintegro IVA Granos BNA #15833: cancela certs #6, #11, #12"),
    (15843, 10083.07, "Reintegro IVA Granos BNA #15843: cancela certs #17, #18, #108, #109"),
    (15848, 19441.67, "Reintegro IVA Granos BNA #15848: cancela certs #110 a #113 y #13"),
    (15852, 8321.44, "Reintegro IVA Granos BNA #15852: cancela cert #114"),
    (15854, 6236.10, "Reintegro IVA Granos BNA #15854: cancela cert #115"),
    (15857, 3533.60, "Reintegro IVA Granos BNA #15857: cancela cert #116"),
    (15870, 23039.23, "Reintegro IVA Granos BNA #15870: cancela certs #117, #118"),
    (15873, 36050.24, "Reintegro IVA Granos BNA #15873: cancela certs #119 a #121"),
    (15876, 9443.46, "Reintegro IVA Granos BNA #15876: cancela cert #123"),
    (15885, 19542.63, "Reintegro IVA Granos BNA #15885: cancela cert #124"),
    (15889, 49037.21, "Reintegro IVA Granos BNA #15889: cancela certs #125 a #127"),
    (15896, 76518.27, "Reintegro IVA Granos BNA #15896: cancela certs #128 a #134"),
    (15899, 1472.93, "Reintegro IVA Granos BNA #15899: cancela cert #135"),
    (15911, 42376.42, "Reintegro IVA Granos BNA #15911: cancela certs #138 a #141"),
    (15912, 24548.34, "Reintegro IVA Granos BNA #15912: cancela certs #136, #137"),
    (15921, 39545.98, "Reintegro IVA Granos BNA #15921: cancela certs #142, #143"),
    (15928, 32787.47, "Reintegro IVA Granos BNA #15928: cancela certs #144, #145"),
    (15937, 111112.96, "Reintegro IVA Granos BNA #15937: cancela certs #146 a #150"),
    (15940, 323.32, "Reintegro IVA Granos BNA #15940: ajuste reintegro AFIP"),
    (15962, 32387.55, "Reintegro IVA Granos BNA #15962: cancela certs Cargill #291, #292"),
    (15969, 112923.16, "Reintegro IVA Granos BNA #15969: cancela certs Cargill #293 a #297"),
]


def main(aplicar=False):
    _assert_target_is_wc()
    total = sum(r[1] for r in REINTEGROS_BNA)
    print(f"Total reintegros BNA a clasificar en IVA: {len(REINTEGROS_BNA)} por ${total:,.2f}")

    if not aplicar:
        print("[DRY-RUN] Ejecute con --aplicar para registrar en WC.")
        return

    bak = backup_verificado(REGLA)
    print(f"Backup verificado: {bak}")

    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()

        for id_bna, imp, motivo in REINTEGROS_BNA:
            # En vw_MovimientosCuenta_Base, los abonos bancarios de AFIP figuran como Deuda en ARCA (cobro de crédito fiscal)
            reparto = json.dumps([{"subcuenta": "iva", "deuda": imp, "credito": 0}])
            cursor.execute("""
                INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
                VALUES ('Banco Nacion', ?, ?, ?, 'Gemini036')
            """, (id_bna, reparto, motivo))

        conn.commit()
        print(f"[OK] {len(REINTEGROS_BNA)} reintegros BNA de IVA clasificados exitosamente en WC.")


if __name__ == "__main__":
    aplicar = "--aplicar" in sys.argv
    main(aplicar=aplicar)

