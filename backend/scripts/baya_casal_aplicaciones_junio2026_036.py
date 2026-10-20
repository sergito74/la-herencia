"""Pago Galicia 3274 + RG19 (junio 2026): créditos USD según CA145870/145871/146076.

Crea dbo.ValuacionProveedorEventos (si falta) y registra las tres aplicaciones con
su TC. Banco, certificado y aplicaciones en pesos quedan intactos.
"""
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction, _reconciliation_connection
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'
JUN10, JUN16 = date(2026, 6, 10), date(2026, 6, 16)
# (documento, fecha, pesos de la transferencia aplicados, TC del recibo)
PARTES = [('CA0006-00145870', JUN10, D('36962653.41'), D('1441')),
          ('CA0006-00145871', JUN10, D('259059.15'), D('1441')),
          ('CA0006-00146076', JUN16, D('3374532.38'), D('1432.5'))]
RET_PESOS, RET_TC = D('621445.56'), D('1441')
FUENTES = ['CA_0006_00145870.pdf', 'CA_0006_00145871.pdf', 'CA_0006_00146076.pdf']
DDL = ('CREATE TABLE dbo.ValuacionProveedorEventos (IdEvento int IDENTITY PRIMARY KEY, Origen varchar(50) NOT NULL, '
       'IdOrigen bigint NOT NULL, IdContacto int NOT NULL, Fecha date NOT NULL, Documento varchar(50) NOT NULL, '
       'Dolares money NOT NULL, Fuente varchar(200) NULL, Usuario varchar(50) NULL, Alta datetime2 NOT NULL DEFAULT SYSDATETIME())')


def usd(p, tc):
    return (p / tc).quantize(D('0.01'))


def vals():
    return fetch_all("SELECT * FROM dbo.ValuacionProveedor WHERE (Origen='Galicia' AND IdOrigen=3274) OR (Origen='Retenciones' AND IdOrigen=240) ORDER BY Origen")


def origen():
    return (fetch_all('SELECT * FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=3274'),
            fetch_all('SELECT * FROM dbo.Retenciones WHERE IdRetencionSQL=240'))


def main():
    bank, ret = origen()
    assert bank[0]['IdContacto'] == 226 and D(str(bank[0]['Débitos'])) == sum(p[2] for p in PARTES)
    assert ret[0]['IdContacto'] == 226 and D(str(ret[0]['Importe'])) == RET_PESOS
    if vals():
        print('Valuaciones ya aplicadas; sin cambios.'); return
    eventos = [(doc, f, usd(p, tc)) for doc, f, p, tc in PARTES]
    total = sum(e[2] for e in eventos)
    ret_usd = usd(RET_PESOS, RET_TC)
    before = cargar_cuenta(226, refrescar=True)
    audit = {'autorizacion': 'Sergio 20/10/2026: puntos 1-3 de Bayá (pagos, imputaciones, historia)',
             'banco': bank, 'retencion': ret, 'eventos': eventos, 'totalUSD': total, 'retencionUSD': ret_usd,
             'fuentes': {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FUENTES},
             'criterio': 'Transferencia en 3 aplicaciones del proveedor (TC 1441 x2 el 10/06, TC 1432,50 el 16/06); RG19 aplicada en CA145870 a TC 1441. Sin cambios en pesos.',
             'cuentaAntes': {k: v for k, v in before.items() if k != 'filas'},
             'backup': backup_verificado('baya-aplicaciones-junio2026-036')}
    path = ROOT / f'aplicaciones-junio2026-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert origen() == (bank, ret) and not vals()
        if fetch_all("SELECT OBJECT_ID('dbo.ValuacionProveedorEventos','U') AS n")[0]['n'] is None:
            _reconciliation_connection.get().cursor().execute(DDL)
        fuente = 'Bayá CA145870/145871/146076 originales'
        ins = ('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,FechaEfectoUSD,DocumentoEfectoUSD) '
               'VALUES (?,?,226,?,?,?,?,?,?)')
        stmts = [(ins, ('Galicia', 3274, total, fuente, 'Tres aplicaciones con TC distinto; detalle en ValuacionProveedorEventos.', 'sergio', JUN10, PARTES[0][0])),
                 (ins, ('Retenciones', 240, ret_usd, fuente, 'RG0001-00000019 aplicada en CA145870 a TC 1441.', 'sergio', JUN10, PARTES[0][0]))]
        stmts += [('INSERT INTO dbo.ValuacionProveedorEventos (Origen,IdOrigen,IdContacto,Fecha,Documento,Dolares,Fuente,Usuario) VALUES (?,?,226,?,?,?,?,?)',
                   ('Galicia', 3274, f, doc, d, fuente, 'sergio')) for doc, f, d in eventos]
        execute_write_transaction(stmts)
        assert origen() == (bank, ret)
        audit['valuacionesDespues'] = vals()
    invalidar()
    after = cargar_cuenta(226, refrescar=True)
    assert after['saldoPesos'] == before['saldoPesos']
    audit['cuentaDespues'] = {k: v for k, v in after.items() if k != 'filas'}
    audit['variacionSaldoUSD'] = round(after['saldoDolares'] - before['saldoDolares'], 2)
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'totalUSD': total, 'retencionUSD': ret_usd, 'variacionSaldoUSD': audit['variacionSaldoUSD'],
                      'saldoUSD': after['saldoDolares'], 'backup': audit['backup']}, default=str))


if __name__ == '__main__': main()
