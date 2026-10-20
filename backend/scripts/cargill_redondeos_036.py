"""Cargill (258): cierre al centavo de liquidaciones y redondeos contra el libro del portal (Sergio 20/10/2026: las
cuentas con saldo vivo se cierran contra el proveedor, sin umbral).

- Liquidaciones (desde 04/06/2020): el importe acreditado por Cargill difiere en centavos del calculado por el sistema
  (Cargill redondea el neto en pesos). Ajuste "Redondeo cuenta Cargill (036)" sin IVA en el primer renglón de cada
  liquidación por la diferencia (retenciones aparte, ya coinciden).
- "AJUSTE DE REDONDEO" del libro de Cargill (5 movimientos, neto $22,98 a favor de Cargill): ND/NC tipo X en pesos,
  Financiamiento, sin IVA, número RED-<fecha>.
- Cobros con tarjeta acreditados por Cargill con centavos de diferencia contra el cargo de la tarjeta (09/06/2021 +0,22;
  12/08/2021 -0,24; 27/04/2023 -0,01; 08/08/2024 -0,02): mismo tratamiento, número RTJ-<fecha>.
Idempotente.
"""
import collections
import csv
import re
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
CONCEPTO = 'Redondeo cuenta Cargill (036)'


def libro():
    return list(csv.DictReader(open(ROOT / 'portal-ledger-completo.csv', encoding='utf-8')))


def diferencias_lpg(filas):
    portal = collections.Counter()
    for x in filas:
        if x['documentType'].strip().startswith(('LPG', 'AJUSTE DEB')):
            portal[x['legalDocument']] += float(x['customerBalance']) - float(x['cargillBalance'])
    sis, primero = collections.Counter(), {}
    for x in fetch_all("SELECT v.IdVenta i,v.[Nro Documento] n,b.Credito c,ISNULL(v.[Retencion IVA],0)+ISNULL(v.[Otra Retenciones],0)+ISNULL(v.[Ret IG],0) rt "
                       "FROM dbo.[Venta Granos] v JOIN dbo.vw_MovimientosCuenta_Base b ON b.Origen='Venta Granos' AND b.IdOrigen=v.IdVenta "
                       "WHERE v.IdConsignatario=258 AND v.Fecha>='2020-06-04' ORDER BY v.IdVenta"):
        k = re.sub(r'\s*\(\d+\)$', '', x['n'].strip())
        sis[k] += x['c'] + x['rt']
        primero.setdefault(k, x['i'])
    return {k: (primero[k], round(portal[k] - sis[k], 2)) for k in portal if k in sis and abs(portal[k] - sis[k]) >= 0.005}


def main():
    _assert_target_is_wc()
    filas = libro()
    lpg = diferencias_lpg(filas)
    red = [(datetime.strptime(x['documentDate'], '%d/%m/%Y'), round(float(x['cargillBalance']) - float(x['customerBalance']), 2))
           for x in filas if x['documentType'].strip() == 'AJUSTE DE REDONDEO']
    red = [(f, v, f'RED-{f:%Y%m%d}') for f, v in red] + [(datetime(2021, 6, 9), 0.22, 'RTJ-20210609'), (datetime(2021, 8, 12), -0.24, 'RTJ-20210812'),
                                                            (datetime(2023, 4, 27), -0.01, 'RTJ-20230427'), (datetime(2024, 8, 14), -0.02, 'RTJ-20240814')]
    red = [(f, v, nro) for f, v, nro in red
           if not fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=258 AND [Nro Documento]=?', (nro,))]
    if not lpg and not red:
        print('Nada pendiente.'); return
    print(backup_verificado('cargill-redondeos-036'))
    with reconciliation_transaction():
        if lpg:
            execute_write_transaction([("INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta,Concepto,Importe,AlicuotaIVA) VALUES (?,?,?,0)", (i, CONCEPTO, d))
                                       for i, d in lpg.values()])
        for f, v, nro in red:
            cab = {'idContacto': 258, 'fecha': f, 'tipoDocumento': 'Nota de Débito' if v > 0 else 'Nota de Crédito', 'tipo': 'X',
                   'numeroDocumento': nro, 'moneda': 'Pesos', 'tipoDeCambio': 1}
            linea = {'productoServicio': 'Ajuste de redondeo Cargill' if nro.startswith('RED') else 'Dif. cobro con tarjeta Cargill', 'cantidad': 1, 'precioUnitario': v, 'iva': 0, 'idCentroCosto': 3,
                     'idDestino': 1, 'idRubro': 2047893443, 'campaña': 'No Aplica', 'idCampania': compras.get_id_campania_por_nombre('No Aplica')}
            execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(linea),
                                       compras._vencimiento_insert_statement({'fechaVencimiento': f})])
        assert not diferencias_lpg(filas)
    print(len(lpg), 'liquidaciones;', len(red), 'redondeos', sum(v for _, v, _ in red))


if __name__ == '__main__': main()
