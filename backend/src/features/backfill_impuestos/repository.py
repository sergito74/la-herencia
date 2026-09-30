"""Lectura parametrizada, acotada y con Decimal preservado. Nunca consulta Access."""
import re
from collections import defaultdict
from datetime import datetime, timezone
from src.db.connection import get_connection, _assert_read_only
from src.features.traspasos_internos_tesoreria.repository import _MEDIOS
from .diagnostico import money, diagnosticar, resumen, digest, ZERO

NATIVOS={'bna':'Banco Nacion','galicia':'Galicia','efectivo':'Pagos efectivo',
         'valores-recibidos':'Pagos Valores Recibidos'}

# Decisión del usuario (2026-09-30): el saldo de AFIP mezcla ~$18M de
# devoluciones de IVA granos con pagos de impuestos — puede faltar un
# certificado y no una boleta. Se diagnostica igual, pero no se generan
# boletas hasta revisar ese ciclo aparte.
ORGANISMOS_SIN_GENERACION={'AFIP'}

# `[Tipo Impuesto].IdOrganismo` usa una numeración propia heredada de Access,
# no `Contactos.IdContacto` — verificado contra los tipos que usa cada
# organismo en sus boletas reales (2026-09-30). UATRE usa "Aporte Sindical"
# (código 1) sin compartir el catálogo de AFIP, por eso no está acá.
CODIGO_TIPO_LEGADO={119:1,12:2,72:3,422:4}  # 4 = Tapalqué, creado 2026-09-30

# "RECAUDACION ARBA" en el extracto es percepción de Ingresos Brutos
# (recaudación bancaria de la Provincia): no tiene boleta como
# contrapartida — pedido del usuario 2026-09-30. Nunca la cubre otra
# boleta ni documento; se registra desde el propio pago con su tipo.
RECAUDACION_ARBA=re.compile(r'RECAUD\w*\s+ARBA',re.I)
TIPO_PERCEPCION_IIBB='Percepción Ingresos Brutos'


def tipos_del_organismo(organismo_id):
    """Tipos de su catálogo heredado, los que ya usa en boletas reales y los creados por 029."""
    return read("""SELECT IdTipoImpuesto AS idTipoImpuesto,[Nombre Impuesto] AS nombre FROM dbo.[Tipo Impuesto]
        WHERE IdOrganismo=? OR IdOrganismo=? OR IdTipoImpuesto IN (SELECT IdTipoImpuesto FROM dbo.Impuestos WHERE IdOrganismo=?)
        ORDER BY [Nombre Impuesto]""",(organismo_id,CODIGO_TIPO_LEGADO.get(organismo_id,-1),organismo_id))

def read(sql,params=()):
    _assert_read_only(sql)
    with get_connection() as conn:
        cur=conn.cursor();cur.execute(sql,params)
        names=[x[0] for x in cur.description]
        result=[]
        while True:
            batch=cur.fetchmany(1000)
            if not batch: break
            result.extend(dict(zip(names,row)) for row in batch)
            if len(result)>100000: raise ValueError('La consulta excede el límite seguro; no se emitió un diagnóstico parcial')
        return result

def schema_ready():
    names=('BackfillImpuestosLotes','BackfillImpuestosBoletas','BackfillImpuestosVinculos','BackfillImpuestosEventos')
    found=read("SELECT name FROM sys.tables WHERE schema_id=SCHEMA_ID('dbo') AND name IN (?,?,?,?)",names)
    if found and len(found)!=4: raise ValueError('Esquema 029 incompleto')
    return len(found)==4

def organismos():
    return read("SELECT IdContacto AS idOrganismo,[Razon Social] AS organismo FROM dbo.Contactos WHERE [Tipo Contacto]=? ORDER BY [Razon Social]",('Organismo',))

