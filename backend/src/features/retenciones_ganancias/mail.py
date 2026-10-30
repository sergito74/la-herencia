"""Borrador del mail al estudio contable para que emita el certificado de retención (Sergio 30/10/2026).

Mismo formato que los mails enviados a administracion@estudiocriado.com desde 2021: detalle por factura y facturas
adjuntas. Se descarga como .eml sin enviar (X-Unsent) para que Outlook lo abra como borrador; el sistema no envía nada.
"""
import mimetypes
import os
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
    return f'{d:%d/%m/%Y}' if d else ''


def _archivos(doc: str | None) -> list[str]:
    out = []
    for p in (doc or '').split('#'):
        p = p.strip()
        f = p if os.path.isabs(p) else os.path.join(COMPRAS, p)
        if p and os.path.isfile(f):
            out.append(f)
    return out


def armar(orden: dict) -> tuple[bytes, list[str]]:
    """Devuelve el .eml y los avisos (facturas sin archivo para adjuntar)."""
    ids = [f['idCompra'] for f in orden['facturas']]
    marcas = ','.join('?' * len(ids))
    compras = {c['i']: c for c in fetch_all(
        f'SELECT IdDeuda i,Fecha f,[Fecha Vto] v,[Tipo documento] t,[Nro Documento] n,[Documento Original] d,Moneda m,[Tipo de Cambio] tc '
        f'FROM dbo.Compras WHERE IdDeuda IN ({marcas})', tuple(ids))}
    forma = ' / '.join(dict.fromkeys(FORMA.get(m['medio'], m['medio']) for m in orden['medios']))
    filas, adjuntos, avisos = [], [], []
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
            avisos.append(f"La factura {c['n']} no tiene archivo para adjuntar")
        adjuntos += archivos
    columnas = COLUMNAS + ('Tipo Cambio', 'Importe pesos') if any(r[6] == 'Dolares' for r in filas) else COLUMNAS
    filas = [r if len(columnas) > len(COLUMNAS) else r[:len(COLUMNAS)] for r in filas]
    varias = len(orden['facturas']) > 1
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
