"""Clasifica pagos historicos (2012-2018) de Autonomos y Cargas Sociales (BNA y Caja La Herencia).

Regla: arca-autonomos-historicos-bna-pe-036
Auditada con backup verificado e invariantes WC.
"""
from collections import defaultdict
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca
from src.features.vinculos.backup import backup_verificado

REGLA = "arca-autonomos-historicos-bna-pe-036"

# 25 pagos efectivo de La Herencia (Autonomos 2017-2018)
AUTONOMOS_PE = [
    (1413, "autonomos-sergio", "Autonomos Sergio 06/2017 - Caja La Herencia"),
    (1414, "autonomos-lucy",   "Autonomos Lucy 06/2017 - Caja La Herencia"),
    (1415, "autonomos-sergio", "Autonomos Sergio 08/2017 - Caja La Herencia"),
    (1416, "autonomos-lucy",   "Autonomos Lucy 08/2017 - Caja La Herencia"),
    (1417, "autonomos-sergio", "Autonomos Sergio 09/2017 - Caja La Herencia"),
    (1418, "autonomos-lucy",   "Autonomos Lucy 09/2017 - Caja La Herencia"),
    (1419, "autonomos-lucy",   "Autonomos Lucy 10/2017 - Caja La Herencia"),
    (1420, "autonomos-sergio", "Autonomos Sergio 10/2017 - Caja La Herencia"),
    (1421, "autonomos-lucy",   "Autonomos Lucy 11/2017 - Caja La Herencia"),
    (1422, "autonomos-sergio", "Autonomos Sergio 11/2017 - Caja La Herencia"),
    (1423, "autonomos-lucy",   "Autonomos Lucy 12/2017 - Caja La Herencia"),
    (1425, "autonomos-sergio", "Autonomos Sergio 12/2017 - Caja La Herencia"),
    (1426, "autonomos-lucy",   "Autonomos Lucy 01/2018 - Caja La Herencia"),
    (1427, "autonomos-sergio", "Autonomos Sergio 01/2018 - Caja La Herencia"),
    (1428, "autonomos-lucy",   "Autonomos Lucy 02/2018 - Caja La Herencia"),
    (1429, "autonomos-sergio", "Autonomos Sergio 02/2018 - Caja La Herencia"),
    (1430, "autonomos-lucy",   "Autonomos Lucy 03/2018 - Caja La Herencia"),
    (1431, "autonomos-sergio", "Autonomos Sergio 03/2018 - Caja La Herencia"),
    (1432, "autonomos-sergio", "Autonomos Sergio 04/2018 - Reintegro Caja La Herencia"),
    (1433, "autonomos-lucy",   "Autonomos Lucy 04/2018 - Reintegro Caja La Herencia"),
    (1716, "autonomos-lucy",   "Autonomos Lucy 05/2018 - Reintegro Caja La Herencia"),
    (1717, "autonomos-sergio", "Autonomos Sergio 05/2018 - Reintegro Caja La Herencia"),
    (1579, "autonomos-lucy",   "Autonomos Lucy 06/2018 - Reintegro Caja La Herencia"),
    (1580, "autonomos-sergio", "Autonomos Sergio 06/2018 - Reintegro Caja La Herencia"),
    (1718, "autonomos-sergio", "Autonomos Sergio 07/2019 - Caja La Herencia"),
]

# 14 pagos efectivo de La Herencia (Cargas Sociales F931 cuota fija 252.0 y 276.36 en 2017-2018)
CARGAS_PE = [
    (1435, "cargas-sociales", "Cargas Sociales 05/2017 $252,00 - Caja La Herencia"),
    (1434, "cargas-sociales", "Cargas Sociales 06/2017 $252,00 - Caja La Herencia"),
    (1436, "cargas-sociales", "Cargas Sociales 07/2017 $252,00 - Caja La Herencia"),
    (1437, "cargas-sociales", "Cargas Sociales 08/2017 $252,00 - Caja La Herencia"),
    (1438, "cargas-sociales", "Cargas Sociales 09/2017 $252,00 - Caja La Herencia"),
    (1439, "cargas-sociales", "Cargas Sociales 10/2017 $252,00 - Caja La Herencia"),
    (1440, "cargas-sociales", "Cargas Sociales 11/2017 $252,00 - Caja La Herencia"),
    (1441, "cargas-sociales", "Cargas Sociales 12/2017 $252,00 - Caja La Herencia"),
    (1442, "cargas-sociales", "Cargas Sociales 01/2018 $276,36 - Caja La Herencia"),
    (1443, "cargas-sociales", "Cargas Sociales 02/2018 $276,36 - Caja La Herencia"),
    (1444, "cargas-sociales", "Cargas Sociales 03/2018 $276,36 - Caja La Herencia"),
    (1445, "cargas-sociales", "Cargas Sociales 04/2018 $276,36 - Caja La Herencia"),
    (1457, "cargas-sociales", "Cargas Sociales 05/2018 $276,36 - Caja La Herencia"),
    (1581, "cargas-sociales", "Cargas Sociales 06/2018 $276,36 - Caja La Herencia"),
]


