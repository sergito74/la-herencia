"""Cheques entregados: lectura de comprobantes y cruce con Galicia — 035. Textos reales de los PDF; sin base."""

from datetime import date

from src.features.auditoria_cuentas import echeqs as e

DETALLE = """Office Banking
Detalle de cheque electrónico
Importe N° de Cheque Emitido a
$ 114061.38 00000065 PALAVERSICH Y COMPANIA
SOCIEDD ANONIMA
30523522961
Estado
Emitido
Datos del cheque
Importe N° de cheque
114061.38 00000065
ID del cheque ID Multicheque
GOW9MXZZJVYNEXD N/A
Fecha de pago Fecha de Emisión
13/05/23 24/04/23
Cláusula Descripción del pago
A la orden Factura 32206
Emitido a CUIT/CUIL/CDI
PALAVERSICH Y COMPANIA 30523522961
SOCIEDD ANONIMA
Datos del librador
Razón social CUIT/CUIL/CDI
GIAMIGLI DE BOLIVAR SA 30712114602
"""
OPERACION = """Consultas
Consulta de Operaciones
Número de operación 105332955
Emitido a TIERRAS DE HENDERSON SA
Documento 30-70936414-2
Importe Total $ 495.170,50
Fecha de Pago 04/06/2022
Referencia 0004-00003911
Estado Ejecutada
GIAMBERARDINI Sergio Gabriel DU 23859810 20210610 123627 a.m. Autoriza
"""
EMISION = """Datos de la operación LR19DZY824
Estado Motivo
Realizado -
Fecha de ejecución Tipo de operación
09/01/2026 Emisión
Datos del beneficiario
Razón social
PEREZ CLAUDIO ALEJANDRO
CUIT/CUIL
20218532064
Datos del cheque
Número de cheque Cláusula
118 A la orden
Fecha de pago Monto
05/02/2026 $ 1.107.649,24
Motivo de la emisión
Factura / 00002-00000701
"""
RECIBIDO = DETALLE.replace("GIAMIGLI DE BOLIVAR SA 30712114602", "AGROPECUARIA SARCIAT 30709089443").replace("Emitido\n", "Endoso enviado\n")


def test_comprobante_de_detalle_trae_la_fecha_de_emision_como_fecha_de_entrega():
    r = e.leer_pdf(DETALLE)
    assert (r["numero"], r["importe"], r["fechaEntrega"], r["fechaPago"], r["tipo"]) == ("00000065", 114061.38, "2023-04-24", "2023-05-13", "emitido")
    assert r["cuitBeneficiario"] == "30523522961" and r["descripcion"] == "Factura 32206"


def test_comprobante_de_operacion_y_de_emision():
    o = e.leer_pdf(OPERACION, "E-Cheq 00000005.pdf")
    assert (o["numero"], o["importe"], o["fechaEntrega"], o["fechaPago"]) == ("00000005", 495170.5, "2021-06-10", "2022-06-04")
    m = e.leer_pdf(EMISION)
    assert (m["numero"], m["importe"], m["fechaEntrega"], m["fechaPago"], m["tipo"]) == ("118", 1107649.24, "2026-01-09", "2026-02-05", "emitido")
    assert m["beneficiario"] == "PEREZ CLAUDIO ALEJANDRO" and m["descripcion"] == "Factura / 00002-00000701"


def test_cheque_de_un_tercero_endosado_no_usa_la_emision_del_tercero_como_entrega():
    r = e.leer_pdf(RECIBIDO)
    assert r["tipo"] == "endoso" and "fechaEntrega" not in r and r["fechaEmisionTercero"] == "2023-04-24"
    e.completar_fecha_con_el_archivo(r, 1719327600.0)
    assert r["fechaEstimada"] is True and r["fechaEntrega"]


def test_pdf_escaneado_no_se_reconoce():
    assert e.leer_pdf("") == {} and e.leer_pdf(None) == {}


def test_numero_normalizado():
    assert e.numero_normalizado("00000065") == "65" and e.numero_normalizado("65") == "65" and e.numero_normalizado(None) is None


def test_fusionar_enriquece_con_la_planilla_y_agrega_lo_que_solo_esta_en_ella():
    pdf = [{"numero": "00000065", "importe": 114061.38, "tipo": "emitido", "fechaEntrega": "2023-04-24", "fuente": "pdf"}]
    planilla = [{"tipo": "emitido", "numero": "00000065", "importe": 114061.4, "documento": "Factura 32206", "importeUsd": 2129.6, "tcEmision": 214.24, "fuente": "excel"},
                {"tipo": "papel", "numero": "28479816", "importe": 450000.0, "fuente": "excel"}]
    r = e.fusionar(pdf, planilla)
    assert len(r) == 2 and r[0]["fuente"] == "pdf+excel" and r[0]["documento"] == "Factura 32206" and r[0]["tcEmision"] == 214.24
    assert r[1]["tipo"] == "papel" and r[1]["fuente"] == "excel"


def test_cruce_con_el_debito_de_galicia():
    cheques = [{"numero": "00000065", "importe": 114061.38, "fechaPago": "2023-05-13", "tipo": "emitido"},
               {"numero": "00000066", "importe": 114031.38, "fechaPago": "2023-06-11", "tipo": "emitido"},
               {"numero": "00000099", "importe": 5.0, "fechaPago": "2023-06-11", "tipo": "emitido"},
               {"numero": "80655", "importe": 1.0, "fechaPago": "2023-06-11", "tipo": "endoso"}]
    mov = [{"id": 1196, "fecha": date(2023, 5, 16), "descripcion": "Echeq 48 Hs. Nro.       65", "debito": 114061.38},
           {"id": 1254, "fecha": date(2023, 6, 13), "descripcion": "ECHEQ 48 HS. NRO. 66", "debito": 114031.38},
           {"id": 7, "fecha": date(2023, 6, 13), "descripcion": "OTRO", "debito": 99.0}]
    c = e.cruzar_con_galicia(cheques, mov)
    assert {i: m["id"] for i, m in c.items()} == {0: 1196, 1: 1254}
