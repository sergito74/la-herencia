import io

from fastapi.testclient import TestClient

from src.features.tesoreria import confirmacion_carga, excel_import, repository
from src.main import app

client = TestClient(app)

_ARCHIVO = ("resumen.xls", io.BytesIO(b"contenido"), "application/vnd.ms-excel")


def test_confirmar_excel_inserta_y_devuelve_conteos(monkeypatch):
    monkeypatch.setattr(
        excel_import,
        "validar_y_previsualizar",
        lambda *a, **k: {"medioDetectado": "bna", "valido": True, "errores": [], "movimientosPrevisualizados": []},
    )
    monkeypatch.setattr(
        confirmacion_carga,
        "confirmar_carga",
        lambda banco, filename, contenido: {
            "valido": True,
            "banco": "bna",
            "idCarga": 1,
            "insertados": 5,
            "omitidosDuplicado": 2,
            "omitidosIncompletos": 0,
            "total": 7,
        },
    )
    r = client.post("/api/tesoreria/excel/confirmar", files={"archivo": _ARCHIVO})
    assert r.status_code == 200
    body = r.json()
    assert (body["insertados"], body["omitidosDuplicado"], body["total"]) == (5, 2, 7)


def test_confirmar_excel_archivo_invalido_devuelve_422_sin_escribir(monkeypatch):
    monkeypatch.setattr(
        excel_import,
        "validar_y_previsualizar",
        lambda *a, **k: {"medioDetectado": None, "valido": False, "errores": ["Formato no reconocido"], "movimientosPrevisualizados": []},
    )

    def _no_deberia_llamarse(*a, **k):
        raise AssertionError("confirmar_carga no debe llamarse con un archivo inválido")

    monkeypatch.setattr(confirmacion_carga, "confirmar_carga", _no_deberia_llamarse)
    r = client.post("/api/tesoreria/excel/confirmar", files={"archivo": _ARCHIVO})
    assert r.status_code == 422


def test_confirmar_la_segunda_vez_no_inserta_nada(monkeypatch):
    monkeypatch.setattr(
        excel_import,
        "validar_y_previsualizar",
        lambda *a, **k: {"medioDetectado": "bna", "valido": True, "errores": [], "movimientosPrevisualizados": []},
    )
    llamadas = {"n": 0}

    def fake_confirmar(banco, filename, contenido):
        llamadas["n"] += 1
        insertados = 0 if llamadas["n"] > 1 else 5
        return {
            "valido": True, "banco": "bna", "idCarga": llamadas["n"],
            "insertados": insertados, "omitidosDuplicado": 7 - insertados,
            "omitidosIncompletos": 0, "total": 7,
        }

    monkeypatch.setattr(confirmacion_carga, "confirmar_carga", fake_confirmar)
    primera = client.post("/api/tesoreria/excel/confirmar", files={"archivo": _ARCHIVO}).json()
    segunda = client.post("/api/tesoreria/excel/confirmar", files={"archivo": _ARCHIVO}).json()
    assert primera["insertados"] == 5
    assert segunda["insertados"] == 0


def test_previsualizar_confirmacion_no_escribe(monkeypatch):
    monkeypatch.setattr(
        excel_import,
        "validar_y_previsualizar",
        lambda *a, **k: {"medioDetectado": "bna", "valido": True, "errores": [], "movimientosPrevisualizados": []},
    )

    def _no_deberia_escribir(*a, **k):
        raise AssertionError("previsualizar no debe insertar nada")

    from src.db import connection

    monkeypatch.setattr(connection, "execute_write_transaction", _no_deberia_escribir)
    monkeypatch.setattr(
        confirmacion_carga,
        "previsualizar_confirmacion",
        lambda banco, filename, contenido: {
            "medioDetectado": "bna", "valido": True, "errores": [],
            "movimientosPrevisualizados": [],
            "resumen": {"nuevos": 3, "omitidosDuplicado": 1, "omitidosIncompletos": 0, "total": 4},
        },
    )
    r = client.post("/api/tesoreria/excel/previsualizar-confirmacion", files={"archivo": _ARCHIVO})
    assert r.status_code == 200
    assert r.json()["resumen"] == {"nuevos": 3, "omitidosDuplicado": 1, "omitidosIncompletos": 0, "total": 4}


def test_previsualizar_y_confirmar_coinciden_en_el_conteo(monkeypatch):
    """El conteo de la previsualización (US3) debe coincidir con el resultado real de confirmar (US1/US2)."""
    monkeypatch.setattr(
        excel_import,
        "validar_y_previsualizar",
        lambda *a, **k: {"medioDetectado": "bna", "valido": True, "errores": [], "movimientosPrevisualizados": []},
    )
    resumen = {"nuevos": 5, "omitidosDuplicado": 2, "omitidosIncompletos": 0, "total": 7}
    monkeypatch.setattr(
        confirmacion_carga,
        "previsualizar_confirmacion",
        lambda banco, filename, contenido: {
            "medioDetectado": "bna", "valido": True, "errores": [], "movimientosPrevisualizados": [], "resumen": resumen,
        },
    )
    monkeypatch.setattr(
        confirmacion_carga,
        "confirmar_carga",
        lambda banco, filename, contenido: {
            "valido": True, "banco": "bna", "idCarga": 9,
            "insertados": resumen["nuevos"], "omitidosDuplicado": resumen["omitidosDuplicado"],
            "omitidosIncompletos": resumen["omitidosIncompletos"], "total": resumen["total"],
        },
    )
    preview = client.post("/api/tesoreria/excel/previsualizar-confirmacion", files={"archivo": _ARCHIVO}).json()
    confirmado = client.post("/api/tesoreria/excel/confirmar", files={"archivo": _ARCHIVO}).json()
    assert preview["resumen"]["nuevos"] == confirmado["insertados"]
    assert preview["resumen"]["omitidosDuplicado"] == confirmado["omitidosDuplicado"]


def test_listar_cargas_devuelve_lo_que_expone_el_repositorio(monkeypatch):
    monkeypatch.setattr(
        repository,
        "listar_cargas",
        lambda banco: [
            {
                "idCarga": 1, "nombreArchivo": "BNA_agosto.xls", "fechaHoraCarga": "2026-09-22T14:03:00",
                "insertados": 37, "omitidosDuplicado": 3, "omitidosIncompletos": 0,
            }
        ],
    )
    r = client.get("/api/tesoreria/bna/cargas")
    assert r.status_code == 200
    assert r.json()["items"][0]["idCarga"] == 1


def test_listar_cargas_medio_sin_historial_da_404():
    r = client.get("/api/tesoreria/efectivo/cargas")
    assert r.status_code == 404


def test_movimiento_con_y_sin_carga_expone_idcarga(monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_movimientos",
        lambda *a, **k: (
            [
                {"idMovimientoBNA": 1, "fechaHora": None, "concepto": "x", "importe": 1.0, "idContacto": None, "contacto": None, "idCarga": 9},
                {"idMovimientoBNA": 2, "fechaHora": None, "concepto": "y", "importe": 2.0, "idContacto": None, "contacto": None, "idCarga": None},
            ],
            2,
        ),
    )
    r = client.get("/api/tesoreria/bna/movimientos")
    items = r.json()["items"]
    assert items[0]["idCarga"] == 9
    assert items[1]["idCarga"] is None
