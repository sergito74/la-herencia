"""Pagos ya hechos que todavía no están en el extracto del banco (Sergio, 05/11/2026).

Se leen los comprobantes de transferencias y eCheqs emitidos que se guardan en la carpeta
Documents/La Herencia/Administracion y gestion/Cuentas a pagar (subcarpetas Transferencias y Cheques electronicos).
Mientras su débito no aparece en el extracto de Galicia, cuentan como pagados "esperando el banco" y se descuentan de lo
que hay que pagar a ese proveedor. Cuando se sube el extracto, se confirman contra el débito (mismo importe, fecha desde
el envío o el pago del eCheq hasta 7 días después, si hay más de un débito posible desempata el proveedor).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.db.connection import execute_write, fetch_all

CARPETA = Path.home() / 'Documents' / 'La Herencia' / 'Administracion y gestion' / 'Cuentas a pagar'
SUBCARPETAS = ('Transferencias', 'Cheques electronicos')
DIAS_DEBITO = 7
# Un comprobante sin débito y anterior a lo que ya cubre el extracto (menos este margen) no se cuenta como pago en
# camino: queda como "no encontrado en el banco" para revisar.
MARGEN_EXTRACTO = 10


def _importe(txt: str) -> Decimal | None:
    m = re.search(r'\$\s*([\d.]+,\d{2})', txt)
    return Decimal(m.group(1).replace('.', '').replace(',', '.')) if m else None


def _fecha(s: str | None) -> date | None:
    try:
        return datetime.strptime(s, '%d/%m/%Y').date() if s else None
    except ValueError:
        return None


def leer_pdf(ruta: Path) -> dict:
    """Datos de un comprobante de Office Banking o de un eCheq de Galicia; {} si no es uno de esos."""
    import pdfplumber

    try:
        with pdfplumber.open(ruta) as pdf:
            txt = '\n'.join((p.extract_text() or '') for p in pdf.pages[:2])
    except Exception:
        return {}
    lineas = [l.strip() for l in txt.splitlines()]

    def despues(rotulo, salto=1):
        for i, l in enumerate(lineas):
            if l.startswith(rotulo) and i + salto < len(lineas):
                return lineas[i + salto]
        return None

    if 'Datos del cheque' in txt and 'Emisi' in txt and 'Realizado' in txt:
        cuit_razon = [l for l in lineas if re.fullmatch(r'\d{11}', l)]
        fp = despues('Fecha de pago')
        num = despues('Número de cheque') or ''
        op = re.search(r'operaci\S* (\w+)', txt)
        return {'Tipo': 'echeq', 'Operacion': op.group(1) if op else None,
                'NumeroCheque': num.split()[0] if num else None,
                'Fecha': _fecha((despues('Fecha de ejecuci') or '').split(' ')[0]),
                'FechaPago': _fecha(fp.split(' ')[0] if fp else None), 'Importe': _importe(fp or ''),
                'CuitDestino': cuit_razon[-1] if len(cuit_razon) > 1 else None,
                'Destinatario': _beneficiario(lineas),
                'Concepto': despues('Motivo de la emisi')}
    if 'Office Banking' in txt and 'Datos del destinatario' in txt:
        fm = despues('Fecha de env')
        partes = (fm or '').split(' ', 1)
        dest = despues('Datos del destinatario', 2) or ''
        m = re.match(r'(\d{11})\s+(.*)', dest)
        op = re.search(r'Identificador de la operaci\S*:\s*(\w+)', txt)
        return {'Tipo': 'transferencia', 'Operacion': op.group(1) if op else None, 'NumeroCheque': None,
                'Fecha': _fecha(partes[0]), 'FechaPago': _fecha(partes[0]), 'Importe': _importe(fm or ''),
                'CuitDestino': m.group(1) if m else None, 'Destinatario': m.group(2) if m else dest or None,
                'Concepto': despues('Concepto')}
    return {}


def _d(v):
    if isinstance(v, datetime):
        return v.date()
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


def _beneficiario(lineas):
    for i, l in enumerate(lineas):
        if l.startswith('Datos del beneficiario') and i + 2 < len(lineas):
            return lineas[i + 2]
    return None


def _contactos_por_cuit() -> dict[str, int]:
    res = {}
    for r in fetch_all("SELECT IdContacto id, [CUIT/CUIL] cuit FROM dbo.Contactos WHERE [CUIT/CUIL] IS NOT NULL"):
        c = re.sub(r'\D', '', str(r['cuit']))
        if len(c) == 11:
            res.setdefault(c, r['id'])
    return res


def sincronizar(carpeta: Path = CARPETA) -> dict:
    """Lee los PDF nuevos o modificados de la carpeta y confirma contra el extracto los que todavía esperan."""
    previos = {r['Archivo']: r for r in fetch_all(
        "SELECT IdComprobante, Archivo, Modificado, IdContacto FROM dbo.PagosEmitidosComprobantes")}
    cuits = None
    nuevos = 0
    for sub in SUBCARPETAS:
        base = carpeta / sub
        if not base.exists():
            continue
        for ruta in base.rglob('*'):
            if not ruta.is_file() or ruta.suffix.lower() != '.pdf':
                continue
            rel = str(ruta.relative_to(carpeta))
            mod = datetime.fromtimestamp(ruta.stat().st_mtime).replace(microsecond=0)
            prev = previos.get(rel)
            if prev and prev['Modificado'] and str(prev['Modificado'])[:19] == mod.isoformat(sep=' ')[:19]:
                continue
            d = leer_pdf(ruta)
            if cuits is None:
                cuits = _contactos_por_cuit()
            idc = cuits.get(d.get('CuitDestino') or '')
            vals = (mod, d.get('Tipo'), d.get('Operacion'), d.get('NumeroCheque'), d.get('Fecha'), d.get('FechaPago'),
                    d.get('Importe'), d.get('CuitDestino'), (d.get('Destinatario') or '')[:200] or None,
                    (d.get('Concepto') or '')[:300] or None, idc)
            if prev:
                execute_write("UPDATE dbo.PagosEmitidosComprobantes SET Modificado=?,Tipo=?,Operacion=?,NumeroCheque=?,"
                              "Fecha=?,FechaPago=?,Importe=?,CuitDestino=?,Destinatario=?,Concepto=?,IdContacto=?,"
                              "Medio=NULL,IdMovimiento=NULL,Confirmado=NULL,Leido=SYSUTCDATETIME() WHERE IdComprobante=?",
                              (*vals, prev['IdComprobante']))
            else:
                execute_write("INSERT INTO dbo.PagosEmitidosComprobantes (Modificado,Tipo,Operacion,NumeroCheque,Fecha,"
                              "FechaPago,Importe,CuitDestino,Destinatario,Concepto,IdContacto,Archivo) "
                              "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (*vals, rel))
            nuevos += 1
    return {'leidos': nuevos, 'confirmados': confirmar()}


def confirmar() -> int:
    """Busca el débito de Galicia de cada comprobante sin confirmar. Un mismo débito confirma un solo comprobante; si hay
    más de un débito posible se deja sin confirmar (no se adivina)."""
    pend = fetch_all("SELECT IdComprobante id, FechaPago f, Importe i, IdContacto c FROM dbo.PagosEmitidosComprobantes "
                     "WHERE Tipo IS NOT NULL AND IdMovimiento IS NULL AND Importe>0 AND FechaPago IS NOT NULL "
                     "ORDER BY FechaPago, IdComprobante")
    if not pend:
        return 0
    usados = {r['m'] for r in fetch_all(
        "SELECT IdMovimiento m FROM dbo.PagosEmitidosComprobantes WHERE Medio='galicia' AND IdMovimiento IS NOT NULL")}
    n = 0
    for p in pend:
        cands = [r for r in fetch_all(
            "SELECT IdMovimiento m, IdContacto c FROM dbo.[Movimientos Galicia] WHERE [Débitos]=? AND Fecha BETWEEN ? AND ?",
            (p['i'], _d(p['f']), _d(p['f']) + timedelta(days=DIAS_DEBITO)))
            if r['m'] not in usados]
        if len(cands) > 1:  # el proveedor solo desempata (el débito puede estar a otro contacto, ej. el socio)
            cands = [r for r in cands if p['c'] and r['c'] and int(r['c']) == p['c']]
        if len(cands) != 1:
            continue
        execute_write("UPDATE dbo.PagosEmitidosComprobantes SET Medio='galicia', IdMovimiento=?, Confirmado=SYSUTCDATETIME() "
                      "WHERE IdComprobante=?", (cands[0]['m'], p['id']))
        usados.add(cands[0]['m'])
        n += 1
    return n


def esperando_banco() -> dict[int, list[dict]]:
    """Pagos hechos cuyo débito todavía no puede estar en el extracto cargado, por proveedor."""
    ult = fetch_all("SELECT MAX(Fecha) f FROM dbo.[Movimientos Galicia]")[0]['f']
    ult = ult.date() if hasattr(ult, 'date') else ult
    desde = (ult or date.min) - timedelta(days=MARGEN_EXTRACTO)
    res: dict[int, list[dict]] = {}
    for r in fetch_all("SELECT Tipo tipo, Operacion operacion, NumeroCheque cheque, Fecha fecha, FechaPago fechaPago, "
                       "Importe importe, Destinatario destinatario, Concepto concepto, IdContacto idContacto, Archivo archivo "
                       "FROM dbo.PagosEmitidosComprobantes WHERE Tipo IS NOT NULL AND IdMovimiento IS NULL "
                       "AND IdContacto IS NOT NULL AND Importe>0 AND FechaPago>=? ORDER BY FechaPago", (desde,)):
        r['importe'] = Decimal(str(r['importe']))
        r['fecha'], r['fechaPago'] = (_d(r['fecha']) if r['fecha'] else None), _d(r['fechaPago'])
        res.setdefault(r['idContacto'], []).append(r)
    return res
