"""Contract tests for POST/PUT /api/compras y sus endpoints de bloqueo (006-carga-compras).

Fixtures only, no real DB access — mismo patrón que los demás
test_compras_*.py. `repository.create_compra`/`update_compra` se
mockean directamente porque su lógica interna (transacción,
validación) ya tiene cobertura propia en `test_db_connection.py` y en
las pruebas de humo manuales contra `WC` hechas durante la
implementación.
"""

from __future__ import annotations

import httpx
import pytest

from src.features.compras import repository, repository_locks
from src.main import app

VALID_BODY = {
    "idContacto": 1,
    "fecha": "2026-09-17",
    "tipo": "A",
    "tipoDocumento": "Factura",
    "numeroDocumento": "0001-00099999",
    "moneda": "Pesos",
    "lineas": [
        {
            "productoServicio": "Fertilizante Urea",
            "cantidad": 10,
            "precioUnitario": 55000,
            "iva": 21,
        }
    ],
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _fake_totales(lineas, cabecera):
    subtotal = sum(l["cantidad"] * l["precioUnitario"] for l in lineas)
    iva_lineas = sum(l["cantidad"] * l["precioUnitario"] * l["iva"] / 100 for l in lineas)
    importe_total = subtotal + iva_lineas
    pesificado = None
    if cabecera.get("moneda") == "Dolares" and cabecera.get("tipoDeCambio"):
        tc = cabecera["tipoDeCambio"]
        pesificado = {
            "subtotalNeto": subtotal * tc,
            "ivaCabecera": iva_lineas * tc,
            "importeTotal": importe_total * tc,
        }
    lineas_calc = [
        {**l, "subtotal": l["cantidad"] * l["precioUnitario"], "importeIva": l["cantidad"] * l["precioUnitario"] * l["iva"] / 100}
        for l in lineas
    ]
    return {
        "lineas": lineas_calc,
        "subtotalNeto": subtotal,
        "ivaCabecera": iva_lineas,
        "importeTotal": importe_total,
        "pesificado": pesificado,
    }


@pytest.mark.anyio
async def test_post_compra_alta_exitosa_calcula_totales(client, monkeypatch):
    monkeypatch.setattr(repository, "create_compra", lambda cabecera, lineas, vencimientos: 555)
    monkeypatch.setattr(repository, "calcular_totales", _fake_totales)
    monkeypatch.setattr(repository, "get_vencimientos_compra", lambda id_compra: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras", json=VALID_BODY)

    assert response.status_code == 201
    body = response.json()
    assert body["idCompra"] == 555
    assert body["subtotalNeto"] == 550000
    assert body["ivaCabecera"] == 115500
    assert body["importeTotal"] == 665500
    assert body["pesificado"] is None
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_post_compra_dolares_calcula_bloque_pesificado(client, monkeypatch):
    monkeypatch.setattr(repository, "create_compra", lambda cabecera, lineas, vencimientos: 556)
    monkeypatch.setattr(repository, "calcular_totales", _fake_totales)
    monkeypatch.setattr(repository, "get_vencimientos_compra", lambda id_compra: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: False)

    body = {**VALID_BODY, "moneda": "Dolares", "tipoDeCambio": 350}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras", json=body)

    assert response.status_code == 201
    data = response.json()
    assert data["pesificado"]["importeTotal"] == data["importeTotal"] * 350


@pytest.mark.anyio
async def test_post_compra_dolares_sin_tipo_de_cambio_es_400(client, monkeypatch):
    def fake_create(cabecera, lineas, vencimientos):
        raise ValueError(["El tipo de cambio es obligatorio para compras en Dólares."])

    monkeypatch.setattr(repository, "create_compra", fake_create)

    body = {**VALID_BODY, "moneda": "Dolares"}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras", json=body)

    assert response.status_code == 400
    assert "tipo de cambio" in response.json()["detail"][0].lower()


@pytest.mark.anyio
async def test_post_compra_sin_lineas_es_422(client):
    body = {**VALID_BODY, "lineas": []}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras", json=body)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_compra_referencia_invalida_es_400(client, monkeypatch):
    def fake_create(cabecera, lineas, vencimientos):
        raise ValueError(["El rubro 999999 no existe."])

    monkeypatch.setattr(repository, "create_compra", fake_create)

    body = {**VALID_BODY, "lineas": [{**VALID_BODY["lineas"][0], "idRubro": 999999}]}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras", json=body)

    assert response.status_code == 400


@pytest.mark.anyio
async def test_lock_primer_token_adquiere_segundo_es_409(client, monkeypatch):
    calls = {}

    def fake_adquirir(id_compra, lock_token):
        calls.setdefault("tokens", []).append(lock_token)
        if len(calls["tokens"]) == 1:
            from datetime import datetime

            return repository_locks.LockInfo(id_compra, lock_token, datetime(2026, 9, 17, 12, 0))
        return None

    monkeypatch.setattr(repository_locks, "adquirir_lock", fake_adquirir)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        r1 = await ac.post("/api/compras/1/lock", json={"lockToken": "A"})
        r2 = await ac.post("/api/compras/1/lock", json={"lockToken": "B"})

    assert r1.status_code == 200
    assert r2.status_code == 409


@pytest.mark.anyio
async def test_lock_token_con_formato_invalido_es_400(client, monkeypatch):
    """`LockToken` es `uniqueidentifier` en SQL Server — un valor no-GUID debe dar 400, no 500."""

    def fake_adquirir(id_compra, lock_token):
        raise ValueError(f"lockToken inválido: debe ser un UUID, se recibió {lock_token!r}")

    monkeypatch.setattr(repository_locks, "adquirir_lock", fake_adquirir)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras/1/lock", json={"lockToken": "no-es-un-uuid"})

    assert response.status_code == 400


@pytest.mark.anyio
async def test_lock_mismo_token_renueva_sin_conflicto(client, monkeypatch):
    from datetime import datetime

    monkeypatch.setattr(
        repository_locks,
        "adquirir_lock",
        lambda id_compra, lock_token: repository_locks.LockInfo(
            id_compra, lock_token, datetime(2026, 9, 17, 12, 15)
        ),
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        r1 = await ac.post("/api/compras/1/lock", json={"lockToken": "A"})
        r2 = await ac.post("/api/compras/1/lock", json={"lockToken": "A"})

    assert r1.status_code == 200
    assert r2.status_code == 200


@pytest.mark.anyio
async def test_lock_release_wrong_token_es_409(client, monkeypatch):
    monkeypatch.setattr(repository_locks, "liberar_lock", lambda id_compra, token: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.request(
            "DELETE", "/api/compras/1/lock", headers={"X-Lock-Token": "B"}
        )

    assert response.status_code == 409


@pytest.mark.anyio
async def test_lock_release_correct_token_es_204(client, monkeypatch):
    monkeypatch.setattr(repository_locks, "liberar_lock", lambda id_compra, token: True)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.request(
            "DELETE", "/api/compras/1/lock", headers={"X-Lock-Token": "A"}
        )

    assert response.status_code == 204


@pytest.mark.anyio
async def test_put_compra_sin_lock_vigente_es_409(client, monkeypatch):
    monkeypatch.setattr(repository, "get_compra_cabecera", lambda id_compra: {"idCompra": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_compra, token: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put(
            "/api/compras/1", json=VALID_BODY, headers={"X-Lock-Token": "B"}
        )

    assert response.status_code == 409


@pytest.mark.anyio
async def test_put_compra_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_compra_cabecera", lambda id_compra: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put(
            "/api/compras/999999", json=VALID_BODY, headers={"X-Lock-Token": "A"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_put_compra_con_lock_valido_recalcula_totales(client, monkeypatch):
    monkeypatch.setattr(repository, "get_compra_cabecera", lambda id_compra: {"idCompra": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_compra, token: True)
    monkeypatch.setattr(repository, "update_compra", lambda *a, **kw: None)
    monkeypatch.setattr(repository, "calcular_totales", _fake_totales)
    monkeypatch.setattr(repository, "get_vencimientos_compra", lambda id_compra: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: False)

    body = {**VALID_BODY, "lineas": [{**VALID_BODY["lineas"][0], "precioUnitario": 60000}]}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/compras/1", json=body, headers={"X-Lock-Token": "A"})

    assert response.status_code == 200
    assert response.json()["subtotalNeto"] == 600000


@pytest.mark.anyio
async def test_documento_duplicado_agrega_warning_sin_bloquear(client, monkeypatch):
    monkeypatch.setattr(repository, "create_compra", lambda cabecera, lineas, vencimientos: 557)
    monkeypatch.setattr(repository, "calcular_totales", _fake_totales)
    monkeypatch.setattr(repository, "get_vencimientos_compra", lambda id_compra: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: True)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras", json=VALID_BODY)

    assert response.status_code == 201
    assert len(response.json()["warnings"]) == 1


@pytest.mark.anyio
async def test_rubro_sugerido_con_coincidencia(client, monkeypatch):
    monkeypatch.setattr(
        repository, "get_rubro_sugerido", lambda texto: {"idRubro": 12, "rubro": "Fertilizantes", "frecuencia": 7}
    )
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/compras/rubro-sugerido?productoServicio=Urea")

    assert response.status_code == 200
    assert response.json() == {"idRubro": 12, "rubro": "Fertilizantes", "frecuencia": 7}


@pytest.mark.anyio
async def test_rubro_sugerido_sin_coincidencia(client, monkeypatch):
    monkeypatch.setattr(repository, "get_rubro_sugerido", lambda texto: None)
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/compras/rubro-sugerido?productoServicio=NuncaUsado")

    assert response.status_code == 200
    assert response.json() == {"idRubro": None, "rubro": None, "frecuencia": 0}


# --- Alta controlada de catálogos (Rubro/Centro de Costos/Destino/Campaña) ---


@pytest.mark.anyio
async def test_crear_rubro(client, monkeypatch):
    monkeypatch.setattr(repository, "create_rubro", lambda nombre: {"idRubro": 99, "rubro": nombre})
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras/rubros", json={"nombre": "Nuevo Rubro"})

    assert response.status_code == 201
    assert response.json() == {"idRubro": 99, "rubro": "Nuevo Rubro"}


@pytest.mark.anyio
async def test_crear_centro_costo(client, monkeypatch):
    monkeypatch.setattr(
        repository, "create_centro_costo", lambda nombre: {"idCentroCosto": 8, "centroCosto": nombre}
    )
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras/centros-costo", json={"nombre": "Nuevo Centro"})

    assert response.status_code == 201
    assert response.json() == {"idCentroCosto": 8, "centroCosto": "Nuevo Centro"}


@pytest.mark.anyio
async def test_crear_destino(client, monkeypatch):
    monkeypatch.setattr(repository, "create_destino", lambda nombre: {"idDestino": 4, "destino": nombre})
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras/destinos", json={"nombre": "Nuevo Destino"})

    assert response.status_code == 201
    assert response.json() == {"idDestino": 4, "destino": "Nuevo Destino"}


@pytest.mark.anyio
async def test_crear_campania(client, monkeypatch):
    monkeypatch.setattr(
        repository, "create_campania", lambda nombre: {"idCampania": 2, "campania": nombre}
    )
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras/campanias", json={"nombre": "2027/28"})

    assert response.status_code == 201
    assert response.json() == {"idCampania": 2, "campania": "2027/28"}


@pytest.mark.anyio
async def test_crear_campania_rechaza_texto_muy_largo(client):
    """Campañas.Campaña es nvarchar(9) en el esquema real — más de 9 caracteres debe ser 422."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras/campanias", json={"nombre": "2027/2028/2029"})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_compras_filtra_por_id_contacto(client, monkeypatch):
    captured = {}

    def fake_search(*args):
        captured["id_contacto"] = args[-1]
        return [], 0

    monkeypatch.setattr(repository, "search_compras", fake_search)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/compras?idContacto=158")

    assert response.status_code == 200
    assert captured["id_contacto"] == 158


# --- Documentos relacionados (Nota de Crédito/Débito vinculada a una Factura) ---


@pytest.mark.anyio
async def test_get_documentos_relacionados(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_documentos_relacionados",
        lambda id_compra: [
            {"idCompra": 999, "fecha": "2026-09-01", "tipoDocumento": "Nota de Crédito", "numeroDocumento": "NC-1"}
        ],
    )
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/compras/1/relacionados")

    assert response.status_code == 200
    assert response.json()[0]["numeroDocumento"] == "NC-1"


@pytest.mark.anyio
async def test_agregar_documento_relacionado(client, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        repository,
        "agregar_documento_relacionado",
        lambda id_compra, id_relacionada: captured.update(id_compra=id_compra, id_relacionada=id_relacionada),
    )
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras/1/relacionados", json={"idCompraRelacionada": 2})

    assert response.status_code == 204
    assert captured == {"id_compra": 1, "id_relacionada": 2}


@pytest.mark.anyio
async def test_agregar_documento_relacionado_inexistente_es_400(client, monkeypatch):
    def fake_agregar(id_compra, id_relacionada):
        raise ValueError(f"La compra {id_relacionada} no existe.")

    monkeypatch.setattr(repository, "agregar_documento_relacionado", fake_agregar)
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/compras/1/relacionados", json={"idCompraRelacionada": 999999})

    assert response.status_code == 400


@pytest.mark.anyio
async def test_quitar_documento_relacionado(client, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        repository,
        "quitar_documento_relacionado",
        lambda id_compra, id_relacionada: captured.update(id_compra=id_compra, id_relacionada=id_relacionada),
    )
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/compras/1/relacionados/2")

    assert response.status_code == 204
    assert captured == {"id_compra": 1, "id_relacionada": 2}
