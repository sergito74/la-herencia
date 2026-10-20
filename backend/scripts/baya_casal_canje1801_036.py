"""036: liquidación reconstruida por autorización de Sergio, sin PDF original.

Precio/IVA de la liquidación hermana; deducción global sin desglose fiscal.
CA78182 acredita cantidad y neto. No inventa un original ni pagos adicionales.
"""
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src.db.connection import fetch_all, reconciliation_transaction, _assert_target_is_wc
from src.features.ventas_granos.repository import (
    get_venta_cabecera, get_ajustes, get_deducciones, calcular_totales, create_venta,
)
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
NUMBER = '330223253039'


def state():
    return {'cabecera': get_venta_cabecera(177), 'ajustes': get_ajustes(177),
            'deducciones': get_deducciones(177)}


def main():
    _assert_target_is_wc()
    existing = fetch_all('SELECT IdVenta FROM dbo.[Venta Granos] WHERE [Nro Documento]=?', (NUMBER,))
    if existing:
        print('Ya registrada:', existing)
        return
    origin = state()
    ref = origin['cabecera']
    assert ref['numeroDocumento'] == '330223253060'
    assert ref['precioUnitario'] == 100000 and ref['alicuotaIVA'] == 10.5
    evidence = ROOT / 'CA_0006_00078182.pdf.txt'
    assert NUMBER[-8:] in evidence.read_text(encoding='utf-8-sig')
    cabecera = {
        'idConsignatario': 226, 'idTipoDocumento': ref['idTipoDocumento'],
        'idProducto': ref['idProducto'], 'numeroDocumento': NUMBER,
        'fecha': date(2023, 5, 3), 'precioUnitario': 100000, 'tipoCambio': 224.65,
        'campania': ref['campania'], 'factor': 100, 'flete': 0,
        'cantidadEntregada': 1801, 'cantidadVendida': 1801, 'alicuotaIVA': 10.5,
        'documentoOriginal': None,
    }
    deducciones = [{'idConcepto': 2,
        'detalle': 'Reconstruido sin original; sin desglose',
        'porc': 100, 'baseCalculo': 11464.19, 'alicuota': 0}]
    totals = calcular_totales(cabecera, [], deducciones)
    assert round(totals['importeNetoAPercibir'], 2) == 187546.31
    audit = {'autorizacion': 'Sergio 20/10/2026: cargar sin PDF, precio de venta 30091 kg',
             'fuente': 'CA0006-00078182: 1801 kg, neto187546.31, TC224.65',
             'criterio': 'Precio e IVA de venta177; deduccion agregada sin desglose ni credito fiscal presumido. Grado no documentado: NULL. Sin original PDF.',
             'cabecera': cabecera, 'deducciones': deducciones, 'totales': totals,
             'origenAntes': origin}
    audit['backup'] = backup_verificado('baya-canje1801-036')
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    output = ROOT / f'canje1801-alta-{stamp}.json'
    output.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert not fetch_all('SELECT IdVenta FROM dbo.[Venta Granos] WHERE [Nro Documento]=?', (NUMBER,))
        assert state() == origin
        new_id = create_venta(cabecera, [], deducciones)
        actual = calcular_totales(get_venta_cabecera(new_id), get_ajustes(new_id), get_deducciones(new_id))
        assert round(actual['importeNetoAPercibir'], 2) == 187546.31
        movements = fetch_all("SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE Origen=? AND IdOrigen=?", ('Venta Granos', new_id))
        assert len(movements) == 1
        assert Decimal(str(movements[0]['Credito'])).quantize(Decimal('.01')) == Decimal('187546.31')
        assert state() == origin
        audit.update({'IdVenta': new_id, 'verificacion': actual, 'movimientos': movements})
    audit['persistido'] = get_venta_cabecera(new_id)
    assert audit['persistido'] is not None
    output.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'IdVenta': new_id, 'neto': actual['importeNetoAPercibir'],
                      'backup': audit['backup'], 'auditoria': str(output)}, default=str))


if __name__ == '__main__':
    main()
