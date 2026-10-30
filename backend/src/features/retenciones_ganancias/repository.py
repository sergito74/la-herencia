"""Retención de Ganancias RG 830 propuesta para una orden de pago (046, T018).

El sistema solo calcula; el certificado lo emite el estudio contable (Sergio 30/10/2026). Criterio de ARCA: base neta de
IVA, acumulada por proveedor y régimen en el mes del pago, no sujeto una sola vez por mes. Alícuotas, no sujeto y mínimo
salen del simulador de ARCA. Rubro → régimen es un borrador que valida el contador y ratifica el estudio.
"""
import json
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from src.db.connection import execute_write, fetch_all, fetch_one
from src.features.retenciones_ganancias import simulador

# Borrador inicial (Sergio 30/10: lo valida el contador). Sin régimen = no corresponde RG 830 o excluido (granos, hacienda).
BIENES, SERVICIOS, TRANSPORTE = 78, 94, 95
BORRADOR = {
    BIENES: ('Herramientas', 'Herbicidas', 'Alimento feed lot', 'Bienes de uso', 'Alimento general',
             'Semillas', 'Combustible', 'Fertilizantes', 'Insumos productivos', 'Productos Veterinarios', 'Insumos Generales',
             'Vacunas', 'Insecticidas', 'Fungicidas', 'Inoculantes', 'Coadyuvantes', 'Varios', 'Viaticos'),
    SERVICIOS: ('Siembra', 'Fertilizacion', 'Mantenimiento Construcciones', 'Cosecha', 'Mantenimiento Maquinarias', 'Inseminacion', 'Fumigacion',
                'Mantenimiento Instalaciones', 'Analisis laboratorio', 'Aranceles Vacunacion', 'Tacto/Ecografia',
                'Confeccion Silo', 'Embolsado Grano', 'Disqueado', 'Extraccion Grano', 'Secado', 'Zarandeo',
                'Servicio Logistica', 'Seguimiento cultivos', 'Control Cosecha', 'Analisis suelo', 'Analisis PG',
                'Gastos de Administracion', 'Pastaje',
                # Honorarios: el estudio los retiene como servicios (Detalle de Pagos 2025-2026, al centavo).
                'Honorarios Administracion', 'Honorarios Contables', 'Honorarios Profesionales', 'Honorarios Laboratorio'),
    TRANSPORTE: ('Flete insumos', 'Flete maquinaria', 'Flete hacienda', 'Flete granos'),
}


