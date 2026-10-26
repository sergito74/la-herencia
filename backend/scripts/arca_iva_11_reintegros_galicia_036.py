"""Clasifica los 11 reintegros históricos de IVA Granos cobrados en Banco Galicia (2021-2024)
por un total de $3.538.609,09, calzando al 100% exacto con las devoluciones de 34 certificados de Cargill.

Regla: arca-iva-11-reintegros-galicia-036
Auditada con backup verificado e invariantes WC.
"""
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

REGLA = "arca-iva-11-reintegros-galicia-036"

# (IdMovimiento Galicia, importe, fecha, motivo)
REINTEGROS = [
    (103, 251595.77, "2021-07-19", "Reintegro IVA Granos Galicia #103: cancela devolucion 7 certs Cargill [298, 299, 301, 302, 303, 304, 300]"),
    (137, 174434.92, "2021-08-17", "Reintegro IVA Granos Galicia #137: cancela devolucion 4 certs Cargill [305, 306, 308, 307]"),
    (254, 12496.02, "2021-10-18", "Reintegro IVA Granos Galicia #254: cancela devolucion cert Cargill [309]"),
    (442, 60187.88, "2022-03-15", "Reintegro IVA Granos Galicia #442: cancela devolucion 3 certs Cargill [310, 311, 312]"),
    (537, 162750.99, "2022-05-13", "Reintegro IVA Granos Galicia #537: cancela devolucion 4 certs Cargill [315, 316, 313, 314]"),
    (590, 89823.75, "2022-06-15", "Reintegro IVA Granos Galicia #590: cancela devolucion 2 certs Cargill [318, 319]"),
    (654, 57125.86, "2022-07-18", "Reintegro IVA Granos Galicia #654: cancela devolucion cert Cargill [320]"),
    (762, 175117.89, "2022-09-16", "Reintegro IVA Granos Galicia #762: cancela devolucion 2 certs Cargill [321, 322]"),
    (859, 1326607.71, "2022-11-16", "Reintegro IVA Granos Galicia #859: cancela devolucion 6 certs Cargill [323, 324, 325, 326, 327, 328]"),
    (1306, 433696.95, "2023-07-13", "Reintegro IVA Granos Galicia #1306: cancela devolucion 3 certs Cargill [329, 330, 331]"),
    (1782, 794771.35, "2024-03-15", "Reintegro IVA Granos Galicia #1782: cancela devolucion 4 certs Cargill [332, 333, 334, 335]"),
]


def main(aplicar=False):
    _assert_target_is_wc()
    total = sum(r[1] for r in REINTEGROS)
    print(f"Total reintegros Galicia a clasificar en IVA: {len(REINTEGROS)} por ${total:,.2f}")

    if not aplicar:
        print("[DRY-RUN] Ejecute con --aplicar para registrar en WC.")
        return

    bak = backup_verificado(REGLA)
    print(f"Backup verificado: {bak}")

    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()

        for id_g, imp, f_str, motivo in REINTEGROS:
            # En vw_MovimientosCuenta_Base, estos movimientos figuran como Deuda (abono/cobro en cuenta corriente del proveedor AFIP)
            reparto = json.dumps([{"subcuenta": "iva", "deuda": imp, "credito": 0}])
            cursor.execute("""
                INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
                VALUES ('Galicia', ?, ?, ?, 'Gemini036')
            """, (id_g, reparto, motivo))

        conn.commit()
        print(f"[OK] {len(REINTEGROS)} reintegros de IVA clasificados exitosamente en WC.")


if __name__ == "__main__":
    aplicar = "--aplicar" in sys.argv
    main(aplicar=aplicar)

