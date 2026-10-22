"""Libro de caja de efectivo de Giamigli completo (Sergio 22/10/2026, cajas y socios, etapa 1).

La hoja "Caja Efectivo Pesos" de Cajas Giamigli.xlsx (1.844 movimientos, 2011–2026; "lo mejor que tenemos") se refleja 1:1 en
MovimientosCajaEfectivo (Caja 'GiamigliSA'). La migración 027 había omitido 697 filas que ya estaban en Access como pago a
proveedor (Pagos efectivo, cajas "La Herencia"/"Condominio" = la misma caja física, según Sergio). Se agregan con su vínculo:
- columnas nuevas FilaPlanilla (fila de la hoja) e IdPagoEfectivo (pago de Access que representa ese mismo egreso: el contacto
  se lleva por Pagos efectivo; este libro no entra en las cuentas corrientes, no duplica).
- La columna Saldo de la hoja empieza el 14/07/2015 (fila 486) con $15.491,20 y es consistente hasta $381.785,15. Las 484
  filas anteriores son solo egresos (−$212.256,32): los ingresos de 2011–jul-2015 no están en la planilla. Se registra un
  ingreso de apertura PROVISORIO de $227.747,52 (13/07/2015) a reconstruir en la etapa 3 (retiros bancarios, aportes).
Resultado: saldo = $381.785,15 (informado por Sergio). Idempotente.
"""
import json
import warnings
from collections import defaultdict
from datetime import date

import openpyxl
import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

PLANILLA = r'C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar\Cajas Giamigli.xlsx'
USUARIO = 'Sergio (036, libro de caja 22/10/2026)'
APERTURA = 'Ingresos 2011–jul-2015 no registrados en la planilla (apertura PROVISORIA, a reconstruir)'
SALDO_REAL = 381785.15


def columnas():
    c = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    c.cursor().execute("IF COL_LENGTH('dbo.MovimientosCajaEfectivo','FilaPlanilla') IS NULL ALTER TABLE dbo.MovimientosCajaEfectivo ADD FilaPlanilla int NULL")
    c.cursor().execute("IF COL_LENGTH('dbo.MovimientosCajaEfectivo','IdPagoEfectivo') IS NULL ALTER TABLE dbo.MovimientosCajaEfectivo ADD IdPagoEfectivo int NULL")
    c.close()


def main():
    _assert_target_is_wc()
    warnings.filterwarnings('ignore')
    print(backup_verificado('caja-giamigli-libro-completo-036'))
    columnas()
    wb = openpyxl.load_workbook(PLANILLA, data_only=True, read_only=True)
    P = []
    for i, r in enumerate(wb['Caja Efectivo Pesos'].iter_rows(values_only=True), 1):
        if i == 1 or not (r[0] and hasattr(r[0], 'year')) or not isinstance(r[6], (int, float)) or r[6] == 0:
            continue
        P.append({'fila': i, 'f': r[0].date(), 'c': str(r[1] or '')[:200], 'cta': r[2], 'rs': r[3], 'doc': r[5], 'm': round(float(r[6]), 2)})
    W = fetch_all("SELECT IdMovimiento i, CONVERT(date,Fecha) f, Importe m, FilaPlanilla fp FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA' AND ISNULL(Concepto,'')<>?", (APERTURA,))
    ya = {w['fp'] for w in W if w['fp']}
    idx = defaultdict(list)
    for w in W:
        if not w['fp']:
            idx[(str(w['f']), round(float(w['m']), 2))].append(w)
    PE = fetch_all("SELECT IdPagoEfectivo i, CONVERT(date,Fecha) f, [Importe imputado] m FROM dbo.[Pagos efectivo] WHERE Caja IN ('La Herencia','GiamigliSA','Condominio')")
    pidx = defaultdict(list)
    for p in PE:
        pidx[round(abs(float(p['m'])), 2)].append(p)
    usados_pe = {r['p'] for r in fetch_all('SELECT IdPagoEfectivo p FROM dbo.MovimientosCajaEfectivo WHERE IdPagoEfectivo IS NOT NULL')}
    st, nuevos, vinc = [], 0, 0
    for p in P:
        if p['fila'] in ya:
            continue
        c = idx[(str(p['f']), p['m'])]
        if c:
            w = c.pop(0)
            st.append(('UPDATE dbo.MovimientosCajaEfectivo SET FilaPlanilla=? WHERE IdMovimiento=?', (p['fila'], w['i'])))
            continue
        cand = [x for x in pidx[abs(p['m'])] if x['i'] not in usados_pe and abs((date.fromisoformat(str(x['f'])[:10]) - p['f']).days) <= 3]
        cand.sort(key=lambda x: abs((date.fromisoformat(str(x['f'])[:10]) - p['f']).days))
        pe = cand[0]['i'] if cand else None
        if pe:
            usados_pe.add(pe); vinc += 1
        st.append(('INSERT INTO dbo.MovimientosCajaEfectivo (Caja,Fecha,Concepto,Detalle,Importe,Cuenta,NumeroDocumento,Usuario,FilaPlanilla,IdPagoEfectivo) '
                   "VALUES ('GiamigliSA',?,?,?,?,?,?,?,?,?)",
                   (p['f'].isoformat(), p['c'], (str(p['rs'])[:200] if p['rs'] else None), p['m'], (str(p['cta'])[:20] if p['cta'] else None),
                    (str(p['doc'])[:50] if p['doc'] else None), USUARIO, p['fila'], pe)))
        nuevos += 1
    with reconciliation_transaction():
        st and execute_write_transaction(st)
        saldo = float(fetch_all("SELECT SUM(Importe) s FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA' AND ISNULL(Concepto,'')<>?", (APERTURA,))[0]['s'])
        ap = round(SALDO_REAL - saldo, 2)
        if not fetch_all("SELECT 1 x FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA' AND Concepto=?", (APERTURA,)):
            execute_write_transaction([("INSERT INTO dbo.MovimientosCajaEfectivo (Caja,Fecha,Concepto,Importe,Cuenta,Usuario) VALUES ('GiamigliSA','2015-07-13',?,?,'B',?)",
                                        (APERTURA, ap, USUARIO))])
    tot = fetch_all("SELECT ROUND(SUM(Importe),2) s, COUNT(*) n FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA'")[0]
    print('nuevos', nuevos, 'vinculados a Access', vinc, '| apertura', ap, '| libro', tot)


if __name__ == '__main__': main()
