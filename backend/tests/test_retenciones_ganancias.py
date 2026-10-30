from datetime import date
from decimal import Decimal
from email import message_from_bytes, policy

import pytest
from pydantic import ValidationError

from src.db import connection
from src.features.ordenes_pago.schemas import OrdenInput
from src.features.retenciones_ganancias import mail, padron, repository as r


@pytest.fixture(autouse=True)
def aislado(monkeypatch):
    monkeypatch.setattr(connection.pyodbc, 'connect', lambda *a, **k: pytest.fail('La prueba no debe acceder a WC'))


def padron_de(monkeypatch, cuit='30613985995', fila=None, exclusion=None):
    def uno(sql, params=()):
        if 'Contactos' in sql:
            return {'cuit': cuit}
        if 'Exclusiones' in sql:
            return exclusion
        return fila
    monkeypatch.setattr(r, 'fetch_one', uno)


@pytest.mark.parametrize('fila,exclusion,retiene,texto', [
    (None, None, False, 'padrón'),
    ({'g': 'AC', 'm': 'A', 'a': date(2026, 10, 30)}, None, False, 'Monotributista'),
    ({'g': 'EX', 'm': 'NI', 'a': date(2026, 10, 30)}, None, False, 'Exento'),
    ({'g': 'AC', 'm': 'NI', 'a': date(2026, 10, 30)}, {'h': date(2026, 12, 31)}, False, 'exclusión'),
])
def test_condiciones_sin_retencion(monkeypatch, fila, exclusion, retiene, texto):
    padron_de(monkeypatch, fila=fila, exclusion=exclusion)
    c = r.condicion(1, date(2026, 10, 30))
    assert c['retiene'] is retiene and texto in c['motivo']


def test_inscripto_no_inscripto_y_no_corresponde(monkeypatch):
    padron_de(monkeypatch, fila={'g': 'AC', 'm': 'NI', 'a': date(2026, 10, 30)})
    c = r.condicion(1, date(2026, 10, 30))
    assert (c['retiene'], c['inscripto'], c['persona']) == (True, True, 'J')
    padron_de(monkeypatch, cuit='20218532064', fila={'g': 'NI', 'm': 'NI', 'a': date(2026, 10, 30)})
    c = r.condicion(1, date(2026, 10, 30))
    assert c['inscripto'] is False and c['persona'] == 'H'
    padron_de(monkeypatch, cuit='30708885084', fila={'g': 'NC', 'm': 'NI', 'a': date(2026, 10, 30)})
    c = r.condicion(1, date(2026, 10, 30))
    assert c['retiene'] and c['inscripto'] and 'estudio' in c['aviso']


def test_sin_cuit(monkeypatch):
    padron_de(monkeypatch, cuit=None)
    assert 'CUIT' in r.condicion(1, date(2026, 10, 30))['motivo']


def test_base_neta_repartida_por_regimen(monkeypatch):
    def todos(sql, params=()):
        if 'vw_Cns_Total_Compra' in sql:
            return [{'i': 1, 'g': 1210.0}]
        return [{'i': 1, 'neto': 600.0, 'cod': 78, 'rubro': 5}, {'i': 1, 'neto': 400.0, 'cod': 94, 'rubro': 6}]
    monkeypatch.setattr(r, 'fetch_all', todos)
    bases, avisos = r._bases([{'idCompra': 1, 'importe': 605}])  # mitad de la factura
    assert bases == {78: Decimal('300.00'), 94: Decimal('200.00')} and not avisos


def test_acumula_el_mes_y_aplica_minimo(monkeypatch):
    monkeypatch.setattr(r, 'condicion', lambda *a: {'retiene': True, 'inscripto': True, 'persona': 'J'})
    monkeypatch.setattr(r, '_bases', lambda f: ({94: Decimal('899099.98')}, []))
    monkeypatch.setattr(r, '_mes_anterior', lambda *a: (Decimal('899099.98'), Decimal('16638.60')))
    monkeypatch.setattr(r.simulador, 'concepto', lambda *a: {'ID_ALICUOTA': 34, 'CONCEPTO': 'Servicios'})
    llamadas = []

    def calcular(alic, insc, pers, base, ant, ret):
        llamadas.append((base, ant, ret))
        total = (base + ant - 67170) * 0.02 - ret
        return {'r_vmonto_a_retener': total, 'r_monto_minimo': 240, 'r_valicuota': 2, 'r_vmonto_no_imponible': 67170}
    monkeypatch.setattr(r.simulador, 'calcular', calcular)
    p = r.proponer(1, date(2026, 10, 30), [{'idCompra': 1, 'importe': 1}])
    assert llamadas == [(899099.98, 899099.98, 16638.6)]
    assert p['total'] == Decimal('17982.00')  # (899.099,98 × 2 − 67.170) × 2% − 16.638,60: la segunda cuota del mes de Pérez

    monkeypatch.setattr(r.simulador, 'calcular', lambda *a: {'r_vmonto_a_retener': 200, 'r_monto_minimo': 240,
                                                             'r_valicuota': 2, 'r_vmonto_no_imponible': 67170})
    assert r.proponer(1, date(2026, 10, 30), [{'idCompra': 1, 'importe': 1}])['total'] == 0


