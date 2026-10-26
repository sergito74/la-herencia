from decimal import Decimal

from scripts.conciliar_sct_arca_036 import parse
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.features.cuentas_corrientes import arca_fiscal, arca_router


def test_conserva_compensacion_y_contrapartida_sin_convertir_en_pago(tmp_path):
    path = tmp_path / 'sct.txt'
    path.write_text('IMPUESTO DETERMINADO - SALDO: $0.00\n'
                    '01/10/2025 08:00\t01/10/2025 08:01\tDébito de Anticipo Generado\t442,267.59\t \t\n'
                    '01/10/2025 08:06\t01/10/2025 08:06\tCompensación\t \t442,267.59\t\n'
                    'SALDO A FAVOR - SALDO: ($17,159.07)\n'
                    '01/10/2025 08:06\t01/10/2025 08:06\tConversión\t \t17,159.07\t\n', encoding='utf-8')
    sections = parse(path)['conceptos']
    assert all(s['verificado'] for s in sections)
    assert sections[0]['movimientos'][1]['detalle'] == 'Compensación'
    assert sections[1]['saldoDeudorPublicado'] == Decimal('-17159.07')


def test_pagina_incompleta_no_se_declara_verificada_aunque_saldo_coincida(tmp_path):
    path = tmp_path / 'sct.txt'
    path.write_text('PAGOS - SALDO: $0.00\nMostrando registros del 1 al 10 de un total de 12 registros\n', encoding='utf-8')
    section = parse(path)['conceptos'][0]
    assert section['incompleto']
    assert not section['verificado']


def test_saldo_inconsistente_se_senala(tmp_path):
    path = tmp_path / 'sct.txt'
    path.write_text('INTERESES - SALDO: $54.58\n'
                    '22/10/2025 10:40\t22/10/2025 10:40\tLiquidación\t54.57\t \t\n', encoding='utf-8')
    section = parse(path)['conceptos'][0]
    assert section['diferencia'] == Decimal('-0.01')
    assert not section['verificado']


def test_contrato_fiscal_validacion_vacio_y_faltante(monkeypatch):
    app = FastAPI()
    app.include_router(arca_router.router)
    monkeypatch.setattr(arca_fiscal, 'read', lambda sql, params=(): [])
    with TestClient(app) as client:
        assert client.get('/api/arca/fiscal?impuesto=GANANCIAS').json() == {'items': [], 'limite': 100}
        assert client.get('/api/arca/fiscal?impuesto=OTRO').status_code == 422
        assert client.get('/api/arca/fiscal/999').status_code == 404
        assert client.get('/api/arca/fiscal/999/archivo').status_code == 404


def test_detalle_conserva_importes_como_cadenas_sin_sumar_conceptos(monkeypatch):
    import json
    concepts = [{'concepto': 'A', 'saldoDeudorPublicado': '-3715623.22', 'movimientos': []},
                {'concepto': 'B', 'saldoDeudorPublicado': '-1007737.91', 'movimientos': []}]
    monkeypatch.setattr(arca_fiscal, 'read', lambda sql, params=(): [] if 'TOP (20)' in sql else [{'id': 1, 'fuente': 'SCT-GANANCIAS-2026-DDJJ-movimientos.txt', 'contenido': json.dumps(concepts)}])
    assert arca_fiscal.detalle(1)['conceptos'] == concepts
    assert arca_fiscal.detalle(1)['registrosMayor'] == []
