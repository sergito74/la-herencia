"""Borrador del mail al estudio contable para que emita el certificado de retención (Sergio 30/10/2026).

Mismo formato que los mails enviados a administracion@estudiocriado.com desde 2021: detalle por factura y facturas
adjuntas. Se descarga como .eml sin enviar (X-Unsent) para que Outlook lo abra como borrador; el sistema no envía nada.
"""
import mimetypes
import os
from datetime import date, datetime
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


def _cuotas_brutas(factura: dict, medios: list[dict]):
    """Vencimiento e importe bruto de cada cuota que paga la orden (una por medio con fecha), según los vencimientos
    cargados en la compra; la última absorbe la diferencia para que la suma sea lo aplicado a la factura."""
    if not all(m.get('fecha') for m in medios):
        return None
    vtos = {str(v['f'])[:10]: float(v['i']) for v in fetch_all(
        "SELECT [Fecha de vencimiento] f, Importe i FROM dbo.[Vencimiento Compras] WHERE IdCompra=? AND Importe IS NOT NULL",
        (factura['idCompra'],))}
    if not vtos:
        return None
    filas = [(str(m['fecha'])[:10], vtos.get(str(m['fecha'])[:10])) for m in medios]
    if any(i is None for _, i in filas):
        return None
    filas[-1] = (filas[-1][0], round(filas[-1][1] + float(factura['importe']) - sum(i for _, i in filas), 2))
    return filas


def datos(ordenes: dict | list[dict]) -> dict:
    """Un solo mail con todas las órdenes (Sergio 10/11/2026): asunto, cuerpo, PDF a adjuntar y avisos."""
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
        medios = orden['medios']
        forma = ' / '.join(dict.fromkeys(FORMA.get(m['medio'], m['medio']) for m in medios))
        for f in orden['facturas']:
            c = compras[f['idCompra']]
            fila = [_fecha(c['f']), _fecha(c['v']), _fecha(orden['fechaPago']), orden['proveedor'], c['t'] or 'Factura', c['n'] or '']
            # Como en los mails de Sergio (08/04/2026): una factura pagada con dos medios va en una fila por medio.
            partes = ([(FORMA.get(m['medio'], m['medio']), float(m['importe'])) for m in medios]
                      if len(orden['facturas']) == 1 and len(medios) > 1 and all(m.get('importe') for m in medios)
                      else [(forma, float(f['importe']))])
            cuotas = _cuotas_brutas(f, medios) if len(orden['facturas']) == 1 and len(medios) > 1 else None
            if cuotas:
                # Factura en cuotas (12/11/2026): una fila por cuota con su vencimiento y su importe BRUTO; la retención
                # todavía no está confirmada (la calcula el estudio), así que no se descuenta en el cuadro.
                for m, (vto, importe) in zip(medios, cuotas):
                    filas.append((fila[0], _fecha(vto), _fecha(m.get('fecha') or vto), *fila[3:], 'Pesos',
                                  FORMA.get(m['medio'], m['medio']), _pesos(importe), '', _pesos(importe)))
                partes = []
            for forma_i, importe in partes:
                if c.get('m') == 'Dolares':  # importe en US$, TC del comprobante e importe en pesos
                    tc = float(c['tc'])
                    filas.append((*fila, 'Dolares', forma_i, _pesos(importe / tc).replace('$', 'US$'),
                                  f"$ {_pesos(tc)[2:]}/u$s", _pesos(importe)))
                else:
                    filas.append((*fila, 'Pesos', forma_i, _pesos(importe), '', _pesos(importe)))
            archivos = _archivos(c['d'])
            if not archivos:
                avisos.append(f"La factura {c['n'] or 'sin número'} de {orden['proveedor']} no tiene archivo para adjuntar")
            adjuntos += archivos
    columnas = COLUMNAS + ('Tipo Cambio', 'Importe pesos') if any(r[6] == 'Dolares' for r in filas) else COLUMNAS
    filas = [r if len(columnas) > len(COLUMNAS) else r[:len(COLUMNAS)] for r in filas]
    # Formato de los mails de Sergio a Karen (Enviados 2026): saludo según la hora, "una factura" o "N facturas",
    # asunto siempre "Retencion", importes alineados a la derecha.
    n = len(ids)
    saludo = 'Hola Karen, buen día.' if datetime.now().hour < 13 else 'Buenas tardes Karen,'
    intro = (f"Te mando {'adjunta una factura' if n == 1 else f'{n} facturas'} para hacer el cálculo de la "
             f"retención de acuerdo al siguiente detalle:")
    texto = '\n'.join([saludo, '', intro, '', ' | '.join(columnas)] + [' | '.join(r) for r in filas]
                      + ['', 'Gracias!', 'Saludos,', 'Sergio'])
    celda = 'border:1px solid #999;padding:3px 6px;font-family:Calibri,sans-serif;font-size:11pt'
    tabla = ('<table style="border-collapse:collapse">' + '<tr>' + ''.join(f'<th style="{celda}">{escape(c)}</th>' for c in columnas) + '</tr>'
             + ''.join('<tr>' + ''.join(f'<td style="{celda}{";text-align:right" if "$" in str(v) else ""}">{escape(str(v))}</td>'
                                        for v in r) + '</tr>' for r in filas) + '</table>')
    p = 'style="font-family:Calibri,sans-serif;font-size:11pt"'
    html = f'<p {p}>{escape(saludo)}</p><p {p}>{escape(intro)}</p>{tabla}<p {p}>Gracias!<br>Saludos,<br>Sergio</p>'
    return {'asunto': 'Giamigli de Bolivar S.A. - Retencion', 'texto': texto, 'html': html,
            'adjuntos': list(dict.fromkeys(adjuntos)), 'avisos': avisos}


def armar(ordenes: dict | list[dict]) -> tuple[bytes, list[str]]:
    """Alternativa sin Outlook: .eml sin enviar (X-Unsent) con las facturas adjuntas."""
    d = datos(ordenes)
    msg = EmailMessage()
    msg['To'] = PARA
    msg['Cc'] = COPIA
    msg['Subject'] = d['asunto']
    msg['X-Unsent'] = '1'
    msg.set_content(d['texto'])
    msg.add_alternative(d['html'], subtype='html')
    for a in d['adjuntos']:
        tipo, _ = mimetypes.guess_type(a)
        principal, sub = (tipo or 'application/octet-stream').split('/')
        with open(a, 'rb') as fh:
            msg.add_attachment(fh.read(), maintype=principal, subtype=sub, filename=os.path.basename(a))
    return bytes(msg), d['avisos']


def abrir_en_outlook(ordenes: dict | list[dict]) -> list[str]:
    """Crea el borrador en el Outlook de escritorio de esta PC y abre su ventana. NUNCA lo envía (Sergio 10/11/2026)."""
    d = datos(ordenes)
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            m = win32com.client.Dispatch('Outlook.Application').CreateItem(0)  # olMailItem
            m.To, m.CC, m.Subject, m.HTMLBody = PARA, COPIA, d['asunto'], d['html']
            for a in d['adjuntos']:
                m.Attachments.Add(a)
            m.Save()      # queda en Borradores aunque se cierre la ventana
            m.Display(False)
        finally:
            pythoncom.CoUninitialize()
    except Exception as exc:  # sin Outlook o COM caído: el frontend cae a la descarga del .eml
        raise ConnectionError(f'No se pudo abrir Outlook ({exc}). Se descarga el mail como archivo') from exc
    return d['avisos']
