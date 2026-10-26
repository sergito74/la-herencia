"""Clasifica pagos en efectivo por su IdOperacion explícito en WC.

No usa coincidencia de importe como evidencia del impuesto. No modifica el libro.
"""
import argparse
from collections import Counter
from decimal import Decimal as D
import json

from scripts.conciliar_sct_arca_036 import SOURCE
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import reconciliation_transaction, _reconciliation_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca
from src.features.vinculos.backup import backup_verificado

RULE = 'arca-pagos-por-idoperacion-036'


def candidates():
    links = read('SELECT p.IdPagoEfectivo,p.IdOperacion,i.IdImpuesto,i.IdTipoImpuesto,i.[Periodo liquidado] periodo,p.[Importe imputado] importe FROM dbo.vw_PagosEfectivoVigentes p JOIN dbo.Impuestos i ON i.IdOperacion=p.IdOperacion WHERE p.IdContacto=119 AND i.IdOrganismo=119')
    counts = Counter(p['IdPagoEfectivo'] for p in links)
    rows, marks = arca.cargar()
    bykey = {(r['origen'], r['idOrigen']): r for r in rows}
    plan = []
    for p in links:
        key = ('Pagos efectivo', p['IdPagoEfectivo'])
        original = bykey.get(key)
        if not original or counts[p['IdPagoEfectivo']] != 1 or marks.get(key):
            continue
        if original['deuda'] or D(str(original['credito'])) != D(str(p['importe'])):
            continue
        tax = bykey.get(('Impuestos', p['IdImpuesto']))
        if not tax:
            continue
        # La clasificación vigente de la obligación identifica al titular cuando corresponde.
        classified = arca.construir([tax], marks)['items'][0]['partes']
        if len(classified) != 1:
            continue
        account = classified[0]['subcuenta']
        if account in ('por-identificar', 'otros-impuestos'):
            continue
        plan.append({**p, 'subcuenta': account, 'version': 0})
    return plan


def run(apply=False):
    plan = candidates()
    result = {'estado': 'inspeccion', 'pagos': plan, 'cantidad': len(plan), 'importe': sum((D(str(p['importe'])) for p in plan), D(0))}
    if not apply or not plan:
        return result
    backup = backup_verificado('arca-pagos-idoperacion-036')
    with reconciliation_transaction():
        cur = _reconciliation_connection.get().cursor()
        before = control(cur)
        if candidates() != plan:
            raise ValueError('Cambió el inventario de pagos')
        for p in plan:
            arca.guardar('Pagos efectivo', p['IdPagoEfectivo'], p['version'], [{'subcuenta': p['subcuenta'], 'deuda': D(0), 'credito': D(str(p['importe']))}], f"Vínculo explícito WC IdOperacion={p['IdOperacion']} con Impuestos {p['IdImpuesto']} ({p['periodo']}); solo clasificación del pago existente.", 'Codex036')
        after = control(cur)
        if before != after:
            raise ValueError('Cambió el libro, caja o socios')
        result.update(estado='aplicado', respaldo=backup)
        cur.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps(result, default=str, ensure_ascii=False), backup, f"Clasificados {len(plan)} pagos por IdOperacion explícito. Sin cambios financieros.")
    (SOURCE / 'clasificaciones-idoperacion-aplicadas.json').write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))
