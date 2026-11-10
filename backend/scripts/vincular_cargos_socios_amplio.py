"""Cargos a socios (Debe) sin origen: busca su contrapartida en compras cargadas, tarjetas, bancos, Mercado Pago o caja
(Sergio 10/11/2026). Candidato único y no usado; solo completa Origen/IdOrigen; saldos verificados.
Uso: python -m scripts.vincular_cargos_socios_amplio [--aplicar]
"""
import sys
from datetime import date

from src.db.connection import execute_write_transaction, fetch_all

D = lambda x: date.fromisoformat(str(x)[:10])


def fuentes():
    usados = {(r['o'], r['i']) for r in fetch_all("SELECT Origen o, IdOrigen i FROM dbo.MovimientosCuentaSocio WHERE Anulada=0 AND Origen IS NOT NULL", ())}
    f = []
    for r in fetch_all("SELECT c.IdDeuda i, c.Fecha f, CAST(t.GranTotal AS float) g, ct.[Razon Social] p FROM dbo.Compras c JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda JOIN dbo.Contactos ct ON ct.IdContacto=c.IdContacto", ()):
        f.append(('CompraParticular', r['i'], D(r['f']), round(r['g'], 2), r['p'], 10))
    for r in fetch_all("SELECT IdLineaConsumo i, FechaCompra f, CAST(Importe AS float) g, Detalle d FROM dbo.Tarjetas_Resumenes_Lineas", ()):
        f.append(('TarjetaLineaConsumo', r['i'], D(r['f']), round(r['g'], 2), r['d'], 15))
    for r in fetch_all("SELECT IdMovimiento i, Fecha f, CAST([Débitos] AS float) g, [Descripción] d FROM dbo.[Movimientos Galicia] WHERE [Débitos]>0", ()):
        f.append(('Galicia', r['i'], D(r['f']), round(r['g'], 2), r['d'], 10))
    for r in fetch_all("SELECT IdMovimientoBNA i, [Fecha / Hora Mov#] f, CAST(-Importe AS float) g, Concepto d FROM dbo.[Movimientos BNA] WHERE Importe<0", ()):
        f.append(('Banco Nacion', r['i'], D(r['f']), round(r['g'], 2), r['d'], 10))
    for r in fetch_all("SELECT IdMovimiento i, Fecha f, CAST(-Importe AS float) g, Descripcion d FROM dbo.[Movimientos Mercado Libre] WHERE Importe<0", ()):
        f.append(('MercadoPago', r['i'], D(r['f']), round(r['g'], 2), r['d'], 7))
    for r in fetch_all("SELECT IdMovimiento i, Fecha f, CAST(-Importe AS float) g, Concepto d FROM dbo.MovimientosCajaEfectivo WHERE Anulada=0 AND Importe<0 AND Caja IN ('GiamigliSA','CampoChica')", ()):
        f.append(('CajaGiamigli036', r['i'], D(r['f']), round(r['g'], 2), r['d'], 5))
    return [x for x in f if (x[0], x[1]) not in usados]


def proponer():
    cargos = fetch_all("""SELECT m.IdMovimiento i, m.IdSocio s, CAST(m.Importe AS float) imp, m.Fecha f, m.Medio me, m.Motivo mo FROM dbo.MovimientosCuentaSocio m
        WHERE m.Anulada=0 AND m.Origen IS NULL AND m.Tipo='AsignacionGasto' AND ISNULL(m.Medio,'') NOT LIKE 'Corrección%'""", ())
    fu = fuentes()
    por = {}
    for x in fu:
        por.setdefault(x[3], []).append(x)
    res = []
    for a in cargos:
        f = D(a['f'])
        c = [x for x in por.get(round(a['imp'], 2), []) if abs((x[2] - f).days) <= x[5]]
        res.append((a, c))
    uso = {}
    for a, c in res:
        for x in c:
            uso[x[:2]] = uso.get(x[:2], 0) + 1
    # Revisados a mano 10/11/2026: 2155 (reintegro vs compra Ceamse), 2290 (ambiguo), 2799 (cubierto por los $650.000).
    seguros = [(a, c[0]) for a, c in res if len(c) == 1 and uso[c[0][:2]] == 1 and a['i'] not in (2155, 2290, 2799)]
    return seguros, [(a, c) for a, c in res if len(c) != 1 or uso[c[0][:2]] > 1]


if __name__ == '__main__':
    seguros, resto = proponer()
    print('seguros', len(seguros), '| resto', len(resto))
    for a, x in seguros:
        print(f"  {a['i']} {D(a['f'])} {a['imp']:>11,.2f} {str(a['me'])[:12]:12} {str(a['mo'])[:36]:36} -> {x[0][:9]} {x[1]} {x[2]} {str(x[4])[:30]}")
    for a, c in resto:
        print(f"  RESTO {a['i']} {D(a['f'])} {a['imp']:,.2f} {str(a['me'])[:12]} {str(a['mo'])[:34]} -> {[(x[0][:7], x[1], str(x[2])) for x in c][:3]}")
    if '--aplicar' in sys.argv:
        q = ("SELECT IdSocio s, SUM(CASE WHEN Tipo='AsignacionGasto' THEN 1 ELSE -1 END*(Importe+ImporteUSD*1000+ImporteKgCarne*100000)) v "
             "FROM dbo.MovimientosCuentaSocio WHERE Anulada=0 GROUP BY IdSocio")
        antes = fetch_all(q, ())
        execute_write_transaction([("UPDATE dbo.MovimientosCuentaSocio SET Origen=?, IdOrigen=? WHERE IdMovimiento=? AND Origen IS NULL",
                                    (x[0], x[1], a['i'])) for a, x in seguros])
        assert fetch_all(q, ()) == antes
        print('aplicado', len(seguros))
