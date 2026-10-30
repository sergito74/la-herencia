"""046: planificación sin deuda; confirmación con fondos existentes y auditoría."""
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from src.db.connection import atomic_reconciliation, execute_insert_returning_id, execute_write, fetch_all, fetch_one
from src.features.aplicaciones_pago import repository as aplicaciones
from src.features.conciliacion_tesoreria.repository import _MEDIOS, _movimiento_original
from src.features.documentos_nuevos import repository as avisos
from src.features.ordenes_pago.schemas import OrdenInput, VincularInput
from src.features.vinculos import fuente, cadenas


def dinero(value):
    return Decimal(str(value or 0)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


COLS = """o.IdOrdenPago idOrdenPago,o.IdContacto idContacto,c.[Razon Social] proveedor,
o.Fecha fecha,o.FechaPago fechaPago,o.ImporteTotal importeTotal,o.Moneda moneda,o.Estado estado,
o.Observaciones observaciones,o.Version version,o.RetencionGanancias retencionGanancias"""
BASE = ' FROM dbo.OrdenesPago o JOIN dbo.Contactos c ON c.IdContacto=o.IdContacto '


def listar(id_contacto=None, estado=None, page=1, page_size=50):
    clauses, params = [], []
    if id_contacto:
        clauses.append('o.IdContacto=?')
        params.append(id_contacto)
    if estado:
        clauses.append('o.Estado=?')
        params.append(estado)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    total = fetch_one('SELECT COUNT(*) total'+BASE+where, tuple(params))['total']
    items = fetch_all('SELECT '+COLS+BASE+where+' ORDER BY o.IdOrdenPago DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY',
                      (*params, (page-1)*page_size, page_size))
    return {'items': items, 'total': total}


def obtener(id_):
    row = fetch_one('SELECT '+COLS+BASE+' WHERE o.IdOrdenPago=?', (id_,))
    if not row:
        raise LookupError('No existe la orden de pago')
    row['facturas'] = fetch_all('SELECT d.IdCompra idCompra,c.[Nro Documento] numero,d.Importe importe '
                               'FROM dbo.OrdenesPago_Detalle d JOIN dbo.Compras c ON c.IdDeuda=d.IdCompra '
                               'WHERE d.IdOrdenPago=? ORDER BY d.IdDetalle', (id_,))
    row['medios'] = fetch_all('SELECT Medio medio,Cuenta cuenta,Importe importe FROM dbo.OrdenesPago_Medios '
                             'WHERE IdOrdenPago=? ORDER BY IdMedio', (id_,))
    row['retenciones'] = fetch_all('SELECT CodRegimen codRegimen,Concepto concepto,BasePago basePago,PagosAnteriores pagosAnteriores,'
                                   'RetencionesAnteriores retencionesAnteriores,Alicuota alicuota,NoSujeto noSujeto,Retencion retencion '
                                   'FROM dbo.OrdenesPago_Retenciones WHERE IdOrdenPago=? ORDER BY CodRegimen', (id_,))
    row['repartoNeto'] = reparto_neto(row)
    return row


def facturas(id_contacto, excluir_op=None, incluir_saldadas=False):
    # 046 T027: documentos en US$ en pesos al TC del comprobante (regla usd-tc-comprobante), como la fuente unificada.
    rows = fetch_all("SELECT TOP (2000) c.IdDeuda idCompra,c.[Nro Documento] numero,c.Fecha fecha,c.Moneda moneda,"
                     "CASE WHEN c.Moneda='Dolares' THEN c.[Tipo de Cambio] END tc,"
                     "(t.GranTotal-ISNULL(pa.cp,0))*CASE WHEN c.Moneda='Dolares' THEN c.[Tipo de Cambio] ELSE 1 END total "
                     "FROM dbo.Compras c "
                     "JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda "
                     "OUTER APPLY (SELECT SUM(d.Cantidad*d.[Precio Unitario]*(1+ISNULL(d.IVA,0)/100.0)) cp "
                     "FROM dbo.Det_Compras d WHERE d.IdCompra=c.IdDeuda AND d.Cantidad*d.[Precio Unitario]<0 "
                     "AND d.[Producto/Servicio] LIKE '%particular%') pa "
                     "WHERE c.IdContacto=? AND ISNULL(c.Suspendida,0)=0 AND (c.Moneda IN ('Pesos','ARS','$') "
                     "OR (c.Moneda='Dolares' AND c.[Tipo de Cambio]>1)) "
                     "ORDER BY c.Fecha DESC,c.IdDeuda DESC", (id_contacto,))
    paid = fuente.pagado_de_documentos([('CompraDeuda', f['idCompra']) for f in rows])
    reserved = {f['idCompra']: dinero(f['importe']) for f in fetch_all(
        "SELECT d.IdCompra idCompra,SUM(d.Importe) importe FROM dbo.OrdenesPago_Detalle d "
        "JOIN dbo.OrdenesPago o ON o.IdOrdenPago=d.IdOrdenPago WHERE o.Estado='Emitida' "
        "AND o.IdContacto=? AND o.IdOrdenPago<>? GROUP BY d.IdCompra", (id_contacto, excluir_op or 0))}
    result = []
    for row in rows:
        p = dinero(paid[('CompraDeuda', row['idCompra'])])
        saldo = dinero(row['total'])-p
        reserva = reserved.get(row['idCompra'], Decimal(0))
        if saldo > 0 or incluir_saldadas:
            result.append({**row, 'pagado': p, 'saldo': saldo, 'reservado': reserva,
                           'disponible': max(Decimal(0), saldo-reserva)})
    return result


def validar_facturas(body, excluir_op=None):
    available = {f['idCompra']: f for f in facturas(body.idContacto, excluir_op)}
    for f in body.facturas:
        row = available.get(f.idCompra)
        if not row or f.importe > row['disponible']:
            raise ValueError('Una factura no pertenece al proveedor o ya no tiene saldo disponible para esta orden')


def auditar(accion, datos, usuario, id_op=None, id_recibo=None):
    execute_write('INSERT INTO dbo.OrdenesPago_Auditoria (IdOrdenPago,IdRecibo,Accion,Datos,Usuario) VALUES (?,?,?,?,?)',
                  (id_op, id_recibo, accion, json.dumps(datos, default=str, ensure_ascii=False), usuario))


@atomic_reconciliation
def guardar(body: OrdenInput, usuario, id_=None):
    previo = obtener(id_) if id_ else None
    if previo and (previo['estado'] != 'Borrador' or body.version != previo['version']):
        raise ValueError('La orden cambió o ya no está en borrador. Volvé a abrirla')
    validar_facturas(body, id_)
    total = sum(f.importe for f in body.facturas)
    if id_:
        execute_write('UPDATE dbo.OrdenesPago SET IdContacto=?,Fecha=?,FechaPago=?,ImporteTotal=?,Observaciones=?, '
                      'Version=Version+1,Modificado=SYSUTCDATETIME() WHERE IdOrdenPago=?',
                      (body.idContacto, body.fecha, body.fechaPago, total, body.observaciones, id_))
        execute_write('DELETE FROM dbo.OrdenesPago_Detalle WHERE IdOrdenPago=?', (id_,))
        execute_write('DELETE FROM dbo.OrdenesPago_Medios WHERE IdOrdenPago=?', (id_,))
        execute_write('DELETE FROM dbo.OrdenesPago_Retenciones WHERE IdOrdenPago=?', (id_,))
    else:
        id_ = execute_insert_returning_id('INSERT INTO dbo.OrdenesPago '
            '(IdContacto,Fecha,FechaPago,ImporteTotal,Observaciones,CreadoPor) OUTPUT INSERTED.IdOrdenPago VALUES (?,?,?,?,?,?)',
            (body.idContacto, body.fecha, body.fechaPago, total, body.observaciones, usuario))
    for f in body.facturas:
        execute_write('INSERT INTO dbo.OrdenesPago_Detalle (IdOrdenPago,IdCompra,Importe) VALUES (?,?,?)', (id_, f.idCompra, f.importe))
    for m in body.medios:
        execute_write('INSERT INTO dbo.OrdenesPago_Medios (IdOrdenPago,Medio,Cuenta,Importe) VALUES (?,?,?,?)',
                      (id_, m.medio, m.cuenta, m.importe))
    for r in body.retenciones:
        execute_write('INSERT INTO dbo.OrdenesPago_Retenciones (IdOrdenPago,CodRegimen,Concepto,BasePago,PagosAnteriores,'
                      'RetencionesAnteriores,Alicuota,NoSujeto,Retencion,Simulador) VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (id_, r.codRegimen, r.concepto, r.basePago, r.pagosAnteriores, r.retencionesAnteriores, r.alicuota,
                       r.noSujeto, r.retencion, r.simulador))
    execute_write('UPDATE dbo.OrdenesPago SET RetencionGanancias=? WHERE IdOrdenPago=?',
                  (sum((r.retencion for r in body.retenciones), Decimal(0)), id_))
    auditar('Editar' if previo else 'Crear', {'antes': previo, 'despues': body.model_dump()}, usuario, id_)
    return obtener(id_)


