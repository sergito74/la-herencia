"""Cargill (258): alta de 17 facturas/notas del portal que faltaban en el sistema (PDF del portal, 20/10/2026).

Cada renglón replica el reparto (centro, destino, rubro, campaña) de su comprobante de origen, en proporción al neto:
- Diferencia de cambio (ND 5848-515/2356/4532, NC 5850-1993): Ajusta Tipo Cambio, renglones financieros.
- Percepción IVA (notas 7050): rubro Gastos Comercialización, sin IVA.
- Honorarios de laboratorio / fumigación: cultivo y campaña del grano; logística: soja 24/25, Gastos Comercialización.
- Silo bolsa (FC 5850-9422, NC 5850-1948): como el silo bolsa de FC 5850-10054 (rubro 8, soja segunda 24/25).
PDF copiado a Dropbox/Compras/<ejercicio>. Verifica total = PDF. Idempotente.
"""
import json

import shutil
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
COMPRAS = Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras')
LAB, COM = 2047893494, 2047893445


def fijo(destino, campania, rubro, cc=1):
    return {'idDestino': destino, 'campaña': campania, 'idRubro': rubro, 'idCentroCosto': cc}


# nro: (tipo doc, renglones [(producto, importe neto, iva, clasificación o 'ref:<nro>')], ajusta TC)
PLAN = {
    '5850-00007633': ('Factura', [('Honorarios laboratorio', 44.07, 21, fijo(6, '2023/2024', LAB))], False),
    '5850-00009578': ('Factura', [('Honorarios laboratorio', 35.77, 21, fijo(8, '2024/2025', LAB)), ('Fumigada planta', 22.57, 21, fijo(8, '2024/2025', LAB))], False),
    '5850-00010778': ('Factura', [('Honorarios laboratorio', 49.23, 21, fijo(6, '2024/2025', LAB))], False),
    '5850-00010872': ('Factura', [('Servicio logistica', 97108.97, 21, fijo(6, '2024/2025', COM))], False),
    '5850-00009422': ('Factura', [('Silo bolsa 9 x 60', 455.00, 21, 'silo')], False),
    '5850-00001948': ('Nota de Crédito', [('Silo bolsa 9 x 75', -41215.20, 21, 'silo')], False),
    '5850-00001993': ('Nota de Crédito', [('Dif. tipo cambio silo bolsa FC 5850-9422', -436079.80, 21, 'ref:5850-00009422')], True),
    '5848-00000515': ('Nota de Débito', [('Dif. tipo cambio FC 5850-1569', 1438.15, 10.5, 'ref:5850-00001569')], True),
    '5848-00002356': ('Nota de Débito', [('Dif. tipo cambio FC 5850-5539', 6650.71, 21, 'ref:5850-00005539')], True),
    '5848-00004532': ('Nota de Débito', [('Dif. tipo cambio FC 5850-10054', 90221.37, 21, 'ref:5850-00010054')], True),
    '7050-00085557': ('Nota de Crédito', [('Percepcion IVA RG general FC 5850-5482', -272.28, 0, 'ref:5850-00005482:com')], False),
    '7050-00162915': ('Nota de Crédito', [('Percepcion IVA RG general FC 5850-9578', -1.75, 0, 'ref:5850-00009578:com')], False),
    '7050-00186671': ('Nota de Crédito', [('Percepcion IVA RG general ND 5848-4532', -2706.64, 0, 'ref:5850-00010054:com')], False),
    '7050-00186672': ('Nota de Crédito', [('Percepcion IVA RG general FC 5850-10054', -13.73, 0, 'ref:5850-00010054:com')], False),
    '7050-00186673': ('Nota de Crédito', [('Percepcion IVA RG general FC 5850-10778', -1.48, 0, 'ref:5850-00010778:com')], False),
    '7050-00076972': ('Nota de Débito', [('Percepcion IVA RG general FC 5850-12456', 570.54, 0, 'ref:5850-00012456:com')], False),
    '7050-00077233': ('Nota de Débito', [('Percepcion IVA RG general FC 5850-12456', 10422.48, 0, 'ref:5850-00012456:com')], False),
}


def lineas_de(nro):
    return fetch_all('SELECT d.* FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda=d.IdCompra WHERE c.IdContacto=258 AND c.[Nro Documento]=?', (nro,))


