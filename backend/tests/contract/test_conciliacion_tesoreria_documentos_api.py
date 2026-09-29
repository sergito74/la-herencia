"""026: contrato con repositorio simulado, incluida autenticación."""

import pytest
from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.conciliacion_tesoreria import repository, router
from src.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(router, "_usuario_actual", lambda request: "fixture")
    with TestClient(app) as c:
        c.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))
        yield c


@pytest.fixture(autouse=True)
def no_db(monkeypatch):
    from src.db import connection

    def fail(*args, **kwargs):
        raise AssertionError("Este test de contrato no debe acceder a WC")

    monkeypatch.setattr(connection.pyodbc, "connect", fail)


def calculo():
    return dict(
        estado="exacta",
        diferencia=0,
        pagoParcial=False,
        permiteParcial=False,
        imputados=[dict(origen="Compras", idOrigen=1, importeImputado=100)],
    )


@pytest.mark.parametrize("medio", repository.MEDIOS_SOPORTADOS)
def test_candidatos_preview_lote_en_seis_medios(client, monkeypatch, medio):
    prefix = f"/api/tesoreria/{medio}/movimientos/1"
    monkeypatch.setattr(repository, "candidatos", lambda *a: dict(documentos=[], sugerencias=[]))
    assert client.get(prefix + "/candidatos").json() == dict(documentos=[], sugerencias=[])
    visto = []

    def preview(*args):
        visto.extend(args[2])
        return calculo()

    monkeypatch.setattr(repository, "calcular_conciliacion", preview)
    r = client.get(
        prefix + "/conciliacion-preview",
        params=[("documentos", "Compras:1"), ("documentos", "Impuestos:1")],
    )
    assert r.status_code == 200
    assert [d["origen"] for d in visto] == ["Compras", "Impuestos"]

    def lote(m, id, docs, dif, usuario):
        assert usuario == "fixture"
        assert len(docs) == 2
        return [
            dict(
                idConciliacion=1,
                idContacto=2,
                importe=100,
                usuario=usuario,
                fecha="2026-09-29T12:00:00",
                tipoOrigenDocumento="Compras",
                idOrigenDocumento=1,
            )
        ]

    monkeypatch.setattr(repository, "vincular_lote", lote)
    r = client.post(prefix + "/conciliacion-lote", json={"documentos": visto})
    assert r.status_code == 201 and r.json()[0]["idOrigenDocumento"] == 1


@pytest.mark.parametrize(
    "body",
    [
        {"documentos": []},
        {"documentos": [{"origen": "Compras", "idOrigen": 1}] * 2},
        {"documentos": [{"origen": "Inventado", "idOrigen": 1}]},
        {"documentos": [{"origen": "Compras", "idOrigen": 2**63}]},
        {"documentos": [{"origen": "Compras", "idOrigen": i + 1} for i in range(21)]},
        {"documentos": [{"origen": "Compras", "idOrigen": 1}], "usuario": "intruso"},
        {
            "documentos": [{"origen": "Compras", "idOrigen": 1}],
            "aceptarDiferencia": {"motivo": "Otro", "detalle": " "},
        },
    ],
)
def test_request_invalido_422(client, body):
    assert (
        client.post("/api/tesoreria/bna/movimientos/1/conciliacion-lote", json=body).status_code
        == 422
    )


@pytest.mark.parametrize("ref", ["1", "Compras:9223372036854775808", "Compras:no", "Otra:1", "Compras:1:2"])
def test_preview_referencia_invalida(client, ref):
    assert (
        client.get(
            "/api/tesoreria/bna/movimientos/1/conciliacion-preview", params={"documentos": ref}
        ).status_code
        == 422
    )


def test_busqueda_vacia_y_limites(client, monkeypatch):
    monkeypatch.setattr(repository, "buscar_documentos", lambda q: [])
    assert client.get("/api/tesoreria/documentos-buscar?q=nada").json() == []
    for q in ("a", "x" * 101):
        assert client.get("/api/tesoreria/documentos-buscar", params={"q": q}).status_code == 422


