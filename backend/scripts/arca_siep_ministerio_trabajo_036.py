"""Cuatro pagos provinciales SIEP mal asignados a ARCA: tickets y banco, sin duplicar pagos."""
import argparse
from datetime import datetime
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import pdfplumber

from scripts.relevar_retenciones_arca_cierre_036 import OUT
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction, execute_write_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

RULE = 'arca-siep-ministerio-trabajo-4-036'
FOLDER = Path.home() / 'Documents/La Herencia/Administracion y gestion/Cuentas a pagar/Transferencias/ARBA'


def run(apply=False):
    _assert_target_is_wc()
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        assert read('SELECT COUNT(*) n FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA IN (15616,15617,15618,15619) AND IdContacto=351')[0]['n'] == 4
        assert read("SELECT COUNT(*) n FROM dbo.Compras WHERE IdContacto=351 AND [Nro Documento] LIKE 'SIEP351-2025%' ")[0]['n'] == 4
        return {'estado': 'ya_aplicado_sin_escrituras'}
    previous = read('SELECT * FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA IN (15616,15617,15618,15619) ORDER BY IdMovimientoBNA')
    assert len(previous) == 4 and all(r['IdContacto'] == 119 and r['Importe'] == D('-152') for r in previous)
    destination = read('SELECT * FROM dbo.RevisionFichas WHERE IdContacto=351')
    assert destination[0]['Estado'] == 'cerrada' and destination[0]['SaldoAlCierre'] == 0
    plans = []
    for month in range(5, 9):
        p = FOLDER / f'Ticket Hoja Libro Sueldo {month:02d}2025 09.09.2025.pdf'
        with pdfplumber.open(p) as pdf:
            text = '\n'.join(pg.extract_text() or '' for pg in pdf.pages)
        assert all(s in text for s in ['Buenos Aires- Tasas No Impositivas', 'SIEP', '$ 152,00', 'CC $ 18876150111899', '09/09/2025'])
        plans.append({'mes': month, 'numero': f'SIEP351-2025{month:02d}', 'ruta': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    result = {'estado': 'inspeccion', 'planes': plans, 'bancosAntes': previous, 'fichaDestinoAntes': destination}
    if not apply:
        return result
    result['backup'] = backup_verificado(RULE)
    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / 'siep-ministerio-trabajo-aplicado.json'
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        c = _reconciliation_connection.get().cursor()
        assert read('SELECT * FROM dbo.[Movimientos BNA] WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimientoBNA IN (15616,15617,15618,15619) ORDER BY IdMovimientoBNA') == previous
        assert read('SELECT * FROM dbo.RevisionFichas WHERE IdContacto=351') == destination
        before = control(c)
        result['comprasNuevas'] = []
        for p in plans:
            assert hashlib.sha256(Path(p['ruta']).read_bytes()).hexdigest() == p['sha256']
            assert not read('SELECT 1 x FROM dbo.Compras WHERE IdContacto=351 AND [Nro Documento]=?', (p['numero'],))
            fecha = datetime(2025, 9, 9)
            cab = {'idContacto': 351, 'fecha': fecha, 'tipoDocumento': 'Factura', 'tipo': 'X', 'numeroDocumento': p['numero'],
                   'moneda': 'Pesos', 'tipoDeCambio': 1, 'documentoOriginal': p['ruta']}
            line = {'productoServicio': f"Tasa SIEP libro sueldos {p['mes']:02d}/2025", 'cantidad': 1, 'precioUnitario': D('152'), 'iva': 0,
                    'idCentroCosto': 3, 'idDestino': 1, 'idRubro': 14, 'campaña': 'No Aplica', 'idCampania': 20}
            new_id = execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(line), compras._vencimiento_insert_statement({'fechaVencimiento': fecha})])[0]
            result['comprasNuevas'].append(new_id)
        # Los cuatro movimientos son del mismo importe/fecha/cuenta; no afirmar asociación
        # individual con el mes: los cuatro tickets cubren el lote completo por $608.
        c.execute("UPDATE dbo.[Movimientos BNA] SET IdContacto=351,Contacto='Ministerio de Trabajo BA' WHERE IdMovimientoBNA IN (15616,15617,15618,15619)")
        after = control(c)
        assert before['cajas'] == after['cajas'] and before['socios'] == after['socios']
        assert [r for r in before['cuentas'] if r[0] != 119] == [r for r in after['cuentas'] if r[0] != 119]
        assert next(r[1] for r in after['cuentas'] if r[0] == 119) - next(r[1] for r in before['cuentas'] if r[0] == 119) == D('-608')
        assert read('SELECT * FROM dbo.RevisionFichas WHERE IdContacto=351') == destination
        result.update(estado='aplicado', antes=before, despues=after)
        c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps({'informe': str(log), 'compras': result['comprasNuevas']}), result['backup'], 'Cuatro SIEP $608 de ARCA a MinisterioTrabajo con comprobantes X y tickets originales; banco intacto, destino sigue cerrado y saldo0.')
    log.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'estado': result['estado'], 'backup': result['backup'], 'informe': str(log)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--aplicar', action='store_true')
    print(json.dumps(run(p.parse_args().aplicar), default=str, ensure_ascii=False))