def repartir(prod, neto, iva, clasif, financiero):
    if isinstance(clasif, dict):
        return [{'productoServicio': prod, 'cantidad': 1, 'precioUnitario': neto, 'iva': iva, 'ajusteFinanciero': financiero, **clasif}]
    if clasif == 'silo':
        src = [r for r in lineas_de('5850-00010054') if 'ilo' in r['Producto/Servicio']]
        rubro = None
    else:
        partes = clasif.split(':')
        src, rubro = lineas_de(partes[1]), (COM if len(partes) > 2 else None)
    assert src, clasif
    pesos = [abs(r['Cantidad'] * r['Precio Unitario']) for r in src]
    tot = sum(pesos)
    cents = [int(round(neto * 100)) * w / tot for w in pesos]
    base = [int(c) for c in cents]
    for k in sorted(range(len(base)), key=lambda k: -(abs(cents[k]) - abs(base[k])))[:abs(int(round(neto * 100)) - sum(base))]:
        base[k] += 1 if neto > 0 else -1
    return [{'productoServicio': prod, 'cantidad': 1, 'precioUnitario': b / 100, 'iva': iva, 'ajusteFinanciero': financiero,
             'idCentroCosto': r['IdCentroCostos'], 'idDestino': r['IdDestino'], 'idRubro': rubro or r['IdRubro'], 'campaña': r['Campaña'],
             'idCampania': r['IdCampaña']} for b, r in zip(base, src) if b]


def archivar(d):
    f = datetime.strptime(d['fecha'], '%d/%m/%Y')
    y = f.year if f.month >= 4 else f.year - 1
    carpeta = COMPRAS / f'04 {y} - 03 {y + 1}'
    nombre = f'{f:%Y%m%d}_Cargill.pdf'
    n = 1
    while (carpeta / nombre).exists():
        n += 1
        nombre = f'{f:%Y%m%d}_Cargill {n:03d}.pdf'
    origen = Path(d['archivo'])
    if not origen.is_absolute():
        origen = (Path(__file__).resolve().parents[1] / origen).resolve()
    shutil.copy2(origen, carpeta / nombre)
    return str(carpeta / nombre)


def main():
    _assert_target_is_wc()
    docs = {v['nro']: v for v in json.load(open(ROOT / 'docs_parseados.json', encoding='utf-8')).values()}
    pend = {n: p for n, p in PLAN.items() if not fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=258 AND [Nro Documento]=?', (n,))}
    if not pend:
        print('Nada pendiente.'); return
    backup = backup_verificado('cargill-comprobantes-faltantes-036')
    creados = {}
    for nro, (tipo, renglones, ajusta) in pend.items():
        d = docs[nro]
        signo = -1 if tipo == 'Nota de Crédito' else 1
        usd = d['moneda'] == 'USD'
        cab = {'idContacto': 258, 'fecha': datetime.strptime(d['fecha'], '%d/%m/%Y'), 'tipoDocumento': tipo, 'tipo': 'A', 'numeroDocumento': nro,
               'moneda': 'Dolares' if usd else 'Pesos', 'tipoDeCambio': d['tc'] if usd else 1, 'percepcionIva': signo * d['percIVA'],
               'ingresosBrutos': signo * d['percIIBB'], 'ajustaTipoCambio': ajusta, 'documentoOriginal': archivar(d)}
        lineas = [l for (p, neto, iva, c) in renglones for l in repartir(p, neto, iva, c, ajusta)]
        for l in lineas:
            l.setdefault('idCampania', compras.get_id_campania_por_nombre(l['campaña']))
        st = [compras._cabecera_insert_statement(cab)] + [compras._linea_insert_statement(l) for l in lineas] + \
             [compras._vencimiento_insert_statement({'fechaVencimiento': cab['fecha']})]
        with reconciliation_transaction():
            i = execute_write_transaction(st)[0]
            g = fetch_all('SELECT GranTotal g FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=?', (i,))[0]['g']
            assert abs(g - signo * d['total']) <= 0.02, (nro, g, d['total'])
        creados[nro] = (i, round(g, 2))
    (ROOT / f'faltantes-{datetime.now():%Y%m%d_%H%M%S}.json').write_text(json.dumps({'backup': backup, 'creados': creados}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(creados))


if __name__ == '__main__': main()
