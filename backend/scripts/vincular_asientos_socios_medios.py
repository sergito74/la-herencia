"""Vincula cargos a socios (Debe) sin origen con su pago real en un medio de Giamigli (Sergio 10/11/2026): línea de
resumen de tarjeta, débito de Galicia/BNA (±15 días) o movimiento de Mercado Pago. Par único en ambas direcciones,
importe exacto, medio coherente con el que dice el asiento. Solo completa Origen/IdOrigen; saldos verificados.
Uso: python -m scripts.vincular_asientos_socios_medios [--aplicar]
"""
import sys
from collections import defaultdict
from datetime import date

from src.db.connection import execute_write_transaction, fetch_all

TARJETAS = ('mastercard', 'visa', 'corporativa')


def _d(x):
    return date.fromisoformat(str(x)[:10])


def candidatos():
    usados = {(r['o'], r['i']) for r in fetch_all("SELECT Origen o, IdOrigen i FROM dbo.MovimientosCuentaSocio WHERE Anulada=0 AND Origen IS NOT NULL", ())}
    out = []
    for r in fetch_all("SELECT IdLineaConsumo i, FechaCompra f, CAST(Importe AS float) imp, Detalle d FROM dbo.Tarjetas_Resumenes_Lineas", ()):
        out.append(('TarjetaLineaConsumo', r['i'], _d(r['f']), round(r['imp'], 2), r['d'], 10))
    for r in fetch_all("SELECT IdMovimiento i, Fecha f, CAST(ISNULL([Débitos],0) AS float) d, [Descripción] t, LeyendasAdicionales1 l FROM dbo.[Movimientos Galicia] WHERE [Débitos]>0", ()):
        out.append(('Galicia', r['i'], _d(r['f']), round(r['d'], 2), f"{r['t']} {r['l'] or ''}", 15))
    for r in fetch_all("SELECT IdMovimientoBNA i, [Fecha / Hora Mov#] f, CAST(-Importe AS float) d, Concepto t FROM dbo.[Movimientos BNA] WHERE Importe<0", ()):
        out.append(('Banco Nacion', r['i'], _d(r['f']), round(r['d'], 2), r['t'] or '', 15))
    for r in fetch_all("SELECT IdMovimiento i, Fecha f, CAST(-Importe AS float) d, Descripcion t FROM dbo.[Movimientos Mercado Libre] WHERE Importe<0", ()):
        out.append(('MercadoPago', r['i'], _d(r['f']), round(r['d'], 2), r['t'] or '', 5))
    return [c for c in out if (c[0], c[1]) not in usados]


def _medio_ok(medio, origen):
    m = (medio or '').lower()
    if origen == 'TarjetaLineaConsumo':
        return any(t in m for t in TARJETAS)
    if origen == 'Galicia':
        return 'galicia' in m and not any(t in m for t in TARJETAS)
    if origen == 'Banco Nacion':
        return ('nacion' in m or 'bna' in m) and 'corporativa' not in m
    return 'mercado' in m


def proponer():
    asientos = fetch_all("SELECT IdMovimiento i, IdSocio s, CAST(Importe AS float) imp, Fecha f, Medio m, Motivo mo FROM dbo.MovimientosCuentaSocio "
                         "WHERE Origen IS NULL AND Anulada=0 AND Tipo='AsignacionGasto'", ())
    por = defaultdict(list)
    for c in candidatos():
        por[c[3]].append(c)
    cands = {a['i']: [c for c in por[round(a['imp'], 2)] if _medio_ok(a['m'], c[0]) and abs((c[2] - _d(a['f'])).days) <= c[5]] for a in asientos}
    uso = defaultdict(int)
    for l in cands.values():
        for c in l:
            uso[c[:2]] += 1
    by = {a['i']: a for a in asientos}
    # 2799: retiro de Sergio 11/11/2025 cubierto por la transferencia de $650.000 junto con 2209 (no por un débito propio).
    seguros = [(by[i], l[0]) for i, l in cands.items() if len(l) == 1 and uso[l[0][:2]] == 1 and i != 2799]
    return seguros, [(by[i], l) for i, l in cands.items() if len(l) > 1 or (l and uso[l[0][:2]] > 1)]


if __name__ == '__main__':
    seguros, dudosos = proponer()
    print(f'seguros {len(seguros)} | dudosos {len(dudosos)}')
    for a, c in seguros:
        print(f"  {a['i']} s{a['s']} {_d(a['f'])} {a['imp']:>11,.2f} {str(a['m'])[:12]:12} {str(a['mo'])[:38]:38} | {c[0][:7]} {c[1]} {c[2]} {c[4][:34]}")
    for a, l in dudosos:
        print(f"  DUDOSO {a['i']} {_d(a['f'])} {a['imp']:,.2f} {str(a['mo'])[:30]} -> {[(c[0][:7], c[1], str(c[2])) for c in l][:4]}")
    if '--aplicar' in sys.argv:
        q = ("SELECT IdSocio s, SUM(CASE WHEN Tipo='AsignacionGasto' THEN 1 ELSE -1 END*(Importe+ImporteUSD*1000+ImporteKgCarne*100000)) v "
             "FROM dbo.MovimientosCuentaSocio WHERE Anulada=0 GROUP BY IdSocio")
        antes = fetch_all(q, ())
        execute_write_transaction([("UPDATE dbo.MovimientosCuentaSocio SET Origen=?, IdOrigen=? WHERE IdMovimiento=? AND Origen IS NULL",
                                    (c[0], c[1], a['i'])) for a, c in seguros])
        assert fetch_all(q, ()) == antes, 'los saldos cambiaron'
        print('aplicado', len(seguros), '- saldos iguales')
