"""Borrador del mail al estudio contable para que emita el certificado de retención (Sergio 30/10/2026).

Mismo formato que los mails enviados a administracion@estudiocriado.com desde 2021: detalle por factura y facturas
adjuntas. Se descarga como .eml sin enviar (X-Unsent) para que Outlook lo abra como borrador; el sistema no envía nada.
"""
import mimetypes
import os
from datetime import date
from email.message import EmailMessage
from html import escape

from src.db.connection import fetch_all
from src.features.descarga_peajes.portales import COMPRAS

PARA = 'administracion@estudiocriado.com'
COPIA = 'rcriado@estudiocriado.com'
FORMA = {'Transferencia': 'Transferencia bancaria', 'Cheque': 'Cheque Electronico', 'Efectivo': 'Efectivo'}
COLUMNAS = ('Fecha', 'Vencimiento', 'Fecha pago', 'Proveedor', 'Tipo Documento', 'Nro. Documento', 'Moneda',
            'Forma de pago', 'Importe')


def _pesos(v) -> str:
    entero, dec = f'{float(v):,.2f}'.split('.')
    return f"$ {entero.replace(',', '.')},{dec}"


def _fecha(d) -> str:
    if isinstance(d, str):  # el repositorio devuelve fechas ISO como texto
        d = date.fromisoformat(d[:10]) if d else None
    return f'{d:%d/%m/%Y}' if d else ''


def _archivos(doc: str | None) -> list[str]:
    out = []
    for p in (doc or '').split('#'):
        p = p.strip()
        f = p if os.path.isabs(p) else os.path.join(COMPRAS, p)
        if p and os.path.isfile(f):
            out.append(f)
    return out


def armar(ordenes: dict | list[dict]) -> tuple[bytes, list[str]]:
    """Un solo mail con todas las órdenes (Sergio 10/11/2026). Devuelve el .eml y los avisos (facturas sin archivo)."""
    ordenes = [ordenes] if isinstance(ordenes, dict) else ordenes
    if not ordenes:
        raise ValueError('Elegí al menos una orden de pago')
    ids = list(dict.fromkeys(f['idCompra'] for o in ordenes for f in o['facturas']))
    marcas = ','.join('?' * len(ids))
    # Vencimiento: dbo.[Vencimiento Compras] (A Plazo); si no hay, Contado = fecha de la factura. Nunca Compras.[Fecha Vto].
    compras = {c['i']: c for c in fetch_all(
        f'SELECT c.IdDeuda i,c.Fecha f,ISNULL(v.vto,c.Fecha) v,c.[Tipo documento] t,c.[Nro Documento] n,'
        f'c.[Documento Original] d,c.Moneda m,c.[Tipo de Cambio] tc FROM dbo.Compras c LEFT JOIN '
        f'(SELECT IdCompra,MAX([Fecha de vencimiento]) vto FROM dbo.[Vencimiento Compras] GROUP BY IdCompra) v '
        f'ON v.IdCompra=c.IdDeuda WHERE c.IdDeuda IN ({marcas})', tuple(ids))}
    filas, adjuntos, avisos = [], [], []
    for orden in ordenes:
        forma = ' / '.join(dict.fromkeys(FORMA.get(m['medio'], m['medio']) for m in orden['medios']))
        for f in orden['facturas']:
            c = compras[f['idCompra']]
            fila = [_fecha(c['f']), _fecha(c['v']), _fecha(orden['fechaPago']), orden['proveedor'], c['t'] or 'Factura', c['n'] or '']
            if c.get('m') == 'Dolares':  # como en los mails de siempre: importe en US$, TC del comprobante e importe en pesos
                tc = float(c['tc'])
                filas.append((*fila, 'Dolares', forma, _pesos(float(f['importe']) / tc).replace('$', 'US$'),
                              f"$ {_pesos(tc)[2:]}/u$s", _pesos(f['importe'])))
            else:
                filas.append((*fila, 'Pesos', forma, _pesos(f['importe']), '', _pesos(f['importe'])))
            archivos = _archivos(c['d'])
            if not archivos:
                avisos.append(f"La factura {c['n'] or 'sin número'} de {orden['proveedor']} no tiene archivo para adjuntar")
            adjuntos += archivos
    columnas = COLUMNAS + ('Tipo Cambio', 'Importe pesos') if any(r[6] == 'Dolares' for r in filas) else COLUMNAS
    filas = [r if len(columnas) > len(COLUMNAS) else r[:len(COLUMNAS)] for r in filas]
    varias = len(filas) > 1
    intro = (f"Te mando adjunta{'s' if varias else ''} {'facturas' if varias else 'una factura'} para hacer el cálculo de la "
             f"retención de acuerdo al siguiente detalle:")
    texto = '\n'.join(['Hola Karen, buen día.', '', intro, '', ' | '.join(columnas)] + [' | '.join(r) for r in filas]
                      + ['', 'Gracias!', 'Saludos,', 'Sergio'])
    celda = 'style="border:1px solid #999;padding:3px 6px"'
    tabla = ('<table style="border-collapse:collapse">' + '<tr>' + ''.join(f'<th {celda}>{escape(c)}</th>' for c in columnas) + '</tr>'
             + ''.join('<tr>' + ''.join(f'<td {celda}>{escape(str(v))}</td>' for v in r) + '</tr>' for r in filas) + '</table>')
    html = (f'<p>Hola Karen, buen día.</p><p>{escape(intro)}</p>{tabla}<p>Gracias!<br>Saludos,<br>Sergio</p>')
    msg = EmailMessage()
    msg['To'] = PARA
    msg['Cc'] = COPIA
    msg['Subject'] = 'Giamigli de Bolivar S.A. - Retencion' + ('es' if varias else '')
    msg['X-Unsent'] = '1'
    msg.set_content(texto)
    msg.add_alternative(html, subtype='html')
    for a in dict.fromkeys(adjuntos):
        tipo, _ = mimetypes.guess_type(a)
        principal, sub = (tipo or 'application/octet-stream').split('/')
        with open(a, 'rb') as fh:
            msg.add_attachment(fh.read(), maintype=principal, subtype=sub, filename=os.path.basename(a))
    return bytes(msg), avisos
