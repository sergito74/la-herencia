"""Fechas y monedas reales de aplicaciones, con datos simulados solamente."""
from datetime import date
from src.features.auditoria_cuentas.bimonetaria import construir,CotizacionBNA


def fila(i,importe):
    return {'Fecha':date(2024,9,4),'Documento':'Liquidacion final','Nro Documento':str(i),
            'Deuda':0,'Credito':importe,'Origen':'Venta Granos','IdOrigen':i}


def test_efecto_diferido_no_anticipa_dolares_y_agrupa_la_aplicacion():
    effects={('Venta Granos',1):{'fecha':date(2025,5,22),'documento':'CA0006-00123088'},
             ('Venta Granos',2):{'fecha':date(2025,5,22),'documento':'CA0006-00123088'}}
    r=construir([fila(1,75227.5),fila(2,4502.5)],{},CotizacionBNA({date(2024,9,3):950}),
                valuaciones={('Venta Granos',1):81.36,('Venta Granos',2):1.81},efectos_valuacion=effects)
    assert r['saldoPesos']==79730 and r['saldoDolares']==83.17
    assert [f['saldoDolares'] for f in r['filas']]==[0,0,83.17]
    assert r['filas'][-1]['fecha']==date(2025,5,22)
    assert r['filas'][-1]['creditoPesos']==0 and r['filas'][-1]['creditoOriginal']==83.17


def test_sin_efecto_diferido_conserva_comportamiento_y_no_mutar_entradas():
    fs=[fila(1,100)];vs={('Venta Granos',1):2}
    r=construir(fs,{},CotizacionBNA({date(2024,9,3):950}),valuaciones=vs)
    assert len(r['filas'])==1 and r['saldoDolares']==2 and r['saldoPesos']==100
    assert fs==[fila(1,100)] and vs=={('Venta Granos',1):2}


def test_no_inyectar_efectos_de_otras_cuentas():
    r=construir([fila(1,100)],{},CotizacionBNA({date(2024,9,3):950}),
                valuaciones={('Venta Granos',2):83.17},
                efectos_valuacion={('Venta Granos',2):{'fecha':date(2025,5,22),'documento':'CA ajena'}})
    assert len(r['filas'])==1


def test_importe_reconocido_no_modifica_banco_y_no_genera_residuo_proveedor():
    f={'Fecha':date(2023,8,24),'Documento':'Banco','Nro Documento':'1375',
       'Deuda':0,'Credito':9880148.0,'Origen':'Galicia','IdOrigen':1375}
    result=construir([f],{},CotizacionBNA({date(2023,8,23):349.95}),
        valuaciones={('Galicia',1375):26786.96},efectos_valuacion={('Galicia',1375):{
            'fecha':date(2023,8,29),'documento':'RI33178','pesos':9880147.75}})
    assert result['saldoPesos']==9880147.75 and result['saldoDolares']==26786.96
    assert f['Credito']==9880148.0 and f['Fecha']==date(2023,8,24)
