from pathlib import Path
from datetime import date
from decimal import Decimal
import pytest
from src.features.backfill_impuestos import documentos, propuesta

@pytest.fixture(autouse=True)
def no_db(monkeypatch):
 import pyodbc
 monkeypatch.setattr(pyodbc,'connect',lambda *a,**k: pytest.fail('SQL real bloqueado'))

def test_archivos_y_raiz_ausente(tmp_path):
 (tmp_path/'20250101_ARBA.pdf').write_bytes(b'%PDF test')
 orgs=[dict(idOrganismo=12,organismo='ARBA')]
 result=documentos.inventario(orgs,[],[tmp_path])
 assert result['completo'] and result['items'][0]['idOrganismo']==12
 assert not documentos.inventario(orgs,[],[tmp_path/'ausente'])['completo']

def test_unico_y_ambiguo():
 pagos=[dict(medio='bna',idMovimiento=1,fecha='2025-01-01',estado='faltante',importe=Decimal('100'))]
 files=[dict(archivoId='a',idOrganismo=12,fecha='2025-01-01',usado=False)]
 rows=propuesta.emparejar(pagos,files,12,True)
 assert rows[0]['fuente']=='comprobante'
 assert propuesta.emparejar(pagos+[{**pagos[0],'idMovimiento':2}],files,12,True)[0]['fuente']=='pendiente'
 assert propuesta.emparejar(pagos,[],12,False)[0]['fuente']=='pendiente'
 assert propuesta.emparejar(pagos,[],12,True)[0]['fuente']=='generada'

def test_nombre_pegado_alias_y_ruta_heredada(tmp_path):
 anio=tmp_path/'04 2025 - 03 2026';anio.mkdir()
 (anio/'20250715_MunicipalidadDeBolivar.pdf').write_bytes(b'%PDF a')
 (anio/'20170515_TasaVial.pdf').write_bytes(b'%PDF b')
 (anio/'20250715_Agrovet.pdf').write_bytes(b'%PDF c')
 orgs=[dict(idOrganismo=72,organismo='Municipalidad de Bolivar'),dict(idOrganismo=12,organismo='ARBA')]
 usado='04 2025 - 03 2026\\20250715_MunicipalidadDeBolivar.pdf#04 2025 - 03 2026\\20250715_MunicipalidadDeBolivar.pdf#'
 result=documentos.inventario(orgs,[usado],[tmp_path],base_relativa=tmp_path)
 por_nombre={f['nombre']:f for f in result['items']}
 assert set(por_nombre)=={'20250715_MunicipalidadDeBolivar.pdf','20170515_TasaVial.pdf'}
 assert por_nombre['20250715_MunicipalidadDeBolivar.pdf']['usado']
 assert not por_nombre['20170515_TasaVial.pdf']['usado']
 assert por_nombre['20170515_TasaVial.pdf']['idOrganismo']==72

def test_usado_y_duplicado(tmp_path):
 a=tmp_path/'20250101_ARBA.pdf';a.write_bytes(b'copy')
 (tmp_path/'20250102_ARBA.pdf').write_bytes(b'copy')
 result=documentos.inventario([dict(idOrganismo=12,organismo='ARBA')],[str(a)],[tmp_path])
 assert all(x['usado'] for x in result['items'])

def test_percepcion_no_busca_comprobante_y_lleva_su_tipo():
 pagos=[dict(medio='bna',idMovimiento=1,fecha='2025-01-01',estado='faltante',importe=Decimal('100'),sinBoletaPorNaturaleza=True)]
 files=[dict(archivoId='a',idOrganismo=12,fecha='2025-01-01',usado=False)]
 row=propuesta.emparejar(pagos,files,12,True,25)[0]
 assert row['fuente']=='generada' and row['candidatos']==[] and row['tipoImpuesto']=={'modo':'existente','idTipoImpuesto':25}
