"""Extractos SCT documentales en WC, independientes del mayor financiero."""
import json

from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes.arca_documentos import verificar_archivo

IMPUESTOS = ('GANANCIAS', 'SICORE', 'IVA')


def listar(impuesto=None):
    if impuesto is not None and impuesto not in IMPUESTOS:
        raise ValueError('Impuesto desconocido')
    condition = 'WHERE Impuesto=?' if impuesto else ''
    rows = read('SELECT TOP (100) IdExtracto id,Impuesto impuesto,Periodo periodo,Fuente fuente,'
                'FechaConsulta fechaConsulta,Incompleto incompleto FROM '
                '(SELECT *,ROW_NUMBER() OVER (PARTITION BY REPLACE(Fuente,\'-completo\',\'\') ORDER BY IdExtracto DESC) versionActual FROM dbo.ArcaSctExtractos) q '
                'WHERE versionActual=1 ' + ('AND Impuesto=? ' if impuesto else '')
                + 'ORDER BY Impuesto,Periodo DESC,IdExtracto DESC', (impuesto,) if impuesto else ())
    return {'items': rows, 'limite': 100}


def detalle(ident):
    rows = read('SELECT IdExtracto id,Impuesto impuesto,Periodo periodo,Fuente fuente,FechaConsulta fechaConsulta,'
                'Incompleto incompleto,Contenido contenido FROM dbo.ArcaSctExtractos WHERE IdExtracto=?', (ident,))
    if not rows:
        raise LookupError('Extracto fiscal no encontrado')
    result = rows[0]
    result['conceptos'] = json.loads(result.pop('contenido'))
    source = result['fuente'].replace('-completo', '').removesuffix('-movimientos.txt')
    interest = source.replace('SCT-', 'SCT-INT-', 1)
    result['registrosMayor'] = read('SELECT TOP (20) IdImpuesto idImpuesto,[Numero de documento] numero,Importe importe '
                                   'FROM dbo.Impuestos WHERE IdOrganismo=119 AND [Numero de documento] IN (?,?) ORDER BY IdImpuesto',
                                   (source, interest))
    return result


def archivo(ident):
    rows = read('SELECT PdfRuta ruta,PdfSha256 sha256 FROM dbo.ArcaSctExtractos WHERE IdExtracto=?', (ident,))
    if not rows:
        raise FileNotFoundError('Extracto fiscal no encontrado')
    return verificar_archivo(rows[0]['ruta'], rows[0]['sha256'])
