import pytest
from fastapi.testclient import TestClient

from src.auth.tokens import crear_token

from src.features.remitos import repository, stock_repo
from src.features.remitos.repository import RequiereConfirmacion
from src.main import app

client = TestClient(app)
client.cookies.set(
    "la_herencia_session",
    crear_token(id_usuario=0, rol="Administrador"),
)  # 016-autenticacion: la API ahora exige sesión; estos tests preexistentes
# simulan un Administrador para no cambiar su comportamiento (SC-003).


def test_estado_de_renglon_por_cantidad_vinculada():
    e = repository._estado_renglon
    assert e(100, 0) == "SinVincular"
    assert e(100, 60) == "Parcial"
    assert e(100, 100) == "Completo"
    assert e(100, 100.004) == "Completo"
    assert e(100, 120) == "ConDiferencia"


def test_estado_del_remito_toma_el_peor_caso():
    e = repository._estado_remito
    assert e([], False) == "SinVincular"
    assert e(["Completo", "Completo"], True) == "Completo"
    assert e(["Completo", "SinVincular"], True) == "Parcial"
    assert e(["SinVincular", "SinVincular"], False) == "SinVincular"
    assert e(["Completo", "Parcial"], True) == "Parcial"
    assert e(["Completo", "ConDiferencia"], True) == "ConDiferencia"


@pytest.mark.parametrize(
    "numero,valido",
    [("0043-00070561", True), ("00043-00070561", True), ("SIN REMITO", True), ("sin remito", True), ("43-70561", False), ("PRUEBA-1", False)],
)
def test_formato_de_numero_de_remito(numero, valido, monkeypatch):
    monkeypatch.setattr(repository, "fetch_all", lambda *a, **k: [])
    assert repository.advertencias(1, numero)["formato"] is valido


def test_sin_remito_nunca_es_duplicado(monkeypatch):
    llamado = []
    monkeypatch.setattr(repository, "fetch_all", lambda *a, **k: llamado.append(1) or [{"idRemito": 9, "fecha": None}])
    assert repository.advertencias(1, "SIN REMITO")["duplicados"] == []
    assert not llamado  # ni siquiera consulta la base


def test_duplicado_real_se_informa(monkeypatch):
    monkeypatch.setattr(repository, "fetch_all", lambda *a, **k: [{"idRemito": 9, "fecha": None}])
    adv = repository.advertencias(1, "0043-00070561")
    assert adv["formato"] and [d["idRemito"] for d in adv["duplicados"]] == [9]
    assert "Ya existe" in repository._mensajes_advertencia(adv)[0]


def test_rutas_estaticas_no_se_confunden_con_un_id(monkeypatch):
    monkeypatch.setattr(repository, "listar_remitos", lambda *a, **k: {"items": [], "total": 0, "page": 1, "pageSize": 25})
    monkeypatch.setattr(repository, "facturas_sin_remito", lambda *a, **k: {"items": [], "total": 0, "page": 1, "pageSize": 25})
    assert client.get("/api/remitos").status_code == 200
    assert client.get("/api/remitos/facturas-sin-remito").status_code == 200
    assert client.get("/api/remitos/catalogos").status_code in (200, 500)  # consulta directa a la base


def test_confirmacion_pendiente_es_409_y_error_de_negocio_400(monkeypatch):
    def pide(*a, **k):
        raise RequiereConfirmacion(["El stock quedaría negativo."])

    def falla(*a, **k):
        raise ValueError(["Motivo inválido"])

    body = {"fecha": "2026-09-23", "motivo": "Deterioro", "idRubro": 1, "idCentro": 1, "renglones": [{"idProducto": 1, "cantidad": 2}]}
    monkeypatch.setattr(stock_repo, "crear_baja", pide)
    r = client.post("/api/stock/bajas", json=body)
    assert r.status_code == 409 and r.json()["detail"] == ["El stock quedaría negativo."]
    monkeypatch.setattr(stock_repo, "crear_baja", falla)
    assert client.post("/api/stock/bajas", json=body).status_code == 400


def test_alta_pasa_la_confirmacion_al_repositorio(monkeypatch):
    visto = {}

    def crear(datos, confirmar):
        visto.update(datos=datos, confirmar=confirmar)
        return 77

    monkeypatch.setattr(repository, "crear_remito", crear)
    body = {"fecha": "2026-09-23", "idProveedor": 5, "nroRemito": "SIN REMITO", "confirmar": True,
            "renglones": [{"idProducto": 10, "cantidad": 3, "unidad": "LTS"}]}
    r = client.post("/api/remitos", json=body)
    assert r.status_code == 201 and r.json() == {"idRemito": 77}
    assert visto["confirmar"] is True and visto["datos"]["renglones"][0]["unidad"] == "LTS"


def test_alta_sin_renglones_se_rechaza():
    r = client.post("/api/remitos", json={"fecha": "2026-09-23", "idProveedor": 5, "nroRemito": "X", "renglones": []})
    assert r.status_code == 422


def test_motivo_de_baja_invalido_o_otro_sin_detalle():
    datos = {"fecha": "2026-09-23", "motivo": "Cualquiera", "idRubro": 1, "idCentro": 1, "renglones": [{"idProducto": 1, "cantidad": 1}]}
    with pytest.raises(ValueError):
        stock_repo.crear_baja(datos)
    with pytest.raises(ValueError):
        stock_repo.crear_baja({**datos, "motivo": "Otro"})
