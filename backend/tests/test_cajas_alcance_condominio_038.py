from datetime import date
from decimal import Decimal
from io import BytesIO
import pytest
from openpyxl import Workbook
from src.features.cajas_efectivo.alcance_condominio import evidencia_relacion
from src.features.cajas_efectivo import importacion, arqueos


@pytest.mark.parametrize(
    "concepto",
    [
        "Alquiler Jujuy",
        "Retiro Sergio",
        "Retiro Lucy",
        "Retiro Ceci",
        "Saldo Inicial",
        "Retorno FC Alquiler",
        "Pago Gastos Factura Guille",
        "Pago IIBB Cond. Giamberardini Oscar y otros",
    ],
)
def test_no_infiere_relacion_por_socio_o_ingreso(concepto):
    assert evidencia_relacion(concepto) is None


def test_criado_requiere_fila_fecha_e_importe_documentados():
    assert evidencia_relacion("Pago Honorarios Criado", "2016-04-20", Decimal("-3818"), 15)
    assert not evidencia_relacion("Pago Honorarios Criado", "2026-04-20", -3818, 15)
    assert not evidencia_relacion("Pago Honorarios Criado", "2016-04-20", -3818, 16)
    assert evidencia_relacion("Aporte Efectivo Giamigli")


def test_importa_solo_relacion_y_saldo_de_subconjunto():
    w = Workbook()
    s = w.active
    s.title = "Caja Efectivo"
    s.append(["Fecha", "Descripcion", "Importe", "Saldo"])
    s.append([date(2026, 1, 1), "Alquiler Jujuy", 10000, 10000])
    s.append([date(2026, 1, 2), "Aporte Efectivo Giamigli", -1000, 9000])
    b = BytesIO()
    w.save(b)
    rows = importacion.parse(b.getvalue(), "CondominioLSC", date(2026, 10, 23))
    assert len(rows) == 1
    assert rows[0]["normalizada"]["concepto"] == "Aporte Efectivo Giamigli"
    assert Decimal(rows[0]["saldoPlanilla"]) == Decimal("-1000")


def test_subconjunto_no_admite_arqueos_fisicos():
    with pytest.raises(ValueError, match="registro parcial"):
        arqueos.guardar.__wrapped__("condominio-lsc", None, "prueba")
    with pytest.raises(ValueError, match="registro parcial"):
        arqueos.confirmar.__wrapped__("condominio-lsc", 1, None, "prueba")


def test_importador_completo_retirado_no_escribe():
    from scripts.caja_condominio_lsc_036 import main

    with pytest.raises(RuntimeError, match="deshabilitada"):
        main()


def test_neto_condominio_no_genera_advertencia_de_caja_negativa(monkeypatch):
    from tests.cajas_038_helpers import CajaSimulada, request
    from src.features.cajas_efectivo import service, operaciones as db
    from src.features.cajas_efectivo.schemas import OperacionCaja

    CajaSimulada(monkeypatch)
    monkeypatch.setattr(
        db,
        "caja_context",
        lambda box, *a, **k: {
            "saldoActual": Decimal(-1000 if box == "condominio-lsc" else 100),
            "minimoPosterior": Decimal(-1000 if box == "condominio-lsc" else 100),
            "arqueos": [],
        },
    )
    op = OperacionCaja.model_validate(
        request(
            "aporte",
            idSocio=3,
            cajaContraparte="condominio-lsc",
            motivoRelacionGiamigli="Aporte documentado",
        )
    )
    assert service.previsualizar(op)["advertencias"] == []
