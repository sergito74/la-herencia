"""Contract tests for /api/tarjetas-resumenes (008-tarjetas, Historia 1).

`repository.*` se mockea directamente — mismo patrón que
`test_ventas_hacienda_alta_api.py` (007).
"""

from __future__ import annotations

from datetime import datetime

import httpx
import pytest

from src.features.tarjetas import repository as tarjetas_repository
from src.features.tarjetas_resumenes import repository, repository_locks
from src.main import app

# Referencias a las funciones reales, tomadas antes de que el fixture
# `sin_auto_vinculo_real` (autouse) las reemplace por no-ops — los tests
# que prueban su lógica real las llaman directo, sin pasar por el router.
_auto_vincular_compras_real = repository.auto_vincular_compras
_auto_vincular_pago_real = tarjetas_repository.auto_vincular_pago

VALID_BODY = {
    "idTarjeta": 3,
    "codigo": "0532-000123457",
    "fechaCierre": "2026-07-10",
    "fechaVencimiento": "2026-07-20",
    "impuestoSellos": 120.50,
    "iva21": 350.20,
    "lineas": [
        {"fechaCompra": "2026-06-15", "detalle": "SUPERMERCADO XYZ", "importe": 15230.00},
    ],
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def sin_auto_vinculo_real(monkeypatch):
    """El router llama a `auto_vincular_compras`/`auto_vincular_pago` en
    cada GET/POST/PUT (punto 4/6 del feedback 2026-09-19) — sin este
    mock, tocarían la `WC` real en cada test. Los tests que quieren
    probar el comportamiento real de estas funciones las mockean de
    nuevo con su propio valor dentro del test."""
    monkeypatch.setattr(repository, "auto_vincular_compras", lambda id_resumen: 0)
    monkeypatch.setattr(tarjetas_repository, "auto_vincular_pago", lambda id_resumen: False)


# --- FR-010: listado vacío por defecto ---


@pytest.mark.anyio
async def test_list_resumenes_sin_filtro_vacio(client, monkeypatch):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-resumenes")

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "pageSize": 50, "total": 0}