@atomic_reconciliation
def cambiar_estado(id_, estado, usuario):
    orden = obtener(id_)
    if estado == 'Emitida':
        if orden['estado'] != 'Borrador':
            raise ValueError('Solo se emiten órdenes en borrador')
        body = OrdenInput(**{k: orden[k] for k in ('idContacto','fecha','fechaPago','observaciones','medios','version')},
                          retenciones=[{**r, 'simulador': '{}'} for r in orden['retenciones']],
                          facturas=[{'idCompra': f['idCompra'], 'importe': f['importe']} for f in orden['facturas']])
        validar_facturas(body, id_)
    elif estado != 'Anulada' or orden['estado'] not in ('Borrador', 'Emitida'):
        raise ValueError('No se puede anular una orden pagada o ya anulada')
    execute_write('UPDATE dbo.OrdenesPago SET Estado=?,Version=Version+1,Modificado=SYSUTCDATETIME() WHERE IdOrdenPago=?', (estado,id_))
    auditar(estado, orden, usuario, id_)
    return obtener(id_)


def recibos(id_contacto=None, revisados=False, page=1, page_size=50):
    where = " WHERE d.Tipo='recibo' AND d.Modulo='pagos'"
    params = []
    if not revisados:
        where += ' AND d.Revisado IS NULL'
    if id_contacto:
        where += ' AND d.IdContacto=?'
        params.append(id_contacto)
    base = ' FROM dbo.DocumentosNuevos d LEFT JOIN dbo.Contactos c ON c.IdContacto=d.IdContacto '
    total = fetch_one('SELECT COUNT(*) total'+base+where, tuple(params))['total']
    rows = fetch_all('SELECT d.IdDocumentoNuevo idDocumentoNuevo,d.IdContacto idContacto,c.[Razon Social] proveedor,'
                     'd.Numero numero,d.Fecha fecha,d.Total total,d.Revisado revisado,'
                     'r.IdRecibo idRecibo,r.IdOrdenPago idOrdenPago'+base+
                     'LEFT JOIN dbo.RecibosProveedores r ON r.IdDocumentoNuevo=d.IdDocumentoNuevo'+where+
                     ' ORDER BY d.IdDocumentoNuevo DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY',
                     (*params, (page-1)*page_size, page_size))
    return {'items': rows, 'total': total}


