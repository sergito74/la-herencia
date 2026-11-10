"""Vincula asientos manuales de socios (Origen NULL) con su movimiento en los extractos de la empresa (Sergio 10/11/2026).

Solo se vincula cuando el par es seguro: mismo importe exacto, ±5 días, sentido coherente (cargo al socio = débito
de la empresa; haber del socio = crédito), el movimiento de banco no está usado por otro asiento de socio y el par es
único en las dos direcciones. No cambia importes ni fechas: solo completa Origen/IdOrigen (saldos iguales al centavo).
Uso: python -m scripts.vincular_asientos_socios_banco [--aplicar]
"""
import sys
from collections import defaultdict
from datetime import date, datetime

from src.db.connection import execute_write_transaction, fetch_all

MEDIOS = {'Galicia': 'Galicia', 'Banco Galicia': 'Galicia', 'Banco Nacion': 'Banco Nacion', 'BNA': 'Banco Nacion'}
DIAS = 5
# Contactos que identifican al socio en el banco (contactos.SOCIO_CONTACTO + Sergio empleado 375).
CONTACTOS_SOCIO = {1: (5670, 375), 2: (390,), 3: (549,), 4: (564,)}
# Retiros anotados en la cuenta del Condominio («Lucy — Retiro…»): el par es la transferencia a ese socio.
POR_NOMBRE = {'Lucy': (390,), 'Ceci': (564,), 'Sergio': (5670, 375)}


def _contactos(a):
    if a['s'] == 3:
        for n, c in POR_NOMBRE.items():
            if str(a['mo'] or '').startswith(f'{n} '):
                return c
    return CONTACTOS_SOCIO.get(a['s'], ())


def _d(x):
    return x.date() if isinstance(x, datetime) else date.fromisoformat(str(x)[:10])


def banco():
    usados = {(r['o'], r['i']) for r in fetch_all(
        "SELECT Origen o, IdOrigen i FROM dbo.MovimientosCuentaSocio WHERE Origen IN ('Galicia','Banco Nacion','BNACondominio036')", ())}
    usados |= {('Banco Nacion', i) for o, i in list(usados) if o == 'BNACondominio036'}
    out = []
    for r in fetch_all("SELECT IdMovimiento i, Fecha f, CAST(ISNULL([Débitos],0) AS float) d, CAST(ISNULL([Créditos],0) AS float) c, "
                       "[Descripción] t, LeyendasAdicionales1 l, IdContacto k FROM dbo.[Movimientos Galicia]", ()):
        out.append(('Galicia', r['i'], _d(r['f']), round(r['d'], 2), round(r['c'], 2), f"{r['t']} {r['l'] or ''}".strip(), r['k']))
    for r in fetch_all("SELECT IdMovimientoBNA i, [Fecha / Hora Mov#] f, CAST(Importe AS float) imp, Concepto t, IdContacto k FROM dbo.[Movimientos BNA]", ()):
        v = round(r['imp'] or 0, 2)
        out.append(('Banco Nacion', r['i'], _d(r['f']), -v if v < 0 else 0.0, v if v > 0 else 0.0, r['t'] or '', r['k']))
    return [b for b in out if (b[0], b[1]) not in usados]


def proponer():
    asientos = fetch_all("SELECT IdMovimiento i, IdSocio s, Tipo t, CAST(Importe AS float) imp, Fecha f, Medio m, Motivo mo "
                         "FROM dbo.MovimientosCuentaSocio WHERE Origen IS NULL AND Anulada=0 AND Medio IN (%s)"
                         % ','.join('?' * len(MEDIOS)), tuple(MEDIOS))
    por_importe = defaultdict(list)
    for b in banco():
        por_importe[(b[0], b[3] or b[4], 'debito' if b[3] else 'credito')].append(b)
    cands = {}
    for a in asientos:
        sentido = 'debito' if a['t'] == 'AsignacionGasto' else 'credito'
        f = _d(a['f'])
        cands[a['i']] = [b for b in por_importe[(MEDIOS[a['m']], round(a['imp'], 2), sentido)] if abs((b[2] - f).days) <= DIAS]
    uso = defaultdict(int)
    for lista in cands.values():
        for b in lista:
            uso[(b[0], b[1])] += 1
    seguros, dudosos, sin, reclamos = [], [], [], defaultdict(list)
    by_id = {a['i']: a for a in asientos}
    for i, lista in cands.items():
        a = by_id[i]
        lista = [b for b in lista if b[6]]  # sin contacto en el banco no se puede confirmar de quién es
        propios = [b for b in lista if b[6] in _contactos(a)]
        if len(lista) == 1 and uso[(lista[0][0], lista[0][1])] == 1:
            seguros.append((a, lista[0]))
        elif len(propios) == 1:
            reclamos[propios[0][:2]].append((a, propios[0]))  # el par lo define el contacto del socio en el banco
        elif lista:
            dudosos.append((a, lista))
        else:
            sin.append(a)
    for pares in reclamos.values():
        if len(pares) == 1:
            seguros.append(pares[0])
        else:
            dudosos += [(a, [b]) for a, b in pares]
    return seguros, dudosos, sin


if __name__ == '__main__':
    seguros, dudosos, sin = proponer()
    print(f'seguros {len(seguros)} | dudosos {len(dudosos)} | sin par en el extracto de la empresa {len(sin)}')
    nombres = {r['i']: r['n'] for r in fetch_all('SELECT IdContacto i,[Razon Social] n FROM dbo.Contactos', ())}
    for a, b in seguros:
        print(f"  {a['i']} s{a['s']} {_d(a['f'])} {a['imp']:>13,.2f} {a['mo']!s:42.42} | {b[0][:3]} {b[1]} {b[2]} | {str(nombres.get(b[6]))[:28]}")
    for a, l in dudosos[:10]:
        print(f"  DUDOSO {a['i']} {_d(a['f'])} {a['imp']:,.2f} {a['mo']!s:40.40} -> {[(b[0], b[1], str(b[2])) for b in l]}")
    if '--aplicar' in sys.argv:
        saldo = "SELECT IdSocio s, SUM(CASE WHEN Tipo='AsignacionGasto' THEN 1 ELSE -1 END*(Importe+ImporteUSD*1000+ImporteKgCarne*100000)) v FROM dbo.MovimientosCuentaSocio WHERE Anulada=0 GROUP BY IdSocio"
        antes = fetch_all(saldo, ())
        execute_write_transaction([("UPDATE dbo.MovimientosCuentaSocio SET Origen=?, IdOrigen=? WHERE IdMovimiento=? AND Origen IS NULL",
                                    (b[0], b[1], a['i'])) for a, b in seguros])
        assert fetch_all(saldo, ()) == antes, 'los saldos cambiaron'
        print('aplicado', len(seguros), '- saldos iguales')
