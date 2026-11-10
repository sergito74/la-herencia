"""Vincula asientos manuales de socios (Origen NULL) con su movimiento en las cajas de efectivo de Giamigli (Sergio 10/11/2026).

Lógica de la planilla Cajas Giamigli: el socio fondea la caja en efectivo (haber del socio = entrada en la caja) y la caja le
devuelve o le paga en efectivo (debe del socio = salida de la caja). Par seguro: mismo importe exacto con el signo de la caja
coherente, ±2 días, caja GiamigliSA o CampoChica, movimiento de caja no usado por otro asiento y único en ambas direcciones.
Solo completa Origen='CajaGiamigli036' / IdOrigen; saldos verificados iguales. Uso: python -m scripts.vincular_asientos_socios_caja [--aplicar]
"""
import sys
from collections import defaultdict
from datetime import date

from src.db.connection import execute_write_transaction, fetch_all

ORIGEN = 'CajaGiamigli036'
DIAS = 2


def _d(x):
    return date.fromisoformat(str(x)[:10])


def proponer():
    usados = {r['i'] for r in fetch_all("SELECT IdOrigen i FROM dbo.MovimientosCuentaSocio WHERE Origen=?", (ORIGEN,))}
    caja = [c for c in fetch_all("SELECT IdMovimiento i, Caja c, Fecha f, Concepto co, CAST(Importe AS float) imp FROM dbo.MovimientosCajaEfectivo "
                                 "WHERE Anulada=0 AND Caja IN ('GiamigliSA','CampoChica')", ()) if c['i'] not in usados]
    asientos = fetch_all("SELECT IdMovimiento i, IdSocio s, Tipo t, CAST(Importe AS float) imp, Fecha f, Medio m, Motivo mo "
                         "FROM dbo.MovimientosCuentaSocio WHERE Origen IS NULL AND Anulada=0 AND Medio LIKE '%fectivo%'", ())
    por = defaultdict(list)
    for c in caja:
        por[round(c['imp'], 2)].append(c)
    cands = {}
    for a in asientos:
        signo = 1 if a['t'] == 'Devolucion' else -1  # haber del socio = entra plata a la caja
        cands[a['i']] = [c for c in por[round(signo * a['imp'], 2)] if abs((_d(c['f']) - _d(a['f'])).days) <= DIAS]
    uso = defaultdict(int)
    for l in cands.values():
        for c in l:
            uso[c['i']] += 1
    by = {a['i']: a for a in asientos}
    seguros = [(by[i], l[0]) for i, l in cands.items() if len(l) == 1 and uso[l[0]['i']] == 1]
    return seguros, sum(1 for l in cands.values() if len(l) > 1 or (l and uso[l[0]['i']] > 1)), sum(1 for l in cands.values() if not l)


if __name__ == '__main__':
    seguros, dudosos, sin = proponer()
    print(f'seguros {len(seguros)} | ambiguos {dudosos} | sin entrada en caja {sin}')
    for a, c in seguros:
        print(f"  {a['i']} s{a['s']} {_d(a['f'])} {a['imp']:>11,.2f} {str(a['mo'])[:44]:44} | {c['c'][:6]} {c['i']} {_d(c['f'])} {str(c['co'])[:40]}")
    if '--aplicar' in sys.argv:
        q = ("SELECT IdSocio s, SUM(CASE WHEN Tipo='AsignacionGasto' THEN 1 ELSE -1 END*(Importe+ImporteUSD*1000+ImporteKgCarne*100000)) v "
             "FROM dbo.MovimientosCuentaSocio WHERE Anulada=0 GROUP BY IdSocio")
        antes = fetch_all(q, ())
        execute_write_transaction([("UPDATE dbo.MovimientosCuentaSocio SET Origen=?, IdOrigen=? WHERE IdMovimiento=? AND Origen IS NULL",
                                    (ORIGEN, c['i'], a['i'])) for a, c in seguros])
        assert fetch_all(q, ()) == antes, 'los saldos cambiaron'
        print('aplicado', len(seguros), '- saldos iguales')
