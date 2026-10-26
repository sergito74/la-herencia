"""Clasifica los pagos bancarios específicos de IVA en Banco Galicia y Banco Nación:
1. Galicia #1036 ($139.294,33, 2023-02-22) -> reparto: crédito IVA $134.013,33 (cancela Impuesto #823 IVA 11/2022 VEP 1059635008) + resto $5.281,00 en por-identificar.
2. Banco Nacion #15621 ($6.078,00, 2011-02-28) -> 100% crédito IVA $6.078,00 (cancela Impuesto #899 IVA 02/2011 $6.078,00).

Regla: arca-iva-pagos-bancarios-especificos-036
Auditada con backup verificado e invariantes WC.
"""
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

REGLA = "arca-iva-pagos-bancarios-especificos-036"

CLASIFICACIONES = [
    ("Galicia", 1036, json.dumps([
        {"subcuenta": "iva", "deuda": 0, "credito": 134013.33},
        {"subcuenta": "por-identificar", "deuda": 0, "credito": 5281.00}
    ]), "Pago IVA 11/2022 VEP 1059635008 coincidente con Impuestos[823] ($134.013,33) + saldo $5.281,00"),
    ("Banco Nacion", 15621, json.dumps([
        {"subcuenta": "iva", "deuda": 0, "credito": 6078.00}
    ]), "Pago IVA 02/2011 coincidente con Impuestos[899] ($6.078,00)")
]

def main(aplicar: bool = False):
    print(f"Total clasificaciones bancarias IVA a aplicar: {len(CLASIFICACIONES)}")
    if not aplicar:
        print("[DRY-RUN] Ejecute con --aplicar para registrar en WC.")
        return

    backup = backup_verificado(REGLA)
    print(f"Backup verificado: {backup}")

    with get_connection() as conn:
        _assert_target_is_wc()
        cursor = conn.cursor()
        for origen, id_origen, reparto, motivo in CLASIFICACIONES:
            cursor.execute(
                """
                INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario, Fecha)
                VALUES (?, ?, ?, ?, ?, SYSDATETIME())
                """,
                (origen, id_origen, reparto, motivo, "Gemini036")
            )
        conn.commit()

    print("[OK] Clasificaciones de pagos IVA aplicadas exitosamente en WC.")

if __name__ == "__main__":
    main("--aplicar" in sys.argv)
