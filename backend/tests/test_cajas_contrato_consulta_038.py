from decimal import Decimal
from uuid import uuid4

from tests.cajas_038_helpers import CajaSimulada, request, guardar
from src.features.cajas_efectivo import operaciones as db, repository


def test_saldo_enriquecido_conserva_numero_y_decimal(monkeypatch):
    from src.features.cajas_efectivo import arqueos
    store = CajaSimulada(monkeypatch)
    monkeypatch.setattr(db, 'one', lambda *a: {'saldo': Decimal('123.45')})
    monkeypatch.setattr(arqueos, 'listar', lambda *a: {'items': []})
    response = store.client.get('/api/cajas-efectivo/giamigli-sa/saldo?detalleSaldo=true')
    assert response.status_code == 200
    assert response.json()['saldo'] == 123.45
    assert response.json()['saldoDecimal'] == '123.45'
    assert response.json()['ultimoArqueo'] is None


def test_saldo_real_antes_de_filtros_y_paginacion(monkeypatch):
    calls = []

    def one(sql, params=()):
        calls.append((sql, params))
        if "COUNT(*)" in sql:
            return {"total": 2, "subtotal": Decimal(120)}
        return {"saldo": Decimal(0)}

    def read(sql, params=()):
        calls.append((sql, params))
        return [
            {
                "idMovimiento": 3,
                "fecha": "2026-10-22",
                "importe": Decimal(20),
                "saldoCorridoDecimal": "90.00",
            }
        ]

    monkeypatch.setattr(db, "one", one)
    monkeypatch.setattr(db, "read", read)
    result = repository.consultar_movimientos("GiamigliSA", 2, 1, tipo="cobro")
    assert result["items"][0]["saldoCorridoDecimal"] == "90.00"
    assert result["subtotalFiltradoDecimal"] == "120.00" and isinstance(
        result["items"][0]["importe"], float
    )
    sql = calls[1][0]
    assert sql.index("OVER (ORDER BY") < sql.index("Tipo=?") < sql.index("OFFSET")
    assert calls[1][1][-2:] == (1, 1)


def test_anulacion_revierte_pago_y_socio_idempotente(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert (
        guardar(store, request(compraParticular={"idCompra": 10, "idSocio": 1})).status_code == 201
    )
    r = store.client.post(
        "/api/cajas-efectivo/operaciones/1/anular", json={"motivo": "Error", "versionEsperada": 0}
    )
    assert r.status_code == 200, r.text
    assert all(
        x["anulada"]
        for x in store.rows("AplicacionesPago")
        + store.rows("MovimientosCuentaSocio")
        + store.rows("MovimientosCajaEfectivo")
    )
    before = len(store.state["writes"])
    assert (
        store.client.post(
            "/api/cajas-efectivo/operaciones/1/anular",
            json={"motivo": "Error", "versionEsperada": 0},
        ).status_code
        == 200
    )
    assert len(store.state["writes"]) == before


def test_aplicacion_ajena_bloquea_reversion(monkeypatch):
    store = CajaSimulada(monkeypatch)
    assert guardar(store, request()).status_code == 201
    pago = store.rows("Pagos efectivo")[0]["id"]
    store.state["records"].append(
        {"table": "AplicacionesPago", "id": 999, "params": ("efectivo", pago), "anulada": False}
    )
    r = store.client.post(
        "/api/cajas-efectivo/operaciones/1/anular", json={"motivo": "Error", "versionEsperada": 0}
    )
    assert r.status_code == 409 and "999" in r.text
    assert store.state["ops"] and not store.rows("MovimientosCajaEfectivo")[0]["anulada"]


def test_50_operaciones_reintentos_y_anulacion(monkeypatch):
    store = CajaSimulada(monkeypatch)
    for i in range(50):
        kind = ("pago", "cobro", "aporte", "retiro_a_cuenta", "traspaso_cajas")[i % 5]
        op, key = request(kind), uuid4()
        for application in op.get("aplicaciones", []):
            application["idDocumento"] += i
        first = guardar(store, op, key)
        second = guardar(store, op, key)
        assert first.status_code == 201 and second.status_code == 200
        assert first.json() == second.json()
    assert len(store.state["ops"]) == 50
    assert len(store.rows("MovimientosCajaEfectivo")) == 60
    assert len(store.rows("Pagos efectivo")) == 20
    assert len(store.rows("MovimientosCuentaSocio")) == 20
    for id in range(1, 51):
        response = store.client.post(
            f"/api/cajas-efectivo/operaciones/{id}/anular",
            json={"motivo": "Muestra", "versionEsperada": 0},
        )
        assert response.status_code == 200, response.text
    assert all(x["anulada"] for x in store.rows("MovimientosCajaEfectivo"))
