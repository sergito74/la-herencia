from decimal import Decimal as D
import pytest
from src.features.backfill_impuestos.diagnostico import diagnosticar

@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    import pyodbc
    monkeypatch.setattr(pyodbc, 'connect', lambda *a, **k: pytest.fail('No SQL real en tests'))

def pago(i=1, **kw):
    return dict(medio='bna',idMovimiento=i,idOrganismo=12,fecha='2025-01-01',concepto='Impuesto',importe=D('100'),creditoContable=D('100'),filasContables=1,respaldo=D('0'),**kw)

def test_faltante_y_signos():
    rows=diagnosticar([pago()],[],D('-100'))
    assert rows[0]['estado']=='faltante' and rows[0]['importeAGenerar']==D('100')
    assert diagnosticar([{**pago(),'importe':D('-100')}],[],D('0'))[0]['estado']=='excluido'

def test_reintegro_del_organismo_compensa_el_pago():
    rows=diagnosticar([pago(),{**pago(2),'importe':D('-100')}],[],D('0'))
    assert [x['estado'] for x in rows]==['respaldado','excluido']

def test_respaldo_y_parcial():
    rows=diagnosticar([{**pago(),'respaldo':D('99.91')},{**pago(2),'respaldo':D('40')}],[],D('-200'))
    assert [x['estado'] for x in rows]==['respaldado','pendiente']

def test_boleta_compatible_respalda_un_solo_pago():
    """Cuotas fijas: dos pagos iguales y una boleta — respalda solo al más cercano en fecha."""
    boletas=[dict(idImpuesto=1,saldo=D('100'),fecha='2025-02-10')]
    rows=diagnosticar([pago(),{**pago(2),'fecha':'2025-02-12'}],boletas,D('-200'))
    assert [x['estado'] for x in rows]==['faltante','respaldado']
    assert rows[1]['boletaPorCoincidencia']==1

def test_boleta_fuera_de_ventana_no_coincide_pero_absorbe():
    boletas=[dict(idImpuesto=1,saldo=D('100'),fecha='2025-06-01')]
    row=diagnosticar([pago()],boletas,D('0'))[0]
    assert row['estado']=='respaldado' and row['boletaPorCoincidencia'] is None and row['importeAGenerar']==D('0')

def test_boleta_menor_cubre_en_parte_y_se_genera_la_diferencia():
    boletas=[dict(idImpuesto=1,saldo=D('40'),fecha='2025-01-01')]
    row=diagnosticar([pago()],boletas,D('-60'))[0]
    assert row['estado']=='faltante' and row['importeAGenerar']==D('60') and row['importeCubierto']==D('40')

def test_otros_documentos_absorben_por_fecha_cercana():
    extra=[dict(id='Compras:1',fecha='2025-03-01',importe=D('100'))]
    rows=diagnosticar([pago(),{**pago(2),'fecha':'2025-03-02'}],[],D('-100'),documentos_extra=extra)
    assert [r['estado'] for r in rows]==['faltante','respaldado']

def test_generacion_deshabilitada_deja_pendiente():
    row=diagnosticar([pago()],[],D('-100'),generacion_habilitada=False,motivo_bloqueo='AFIP')[0]
    assert row['estado']=='pendiente' and row['motivo']=='AFIP'

def test_contabilidad_duplicada_o_ausente():
    rows=diagnosticar([{**pago(),'filasContables':2},{**pago(2),'filasContables':0}],[],D('-200'))
    assert all(x['estado']=='pendiente' for x in rows)

def test_otros_documentos_no_bloquean_la_generacion():
    """Decisión del usuario: otros documentos en la cuenta son una advertencia, no un bloqueo."""
    assert diagnosticar([pago()],[],D('0'),otros_documentos=True)[0]['estado']=='faltante'

def test_no_asignado_traspaso_y_fecha_nula():
    rows=diagnosticar([{**pago(),'idOrganismo':None},{**pago(2),'traspaso':True},{**pago(3),'fecha':None}],[],D('-300'))
    assert [r['estado'] for r in rows]==['pendiente','excluido','pendiente']

def test_recaudacion_arba_no_se_empareja_ni_absorbe():
    """Percepción IIBB: aunque haya una boleta del mismo importe, se registra desde el pago."""
    boletas=[dict(idImpuesto=1,saldo=D('100'),fecha='2025-01-01')]
    rows=diagnosticar([{**pago(),'sinBoletaPorNaturaleza':True},pago(2)],boletas,D('-100'))
    assert rows[0]['estado']=='faltante' and rows[0]['importeAGenerar']==D('100') and rows[0]['boletaPorCoincidencia'] is None
    assert rows[1]['estado']=='respaldado' and rows[1]['boletaPorCoincidencia']==1