def documento_recibo(id_):
    row = fetch_one("SELECT IdDocumentoNuevo idDocumentoNuevo,IdContacto idContacto,Numero numero,Fecha fecha,"
                    "Total total,Ruta ruta,Sha256 sha256,Revisado revisado FROM dbo.DocumentosNuevos "
                    "WHERE IdDocumentoNuevo=? AND Tipo='recibo' AND Modulo='pagos'", (id_,))
    if not row:
        raise LookupError('No existe el recibo')
    return row


def pdf_recibo(id_):
    row = documento_recibo(id_)
    path = Path(row['ruta'])
    if path.suffix.lower() != '.pdf' or not path.is_file():
        raise LookupError('No se encuentra el PDF original')
    if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
        raise ValueError('El archivo cambió desde su recepción. Revisá el documento original')
    return path


def _vinculos():
    return fuente.cargar()['vinculos']


def _usado(origen, id_, vinculos):
    return sum((dinero(v['importeArs']) for v in vinculos if v['enMovimiento'] and not v['redundante']
                and v['origenMovimiento']==origen and v['idMovimiento']==id_), Decimal(0))


def movimiento(origen, id_, id_contacto):
    row = _movimiento_original(origen, id_)
    if origen in ('bna','galicia'):
        override = fetch_one('SELECT TOP 1 IdContactoNuevo contacto FROM dbo.ReasignacionesContacto '
                             'WHERE Origen=? AND IdOrigen=? ORDER BY IdReasignacion DESC',
                             ('Banco Nacion' if origen=='bna' else 'Galicia',id_))
        if override and override['contacto'] != id_contacto:
            raise ValueError('El movimiento fue reasignado a otro contacto')
    # Reasignaciones o conciliaciones parciales se resuelven antes en Tesorería.
    if row.get('idContacto') != id_contacto:
        raise ValueError('El pago debe estar asignado al proveedor en Tesorería')
    amount = dinero(row['importe'])
    if origen != 'efectivo' and amount >= 0:
        raise ValueError('Seleccioná una salida de fondos, no un cobro')
    if amount == 0:
        raise ValueError('El movimiento no tiene importe')
    return row, abs(amount)


