"""Clasifica Galicia por número VEP explícito coincidente en Impuestos de WC."""
import argparse
from collections import defaultdict
from decimal import Decimal as D
import json
import re

from scripts.conciliar_sct_arca_036 import SOURCE
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import reconciliation_transaction, _reconciliation_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca
from src.features.vinculos.backup import backup_verificado


def candidates():
    rows, marks = arca.cargar()
    nums = defaultdict(list)
    bykey = {(r['origen'], r['idOrigen']): r for r in rows}
    for row in rows:
        match = re.fullmatch(r'VEP\s+(\d+)', (row['numeroDocumento'] or '').strip(), re.I)
        if row['origen'] == 'Impuestos' and match:
            nums[match[1]].append(row)
    banks = read('SELECT IdMovimiento,LeyendasAdicionales2 FROM dbo.[Movimientos Galicia] WHERE IdContacto=119 ORDER BY IdMovimiento')
    result = []
    for bank in banks:
        match = re.fullmatch(r'VEP\s+(\d+)', (bank['LeyendasAdicionales2'] or '').strip(), re.I)
        key = ('Galicia', bank['IdMovimiento'])
        if not match or key in marks or key not in bykey or match[1] not in nums:
            continue
        original = bykey[key]
        taxes = nums[match[1]]
        if original['deuda'] or sum((D(str(t['deuda'])) for t in taxes), D(0)) != D(str(original['credito'])) or any(t['credito'] for t in taxes):
            continue
        parts = defaultdict(lambda: D(0))
        for tax in taxes:
            classified = arca.construir([tax], marks)['items'][0]['partes']
            for p in classified:
                parts[p['subcuenta']] += D(str(p['deuda']))
        if 'por-identificar' in parts or 'otros-impuestos' in parts:
            continue
        result.append({'idOrigen': bank['IdMovimiento'], 'vep': match[1], 'impuestos': [t['idOrigen'] for t in taxes], 'importe': original['credito'], 'partes': [{'subcuenta': k, 'deuda': D(0), 'credito': v} for k, v in parts.items()]})
    return result


def run(apply=False):
    plan = candidates()
    result = {'estado': 'inspeccion', 'cantidad': len(plan), 'pagos': plan, 'importe': sum((D(str(p['importe'])) for p in plan), D(0))}
    if not apply or not plan:
        return result
    backup = backup_verificado('arca-vep-historico-036')
    with reconciliation_transaction():
        cur = _reconciliation_connection.get().cursor()
        before = control(cur)
        if candidates() != plan:
            raise ValueError('Cambió el inventario')
        for p in plan:
            arca.guardar('Galicia', p['idOrigen'], 0, p['partes'], f"VEP{p['vep']} explícito en banco e Impuestos{p['impuestos']}; suma exacta del débito, sin pago nuevo.", 'Codex036')
        if control(cur) != before:
            raise ValueError('Cambió el libro')
        result.update(estado='aplicado', respaldo=backup)
        cur.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES ('arca-vep-historico-036','aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", json.dumps(result, default=str, ensure_ascii=False), backup, f'{len(plan)} clasificaciones por VEP explícito banco/obligación; sin cambios financieros.')
    (SOURCE / 'vep-historico-clasificado.json').write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))