def dinero(v):
    return Decimal(str(v or 0)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


# Sin régimen con observación propia (analyze 30/10): gastos de venta de granos excluidos; fletes de granos a revisar.
OBSERVACIONES = {
    'Gastos Comercializacion': 'Gastos de venta de granos (Cargill, Lartirigoyen, FEDEA, Agro Hueso): excluido por decisión '
                               'del 30/10. Si aparece un servicio comercial no granario, reclasificar (contador)',
    'Flete granos': 'Revisar: los fletes de granos podrían quedar excluidos junto con los granos',
}


def sembrar_borrador(usuario: str) -> int:
    regimen = {r: cod for cod, rubros in BORRADOR.items() for r in rubros}
    n = 0
    for r in fetch_all('SELECT IdRubro id, Rubro r FROM dbo.Rubros', ()):
        if fetch_one('SELECT 1 x FROM dbo.RetencionesGanancias_Conceptos WHERE IdRubro=?', (r['id'],)):
            continue
        execute_write('INSERT INTO dbo.RetencionesGanancias_Conceptos (IdRubro,CodRegimen,Observaciones,Usuario) VALUES (?,?,?,?)',
                      (r['id'], regimen.get(r['r']), OBSERVACIONES.get(r['r']) or (None if r['r'] in regimen else 'Sin retención RG 830 (borrador)'),
                       usuario))
        n += 1
    return n


def rubros():
    return fetch_all("SELECT r.IdRubro idRubro,r.Rubro rubro,c.CodRegimen codRegimen,ISNULL(c.Estado,'Borrador') estado,"
                     "c.Observaciones observaciones FROM dbo.Rubros r LEFT JOIN dbo.RetencionesGanancias_Conceptos c "
                     "ON c.IdRubro=r.IdRubro ORDER BY r.Rubro", ())


def guardar_rubro(id_rubro, cod_regimen, estado, observaciones, usuario):
    datos = (cod_regimen, estado, observaciones, usuario, id_rubro)
    if not execute_write('UPDATE dbo.RetencionesGanancias_Conceptos SET CodRegimen=?,Estado=?,Observaciones=?,Usuario=?,'
                         'Modificado=SYSUTCDATETIME() WHERE IdRubro=?', datos):
        execute_write('INSERT INTO dbo.RetencionesGanancias_Conceptos (CodRegimen,Estado,Observaciones,Usuario,IdRubro) '
                      'VALUES (?,?,?,?,?)', datos)


def regimenes():
    """Regímenes de ARCA para inscriptos, para elegir en el mapeo."""
    vistos = {}
    for c in simulador.conceptos():
        if c['SITUACION'] == 'I':
            vistos.setdefault(c['COD_REGIMEN'], {'codRegimen': c['COD_REGIMEN'], 'concepto': c['CONCEPTO'],
                                                 'alicuota': c['PORCENT_A_RETENER'], 'noSujeto': c['MONTO_NO_SUJETO']})
    return sorted(vistos.values(), key=lambda x: x['concepto'])


def exclusiones(id_contacto=None):
    sql = ('SELECT e.IdExclusion idExclusion,e.IdContacto idContacto,c.[Razon Social] proveedor,e.Desde desde,e.Hasta hasta,'
           'e.Observaciones observaciones FROM dbo.RetencionesGanancias_Exclusiones e JOIN dbo.Contactos c ON c.IdContacto=e.IdContacto')
    if id_contacto:
        return fetch_all(sql + ' WHERE e.IdContacto=? ORDER BY e.Hasta DESC', (id_contacto,))
    return fetch_all(sql + ' ORDER BY e.Hasta DESC', ())


def agregar_exclusion(id_contacto, desde, hasta, observaciones, usuario):
    execute_write('INSERT INTO dbo.RetencionesGanancias_Exclusiones (IdContacto,Desde,Hasta,Observaciones,Usuario) VALUES (?,?,?,?,?)',
                  (id_contacto, desde, hasta, observaciones, usuario))


def borrar_exclusion(id_):
    execute_write('DELETE FROM dbo.RetencionesGanancias_Exclusiones WHERE IdExclusion=?', (id_,))


def condicion(id_contacto, fecha_pago) -> dict:
    """Situación del proveedor frente a la retención; si `retiene` es False, `motivo` explica por qué."""
    c = fetch_one('SELECT [CUIT/CUIL] cuit FROM dbo.Contactos WHERE IdContacto=?', (id_contacto,))
    cuit = re.sub(r'\D', '', str((c or {}).get('cuit') or ''))
    if len(cuit) != 11:
        return {'retiene': False, 'motivo': 'El proveedor no tiene CUIT cargado'}
    excl = fetch_one('SELECT TOP 1 Hasta h FROM dbo.RetencionesGanancias_Exclusiones WHERE IdContacto=? AND ? BETWEEN Desde AND Hasta',
                     (id_contacto, fecha_pago))
    if excl:
        return {'retiene': False, 'cuit': cuit, 'motivo': f"Certificado de exclusión vigente hasta {excl['h']:%d/%m/%Y}"}
    p = fetch_one('SELECT Ganancias g,Monotributo m,Actualizado a FROM dbo.RetencionesGanancias_Padron WHERE CUIT=?', (cuit,))
    if not p:
        return {'retiene': False, 'cuit': cuit,
                'motivo': 'El CUIT no figura en el padrón de ARCA descargado. Actualizá el padrón o revisá el CUIT'}
    base = {'cuit': cuit, 'padronAl': p['a'], 'persona': 'J' if cuit[:2] in ('30', '33', '34') else 'H'}
    if p['m'] and p['m'] not in ('NI', '00'):
        return {**base, 'retiene': False, 'motivo': 'Monotributista: no corresponde RG 830 (revisar RG 2616 si supera su categoría)'}
    if p['g'] == 'EX':
        return {**base, 'retiene': False, 'motivo': 'Exento en Ganancias según el padrón'}
    if p['g'] == 'NC':
        # Fideicomisos y similares: el estudio les retiene como inscriptos (Fideicomiso La Esperanza, 2025-2026).
        return {**base, 'retiene': True, 'inscripto': True,
                'aviso': 'En el padrón figura "no corresponde" Ganancias; se calcula como inscripto, confirmalo con el estudio'}
    return {**base, 'retiene': True, 'inscripto': p['g'] == 'AC'}


def _bases(facturas):
    """Base neta de IVA por régimen: el pago de cada factura se reparte según el neto de sus renglones."""
    ids = [f['idCompra'] for f in facturas]
    if not ids:
        return {}, []
    marcas = ','.join('?' * len(ids))
    tot = {r['i']: float(r['g']) for r in fetch_all(
        f'SELECT IdDeuda i,GranTotal g FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda IN ({marcas})', tuple(ids))}
    ren = fetch_all(f'SELECT d.IdCompra i,SUM(d.Cantidad*d.[Precio Unitario]) neto,c.CodRegimen cod,MAX(d.IdRubro) rubro '
                    f'FROM dbo.Det_Compras d LEFT JOIN dbo.RetencionesGanancias_Conceptos c ON c.IdRubro=d.IdRubro '
                    f'WHERE d.IdCompra IN ({marcas}) GROUP BY d.IdCompra,c.CodRegimen', tuple(ids))
    bases, avisos = defaultdict(Decimal), []
    pago = {f['idCompra']: float(f['importe']) for f in facturas}
    for r in ren:
        total = tot.get(r['i']) or 0
        if not total or r['cod'] is None:
            continue
        bases[r['cod']] += dinero(pago[r['i']] * float(r['neto']) / total)
    if any(r['rubro'] is None for r in ren):
        avisos.append('Hay renglones sin rubro: no se incluyeron en la base')
    return bases, avisos


def _mes_anterior(id_contacto, fecha_pago, cod, excluir_op):
    r = fetch_one("SELECT ISNULL(SUM(r.BasePago),0) b,ISNULL(SUM(r.Retencion),0) t FROM dbo.OrdenesPago_Retenciones r "
                  "JOIN dbo.OrdenesPago o ON o.IdOrdenPago=r.IdOrdenPago WHERE o.IdContacto=? AND o.Estado IN ('Emitida','Pagada') "
                  "AND YEAR(o.FechaPago)=? AND MONTH(o.FechaPago)=? AND r.CodRegimen=? AND o.IdOrdenPago<>?",
                  (id_contacto, fecha_pago.year, fecha_pago.month, cod, excluir_op or 0))
    return dinero(r['b']), dinero(r['t'])


def proponer(id_contacto: int, fecha_pago: date, facturas: list[dict], excluir_op=None) -> dict:
    cond = condicion(id_contacto, fecha_pago)
    out = {'condicion': cond, 'lineas': [], 'total': Decimal(0),
           'avisos': ['Los pagos del mes hechos fuera de órdenes de pago no se suman a la base']}
    if not cond['retiene']:
        return out
    bases, avisos = _bases(facturas)
    out['avisos'] += avisos
    for cod, base in sorted(bases.items()):
        if base <= 0:
            continue
        ant, ret_ant = _mes_anterior(id_contacto, fecha_pago, cod, excluir_op)
        c = simulador.concepto(cod, cond['inscripto'], cond['persona'])
        d = simulador.calcular(c['ID_ALICUOTA'], cond['inscripto'], cond['persona'], float(base), float(ant), float(ret_ant))
        ret = max(dinero(d['r_vmonto_a_retener']), Decimal(0))
        if ret < dinero(d['r_monto_minimo']):
            ret = Decimal(0)
        out['lineas'].append({'codRegimen': cod, 'concepto': c['CONCEPTO'], 'basePago': base, 'pagosAnteriores': ant,
                              'retencionesAnteriores': ret_ant, 'alicuota': d['r_valicuota'],
                              'noSujeto': dinero(d['r_vmonto_no_imponible']), 'retencion': ret, 'simulador': json.dumps(d)})
        out['total'] += ret
    return out