def movimientos(id_contacto):
    links = _vinculos()
    result = []
    for origen in ('galicia','bna','efectivo'):
        info = _MEDIOS[origen]
        rows = fetch_all(f'SELECT TOP (100) {info.id_col} idMovimiento FROM {info.tabla} '
                         f'WHERE {info.contacto_col}=? ORDER BY {info.fecha_col} DESC', (id_contacto,))
        for r in rows:
            try:
                row, total = movimiento(origen, r['idMovimiento'], id_contacto)
            except ValueError:
                continue
            result.append({'origenMovimiento': origen,'idMovimiento': r['idMovimiento'], 'fecha': row['fecha'],
                           'importe': total, 'disponible': max(Decimal(0), total-_usado(origen,r['idMovimiento'],links))})
    return result


@atomic_reconciliation
def vincular(id_documento, body: VincularInput, usuario):
    doc = documento_recibo(id_documento)
    if fetch_one('SELECT IdRecibo id FROM dbo.RecibosProveedores WHERE IdDocumentoNuevo=?', (id_documento,)):
        raise ValueError('El recibo ya está vinculado; no se volvió a aplicar')
    if doc['revisado']:
        raise ValueError('El recibo ya fue revisado')
    if doc['idContacto'] and doc['idContacto'] != body.idContacto:
        raise ValueError('El proveedor no coincide con el recibo recibido')
    pdf_recibo(id_documento)
    if fetch_one('SELECT IdRecibo id FROM dbo.RecibosProveedores WHERE Sha256=? OR (IdContacto=? AND Numero=?)',
                 (doc['sha256'],body.idContacto,body.numero)):
        raise ValueError('Este recibo ya fue registrado')
    orden = obtener(body.idOrdenPago) if body.idOrdenPago else None
    por_factura, por_mov = defaultdict(Decimal), defaultdict(list)
    for a in body.aplicaciones:
        por_factura[a.idCompra] += a.importe
        por_mov[(a.origenMovimiento,a.idMovimiento)].append(a)
    if orden:
        expected = {f['idCompra']: dinero(f['importe']) for f in orden['facturas']}
        retencion_op = dinero(orden.get('retencionGanancias'))
        if orden['estado'] not in ('Emitida', 'Pagada') or orden['idContacto'] != body.idContacto:
            raise ValueError('El recibo debe corresponder a una orden emitida o pagada del proveedor')
        if orden['estado'] == 'Pagada' and fetch_one('SELECT IdRecibo id FROM dbo.RecibosProveedores WHERE IdOrdenPago=?', (body.idOrdenPago,)):
            raise ValueError('La orden ya tiene un recibo vinculado')
        if body.retencion != retencion_op:
            raise ValueError('La retención del recibo no coincide con la de la orden de pago')
        # Con retención los pagos reales cubren el neto; la retención cancela el resto por el circuito de Retenciones.
        if set(por_factura) - set(expected) or any(v > expected[k] for k, v in por_factura.items())                 or sum(por_factura.values(), Decimal(0)) != sum(expected.values(), Decimal(0)) - retencion_op:
            raise ValueError('El recibo debe cancelar las facturas de la orden: pagos por el neto y la retención de la orden')
    elif body.retencion and not body.certificadoRetencion:
        raise ValueError('Sin orden de pago, indicá el número de certificado de la retención')
    if body.certificadoRetencion:
        cert = fetch_one("SELECT SUM(Importe) i FROM dbo.Retenciones WHERE IdContacto=? AND RTRIM([Numero Certificado]) IN (?,?)",
                         (body.idContacto, body.certificadoRetencion, body.certificadoRetencion + ' B'))
        if not cert or cert['i'] is None:
            raise ValueError('El certificado de retención no está cargado en Retenciones para este proveedor')
        if dinero(cert['i']) != body.retencion:
            raise ValueError('El importe del certificado no coincide con la retención del recibo')
    rows = {f['idCompra']: f for f in facturas(body.idContacto, body.idOrdenPago, incluir_saldadas=True)}
    links = _vinculos()
    crear, confirmar = [], []
    nuevo_factura = defaultdict(Decimal)
    for (origen,id_mov), items in por_mov.items():
        _, importe = movimiento(origen,id_mov,body.idContacto)
        existentes = aplicaciones.aplicaciones_vigentes_de_movimiento(origen,id_mov)
        nuevos = []
        for a in items:
            same = [x for x in existentes if x['tipoDocumento']=='CompraDeuda' and x['idDocumentoAplicado']==a.idCompra]
            if same:
                if len(same)!=1 or dinero(same[0]['importeAplicado']) != a.importe:
                    raise ValueError('El pago ya tiene una aplicación diferente para esta factura; revisala en Cuentas Corrientes')
                confirmar.append(same[0]['idAplicacion'])
            else:
                nuevos.append(a)
                nuevo_factura[a.idCompra] += a.importe
        if sum((a.importe for a in nuevos),Decimal(0))+_usado(origen,id_mov,links) > importe:
            raise ValueError('El movimiento no tiene fondos disponibles para estas aplicaciones')
        crear.extend(nuevos)
    for id_compra in por_factura:
        row = rows.get(id_compra)
        if not row or nuevo_factura[id_compra] > row['disponible']:
            raise ValueError('La factura no pertenece al proveedor o no tiene saldo suficiente')
    for id_app in confirmar:
        if fetch_one('SELECT IdRecibo id FROM dbo.RecibosProveedores_Aplicaciones WHERE IdAplicacion=?',(id_app,)):
            raise ValueError('Una aplicación ya tiene otro recibo asociado')
    id_recibo = execute_insert_returning_id('INSERT INTO dbo.RecibosProveedores '
        '(IdDocumentoNuevo,IdContacto,Numero,Fecha,Total,RutaPdf,Sha256,IdOrdenPago,Usuario,Retencion,Anticipo,CertificadoRetencion) '
        'OUTPUT INSERTED.IdRecibo VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        (id_documento,body.idContacto,body.numero,body.fecha,body.total,doc['ruta'],doc['sha256'],body.idOrdenPago,usuario,
         body.retencion,body.anticipo,body.certificadoRetencion))
    # 019 performs the shared validation/insertion; this outer transaction adds exact centavo limits.
    for a in crear:
        confirmar.extend(aplicaciones.insertar_aplicaciones(a.origenMovimiento,a.idMovimiento,
            [{'tipoDocumento':'CompraDeuda','idDocumento':a.idCompra,'importeAplicado':float(a.importe)}],usuario))
    for id_app in confirmar:
        execute_write('INSERT INTO dbo.RecibosProveedores_Aplicaciones (IdRecibo,IdAplicacion) VALUES (?,?)',(id_recibo,id_app))
    execute_write('UPDATE dbo.DocumentosNuevos SET IdContacto=?,Numero=?,Fecha=?,Total=?,Revisado=SYSUTCDATETIME(),'
                  'RevisadoPor=? WHERE IdDocumentoNuevo=?',(body.idContacto,body.numero,body.fecha,body.total,usuario,id_documento))
    if orden:
        execute_write("UPDATE dbo.OrdenesPago SET Estado='Pagada',Version=Version+1,Modificado=SYSUTCDATETIME() WHERE IdOrdenPago=?",(body.idOrdenPago,))
    auditar('Vincular recibo',body.model_dump(),usuario,body.idOrdenPago,id_recibo)
    return {'idRecibo':id_recibo, 'aplicaciones':confirmar}