def snapshot(organismo_id):
    orgs=organismos()
    org=next((o for o in orgs if o['idOrganismo']==organismo_id),None)
    if org is None: raise LookupError('No existe ese organismo')
    cuentas=read("SELECT Fecha AS fecha,IdContacto AS idContacto,Origen AS origen,IdOrigen AS idOrigen,Deuda AS deuda,Credito AS credito FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?",(organismo_id,))
    referencias=defaultdict(list)
    for c in cuentas: referencias[(c['origen'],c['idOrigen'])].append(c)
    conciliaciones=read("SELECT IdConciliacion AS idConciliacion,Medio AS medio,IdMovimiento AS idMovimiento,IdContacto AS idContacto,Importe AS importe,TipoOrigenDocumento AS origenDocumento,IdOrigenDocumento AS idDocumento FROM dbo.ConciliacionesTesoreria")
    conc=defaultdict(list)
    for c in conciliaciones: conc[(c['medio'],c['idMovimiento'])].append(c)
    tipos=tipos_del_organismo(organismo_id)
    boletas=read("SELECT IdImpuesto AS idImpuesto,IdOrganismo AS idOrganismo,Fecha AS fecha,Importe AS importe,[Documento Original] AS archivo,IdTipoImpuesto AS idTipoImpuesto FROM dbo.Impuestos WHERE IdOrganismo=?",(organismo_id,))
    por_id={b['idImpuesto']:b for b in boletas}
    used=defaultdict(lambda: ZERO)
    for c in conciliaciones:
        if c['origenDocumento']=='Impuestos': used[c['idDocumento']]+=money(c['importe'])
    tarjetas=read("SELECT IdImpuesto AS idImpuesto,SUM(ImporteImputado) AS importe FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdImpuesto IS NOT NULL GROUP BY IdImpuesto")
    for t in tarjetas: used[t['idImpuesto']]+=money(t['importe'])
    propios=[]
    if schema_ready():
        propios=read("SELECT Medio AS medio,IdMovimiento AS idMovimiento,IdImpuesto AS idImpuesto,Importe AS importe FROM dbo.BackfillImpuestosVinculos")
        for v in propios: used[v['idImpuesto']]+=money(v['importe'])
    vinc=defaultdict(list)
    for v in propios: vinc[(v['medio'],v['idMovimiento'])].append(v)
    for b in boletas: b['saldo']=money(b['importe'])-used[b['idImpuesto']]
    traspasos=read("SELECT IdEvento,MedioA,IdMovimientoA,MedioB,IdMovimientoB,Accion FROM dbo.TraspasosInternosTesoreria ORDER BY IdEvento")
    activos={}
    for t in traspasos:
        for suffix in ('A','B'): activos[(t['Medio'+suffix],t['IdMovimiento'+suffix])]=t['Accion']=='Vincular'
    # Reasignaciones a otros contactos también deben excluir un pago de la cuenta original.
    overrides=read("SELECT Origen,IdOrigen,IdContactoNuevo FROM dbo.ReasignacionesContacto ORDER BY IdReasignacion")
    effective={(o['Origen'],o['IdOrigen']):o['IdContactoNuevo'] for o in overrides}
    pagos=[];sin_contacto=0
    for medio,info in _MEDIOS.items():
        contacto='IdContacto' if medio in ('bna','galicia','mercado-libre','efectivo') else 'NULL'
        ultimo=-1
        while True:
            rows=read(f"SELECT TOP (1000) {info.id_col} AS idMovimiento,{info.fecha_col} AS fecha,{info.importe_expr} AS importe,{info.descripcion_expr} AS concepto,{contacto} AS idContacto FROM {info.tabla} WHERE {info.id_col}>? ORDER BY {info.id_col}",(ultimo,))
            if not rows: break
            for m in rows:
                key=(medio,m['idMovimiento']); native=NATIVOS.get(medio,'')
                cs=conc[key]
                refs=list(referencias.get((native,m['idMovimiento']),[]))
                for c in cs: refs.extend(referencias.get(('Conciliación Tesorería',c['idConciliacion']),[]))
                contact=effective.get((native,m['idMovimiento']),m['idContacto'])
                if not contact and not cs and not refs: sin_contacto+=1
                if contact!=organismo_id and not refs: continue
                amount=money(m['importe'])
                if medio in ('bna','galicia','mercado-libre'): amount=-amount
                conflict=None
                if any(effective.get(('Conciliación Tesorería',c['idConciliacion']),c['idContacto'])!=organismo_id for c in cs):
                    conflict='Pago distribuido o reasignado a varios contactos'
                docs=[c for c in cs if c['origenDocumento'] is not None]
                if any(c['origenDocumento']!='Impuestos' or c['idDocumento'] not in por_id for c in docs):
                    conflict='Pago vinculado a otro documento u organismo'
                respaldo=sum((money(c['importe']) for c in docs if c['origenDocumento']=='Impuestos' and c['idDocumento'] in por_id),ZERO)
                respaldo+=sum((money(v['importe']) for v in vinc[key] if v['idImpuesto'] in por_id),ZERO)
                fecha=str(m['fecha'])[:10] if m['fecha'] else None
                pagos.append(dict(medio=medio,idMovimiento=m['idMovimiento'],idOrganismo=organismo_id,
                    fecha=fecha,concepto=m['concepto'] or '',importe=amount,respaldo=respaldo,
                    creditoContable=sum((money(c['credito'])-money(c['deuda']) for c in refs),ZERO),
                    filasContables=len(refs),referenciaContable=[dict(origen=c['origen'],idOrigen=c['idOrigen']) for c in refs],
                    conflicto=conflict,traspaso=activos.get(key,False),
                    sinBoletaPorNaturaleza=bool(RECAUDACION_ARBA.search(m['concepto'] or ''))))
            ultimo=rows[-1]['idMovimiento']
    saldo=sum((money(c['deuda'])-money(c['credito']) for c in cuentas),ZERO)
    origenes_pago=set(NATIVOS.values())|{'Conciliación Tesorería','Impuestos'}
    extra=[dict(id=f"{c['origen']}:{c['idOrigen']}",fecha=c['fecha'],importe=money(c['deuda']))
           for c in cuentas if c['origen'] not in origenes_pago and money(c['deuda'])>0]
    otros=bool(extra)
    pagos.sort(key=lambda p:(p['fecha'] or '',p['medio'],p['idMovimiento']))
    habilitada=org['organismo'].strip().upper() not in ORGANISMOS_SIN_GENERACION
    rows=diagnosticar(pagos,boletas,saldo,otros,documentos_extra=extra,generacion_habilitada=habilitada,
                      motivo_bloqueo='AFIP queda fuera de este backfill: su saldo mezcla devoluciones de IVA granos')
    return dict(**org,items=rows,tipos=tipos,boletas=boletas,**resumen(rows,saldo),
                sinContacto=sin_contacto,huellaFuente=digest(dict(pagos=rows,boletas=boletas,tipos=tipos,saldo=saldo)),
                advertencias=['La cuenta del organismo tiene otros documentos además de boletas: revisá el saldo proyectado.'] if otros else [],
                fechaLectura=datetime.now(timezone.utc).isoformat())

def diagnostico(organismo_id=None,page=1,page_size=50):
    if organismo_id is None:
        orgs=organismos()
        return dict(items=orgs[(page-1)*page_size:page*page_size],total=len(orgs),page=page,pageSize=page_size)
    result=snapshot(organismo_id)
    result.pop('boletas')
    result['items']=result['items'][(page-1)*page_size:page*page_size]
    result.update(page=page,pageSize=page_size)
    return result