@pytest.mark.anyio
async def test_list_resumenes_con_filtro_devuelve_resultados(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "search_resumenes",
        lambda *a, **kw: (
            [
                {
                    "idResumen": 187,
                    "idTarjeta": 3,
                    "tarjeta": "Visa Galicia",
                    "codigo": "0532-000123456",
                    "fechaCierre": "2026-06-10",
                    "fechaVencimiento": "2026-06-20",
                    "totalCalculado": 45230.50,
                    "soloCabecera": False,
                    "pagoConciliado": True,
                    "lineasTotal": 3,
                    "lineasVinculadas": 3,
                }
            ],
            1,
        ),
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-resumenes?idTarjeta=3&fechaCierreDesde=2020-01-01&fechaCierreHasta=2026-12-31")

    assert response.status_code == 200
    assert response.json()["total"] == 1


# --- US1: detalle con y sin líneas ---


@pytest.mark.anyio
async def test_get_resumen_detalle_con_lineas_totalcalculado_signo(client, monkeypatch):
    cabecera = {
        "idResumen": 1,
        "idTarjeta": 3,
        "tarjeta": "Visa Galicia",
        "codigo": "X",
        "fechaCierre": "2026-06-10",
        "fechaVencimiento": "2026-06-20",
        "impuestoSellos": 100.0,
        "gastosAdmin": 0,
        "mantCuenta": 0,
        "renovAnual": 0,
        "promocionBNA": 0,
        "creditoContingente": 0,
        "intFinanc": 0,
        "intCompens": 0,
        "iva105": 0,
        "percepIVA105": 0,
        "iva21": 0,
        "percepIVA21": 0,
        "percepIIBB": 0,
        "ajusteResAnterior": -50.0,
    }
    lineas = [
        {"idLineaConsumo": 1, "fechaCompra": "2026-06-01", "detalle": "A", "importe": 1000.0},
        {"idLineaConsumo": 2, "fechaCompra": "2026-06-02", "detalle": "B (devolución)", "importe": -200.0},
    ]
    monkeypatch.setattr(repository, "get_resumen_detalle", lambda id_resumen: cabecera)
    monkeypatch.setattr(repository, "get_lineas", lambda id_resumen: lineas)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-resumenes/1")

    assert response.status_code == 200
    # 1000 - 200 + 100 (ImpuestoSellos) - 50 (AjusteResAnterior negativo, resta) = 850
    assert response.json()["totalCalculado"] == 850.0


@pytest.mark.anyio
async def test_get_resumen_detalle_sin_lineas_no_es_error(client, monkeypatch):
    cabecera = {
        "idResumen": 2,
        "idTarjeta": 3,
        "tarjeta": "Visa Galicia",
        "codigo": "Y",
        "fechaCierre": "2026-06-10",
        "fechaVencimiento": "2026-06-20",
        "impuestoSellos": 0,
        "gastosAdmin": 0,
        "mantCuenta": 0,
        "renovAnual": 0,
        "promocionBNA": 0,
        "creditoContingente": 0,
        "intFinanc": 0,
        "intCompens": 0,
        "iva105": 0,
        "percepIVA105": 0,
        "iva21": 0,
        "percepIVA21": 0,
        "percepIIBB": 0,
        "ajusteResAnterior": 0,
    }
    monkeypatch.setattr(repository, "get_resumen_detalle", lambda id_resumen: cabecera)
    monkeypatch.setattr(repository, "get_lineas", lambda id_resumen: [])

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-resumenes/2")

    assert response.status_code == 200
    assert response.json()["lineas"] == []


# --- US1: alta ---


@pytest.mark.anyio
async def test_post_resumen_con_lineas_totalcalculado(client, monkeypatch):
    monkeypatch.setattr(repository, "create_resumen", lambda cabecera, lineas: 500)
    monkeypatch.setattr(repository, "get_lineas", lambda id_resumen: VALID_BODY["lineas"])
    monkeypatch.setattr(repository, "hay_resumen_duplicado", lambda *a, **kw: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/tarjetas-resumenes", json=VALID_BODY)

    assert response.status_code == 201
    body = response.json()
    assert body["idResumen"] == 500
    assert body["totalCalculado"] == 15230.00 + 120.50 + 350.20
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_post_resumen_solo_cabecera(client, monkeypatch):
    body = {**VALID_BODY, "lineas": []}
    monkeypatch.setattr(repository, "create_resumen", lambda cabecera, lineas: 501)
    monkeypatch.setattr(repository, "get_lineas", lambda id_resumen: [])
    monkeypatch.setattr(repository, "hay_resumen_duplicado", lambda *a, **kw: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/tarjetas-resumenes", json=body)

    assert response.status_code == 201
    assert response.json()["lineas"] == []


@pytest.mark.anyio
async def test_post_resumen_sin_campos_requeridos_es_422(client):
    body = {k: v for k, v in VALID_BODY.items() if k != "idTarjeta"}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/tarjetas-resumenes", json=body)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_resumen_duplicado_no_bloquea(client, monkeypatch):
    monkeypatch.setattr(repository, "create_resumen", lambda cabecera, lineas: 502)
    monkeypatch.setattr(repository, "get_lineas", lambda id_resumen: VALID_BODY["lineas"])
    monkeypatch.setattr(repository, "hay_resumen_duplicado", lambda *a, **kw: True)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/tarjetas-resumenes", json=VALID_BODY)

    assert response.status_code == 201
    assert len(response.json()["warnings"]) == 1


# --- FR-013: lock / edición / eliminación ---


@pytest.mark.anyio
async def test_lock_resumen_primer_token_adquiere_segundo_es_409(client, monkeypatch):
    calls = {"n": 0}

    def fake_adquirir(id_resumen, lock_token, force=False):
        calls["n"] += 1
        if calls["n"] == 1:
            return repository_locks.LockInfo(id_resumen, lock_token, datetime(2026, 9, 18, 12, 0))
        return None

    monkeypatch.setattr(repository_locks, "adquirir_lock", fake_adquirir)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        r1 = await ac.post("/api/tarjetas-resumenes/1/lock", json={"lockToken": "A"})
        r2 = await ac.post("/api/tarjetas-resumenes/1/lock", json={"lockToken": "B"})

    assert r1.status_code == 200
    assert r2.status_code == 409


@pytest.mark.anyio
async def test_lock_resumen_force_toma_igual(client, monkeypatch):
    monkeypatch.setattr(
        repository_locks,
        "adquirir_lock",
        lambda id_resumen, lock_token, force=False: repository_locks.LockInfo(
            id_resumen, lock_token, datetime(2026, 9, 18, 12, 5)
        ),
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/tarjetas-resumenes/1/lock", json={"lockToken": "B", "force": True})

    assert response.status_code == 200


@pytest.mark.anyio
async def test_delete_lock_resumen(client, monkeypatch):
    monkeypatch.setattr(repository_locks, "liberar_lock", lambda id_resumen, token: token == "A")

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        ok = await ac.delete("/api/tarjetas-resumenes/1/lock", headers={"X-Lock-Token": "A"})
        conflict = await ac.delete("/api/tarjetas-resumenes/1/lock", headers={"X-Lock-Token": "B"})

    assert ok.status_code == 204
    assert conflict.status_code == 409


@pytest.mark.anyio
async def test_put_resumen_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_resumen_detalle", lambda id_resumen: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/tarjetas-resumenes/999999", json=VALID_BODY, headers={"X-Lock-Token": "A"})

    assert response.status_code == 404


@pytest.mark.anyio
async def test_put_resumen_sin_lock_es_409(client, monkeypatch):
    monkeypatch.setattr(repository, "get_resumen_detalle", lambda id_resumen: {"idResumen": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_resumen, token: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/tarjetas-resumenes/1", json=VALID_BODY, headers={"X-Lock-Token": "B"})

    assert response.status_code == 409


@pytest.mark.anyio
async def test_put_resumen_con_lock_recalcula_total(client, monkeypatch):
    monkeypatch.setattr(repository, "get_resumen_detalle", lambda id_resumen: {"idResumen": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_resumen, token: True)
    monkeypatch.setattr(repository, "update_resumen", lambda *a, **kw: None)
    monkeypatch.setattr(repository, "hay_resumen_duplicado", lambda *a, **kw: False)

    body = {**VALID_BODY, "impuestoSellos": 999.0}
    monkeypatch.setattr(repository, "get_lineas", lambda id_resumen: body["lineas"])

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/tarjetas-resumenes/1", json=body, headers={"X-Lock-Token": "A"})

    assert response.status_code == 200
    assert response.json()["totalCalculado"] == 15230.00 + 999.0 + 350.20


@pytest.mark.anyio
async def test_delete_resumen_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_resumen_detalle", lambda id_resumen: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/tarjetas-resumenes/999999", headers={"X-Lock-Token": "A"})

    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_resumen_sin_lock_es_409(client, monkeypatch):
    monkeypatch.setattr(repository, "get_resumen_detalle", lambda id_resumen: {"idResumen": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_resumen, token: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/tarjetas-resumenes/1", headers={"X-Lock-Token": "B"})

    assert response.status_code == 409


@pytest.mark.anyio
async def test_delete_resumen_con_lock_elimina(client, monkeypatch):
    borrado = {"id": None}

    def fake_delete(id_resumen):
        borrado["id"] = id_resumen

    monkeypatch.setattr(repository, "get_resumen_detalle", lambda id_resumen: {"idResumen": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_resumen, token: True)
    monkeypatch.setattr(repository, "delete_resumen", fake_delete)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/tarjetas-resumenes/1", headers={"X-Lock-Token": "A"})

    assert response.status_code == 204
    assert borrado["id"] == 1


# --- Punto 4 del feedback (2026-09-19): vínculo línea de consumo -> Compras reales ---


@pytest.mark.anyio
async def test_vincular_compra_a_linea(client, monkeypatch):
    monkeypatch.setattr(repository, "vincular_compra", lambda idl, idc, imp: 7)
    monkeypatch.setattr(
        repository,
        "get_compras_vinculadas",
        lambda idl: [
            {
                "idVinculo": 7,
                "idCompra": 2143513218,
                "proveedor": "IT Brokers",
                "tipoDocumento": "Factura",
                "numeroDocumento": "0005-00058564",
                "fechaCompra": "2021-06-07",
                "importeImputado": 26340.0,
            }
        ],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post(
            "/api/tarjetas-resumenes/lineas/1/compras", json={"idCompra": 2143513218, "importeImputado": 26340.0}
        )

    assert response.status_code == 201
    assert response.json()["idVinculo"] == 7


@pytest.mark.anyio
async def test_vincular_compra_inexistente_es_400(client, monkeypatch):
    def fake_vincular(idl, idc, imp):
        raise ValueError(["La compra 999999 no existe."])

    monkeypatch.setattr(repository, "vincular_compra", fake_vincular)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post(
            "/api/tarjetas-resumenes/lineas/1/compras", json={"idCompra": 999999, "importeImputado": 100}
        )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_quitar_vinculo_compra(client, monkeypatch):
    monkeypatch.setattr(repository, "quitar_vinculo_compra", lambda idv: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/tarjetas-resumenes/lineas/1/compras/7")

    assert response.status_code == 204


# --- Punto 6 del feedback (2026-09-19): pagos de un resumen ---


@pytest.mark.anyio
async def test_get_pagos_resumen(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_pagos",
        lambda idr: [{"idPago": 1, "fecha": "2021-07-12", "importe": 26340.0, "origen": "Galicia", "idMovimientoOrigen": 95}],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-resumenes/1/pagos")

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.anyio
async def test_registrar_pago_resumen(client, monkeypatch):
    monkeypatch.setattr(repository, "registrar_pago", lambda idr, fecha, importe, origen, idmov: 5)
    monkeypatch.setattr(
        repository,
        "get_pagos",
        lambda idr: [{"idPago": 5, "fecha": "2021-07-12", "importe": 26340.0, "origen": "Galicia", "idMovimientoOrigen": 95}],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post(
            "/api/tarjetas-resumenes/1/pagos",
            json={"fecha": "2021-07-12", "importe": 26340.0, "origen": "Galicia", "idMovimientoOrigen": 95},
        )

    assert response.status_code == 201
    assert response.json()["idPago"] == 5


@pytest.mark.anyio
async def test_eliminar_pago_resumen(client, monkeypatch):
    monkeypatch.setattr(repository, "eliminar_pago", lambda idp: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/tarjetas-resumenes/1/pagos/5")

    assert response.status_code == 204


# --- Auto-vínculo sin intervención del usuario (feedback 2026-09-19, puntos 4 y 6) ---


@pytest.mark.anyio
async def test_get_resumen_intenta_auto_vincular(client, monkeypatch):
    """El GET dispara ambos auto-vínculos — resuelve también los ~1600
    resúmenes históricos migrados antes de que existiera este mecanismo,
    sin que nadie tenga que editarlos."""
    llamados = {"compras": False, "pago": False}
    cabecera = {
        "idResumen": 1,
        "idTarjeta": 3,
        "tarjeta": "Visa Galicia",
        "codigo": "X",
        "fechaCierre": "2026-06-10",
        "fechaVencimiento": "2026-06-20",
        "impuestoSellos": 0,
        "gastosAdmin": 0,
        "mantCuenta": 0,
        "renovAnual": 0,
        "promocionBNA": 0,
        "creditoContingente": 0,
        "intFinanc": 0,
        "intCompens": 0,
        "iva105": 0,
        "percepIVA105": 0,
        "iva21": 0,
        "percepIVA21": 0,
        "percepIIBB": 0,
        "ajusteResAnterior": 0,
    }
    monkeypatch.setattr(repository, "get_resumen_detalle", lambda id_resumen: cabecera)
    monkeypatch.setattr(repository, "get_lineas", lambda id_resumen: [])
    monkeypatch.setattr(repository, "get_pagos", lambda id_resumen: [])
    monkeypatch.setattr(repository, "auto_vincular_compras", lambda id_resumen: llamados.__setitem__("compras", True) or 0)
    monkeypatch.setattr(tarjetas_repository, "auto_vincular_pago", lambda id_resumen: llamados.__setitem__("pago", True) or False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-resumenes/1")

    assert response.status_code == 200
    assert llamados == {"compras": True, "pago": True}


def test_auto_vincular_compras_matchea_unica_candidata(monkeypatch):
    """Línea con contacto+documento que matchea exacto UNA sola Compra
    real → se vincula sola, sin que el usuario busque nada."""
    monkeypatch.setattr(
        repository,
        "get_lineas",
        lambda id_resumen: [
            {"idLineaConsumo": 10, "idContacto": 481, "nroDocumento": "0265-00004930", "importe": 11225.35, "comprasVinculadas": []}
        ],
    )
    monkeypatch.setattr(repository, "fetch_all", lambda sql, params: [{"IdDeuda": 2143513659}])
    vinculado = {}
    monkeypatch.setattr(
        repository, "vincular_compra", lambda idl, idc, imp: vinculado.update(idl=idl, idc=idc, imp=imp) or 1
    )

    creados = _auto_vincular_compras_real(675)

    assert creados == 1
    assert vinculado == {"idl": 10, "idc": 2143513659, "imp": 11225.35}


def test_auto_vincular_compras_no_vincula_si_hay_ambiguedad(monkeypatch):
    """Dos Compras candidatas (mismo contacto+documento) → no adivina,
    queda para vínculo manual."""
    monkeypatch.setattr(
        repository,
        "get_lineas",
        lambda id_resumen: [
            {"idLineaConsumo": 10, "idContacto": 22, "nroDocumento": "11", "importe": 100.0, "comprasVinculadas": []}
        ],
    )
    monkeypatch.setattr(repository, "fetch_all", lambda sql, params: [{"IdDeuda": 1}, {"IdDeuda": 2}])
    monkeypatch.setattr(repository, "vincular_compra", lambda *a: pytest.fail("no debería vincular con ambigüedad"))

    creados = _auto_vincular_compras_real(675)

    assert creados == 0


def test_auto_vincular_pago_match_simple(monkeypatch):
    monkeypatch.setattr(tarjetas_repository, "get_pagos", lambda id_resumen: [])
    monkeypatch.setattr(
        tarjetas_repository,
        "fetch_one",
        lambda *a, **kw: {"IdTarjeta": 4, "FechaVencimiento": datetime(2021, 7, 12)},
    )
    monkeypatch.setattr(tarjetas_repository, "get_resumen_detalle", lambda id_resumen: {})
    monkeypatch.setattr(tarjetas_repository, "get_lineas", lambda id_resumen: [])
    monkeypatch.setattr(tarjetas_repository, "calcular_total", lambda cab, lin: 26969.56)
    monkeypatch.setattr(
        tarjetas_repository,
        "get_pagos_candidatos",
        lambda id_tarjeta: [
            {"origen": "Galicia", "idMovimiento": 95, "fecha": datetime(2021, 7, 12), "importe": 26969.56, "concepto": "PAGO"}
        ],
    )
    registrado = {}
    monkeypatch.setattr(
        tarjetas_repository,
        "registrar_pago",
        lambda idr, fecha, importe, origen, idmov: registrado.update(idr=idr, importe=importe, idmov=idmov),
    )

    assert _auto_vincular_pago_real(426) is True
    assert registrado == {"idr": 426, "importe": 26969.56, "idmov": 95}


def test_auto_vincular_pago_match_par_mismo_dia(monkeypatch):
    """Visa Galicia real: dos movimientos el mismo día suman el total exacto."""
    monkeypatch.setattr(tarjetas_repository, "get_pagos", lambda id_resumen: [])
    monkeypatch.setattr(
        tarjetas_repository,
        "fetch_one",
        lambda *a, **kw: {"IdTarjeta": 4, "FechaVencimiento": datetime(2021, 7, 12)},
    )
    monkeypatch.setattr(tarjetas_repository, "get_resumen_detalle", lambda id_resumen: {})
    monkeypatch.setattr(tarjetas_repository, "get_lineas", lambda id_resumen: [])
    monkeypatch.setattr(tarjetas_repository, "calcular_total", lambda cab, lin: 26969.56)
    monkeypatch.setattr(
        tarjetas_repository,
        "get_pagos_candidatos",
        lambda id_tarjeta: [
            {"origen": "Galicia", "idMovimiento": 95, "fecha": datetime(2021, 7, 12), "importe": 26340.0, "concepto": "PAGO"},
            {"origen": "Galicia", "idMovimiento": 96, "fecha": datetime(2021, 7, 12), "importe": 629.56, "concepto": "PAGO"},
        ],
    )
    registrados = []
    monkeypatch.setattr(
        tarjetas_repository,
        "registrar_pago",
        lambda idr, fecha, importe, origen, idmov: registrados.append(idmov),
    )

    assert _auto_vincular_pago_real(426) is True
    assert sorted(registrados) == [95, 96]


def test_auto_vincular_pago_no_reintenta_si_ya_tiene_pago(monkeypatch):
    monkeypatch.setattr(tarjetas_repository, "get_pagos", lambda id_resumen: [{"idPago": 1}])
    monkeypatch.setattr(
        tarjetas_repository, "registrar_pago", lambda *a: pytest.fail("no debería reintentar")
    )

    assert _auto_vincular_pago_real(426) is False
