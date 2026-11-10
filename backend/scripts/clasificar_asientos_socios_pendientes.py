"""Clasifica los asientos de socios sin vínculo (Origen NULL y sin referencia desde otras tablas) por el documento que
los respalda en el sistema: factura de compra, obligación de impuesto o recibo de sueldo (Sergio 10/11/2026).
Solo lectura. Uso: python -m scripts.clasificar_asientos_socios_pendientes [salida.xlsx]
"""
import re
import sys
from collections import Counter
from datetime import date, timedelta

from src.db.connection import fetch_all

PENDIENTES = """
SELECT m.IdMovimiento i, m.IdSocio s, so.Nombre socio, m.Tipo t, CAST(m.Importe AS float) imp, CONVERT(date,m.Fecha) f, m.Medio me, m.Motivo mo
FROM dbo.MovimientosCuentaSocio m JOIN dbo.Socios so ON so.IdSocio=m.IdSocio
WHERE m.Origen IS NULL AND m.Anulada=0
 AND NOT EXISTS (SELECT 1 FROM dbo.PagosSocioProveedor x WHERE x.IdMovimientoSocio=m.IdMovimiento)
 AND NOT EXISTS (SELECT 1 FROM dbo.ImpuestosParticulares x WHERE x.IdMovimientoSocio=m.IdMovimiento)
 AND NOT EXISTS (SELECT 1 FROM dbo.ImpuestosParticularesDevoluciones x WHERE x.IdMovimientoSocio=m.IdMovimiento)
 AND NOT EXISTS (SELECT 1 FROM dbo.TrabajosEventualesPagos x WHERE x.IdMovimientoSocio=m.IdMovimiento)
 AND NOT EXISTS (SELECT 1 FROM dbo.EfectosOperacionCaja x WHERE x.TipoEfecto='MovimientoSocio' AND x.IdRegistro=m.IdMovimiento)
 AND NOT EXISTS (SELECT 1 FROM dbo.ArcaDocumentos x WHERE x.Origen='Pago por socio' AND x.IdOrigen=m.IdMovimiento)
ORDER BY m.Fecha"""

ORGANISMO = {'afip': 119, 'arca': 119, 'arba': 12, 'tasa vial': 72, 'municipalidad': 72}


def _d(x):
    return date.fromisoformat(str(x)[:10])


def _proveedor(mo):
    return re.split(r'\s+[—–-]\s+', mo or '')[0].strip()


def main(salida=None):
    pend = fetch_all(PENDIENTES, ())
    compras = fetch_all("SELECT c.IdDeuda id, c.IdContacto k, ct.[Razon Social] p, CONVERT(date,c.Fecha) f, CAST(t.GranTotal AS float) g, c.[Nro Documento] n "
                        "FROM dbo.Compras c JOIN dbo.Contactos ct ON ct.IdContacto=c.IdContacto JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda", ())
    pagadas = {r['i'] for r in fetch_all("SELECT DISTINCT IdDocumentoAplicado i FROM dbo.AplicacionesPago WHERE Anulada=0 AND TipoDocumento LIKE '%ompra%'", ())} if fetch_all(
        "SELECT 1 x FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='AplicacionesPago'", ()) else set()
    impuestos = fetch_all("SELECT IdImpuesto id, IdOrganismo o, CONVERT(date,Fecha) f, CAST(Importe AS float) imp, [Periodo liquidado] per FROM dbo.Impuestos", ())
    sueldos = fetch_all("SELECT r.IdSalario id, ct.[Razon Social] p, CONVERT(date,r.[Fecha de pago]) f, r.[Periodo liquidado] per FROM dbo.Remuneraciones r "
                        "JOIN dbo.Contactos ct ON ct.IdContacto=r.IdContacto", ())
    filas, cnt = [], Counter()
    for a in pend:
        prov = _proveedor(a['mo'])
        f = _d(a['f'])
        cat, doc, nota = 'sin respaldo en el sistema', '', ''
        key = prov.lower()
        org = next((v for k, v in ORGANISMO.items() if key.startswith(k) or k in (a['mo'] or '').lower()[:20]), None)
        if org:
            m = [i for i in impuestos if i['o'] == org and abs(i['imp'] - a['imp']) < 0.01 and abs((_d(i['f']) - f).days) <= 15]
            cat = 'impuesto' if len(m) == 1 else ('impuesto (varios)' if m else 'impuesto sin obligación cargada')
            doc = ', '.join(str(i['id']) for i in m[:3])
        elif 'irma' in key or 'sierra' in key or 'mori' in key or 'sueldo' in (a['mo'] or '').lower():
            tok = key.split()[0] if key else ''
            m = [s for s in sueldos if tok and tok in str(s['p']).lower() and abs((_d(s['f']) - f).days) <= 20]
            cat = 'sueldo' if len(m) == 1 else ('sueldo (varios)' if m else 'sueldo sin recibo cargado')
            doc = ', '.join(str(s['id']) for s in m[:3])
        elif prov and a['t'] == 'Devolucion':
            tok = key.split()[0] if key else ''
            m = [c for c in compras if tok and len(tok) > 2 and tok in str(c['p']).lower() and abs(c['g'] - a['imp']) < 0.01
                 and -45 <= (f - _d(c['f'])).days <= 10]
            cat = 'factura' if len(m) == 1 else ('factura (varias)' if m else 'factura no encontrada')
            doc = ', '.join(f"{c['id']} {c['n']}" for c in m[:3])
            nota = 'ya tiene pagos aplicados' if any(c['id'] in pagadas for c in m) else ''
        elif a['t'] == 'AsignacionGasto':
            cat = 'cargo al socio sin origen'
        cnt[cat] += 1
        filas.append([a['i'], a['socio'], a['t'], f, a['imp'], a['me'], a['mo'], cat, doc, nota])
    for k, v in cnt.most_common():
        print(f'{v:4}  {k}')
    if salida:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Pendientes'
        ws.append(['Asiento', 'Socio', 'Tipo', 'Fecha', 'Importe', 'Medio', 'Concepto', 'Clasificación', 'Documento candidato', 'Nota'])
        for r in filas:
            ws.append(r)
        wb.save(salida)
        print('guardado', salida)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
