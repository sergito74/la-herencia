"""Tandas del FIFO completo — 035 (T022–T026). Fixtures puros y lectura del plan real."""

from src.features.auditoria_cuentas import fifo_plan as f


def _c(i, nombre, vol, moneda="ARS"):
    return {"idContacto": i, "nombre": nombre, "moneda": moneda, "volumen": vol, "saldo": 0.0}


def test_tandas_de_las_mas_faciles_a_las_mas_complicadas_y_alfabeticas():
    cs = [_c(1, "Zeta", 100), _c(2, "Alfa", 100), _c(3, "Beta", 600_000), _c(4, "Omega", 9_000_000), _c(5, "Dolar SA", 100, "USD"), _c(6, "alfa dos", 100)]
    t = f.armar_tandas(cs)
    assert [x["rango"] for x in t] == ["hasta $ 250.000", "de $ 250.000 a $ 1 M", "más de $ 5 M", "cuentas en dólares"]
    assert [c["nombre"] for c in t[0]["contactos"]] == ["Alfa", "alfa dos", "Zeta"]
    assert [x["numero"] for x in t] == [1, 2, 3, 4]


def test_las_tandas_no_superan_el_tamano_y_cubren_todos_los_contactos():
    cs = [_c(i, f"C{i:03d}", 100) for i in range(120)]
    t = f.armar_tandas(cs, tamano=50)
    assert [len(x["contactos"]) for x in t] == [50, 50, 20] and [x["parte"] for x in t] == ["1 de 3", "2 de 3", "3 de 3"]
    assert sorted(c["idContacto"] for x in t for c in x["contactos"]) == list(range(120))


def test_plan_real_de_la_ultima_simulacion():
    p = f.plan()
    assert p["base"] and p["tandas"]
    ids = [c["idContacto"] for t in p["tandas"] for c in t["contactos"]]
    assert len(ids) == len(set(ids)) and all(len(t["contactos"]) <= f.TAMANO_TANDA for t in p["tandas"])
    assert p["tandas"][0]["rango"] == "hasta $ 250.000" and p["tandas"][-1]["rango"] == "cuentas en dólares"
    assert all(e["idContacto"] not in ids for e in p["excepciones"])


def test_una_cuenta_sin_cambios_cuenta_como_resuelta_en_su_tanda(monkeypatch):
    import json

    filas = [{"r": json.dumps({"aplicados": [1, 2], "sinCambios": [3]})}, {"r": json.dumps({"aplicados": [4]})}, {"r": "no es json"}]
    monkeypatch.setattr(f, "fetch_all", lambda *a, **k: filas)
    assert f.contactos_aplicados_desde(10) == {1, 2, 3, 4}