@pytest.mark.parametrize(
    "exc,status",
    [
        (LookupError("No existe documento"), 404),
        (ValueError("El movimiento ya está resuelto"), 409),
        (ValueError("Motivo inválido"), 400),
        (ValueError("El medio no se concilia desde este módulo"), 400),
    ],
)
def test_errores_de_negocio(client, monkeypatch, exc, status):
    def fail(*args):
        raise exc

    monkeypatch.setattr(repository, "vincular_lote", fail)
    r = client.post(
        "/api/tesoreria/bna/movimientos/1/conciliacion-lote",
        json={"documentos": [dict(origen="Compras", idOrigen=1)]},
    )
    assert r.status_code == status


def test_estados_y_detalle(client, monkeypatch):
    llamadas = []
    monkeypatch.setattr(repository, "marcar_sin_documento", lambda *a: llamadas.append(a))
    monkeypatch.setattr(repository, "quitar_estado", lambda *a: llamadas.append(a))
    prefix = "/api/tesoreria/bna/movimientos/1"
    assert (
        client.post(
            prefix + "/sin-documento", json={"motivo": "Impuesto", "detalle": None}
        ).status_code
        == 204
    )
    assert llamadas[0][-1] == "fixture"
    assert client.delete(prefix + "/estado").status_code == 204
    for detalle in ("", "x" * 256):
        assert (
            client.post(
                prefix + "/sin-documento", json={"motivo": "Otro", "detalle": detalle}
            ).status_code
            == 422
        )


def test_quitar_vinculo(client, monkeypatch):
    llamadas = []
    monkeypatch.setattr(repository, "quitar_vinculo", lambda *a: llamadas.append(a))
    r = client.delete("/api/tesoreria/mercado-libre/movimientos/25/conciliacion/88")
    assert r.status_code == 204
    assert llamadas[0] == ("mercado-libre", 25, 88)


def test_quitar_vinculo_inexistente_responde_404(client, monkeypatch):
    def fail(*a):
        raise ValueError("No existe la conciliación 999 para este movimiento.")

    monkeypatch.setattr(repository, "quitar_vinculo", fail)
    r = client.delete("/api/tesoreria/mercado-libre/movimientos/25/conciliacion/999")
    assert r.status_code == 404


def test_permisos_no_llegan_al_repository():
    with TestClient(app) as c:
        assert c.get("/api/tesoreria/documentos-buscar?q=abc").status_code == 401
        c.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Lectura"))
        assert (
            c.post(
                "/api/tesoreria/bna/movimientos/1/sin-documento", json={"motivo": "Impuesto"}
            ).status_code
            == 403
        )


def test_get_auditoria_y_metadata(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "calcular_estado",
        lambda *a: dict(
            estado="sin_documento",
            importeTotal=100,
            saldoPendiente=0,
            conciliaciones=[],
            auditoria=dict(
                idEstado=1,
                estado="SinDocumento",
                motivo="Impuesto",
                detalle=None,
                importeDiferencia=None,
                usuario="fixture",
                fecha="2026-09-29T12:00:00",
            ),
        ),
    )
    r = client.get("/api/tesoreria/bna/movimientos/1/conciliacion")
    assert r.status_code == 200 and r.json()["auditoria"]["motivo"] == "Impuesto"


def test_id_heredado_negativo_se_conserva(client, monkeypatch):
    visto = []

    def preview(medio, id_movimiento, refs):
        visto.extend(refs)
        return calculo()

    monkeypatch.setattr(repository, "calcular_conciliacion", preview)
    response = client.get(
        "/api/tesoreria/bna/movimientos/-7/conciliacion-preview",
        params={"documentos": "Compras:-2116671242"},
    )
    assert response.status_code == 200
    assert visto == [{"origen": "Compras", "idOrigen": -2116671242}]