def reparto_neto(orden):
    """Pagos reales por factura (T024/T025): el neto cubre las facturas en orden de carga; la retención descuenta de la última."""
    restante = sum((dinero(f['importe']) for f in orden['facturas']), Decimal(0)) - dinero(orden.get('retencionGanancias'))
    out = []
    for f in orden['facturas']:
        parte = min(dinero(f['importe']), restante)
        if parte > 0:
            out.append({'idCompra': f['idCompra'], 'numero': f.get('numero'), 'importe': parte})
        restante -= parte
    return out


def _dia(v):
    return v.date() if hasattr(v, 'date') else v


def _debito_de_la_orden(orden, links):
    """Único egreso real del proveedor, posterior a la OP, libre y por el neto exacto; None si no hay o es ambiguo."""
    neto = sum((p['importe'] for p in reparto_neto(orden)), Decimal(0))
    candidatos = [m for m in movimientos(orden['idContacto'])
                  if dinero(m['importe']) == neto and dinero(m['disponible']) == neto
                  and (m['fecha'] is None or _dia(m['fecha']) >= _dia(orden['fecha']))]
    usados = {(a['origenMovimiento'], a['idMovimiento']) for a in links if a.get('enMovimiento')}
    candidatos = [m for m in candidatos if (m['origenMovimiento'], m['idMovimiento']) not in usados]
    return candidatos[0] if len(candidatos) == 1 else (None if not candidatos else 'ambiguo')


