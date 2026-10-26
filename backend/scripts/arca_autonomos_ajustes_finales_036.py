"""Ajusta diferencias puntuales de Autonomos en WC:
1. Lucy IdImpuesto=4593: corrige importe de $43.318,70 a $38.313,90 (periodo 11 2024, categoria real coincidente con CCMA y pago).
2. Sergio IdImpuesto 08 2020: incorpora la obligacion omitida de Sergio por $6.058,36 (periodo '08 2020', fecha '2020-09-02').
3. Sergio BNA 15668: clasifica en autonomos-sergio el debito LINK del 01/03/2013 por $697,39 coincidente con Impuesto[143].

Regla: arca-autonomos-ajustes-finales-036
Auditada con backup verificado e invariantes.
"""
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

REGLA = "arca-autonomos-ajustes-finales-036"


def main(aplicar=False):
    _assert_target_is_wc()

    if not aplicar:
        print("[DRY-RUN] Ejecute con --aplicar para registrar en WC.")
        return

    bak = backup_verificado(REGLA)
    print(f"Backup verificado: {bak}")

    with get_connection(readonly=False) as conn:
        cur = conn.cursor()

        # 1. Corregir importe de IdImpuesto 4593
        cur.execute("UPDATE dbo.Impuestos SET Importe = 38313.90 WHERE IdImpuesto = 4593")
        print("1. IdImpuesto 4593 actualizado a $38.313,90")

        # 2. Insertar obligacion omitida 08 2020 de Sergio
        cur.execute("""
            INSERT INTO dbo.Impuestos (Fecha, IdOrganismo, IdTipoImpuesto, [Periodo liquidado], [Numero de documento], Importe, [Documento Original])
            OUTPUT INSERTED.IdImpuesto
            VALUES ('2020-09-02', 119, 5, '08 2020', 'CCMA Sergio', 6058.36, NULL)
        """)
        id_imp_nuevo = cur.fetchone()[0]
        print(f"2. Obligacion 08 2020 Sergio insertada: IdImpuesto = {id_imp_nuevo} por $6.058,36")

        # Clasificar la nueva obligacion en autonomos-sergio
        reparto_tax = json.dumps([{'subcuenta': 'autonomos-sergio', 'deuda': '6058.36', 'credito': '0'}])
        cur.execute("""
            INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
            VALUES ('Impuestos', ?, ?, 'Obligacion Autonomos Sergio 08 2020 coincidente con pago', 'Gemini036')
        """, (id_imp_nuevo, reparto_tax))

        # 3. Clasificar BNA 15668 en autonomos-sergio
        reparto_bna = json.dumps([{'subcuenta': 'autonomos-sergio', 'deuda': '0', 'credito': '697.39'}])
        cur.execute("""
            INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
            VALUES ('Banco Nacion', 15668, ?, 'Debito BNA SETI/LINK autonomos Sergio coincidente con Impuestos[143]', 'Gemini036')
        """, (reparto_bna,))
        print("3. BNA 15668 ($697,39) clasificado en autonomos-sergio")

        conn.commit()

    print("\nEXITO: Ajustes finales de Autonomos aplicados en WC.")


if __name__ == '__main__':
    aplicar_flag = '--aplicar' in sys.argv
    main(aplicar=aplicar_flag)