def test_medios_suman_neto_de_retencion():
    datos = dict(idContacto=7, fecha='2026-10-30', fechaPago='2026-10-30', facturas=[{'idCompra': 1, 'importe': 1000}],
                 medios=[{'medio': 'Transferencia', 'cuenta': 'Galicia', 'importe': 980}],
                 retenciones=[dict(codRegimen=94, concepto='Servicios', basePago=826.45, pagosAnteriores=0,
                                   retencionesAnteriores=0, alicuota=2, noSujeto=67170, retencion=20, simulador='{}')])
    assert OrdenInput(**datos).retenciones[0].retencion == 20
    with pytest.raises(ValidationError):
        OrdenInput(**(datos | {'medios': [{'medio': 'Transferencia', 'cuenta': 'Galicia', 'importe': 1000}]}))


def test_lectura_del_padron_de_ancho_fijo():
    linea = '30613985995' + 'LARTIRIGOYEN Y CIA S A'.ljust(30) + 'AC' + 'AC' + 'NI' + 'N' + 'S' + ' 00'
    assert padron.leer([linea, '20000000001' + 'X' * 30 + 'NI' * 3], {'30613985995'}) == [
        ('30613985995', 'LARTIRIGOYEN Y CIA S A', 'AC', 'AC', 'NI', 'S')]


def test_mail_al_estudio(monkeypatch, tmp_path):
    pdf = tmp_path / 'factura.pdf'
    pdf.write_bytes(b'%PDF-1.4')
    monkeypatch.setattr(mail, 'fetch_all', lambda *a: [{'i': 1, 'f': date(2026, 10, 6), 'v': date(2026, 10, 10), 't': 'Factura',
                                                        'n': '00002-00000065', 'd': str(pdf)}])
    orden = {'proveedor': 'Fideicomiso La Esperanza', 'fechaPago': date(2026, 10, 8),
             'facturas': [{'idCompra': 1, 'importe': 1722568.1}], 'medios': [{'medio': 'Transferencia'}]}
    eml, avisos = mail.armar(orden)
    m = message_from_bytes(eml, policy=policy.default)
    assert not avisos and m['To'] == 'administracion@estudiocriado.com' and m['X-Unsent'] == '1'
    assert m['Subject'] == 'Giamigli de Bolivar S.A. - Retencion'
    texto = m.get_body(('plain',)).get_content()
    assert '06/10/2026 | 10/10/2026 | 08/10/2026 | Fideicomiso La Esperanza | Factura | 00002-00000065 | Pesos | ' \
           'Transferencia bancaria | $ 1.722.568,10' in texto
    assert [a.get_filename() for a in m.iter_attachments()] == ['factura.pdf']


def test_mail_con_factura_en_dolares(monkeypatch):
    monkeypatch.setattr(mail, 'fetch_all', lambda *a: [{'i': 1, 'f': date(2023, 7, 20), 'v': date(2023, 8, 18), 't': 'Factura',
                                                        'n': '0149 - 00011970', 'd': None, 'm': 'Dolares', 'tc': 267.95}])
    orden = {'proveedor': 'Lartirigoyen', 'fechaPago': date(2023, 7, 21),
             'facturas': [{'idCompra': 1, 'importe': 1400628.24}], 'medios': [{'medio': 'Transferencia'}]}
    eml, avisos = mail.armar(orden)
    texto = message_from_bytes(eml, policy=policy.default).get_body(('plain',)).get_content()
    assert '| Tipo Cambio | Importe pesos' in texto
    assert 'Dolares | Transferencia bancaria | US$ 5.227,20 | $ 267,95/u$s | $ 1.400.628,24' in texto
    assert avisos == ['La factura 0149 - 00011970 no tiene archivo para adjuntar']
