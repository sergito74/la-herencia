"""Clasifica pagos historicos (2011-2020) de Cargas Sociales (F931) debitados en Banco Nacion.

Regla: arca-cargas-sociales-bna-historicos-036
Auditada con backup verificado e invariantes WC.
"""
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.cuentas_corrientes import arca
from src.features.vinculos.backup import backup_verificado

REGLA = "arca-cargas-sociales-bna-historicos-036"


def obtener_plan():
    rows, marks = arca.cargar()
    bna_pend = [r for r in rows if r['origen'] == 'Banco Nacion' and ('Banco Nacion', r['idOrigen']) not in marks]
    taxes_cs = [r for r in rows if r['origen'] == 'Impuestos' and arca.clasificar(r) == 'cargas-sociales']

    matches = []
    used_taxes = set()
    for b in sorted(bna_pend, key=lambda x: x['fecha']):
        if b['fecha'].year <= 2020:
            imp = b['credito']
            f = b['fecha']
            for t in taxes_cs:
                if t['deuda'] == imp and abs((t['fecha'] - f).days) <= 45 and t['idOrigen'] not in used_taxes:
                    matches.append((b, t))
                    used_taxes.add(t['idOrigen'])
                    break

    plan = []
    for b, t in matches:
        plan.append({
            'origen': 'Banco Nacion',
            'idOrigen': b['idOrigen'],
            'subcuenta': 'cargas-sociales',
            'importe': b['credito'],
            'motivo': f"Debito BNA Cargas Sociales F931 coincidente con Impuestos[{t['idOrigen']}] ({t['detalle'] or ''})."
        })
    return plan


def main(aplicar=False):
    _assert_target_is_wc()
    plan = obtener_plan()
    total_importe = sum(D(str(p['importe'])) for p in plan)
    print(f"Total debitos BNA Cargas Sociales a clasificar: {len(plan)} por un importe de ${total_importe}")

    if not aplicar:
        print("\n[DRY-RUN] Ejecute con --aplicar para registrar en WC.")
        return

    bak = backup_verificado(REGLA)
    print(f"Backup verificado: {bak}")

    with get_connection(readonly=False) as conn:
        cur = conn.cursor()
        for p in plan:
            reparto_json = json.dumps([{
                'subcuenta': p['subcuenta'],
                'deuda': '0',
                'credito': str(p['importe'])
            }])
            cur.execute(
                "INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario) "
                "VALUES (?, ?, ?, ?, ?)",
                (p['origen'], p['idOrigen'], reparto_json, p['motivo'], "Gemini036")
            )
        conn.commit()

    print(f"EXITO: Clasificados {len(plan)} movimientos en dbo.ArcaClasificaciones.")


if __name__ == '__main__':
    aplicar_flag = '--aplicar' in sys.argv
    main(aplicar=aplicar_flag)

