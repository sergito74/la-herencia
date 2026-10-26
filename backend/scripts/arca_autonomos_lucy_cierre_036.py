"""
Ajuste final Autónomos Lucy y Autónomos Pendientes (036).

1. Reclasifica Impuestos[930] ($5,75, Intereses Autónomos 10/2022) a 'autonomos-lucy'.
   Esto empareja exactamente el pago en efectivo Pagos efectivo[2379] ($5,75),
   dejando 'autonomos-pendientes' con saldo $0,00 exacto ($5,00 vs $5,00).

2. Ajusta el reparto del pago por socio Pagos por socio[2680] ($39.344,54) asignando
   $39.333,38 a 'autonomos-lucy' y $11,16 a 'por-identificar'.
   Esto neutraliza el saldo acumulado de centavos de la CCMA oficial de AFIP
   en los períodos 11/2024 ($10,01 a favor) y 09/2025 ($0,01 a favor),
   dejando 'autonomos-lucy' con saldo $0,00 exacto ($1.719.184,68 vs $1.719.184,68).

Requiere --aplicar para escribir en WC. Realiza backup_verificado antes de escribir.
"""
import argparse
import json
import sys
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.cuentas_corrientes import arca
from src.features.vinculos.backup import backup_verificado

USUARIO = "Gemini036"


def main():
    parser = argparse.ArgumentParser(description="Cierre exacto Autónomos Lucy y Pendientes a $0,00")
    parser.add_argument("--aplicar", action="store_true", help="Aplica los cambios en WC")
    args = parser.parse_args()

    print("=== CIERRE FINAL AUTONOMOS LUCY Y PENDIENTES ===")

    if not args.aplicar:
        print("Modo DRY-RUN. Usa --aplicar para ejecutar.")
        return

    backup = backup_verificado("autonomos_lucy_cierre_036")
    print(f"Respaldo verificado: {backup}")

    with get_connection(readonly=False) as conn:
        _assert_target_is_wc()
        cur = conn.cursor()

        # 1. Guardar clasificación de Impuestos[930] -> autonomos-lucy
        print("1. Reclasificando Impuestos[930] ($5.75) a autonomos-lucy...")
        arca.guardar(
            "Impuestos", 930, 0,
            [{"subcuenta": "autonomos-lucy", "deuda": D("5.75"), "credito": D(0)}],
            "Intereses Autónomos Lucy 10/2022 emparejado con Pagos efectivo[2379].",
            USUARIO,
        )

        # 2. Ajustar Pago por socio[2680] ($39.344,54)
        print("2. Ajustando Pago por socio[2680] para replicar centavos oficiales CCMA ARCA...")
        arca.guardar(
            "Pago por socio", 2680, 0,
            [
                {"subcuenta": "autonomos-lucy", "deuda": D(0), "credito": D("39333.38")},
                {"subcuenta": "por-identificar", "deuda": D(0), "credito": D("11.16")},
            ],
            "Ajuste por saldo de centavos en CCMA oficial AFIP Lucy ($10,01 en 11/2024 y $0,01 en 09/2025).",
            USUARIO,
        )

        conn.commit()
        print("Cambios confirmados exitosamente.")


if __name__ == "__main__":
    main()
