"""Revisión de una cuenta: orden de trabajo, estados y avisos — 035 (T045). Fixtures puros."""

from datetime import datetime

from src.features.auditoria_cuentas import revision as r


def _cuenta(id_, nombre, causa="coincide", extras=(), saldo=0.0, sin_explicar=0.0, documentada=None):
    return {"idContacto": id_, "razonSocial": nombre, "causa": causa, "causasExtra": list(extras), "saldoSistema": saldo,
            "sinExplicar": sin_explicar, "documentada": documentada}


def test_dificultad():
    assert r.dificultad(_cuenta(1, "A")) == 0
    assert r.dificultad(_cuenta(1, "A", causa="coincide-causa-conocida")) == 1
    assert r.dificultad(_cuenta(1, "A", extras=["fuera-de-plazo-decidido"])) == 1
    assert r.dificultad(_cuenta(1, "A", causa="otros")) == 2
    assert r.dificultad(_cuenta(1, "A", extras=["doble-descuento-tarjeta"])) == 2
    # saldo esperado cero y no es cero: complicada; el redondeo no cuenta
    assert r.dificultad(_cuenta(1, "A", saldo=5000.0), "cero") == 2
    assert r.dificultad(_cuenta(1, "A", saldo=0.4), "cero") == 0
    assert r.dificultad(_cuenta(1, "A", saldo=5000.0), "puede-tener-saldo") == 0


def test_orden_alfabetico_de_faciles_a_complicadas():
    cuentas = [_cuenta(1, "Zeta"), _cuenta(2, "Alfa", causa="otros"), _cuenta(3, "Beta", causa="coincide-causa-conocida"),
               _cuenta(4, "Alfonso"), _cuenta(5, "Carlos", extras=["sobrepago"])]
    orden = [c["razonSocial"] for c in r.orden_de_revision(cuentas, {})]
    assert orden == ["Alfonso", "Zeta", "Beta", "Alfa", "Carlos"]


def test_siguiente_salta_las_revisadas_y_da_la_vuelta():
    orden = [_cuenta(i, n) for i, n in [(1, "A"), (2, "B"), (3, "C"), (4, "D")]]
    estados = {1: "pendiente", 2: "revisada", 3: "pendiente", 4: "revision-vieja"}
    assert r.siguiente_sin_revisar(orden, estados, 1)["idContacto"] == 3
    assert r.siguiente_sin_revisar(orden, estados, 3)["idContacto"] == 4      # la revisión vieja cuenta como pendiente
    assert r.siguiente_sin_revisar(orden, estados, 4)["idContacto"] == 1      # da la vuelta
    assert r.siguiente_sin_revisar(orden, {i: "revisada" for i in range(1, 5)}, 1) is None
    assert r.siguiente_sin_revisar(orden, estados, None)["idContacto"] == 1


def test_estado_de_revision():
    ok = {"Estado": "revisada", "SaldoAlRevisar": 1000.0, "FechaRevision": datetime(2026, 10, 6)}
    assert r.estado_de_revision(None, 5.0) == "pendiente"
    assert r.estado_de_revision({"Estado": "pendiente", "SaldoAlRevisar": None}, 5.0) == "pendiente"
    assert r.estado_de_revision(ok, 1000.4) == "revisada"
    assert r.estado_de_revision(ok, 1500.0) == "revision-vieja"


def test_avisos_de_cuenta():
    c = _cuenta(1, "A", causa="otros", extras=["doble-descuento-tarjeta"], saldo=300.0, sin_explicar=-50.0)
    tipos = [a["tipo"] for a in r.avisos_de_cuenta(c, "cero")]
    assert tipos == ["saldo-esperado", "diferencia-sin-explicar", "doble-descuento-tarjeta"]
    assert r.avisos_de_cuenta(_cuenta(1, "A"), None) == []
    doc = r.avisos_de_cuenta(_cuenta(1, "A", causa="coincide-causa-conocida", documentada="Pago de Mercado Pago"), None)
    assert doc[0]["tipo"] == "diferencia-documentada"
