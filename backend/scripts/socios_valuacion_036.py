"""Cuentas de socios Sergio (1) y Lucy (2): duplicados y valuación en kg de novillo / US$ como la planilla (Sergio 22/10/2026).

1. Anula los movimientos cargados por la revisión que duplican una fila de la planilla Cajas Giamigli (lista en
   backups/socios-duplicados-20261022.csv, salvo la cuota Sancor de octubre que no es duplicado), El Luchador cargado dos veces
   (3 = 2842) y el Allianz de mayo-2026 de la revisión (2828; la planilla tiene la factura $134.724,39 y el banco debitó
   $134.619,39 por la NC endoso 4 de -$105 del 30/04/2026, que se agrega como Devolución de $105 a favor de Sergio).
   Allianz agosto-2026: se reactiva la fila de la planilla (2273) y se anula la de la revisión (2831).
2. Filas migradas de la planilla: ImporteKgCarne / ImporteUSD = los de la fila de la planilla (columnas F/G Debe, I/J Haber).
3. Resto (revisión, sin valuación): 50% kg (IndiceNovillo) y 50% US$ (Dolar BNA billete promedio) a la fecha, última cotización
   disponible (como el VLOOKUP de la planilla); antes del 16/03/2020 100% US$. El mutuo de Lucy (Origen Mutuo2018) no se toca.
Uso: --simular (default) / --aplicar. Idempotente.
"""
import bisect
import csv
import sys
from datetime import date, datetime

import openpyxl

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.cuentas_socios.valuacion import proporciones

PLANILLA = r'C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar\Cajas Giamigli.xlsx'
HOJAS = {1: 'Cuenta Sergio', 2: 'Cuenta Lucy'}
USUARIO = 'Sergio (036, socios 22/10/2026)'
INICIO_NOVILLO = date(2020, 3, 16)


def _d(v):
    return v if isinstance(v, date) and not isinstance(v, datetime) else datetime.fromisoformat(str(v)[:19]).date()


def cotizaciones():
    nov = sorted((_d(r['f']), float(r['i'])) for r in fetch_all('SELECT Fecha f, Indice i FROM dbo.IndiceNovillo WHERE Indice IS NOT NULL'))
    dol = sorted((_d(r['f']), float(r['p'])) for r in fetch_all('SELECT Fecha f, Prom_billete p FROM dbo.[Dolar BNA] WHERE Prom_billete IS NOT NULL'))
    return nov, dol


def cot(serie, f):
    i = bisect.bisect_right([x[0] for x in serie], f) - 1
    return serie[i][1] if i >= 0 else None


def duplicados():
    ids = set()
    with open(r'C:\dev\LaHerencia\backups\socios-duplicados-20261022.csv', encoding='utf-8-sig') as fh:
        for r in list(csv.reader(fh, delimiter=';'))[1:]:
            if 'Sancor' not in r[11]:
                ids.add(int(r[2]))
    return ids | {3, 2828, 2831}


def filas_planilla(socio):
    wb = openpyxl.load_workbook(PLANILLA, data_only=True, read_only=True)
    out = []
    for r in wb[HOJAS[socio]].iter_rows(min_row=3, values_only=True):
        if not (r[0] and hasattr(r[0], 'year')):
            continue
        n = lambda v: float(v) if isinstance(v, (int, float)) else 0.0
        out.append({'f': r[0].date(), 'debe': n(r[4]), 'kgd': n(r[5]), 'usdd': n(r[6]), 'haber': n(r[7]), 'kgh': n(r[8]), 'usdh': n(r[9])})
    return out


def main():
    _assert_target_is_wc()
    aplicar = '--aplicar' in sys.argv
    nov, dol = cotizaciones()
    dup = duplicados()
    st = []
    # 1. duplicados
    for i in sorted(dup):
        st.append(("UPDATE dbo.MovimientosCuentaSocio SET Anulada=1, MotivoAnulacion=?, UsuarioAnulacion=?, FechaAnulacion=SYSDATETIME() "
                   "WHERE IdMovimiento=? AND Anulada=0 AND Usuario<>'migracion-cajas-giamigli'",
                   ('Duplicado de una fila de la planilla Cajas Giamigli (auditoría socios 22/10/2026)', USUARIO, i)))
    st.append(("UPDATE dbo.MovimientosCuentaSocio SET Anulada=0, MotivoAnulacion=NULL, UsuarioAnulacion=NULL, FechaAnulacion=NULL "
               "WHERE IdMovimiento=2273 AND Anulada=1", ()))
    if not fetch_all("SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=1 AND Motivo LIKE 'Allianz NC endoso 4%'"):
        st.append(("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Medio,Motivo,Usuario,Anulada) "
                   "VALUES (1,'Devolucion',105,?,?,'2026-04-30','Nota de crédito',?,?,0)",
                   (round(105 * 0.5 / cot(dol, date(2026, 4, 30)), 4), round(105 * 0.5 / cot(nov, date(2026, 4, 30)), 4),
                    'Allianz NC endoso 4 (30/04/2026, ajuste impositivo -$105) sobre la cuota de mayo-2026 de la Taos; la planilla tiene la '
                    'factura $134.724,39 y el banco debitó $134.619,39', USUARIO)))
    resumen = {}
    for socio in (1, 2):
        P = filas_planilla(socio)
        movs = fetch_all("SELECT IdMovimiento i, Tipo t, Importe m, Fecha f, Origen o, Usuario u, ImporteUSD usd, ImporteKgCarne kg, Anulada a "
                         "FROM dbo.MovimientosCuentaSocio WHERE IdSocio=?", (socio,))
        usados = set()
        sync = val = 0
        for x in movs:
            if x['i'] in dup or x['o'] == 'Mutuo2018' or (x['a'] and x['i'] != 2273):
                continue
            f, m = _d(x['f']), float(x['m'])
            if x['u'] == 'migracion-cajas-giamigli':
                lado = 'debe' if x['t'] == 'AsignacionGasto' else 'haber'
                cand = [k for k, p in enumerate(P) if k not in usados and p['f'] == f and abs(p[lado] - m) < 0.01]
                if not cand:
                    continue
                k = cand[0]; usados.add(k); p = P[k]
                kg, usd = (p['kgd'], p['usdd']) if lado == 'debe' else (p['kgh'], p['usdh'])
                if abs((x['kg'] or 0) - kg) > 0.01 or abs((x['usd'] or 0) - usd) > 0.01:
                    st.append(('UPDATE dbo.MovimientosCuentaSocio SET ImporteKgCarne=?, ImporteUSD=? WHERE IdMovimiento=?', (round(kg, 4), round(usd, 4), x['i'])))
                    sync += 1
            elif not (x['kg'] or x['usd']):
                parte_kg, parte_usd = proporciones(f)
                kg = m * parte_kg / cot(nov, f) if parte_kg else 0.0
                usd = m * parte_usd / cot(dol, f)
                st.append(('UPDATE dbo.MovimientosCuentaSocio SET ImporteKgCarne=?, ImporteUSD=? WHERE IdMovimiento=?', (round(kg, 4), round(usd, 4), x['i'])))
                val += 1
        resumen[socio] = (sync, val)
    print('duplicados a anular', len(dup), '| resincronizadas con la planilla / valorizadas:', resumen, '| sentencias', len(st))
    if aplicar:
        from src.features.vinculos.backup import backup_verificado
        print(backup_verificado('socios-valuacion-036'))
        with reconciliation_transaction():
            execute_write_transaction(st)
    from src.features.cuentas_socios.repository import calcular_saldo
    for s in (1, 2):
        print(s, calcular_saldo(s))


if __name__ == '__main__': main()
