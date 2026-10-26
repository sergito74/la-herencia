"""Quita dos vínculos duplicados a ARCA, conservando los asientos de Lucy y caja.

Reversible con las filas completas conservadas en AuditoriaCorrecciones.
"""
import argparse
from decimal import Decimal as D
import json

from scripts.conciliar_sct_arca_036 import SOURCE
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import reconciliation_transaction, _reconciliation_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado

RULE = 'arca-lucy-vinculos-reintegrados-036'


def run(apply=False):
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        return {'estado': 'ya_aplicado_sin_escrituras'}
    result = {'estado': 'inspeccion', 'vinculos': [2279, 2281], 'importeDuplicado': '2398.04'}
    if not apply:
        return result
    backup = backup_verificado('arca-lucy-duplicados-036')
    with reconciliation_transaction():
        cur = _reconciliation_connection.get().cursor()
        before = control(cur)
        previous = read('SELECT * FROM dbo.PagosSocioProveedor WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimientoSocio IN (2279,2281) ORDER BY IdMovimientoSocio')
        if len(previous) != 2 or any(p['IdContacto'] != 119 or p['Criterio'] != 'alias' for p in previous):
            raise ValueError('Cambió el vínculo previo')
        for paid, reimbursement, cash, date in ((2279, 2280, 1433, '2018-05-29'), (2281, 2282, 1716, '2018-06-21')):
            people = read('SELECT * FROM dbo.MovimientosCuentaSocio WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimiento IN (?,?) ORDER BY IdMovimiento', (paid, reimbursement))
            if len(people) != 2 or any(p['IdSocio'] != 2 or p['Anulada'] or D(str(p['Importe'])) != D('1199.02') for p in people):
                raise ValueError('Cambió el par de Lucy')
            if people[0]['Tipo'] != 'Devolucion' or people[1]['Tipo'] != 'AsignacionGasto' or str(people[1]['Fecha'])[:10] != date:
                raise ValueError('Cambió la secuencia pago/reintegro')
            cashrows = read("SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=119 AND Origen='Pagos efectivo' AND IdOrigen=?", (cash,))
            if len(cashrows) != 1 or str(cashrows[0]['Fecha'])[:10] != date or D(str(cashrows[0]['Credito'])) != D('1199.02') or cashrows[0]['Deuda']:
                raise ValueError('Falta el pago efectivo ya acreditado')
        removed = cur.execute('DELETE FROM dbo.PagosSocioProveedor OUTPUT DELETED.IdMovimientoSocio WHERE IdMovimientoSocio IN (2279,2281) AND IdContacto=119').fetchall()
        if {row[0] for row in removed} != {2279, 2281}:
            raise ValueError('Cantidad de vínculos inesperada')
        after = control(cur)
        expected = dict(before['cuentas'])
        expected[119] -= D('2398.04')
        if dict(after['cuentas']) != expected or before['cajas'] != after['cajas'] or before['socios'] != after['socios']:
            raise ValueError('Efecto no previsto')
        result.update(estado='aplicado', respaldo=backup, filasAnteriores=previous, saldoAntes=dict(before['cuentas'])[119], saldoDespues=dict(after['cuentas'])[119])
        cur.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps(result, default=str, ensure_ascii=False), backup, 'Quita vínculos alias 2279/2281 ya reintegrados por caja1433/1716. Asientos socios/caja conservados. Filas completas para reversión en Parametros.')
    (SOURCE / 'lucy-vinculos-duplicados-aplicado.json').write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))
