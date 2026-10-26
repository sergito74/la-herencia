"""Clasifica los pagos bancarios de IVA en Banco Galicia:
1. Galicia #370 ($11.527,75, 2022-01-18) -> 100% crédito IVA (cancela Impuesto #890 IVA 10/2021 $11.527,75).
2. Galicia #1049 ($134.013,33, 2023-02-22) -> 100% crédito IVA (cancela Impuesto #823 IVA 11/2022 $134.013,33).
3. Galicia #297 ($34.026,69, 2021-11-17) -> reparto: crédito IVA $7.734,64 (cancela Impuesto #831 IVA 2/2021) + resto $26.292,05 en por-identificar.

Regla: arca-iva-pagos-galicia-036
Auditada con backup verificado e invariantes WC.
"""
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

REGLA = "arca-iva-pagos-galicia-036"

PAGOS = [
    ("Galicia", 370, json.dumps([{"subcuenta": "iva", "deuda": 0, "credito": 11527.75}]), "Pago IVA 10/2021 VEP 914653969 coincidente con Impuestos[890]"),
    ("Galicia", 1049, json.dumps([{"subcuenta": "iva", "deuda": 0, "credito": 134013.33}]), "Pago IVA 11/2022 VEP 1059635008 coincidente con Impuestos[823]"),
    ("Galicia", 297, json.dumps([
        {"subcuenta": "iva", "deuda": 0, "credito": 7734.64},
        {"subcuenta": "por-identificar", "deuda": 0, "credito": 26292.05},
    ]), "Pago IVA 2/2021 VEP 896162890 coincidente con Impuestos[831] ($7.734,64) + resto $26.292,05"),
]


def main(aplicar=False):
    _assert_target_is_wc()
    print(f"Total pagos de IVA a clasificar: {len(PAGOS)}")

    if not aplicar:
        print("[DRY-RUN] Ejecute con --aplicar para registrar en WC.")
        return

    bak = backup_verificado(REGLA)
    print(f"Backup verificado: {bak}")

    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()

        for orig, id_o, reparto, motivo in PAGOS:
            cursor.execute("""
                INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
                VALUES (?, ?, ?, ?, 'Gemini036')
            """, (orig, id_o, reparto, motivo))

        conn.commit()
        print(f"[OK] {len(PAGOS)} pagos de IVA clasificados exitosamente en WC.")


if __name__ == "__main__":
    aplicar = "--aplicar" in sys.argv
    main(aplicar=aplicar)

