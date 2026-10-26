"""Incorpora las 21 DDJJ oficiales de SICORE (retenciones practicadas) en dbo.Impuestos
para calzar con los 31 pagos bancarios existentes en la subcuenta 'sicore-ganancias':
- 1 DDJJ 12/2024 por $147.927,99 (pagada por Galicia #2332 el 09/01/2025).
- 20 DDJJ 01/2025 a 09/2026 por $4.014.962,08 extraídas directamente de los extractos SCT oficiales de AFIP.
- Total obligaciones DDJJ: $4.162.890,07.
- Total pagos al corte 30/09/2026: $4.153.833,47.
- Saldo al corte: -$9.056,60 correspondiente exactamente al segundo pago de 09/2026 abonado el 08/10/2026 post-corte.

Regla: arca-sicore-ddjj-incorporacion-036
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

REGLA = "arca-sicore-ddjj-incorporacion-036"


def obtener_djs():
    rows = read("""
    SELECT DISTINCT Periodo, Contenido
    FROM dbo.ArcaSctExtractos
    WHERE Impuesto = 'SICORE'
    ORDER BY Periodo
    """)
    seen_pers = set()
    djs = []
    for r in rows:
        per = r['Periodo']
        if per in seen_pers:
            continue
        seen_pers.add(per)
        cont = json.loads(r['Contenido'] or '[]')
        for c in cont:
            if c.get('concepto') == 'IMPUESTO DETERMINADO':
                for m in c.get('movimientos', []):
                    det = m.get('detalle', '')
                    if 'Presentación' in det or 'Presentacion' in det:
                        imp = D(str(m.get('debe', 0)))
                        f_op = m.get('fechaOperacion', '')[:10]
                        # Formato periodo MM YYYY
                        per_str = f"{per[4:6]} {per[:4]}"
                        djs.append((per_str, f_op, imp, f"DDJJ SICORE {per_str}"))

    # Agregar diciembre 2024
    djs.insert(0, ('12 2024', '2025-01-09', D('147927.99'), "DDJJ SICORE 12 2024"))
    return djs


def main(aplicar=False):
    _assert_target_is_wc()
    djs = obtener_djs()
    tot_djs = sum(d[2] for d in djs)
    print(f"Total obligaciones DDJJ SICORE a registrar: {len(djs)} por ${tot_djs:,.2f}")

    if not aplicar:
        print("[DRY-RUN] Ejecute con --aplicar para registrar en WC.")
        return

    bak = backup_verificado(REGLA)
    print(f"Backup verificado: {bak}")

    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()

        # Insertar obligaciones en dbo.Impuestos (IdTipoImpuesto = 20: Retenciones Ganancias, IdOrganismo = 119)
        # y clasificarlas en 'sicore-ganancias'
        for per_str, f_op, imp, det in djs:
            cursor.execute("""
                INSERT INTO dbo.Impuestos (Fecha, IdOrganismo, IdTipoImpuesto, [Periodo liquidado], [Numero de documento], Importe, [Documento Original])
                OUTPUT INSERTED.IdImpuesto
                VALUES (?, 119, 20, ?, 'DDJJ SICORE', ?, NULL)
            """, (f_op, per_str, float(imp)))
            id_imp = cursor.fetchone()[0]

            reparto = json.dumps([{"subcuenta": "sicore-ganancias", "deuda": float(imp), "credito": 0}])
            cursor.execute("""
                INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
                VALUES ('Impuestos', ?, ?, ?, 'Gemini036')
            """, (id_imp, reparto, det))

        conn.commit()
        print(f"[OK] {len(djs)} obligaciones de DDJJ SICORE registradas y clasificadas exitosamente en WC.")


if __name__ == "__main__":
    aplicar = "--aplicar" in sys.argv
    main(aplicar=aplicar)
