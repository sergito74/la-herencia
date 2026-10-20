"""Desglose autorizado de liquidación1230; conserva neto y cantidad.

Los32,27 se incluyen como otros gastos de comercialización en la fuente
de deducciones del resultado de Soja2022/2023, sin un segundo gasto.
"""
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.ventas_granos.repository import get_venta_cabecera, get_deducciones, get_ajustes, calcular_totales

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
ROWS = [
    (1, 'Comision', 3602.00, 10.5),
    (2, 'Sellado de contrato', 1801.00, 0),
    (2, 'Ingresos brutos', 1148.14, 0),
    (2, 'A cobrar en Final (RCC)', 4502.50, 0),
    (2, 'Ajuste PE', 0.07, 0),
    (2, 'Otros gastos de comercializacion', 32.27, 0),
]


def main():
    cab = get_venta_cabecera(1230)
    assert cab['numeroDocumento'] == '330223253039'
    before = get_deducciones(1230)
    expected = [(c, d, v, a) for c, d, v, a in ROWS]
    actual = [(r['idConcepto'], r['detalle'], r['baseCalculo'], r['alicuota']) for r in before]
    if actual == expected:
        print('Desglose ya aplicado; sin cambios.')
        return
    assert len(before) == 1 and before[0]['idDeduccion'] == 1364
    assert before[0]['baseCalculo'] == 11464.19 and before[0]['detalle'] == 'Comision'
    old_net = calcular_totales(cab, get_ajustes(1230), before)['importeNetoAPercibir']
    origin177 = get_deducciones(177)
    audit = {'autorizacion': 'Sergio20/10/2026: estructura proporcional y32,27 a otros gastos de comercializacion',
             'cabecera': cab, 'antes': before, 'desglose': ROWS,
             'backup': backup_verificado('baya-canje1801-desglose-036')}
    path = ROOT / ('canje1801-desglose-' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert get_deducciones(1230) == before
        stmts = [('DELETE FROM dbo.[Venta Granos_Deducciones] WHERE IdVenta=? AND IdDeduccion=?', (1230,1364))]
        for c, d, v, a in ROWS:
            stmts.append(('INSERT INTO dbo.[Venta Granos_Deducciones] (IdVenta,IdConcepto,Detalle,Porc,[Base Calculo],Alicuota) VALUES (?,?,?,?,?,?)',
                          (1230,c,d,100,v,a)))
        execute_write_transaction(stmts)
        after = get_deducciones(1230)
        net = calcular_totales(cab, get_ajustes(1230), after)['importeNetoAPercibir']
        assert round(net,2) == round(old_net,2) == 187546.31
        assert get_venta_cabecera(1230) == cab and get_deducciones(177) == origin177
        view = fetch_all('SELECT * FROM dbo.vw_ResultadosCultivo_Deducciones WHERE IdCultivo=? AND [Campaña]=? AND Detalle=?',
                         (3,'2022/2023','Otros gastos de comercializacion'))
        own = fetch_all('SELECT d.[Base Calculo] AS monto FROM dbo.[Venta Granos_Deducciones] d WHERE IdVenta=? AND Detalle=?',
                        (1230,'Otros gastos de comercializacion'))
        assert len(own)==1 and own[0]['monto']==32.27
        assert len(view)==1 and view[0]['Pesos'] >= 32.26
        movement = fetch_all('SELECT Credito FROM dbo.vw_MovimientosCuenta_Base WHERE Origen=? AND IdOrigen=?',('Venta Granos',1230))
        assert len(movement)==1 and round(movement[0]['Credito'],2)==187546.31
        audit.update({'despues': after,'neto': net,'resultadoComercializacion': view,'movimiento': movement})
    assert get_deducciones(1230) == after
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'IdVenta':1230,'neto':net,'lineas':len(after),'otrosGastos':own,'backup':audit['backup']},default=str))


if __name__ == '__main__':
    main()