def plan_bna(rows, marks):
    by_bna = {r['idOrigen']: r for r in rows if r['origen'] == 'Banco Nacion'}
    bna_pend = [r for r in rows if r['origen'] == 'Banco Nacion' and ('Banco Nacion', r['idOrigen']) not in marks]
    impuestos_aut = [r for r in rows if r['origen'] == 'Impuestos' and ('Impuestos', r['idOrigen']) in marks]

    aut_lucy_taxes = [t for t in impuestos_aut if 'autonomos-lucy' in marks[('Impuestos', t['idOrigen'])]['reparto']]
    aut_sergio_taxes = [t for t in impuestos_aut if 'autonomos-sergio' in marks[('Impuestos', t['idOrigen'])]['reparto']]

    lucy_map = {}
    sergio_map = {}

    for b in sorted(bna_pend, key=lambda x: x['fecha']):
        imp = b['credito']
        f = b['fecha']
        for t in aut_lucy_taxes:
            if t['deuda'] == imp and abs((t['fecha'] - f).days) <= 45 and t['idOrigen'] not in lucy_map.values():
                lucy_map[b['idOrigen']] = t['idOrigen']
                break
        for t in aut_sergio_taxes:
            if t['deuda'] == imp and abs((t['fecha'] - f).days) <= 45 and t['idOrigen'] not in sergio_map.values():
                sergio_map[b['idOrigen']] = t['idOrigen']
                break

    items = []
    for id_bna, id_tax in lucy_map.items():
        b = by_bna[id_bna]
        items.append({
            'origen': 'Banco Nacion',
            'idOrigen': id_bna,
            'subcuenta': 'autonomos-lucy',
            'importe': b['credito'],
            'motivo': f"Debito BNA SETI/LINK autonomos Lucy coincidente con Impuestos[{id_tax}]."
        })
    for id_bna, id_tax in sergio_map.items():
        b = by_bna[id_bna]
        items.append({
            'origen': 'Banco Nacion',
            'idOrigen': id_bna,
            'subcuenta': 'autonomos-sergio',
            'importe': b['credito'],
            'motivo': f"Debito BNA SETI/LINK autonomos Sergio coincidente con Impuestos[{id_tax}]."
        })
    return items


def main(aplicar=False):
    _assert_target_is_wc()
    rows, marks = arca.cargar()
    by_pe = {r['idOrigen']: r for r in rows if r['origen'] == 'Pagos efectivo'}

    plan = []
    # PE autonomos
    for id_pe, sub, mot in AUTONOMOS_PE:
        if ('Pagos efectivo', id_pe) not in marks and id_pe in by_pe:
            plan.append({
                'origen': 'Pagos efectivo',
                'idOrigen': id_pe,
                'subcuenta': sub,
                'importe': by_pe[id_pe]['credito'],
                'motivo': mot
            })

    # PE cargas
    for id_pe, sub, mot in CARGAS_PE:
        if ('Pagos efectivo', id_pe) not in marks and id_pe in by_pe:
            plan.append({
                'origen': 'Pagos efectivo',
                'idOrigen': id_pe,
                'subcuenta': sub,
                'importe': by_pe[id_pe]['credito'],
                'motivo': mot
            })

    # BNA
    bna_items = plan_bna(rows, marks)
    plan.extend(bna_items)

    total_importe = sum(D(str(p['importe'])) for p in plan)
    print(f"Total registros a clasificar: {len(plan)} por un importe de ${total_importe}")

    por_sub = defaultdict(lambda: {'cant': 0, 'total': D(0)})
    for p in plan:
        por_sub[p['subcuenta']]['cant'] += 1
        por_sub[p['subcuenta']]['total'] += D(str(p['importe']))

    for sub, d in por_sub.items():
        print(f"  - {sub}: {d['cant']} movimientos, total ${d['total']}")

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

