import pytest
from src.features.backfill_impuestos import respaldo

@pytest.fixture(autouse=True)
def no_db(monkeypatch):
 import pyodbc
 monkeypatch.setattr(pyodbc,'connect',lambda *a,**k: pytest.fail('SQL real bloqueado'))
 monkeypatch.setattr(respaldo,'get_secret',lambda: b'test-secret')

def test_token_separado_y_alterado():
 token=respaldo.preparar('confirmar','abc','1')
 assert respaldo.decode(token)['usuario']=='1'
 with pytest.raises(ValueError): respaldo.decode(token+'x')
 with pytest.raises(ValueError): respaldo.check_preparacion(token,'revertir','abc','1')
 with pytest.raises(ValueError): respaldo.check_preparacion(token,'confirmar','abc','2')

def test_backup_anterior_o_inexistente(tmp_path,monkeypatch):
 monkeypatch.setattr(respaldo,'directorio',lambda:tmp_path)
 token=respaldo.preparar('confirmar','abc','1')
 with pytest.raises(ValueError): respaldo.verificar('00000000-0000-0000-0000-000000000000',token)

from contextlib import contextmanager
from types import SimpleNamespace
from decimal import Decimal
from uuid import uuid4
from src.features.backfill_impuestos import escrituras

def test_confirmacion_rollback_y_no_segundo_asiento(monkeypatch):
    writes=[];audit=[]
    @contextmanager
    def transaction():
        audit.append('begin')
        try: yield
        except Exception:
            writes.clear();audit.append('rollback');raise
        else: audit.append('commit')
    monkeypatch.setattr(escrituras,'reconciliation_transaction',transaction)
    monkeypatch.setattr(escrituras.repo,'schema_ready',lambda:True)
    monkeypatch.setattr(escrituras.repo,'read',lambda *a:[])
    monkeypatch.setattr(escrituras.respaldo,'check_preparacion',lambda *a:None)
    monkeypatch.setattr(escrituras.respaldo,'verificar',lambda *a:None)
    monkeypatch.setattr(escrituras.propuesta,'full',lambda *a:{})
    selected=dict(pago=dict(fecha='2025-01-01',importe=Decimal('100'),importeAGenerar=Decimal('100'),medio='bna',idMovimiento=1,huella='h'),
                  decision=dict(tipoImpuesto=dict(modo='generico'),periodoLiquidado=None,numeroDocumento=None,fuente='generada'),archivo=None)
    monkeypatch.setattr(escrituras.propuesta,'validar',lambda *a:dict(huellaPropuesta='h',cantidad=1,total=Decimal('100'),seleccion=[selected]))
    monkeypatch.setattr(escrituras,'execute_write',lambda sql,args:writes.append(sql) or 1)
    monkeypatch.setattr(escrituras,'execute_insert_returning_id',lambda sql,args:writes.append(sql) or 123)
    monkeypatch.setattr(escrituras,'imagen',lambda i:dict(IdImpuesto=i))
    def fail(*a): raise RuntimeError('fallo de auditoría')
    monkeypatch.setattr(escrituras,'event',fail)
    body=SimpleNamespace(idLote=uuid4(),organismoId=12,huellaPropuesta='h',decisiones=[],preparacion='p',backupId=uuid4())
    with pytest.raises(RuntimeError): escrituras.confirmar(body,'1')
    assert audit==['begin','rollback'] and writes==[]
    monkeypatch.setattr(escrituras,'event',lambda *a:None)
    monkeypatch.setattr(escrituras,'lote',lambda key:dict(IdLote=str(key)))
    assert not escrituras.confirmar(body,'1')['repetido']
    assert all('ConciliacionesTesoreria' not in sql for sql in writes)
    assert all(not sql.startswith(('UPDATE','DELETE')) for sql in writes)

def test_reintento_no_requiere_backup_nuevo(monkeypatch):
    monkeypatch.setattr(escrituras.repo,'schema_ready',lambda:True)
    body=SimpleNamespace(idLote=uuid4(),organismoId=12,huellaPropuesta='h',decisiones=[])
    expected=escrituras.digest(dict(organismoId=12,huellaPropuesta='h',decisiones=[]))
    monkeypatch.setattr(escrituras.repo,'read',lambda *a:[dict(HashSolicitud=expected)])
    monkeypatch.setattr(escrituras,'lote',lambda key:dict(IdLote=str(key)))
    assert escrituras.confirmar(body,'1')['repetido']
    body.huellaPropuesta='other'
    with pytest.raises(ValueError): escrituras.confirmar(body,'1')

def test_reversion_dos_boletas_y_conflicto(monkeypatch):
    writes=[]
    @contextmanager
    def transaction(): yield
    monkeypatch.setattr(escrituras,'reconciliation_transaction',transaction)
    monkeypatch.setattr(escrituras,'lote',lambda key:dict(Estado='confirmado'))
    monkeypatch.setattr(escrituras.respaldo,'check_preparacion',lambda *a:None)
    monkeypatch.setattr(escrituras.respaldo,'verificar',lambda *a:None)
    report=dict(revertido=False,bloqueos=[],huellaReversion='h',boletas=[dict(IdRegistro=1,IdImpuesto=10),dict(IdRegistro=2,IdImpuesto=11)],vinculos=[])
    monkeypatch.setattr(escrituras,'revisar_reversion',lambda *a:report)
    monkeypatch.setattr(escrituras,'execute_write',lambda sql,args:writes.append((sql,args)) or 1)
    monkeypatch.setattr(escrituras,'event',lambda *a:None)
    body=SimpleNamespace(preparacion='p',huellaReversion='h',backupId=uuid4())
    escrituras.revertir(uuid4(),body,'1')
    assert sum('SET IdImpuesto=NULL' in sql for sql,args in writes)==2
    assert {args[0] for sql,args in writes if sql.startswith('DELETE FROM dbo.Impuestos')}=={10,11}
    writes.clear();report['bloqueos']=['edición posterior']
    with pytest.raises(ValueError): escrituras.revertir(uuid4(),body,'1')
    assert writes==[]

def test_migracion_backup_antes_de_ddl(monkeypatch):
    from scripts import crear_tablas_backfill_impuestos as m
    order=[]
    monkeypatch.setattr(escrituras.repo,'schema_ready',lambda:False)
    monkeypatch.setattr(m.respaldo,'crear',lambda t:order.append('backup verificado') or dict(backupId='test',ruta='externa'))
    class Cursor:
        def execute(self,sql): order.append('DDL' if sql==m.DDL else sql)
        def nextset(self): return False
    @contextmanager
    def connection(**kw): yield SimpleNamespace(cursor=lambda:Cursor())
    monkeypatch.setattr(m,'get_connection',connection)
    m.migrate()
    assert order==['backup verificado','BEGIN TRANSACTION','DDL','COMMIT TRANSACTION']
    assert 'WHERE IdImpuesto IS NOT NULL' in m.DDL
