from datetime import date
from decimal import Decimal
from tests.test_cajas_contrato_arqueos_038 import count as count_fixture

from src.features.cajas_efectivo import operaciones as db


count = count_fixture

def confirmado(client):
    a = client.post(
        "/api/cajas-efectivo/giamigli-sa/arqueos",
        json={
            "fechaCorte": "2026-10-22",
            "denominaciones": [
                {"valor": "1000", "cantidad": 1},
                {"valor": "100", "cantidad": 2},
                {"valor": "50", "cantidad": 1},
            ],
        },
    ).json()
    response = client.post(
        "/api/cajas-efectivo/giamigli-sa/arqueos/1/confirmar",
        json={
            "versionEsperada": a["version"],
            "previewVersion": a["previewVersion"],
            "aceptarDiferencia": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_anular_ajuste_invalida_y_nuevo_recuento_enlaza(count):
    client, state = count
    a = confirmado(client)
    response = client.post(
        f"/api/cajas-efectivo/operaciones/{a['idOperacionAjuste']}/anular",
        json={"motivo": "Recuento incorrecto", "versionEsperada": 0},
    )
    assert response.status_code == 200, response.text
    assert state["all"][1]["Estado"] == "Invalidado"
    assert str(state["all"][1]["Diferencia"]) == "249.10"
    response = client.post(
        "/api/cajas-efectivo/giamigli-sa/arqueos",
        json={
            "fechaCorte": "2026-10-22",
            "idArqueoAnterior": 1,
            "denominaciones": [{"valor": "1000", "cantidad": 1}],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["idArqueoAnterior"] == 1 and len(state["all"]) == 2
    assert state["all"][1]["Estado"] == "Invalidado"


def test_retroactividad_desactualiza_sin_reescribir_observaciones(count):
    client, state = count
    original = confirmado(client)
    db.stale_arqueos(["giamigli-sa"], date(2026, 10, 20), "prueba")
    assert state["all"][1]["Estado"] == "Desactualizado"
    assert state["all"][1]["TotalContado"] == Decimal(original["totalContado"])
    assert str(state["all"][1]["Diferencia"]) == original["diferencia"]
