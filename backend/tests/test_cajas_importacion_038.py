from datetime import date, datetime
from io import BytesIO
from zipfile import ZipFile
import pytest

from tests.test_cajas_contrato_importacion_038 import lot as lot_fixture, xlsx

from src.features.cajas_efectivo import importacion as imp


lot = lot_fixture

def existing():
    return {
        "idMovimiento": 10,
        "idOperacion": None,
        "filaPlanilla": 2,
        "concepto": "Pago",
        "anulada": False,
        "cuenta": "White",
        "importe": -100,
    }


def test_fila_historica_se_vincula_sin_recrear_pago(lot):
    lot["movs"] = [existing()]
    result = imp.previsualizar(
        xlsx([[datetime(2026, 10, 22), "Pago", "White", None, None, None, -100, -100]]),
        "CajasGiamigli",
        date(2026, 10, 22),
        "prueba",
    )
    assert result["filas"][0]["estado"] == "Vinculada"
    assert result["filas"][0]["idMovimiento"] == 10 and lot["creadas"] == 0


def test_fila_desplazada_no_se_inserta_silenciosamente(lot):
    lot["movs"] = [existing()]
    result = imp.previsualizar(
        xlsx([[None] * 8, [datetime(2026, 10, 22), "Pago", "White", None, None, None, -100, -100]]),
        "CajasGiamigli",
        date(2026, 10, 22),
        "prueba",
    )
    assert result["filas"][0]["fila"] == 3 and result["filas"][0]["estado"] == "Ambigua"
    assert lot["creadas"] == 0


def test_fila_con_otro_importe_queda_modificada(lot):
    lot["movs"] = [existing()]
    result = imp.previsualizar(
        xlsx([[datetime(2026, 10, 22), "Pago", "White", None, None, None, -120, -120]]),
        "CajasGiamigli",
        date(2026, 10, 22),
        "prueba",
    )
    assert result["filas"][0]["estado"] == "Modificada" and lot["creadas"] == 0


def test_cambio_de_detalle_con_importe_igual_no_se_oculta(lot):
    lot["movs"] = [existing()]
    lot["priorSource"] = {"Huella": "a" * 64, "IdMovimiento": 10}
    result = imp.previsualizar(
        xlsx(
            [[datetime(2026, 10, 22), "Pago", "White", "Detalle cambiado", None, None, -100, -100]]
        ),
        "CajasGiamigli",
        date(2026, 10, 22),
        "prueba",
    )
    assert result["filas"][0]["estado"] == "Modificada" and lot["creadas"] == 0


def test_macros_rechazadas_y_rounding_comercial():
    stream = BytesIO()
    with ZipFile(stream, "w") as z:
        z.writestr("xl/vbaProject.bin", b"macro no ejecutada")
    with pytest.raises(ValueError, match="macros"):
        imp.parse(stream.getvalue(), "CajasGiamigli", date(2026, 10, 22))
    assert str(imp._money("1.005")) == "1.01"
