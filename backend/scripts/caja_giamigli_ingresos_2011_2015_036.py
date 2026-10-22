"""Caja Giamigli: ingresos 2011–13/07/2015 identificados (Sergio 22/10/2026, cajas y socios, etapa 1b).

La planilla registra solo egresos antes del 14/07/2015; el libro tenía una apertura PROVISORIA de $227.747,52. Se identifican:
1. Egresos que pagó directamente el Condominio LSC (caja "Condominio" de Access = Condominio LSC, según Sergio, y/o "Compra
   Giamigli" en Movimientos LSC.xlsx > Movs, EF/CC/TJC): un ingreso "Aporte Condominio LSC (pago directo)" por cada uno,
   mismo día e importe (140 movimientos, $65.645,76).
2. Aportes en efectivo del Condominio a la caja (Movimientos LSC.xlsx, "Retiro Giamigli – Aporte Efectivo"): 06/03/2012
   $1.500, 28/12/2012 $3.000, 07/05/2013 $3.000.
3. Egresos que pagó Sergio de su bolsillo (Access "Particular S", ya registrados a su favor en su cuenta de socio): ingreso
   "Aporte Sergio (pago directo)" por cada uno (36, $10.251,24) y el egreso se vincula al pago de Access.
La apertura provisoria se reduce al remanente NO identificado. El saldo del libro no cambia ($381.785,15). Idempotente.
"""
import openpyxl
import warnings
from collections import defaultdict
from datetime import date

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, caja 2011-2015 22/10/2026)'
APERTURA = 'Ingresos 2011–jul-2015 no registrados en la planilla (apertura PROVISORIA, a reconstruir)'
APERTURA_NUEVA = 'Ingresos 2011–jul-2015 NO identificados (remanente de la apertura; ver etapa 1b)'
LSC = r'C:\Users\Sergio\Documents\Alquileres urbanos\Condominio LSC\Movimientos LSC.xlsx'
d = lambda v: date.fromisoformat(str(v)[:10])


def main():
    _assert_target_is_wc()
    warnings.filterwarnings('ignore')
    if fetch_all("SELECT 1 x FROM dbo.MovimientosCajaEfectivo WHERE Usuario=?", (USUARIO,)):
        print('ya aplicado'); return
    W = fetch_all("SELECT m.IdMovimiento i,CONVERT(date,m.Fecha) f,m.Concepto c,m.Importe v,p.Caja pc FROM dbo.MovimientosCajaEfectivo m "
                  "LEFT JOIN dbo.[Pagos efectivo] p ON p.IdPagoEfectivo=m.IdPagoEfectivo "
                  "WHERE m.Caja='GiamigliSA' AND m.FilaPlanilla IS NOT NULL AND m.Fecha<'2015-07-14' AND m.Importe<0")
    idx = defaultdict(list)
    for w in W:
        idx[round(-float(w['v']), 2)].append(w)
    cond = {w['i'] for w in W if w['pc'] == 'Condominio'}
    wb = openpyxl.load_workbook(LSC, data_only=True, read_only=True)
    us = set()
    for r in list(wb['Movs'].iter_rows(values_only=True))[1:]:
        if r and hasattr(r[0], 'year') and str(r[4]).startswith('Compra Giamigli') and isinstance(r[8], (int, float)):
            c = [w for w in idx[round(r[8], 2)] if w['i'] not in us and abs((d(w['f']) - r[0].date()).days) <= 5]
            if c:
                us.add(c[0]['i']); cond.add(c[0]['i'])
    PS = fetch_all("SELECT IdPagoEfectivo i,CONVERT(date,Fecha) f,[Importe imputado] m FROM dbo.[Pagos efectivo] WHERE Caja='Particular S' AND Fecha<'2015-08-01'")
    pidx = defaultdict(list)
    for p in PS:
        pidx[round(abs(float(p['m'])), 2)].append(p)
    sergio, usp = [], set()
    sin_access = {r['i'] for r in fetch_all("SELECT IdMovimiento i FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA' AND IdPagoEfectivo IS NULL AND Fecha<'2015-07-14'")}
    for w in W:
        if w['i'] in cond or w['i'] not in sin_access:
            continue
        c = [p for p in pidx[round(-float(w['v']), 2)] if p['i'] not in usp and abs((d(p['f']) - d(w['f'])).days) <= 3]
        if c:
            usp.add(c[0]['i']); sergio.append((w, c[0]['i']))
    st = []
    for w in W:
        if w['i'] in cond:
            st.append(("INSERT INTO dbo.MovimientosCajaEfectivo (Caja,Fecha,Concepto,Detalle,Importe,Cuenta,Usuario) VALUES ('GiamigliSA',?,?,?,?,'B',?)",
                       (str(w['f'])[:10], 'Aporte Condominio LSC (pago directo)', f'Pagó el Condominio: {w["c"]} (egreso mov. {w["i"]})', -float(w['v']), USUARIO)))
    for f, imp in (('2012-03-06', 1500.0), ('2012-12-28', 3000.0), ('2013-05-07', 3000.0)):
        st.append(("INSERT INTO dbo.MovimientosCajaEfectivo (Caja,Fecha,Concepto,Detalle,Importe,Cuenta,Usuario) VALUES ('GiamigliSA',?,?,?,?,'B',?)",
                   (f, 'Aporte efectivo Condominio LSC', 'Movimientos LSC.xlsx: "Retiro Giamigli – Aporte Efectivo"', imp, USUARIO)))
    for w, pe in sergio:
        st += [("INSERT INTO dbo.MovimientosCajaEfectivo (Caja,Fecha,Concepto,Detalle,Importe,Cuenta,Usuario) VALUES ('GiamigliSA',?,?,?,?,'B',?)",
                (str(w['f'])[:10], 'Aporte Sergio (pago directo)', f'Pagó Sergio (Access Particular S {pe}): {w["c"]} (egreso mov. {w["i"]})', -float(w['v']), USUARIO)),
               ('UPDATE dbo.MovimientosCajaEfectivo SET IdPagoEfectivo=? WHERE IdMovimiento=? AND IdPagoEfectivo IS NULL', (pe, w['i']))]
    ident = sum(-float(w['v']) for w in W if w['i'] in cond) + 7500 + sum(-float(w['v']) for w, _ in sergio)
    ap = fetch_all("SELECT IdMovimiento i, Importe v FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA' AND Concepto=?", (APERTURA,))[0]
    st.append(('UPDATE dbo.MovimientosCajaEfectivo SET Concepto=?, Importe=? WHERE IdMovimiento=?', (APERTURA_NUEVA, round(float(ap['v']) - ident, 2), ap['i'])))
    print(backup_verificado('caja-giamigli-ingresos-2011-2015-036'))
    with reconciliation_transaction():
        execute_write_transaction(st)
    print('condominio', len(cond), '| sergio', len(sergio), '| identificado', round(ident, 2), '| remanente', round(float(ap['v']) - ident, 2))
    print(fetch_all("SELECT ROUND(SUM(Importe),2) s, COUNT(*) n FROM dbo.MovimientosCajaEfectivo WHERE Caja='GiamigliSA'"))


if __name__ == '__main__': main()
