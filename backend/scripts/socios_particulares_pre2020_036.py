"""Cuentas de socios: pagos Particular L / S de Access anteriores a 2020 sin representar (Sergio 22/10/2026, opción 1).

46 pagos de 2011-2019 (combustible 2012-2015, gastos varios) que no están en la planilla Cajas Giamigli ni en la revisión.
Importe positivo en Pagos efectivo = el socio pagó un gasto de la empresa → Devolución (a favor del socio); negativo = la
empresa pagó un gasto particular → AsignacionGasto. Valuación 100% US$ (Dolar BNA billete promedio a la fecha), como todo
lo anterior al 16/03/2020. Excluye Yanquelen 2018 (cubierto por el mutuo en dólares). Origen 'PagosEfectivo' + IdPagoEfectivo.
Los aportes 2011-2016 ($733.781) son del Condominio LSC para fondear el BNA y no duplican estos pagos (Sergio). Idempotente.
"""
from collections import defaultdict
from datetime import datetime

from scripts.socios_valuacion_036 import cot, cotizaciones
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, particulares pre-2020 22/10/2026)'


def _d(v):
    return v if isinstance(v, datetime) else datetime.fromisoformat(str(v)[:19])


def main():
    _assert_target_is_wc()
    _, dol = cotizaciones()
    pag = fetch_all("SELECT p.IdPagoEfectivo i,p.Caja c,p.Fecha f,p.[Importe imputado] m,co.[Razon Social] rs FROM dbo.[Pagos efectivo] p "
                    "LEFT JOIN dbo.Contactos co ON co.IdContacto=p.IdContacto WHERE p.Caja IN ('Particular L','Particular S')")
    movs = defaultdict(list)
    for x in fetch_all("SELECT IdMovimiento i,IdSocio s,Importe m,Fecha f,Origen o,IdOrigen io FROM dbo.MovimientosCuentaSocio WHERE Anulada=0 AND IdSocio IN (1,2)"):
        movs[x['s']].append(x)
    ya = {x['io'] for v in movs.values() for x in v if x['o'] == 'PagosEfectivo'}
    usado, st = set(), []
    for p in sorted(pag, key=lambda p: _d(p['f'])):
        s = 1 if p['c'].endswith('S') else 2
        m, f = abs(float(p['m'])), _d(p['f'])
        c = [x for x in movs[s] if x['i'] not in usado and abs(float(x['m']) - m) < 1 and abs((_d(x['f']) - f).days) <= 45]
        if c:
            c.sort(key=lambda x: abs((_d(x['f']) - f).days)); usado.add(c[0]['i']); continue
        if f.year >= 2020 or m == 0 or 'Yanquelen' in (p['rs'] or '') or p['i'] in ya:
            continue
        tipo = 'Devolucion' if float(p['m']) > 0 else 'AsignacionGasto'
        st.append(('INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) '
                   "VALUES (?,?,?,?,0,?,'PagosEfectivo',?,?,?,?,0)",
                   (s, tipo, m, round(m / cot(dol, f.date()), 4), f.date().isoformat(), p['i'], p['c'],
                    f"{p['rs'] or 'Sin proveedor'} – pago {p['c']} de Access ({'pagó el socio' if tipo == 'Devolucion' else 'pagó la empresa, gasto particular'})", USUARIO)))
    print('a cargar', len(st))
    if st:
        print(backup_verificado('socios-particulares-pre2020-036'))
        with reconciliation_transaction():
            execute_write_transaction(st)
    from src.features.cuentas_socios.repository import calcular_saldo
    for s in (1, 2):
        print(s, calcular_saldo(s))


if __name__ == '__main__': main()