@atomic_reconciliation
def conciliar_emitidas(usuario, id_contacto=None):
    """T024: las OP emitidas cuyo débito real ya está en Tesorería pasan a Pagada con sus aplicaciones (spec 019)."""
    sql = "SELECT IdOrdenPago id FROM dbo.OrdenesPago WHERE Estado='Emitida'" + (' AND IdContacto=?' if id_contacto else '')
    links = _vinculos()
    pagadas, ambiguas = [], []
    for r in fetch_all(sql + ' ORDER BY IdOrdenPago', (id_contacto,) if id_contacto else ()):
        orden = obtener(r['id'])
        mov = _debito_de_la_orden(orden, links)
        if mov == 'ambiguo':
            ambiguas.append(orden['idOrdenPago'])
            continue
        if not mov:
            continue
        reparto = [{'tipoDocumento': 'CompraDeuda', 'idDocumento': p['idCompra'], 'importeAplicado': float(p['importe'])}
                   for p in reparto_neto(orden)]
        ids = aplicaciones.insertar_aplicaciones(mov['origenMovimiento'], mov['idMovimiento'], reparto, usuario)
        execute_write("UPDATE dbo.OrdenesPago SET Estado='Pagada',Version=Version+1,Modificado=SYSUTCDATETIME() WHERE IdOrdenPago=?",
                      (orden['idOrdenPago'],))
        auditar('Pagada por débito', {'movimiento': mov, 'aplicaciones': ids}, usuario, orden['idOrdenPago'])
        links.append({'origenMovimiento': mov['origenMovimiento'], 'idMovimiento': mov['idMovimiento'], 'enMovimiento': True})
        pagadas.append(orden['idOrdenPago'])
    return {'pagadas': pagadas, 'ambiguas': ambiguas}
