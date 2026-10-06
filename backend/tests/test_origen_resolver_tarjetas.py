"""034 (T011): el resolutor de orígenes entiende las ramas nuevas de la vista."""
from src.features.cuentas_corrientes import origen_resolver as o


def _repo(monkeypatch, **respuestas):
    for nombre, valor in respuestas.items():
        monkeypatch.setattr(o.repository, nombre, lambda _id, v=valor: v)


def test_tarjeta_consumo(monkeypatch):
    _repo(monkeypatch, get_tarjeta_consumo_referencia={"idLineaConsumo": 505, "idResumen": 77, "numeroDocumento": "VI001"})
    assert o.resolve_origen("Tarjeta consumo", 505) == {
        "tipo": "tarjeta_consumo", "idLineaConsumo": 505, "idResumen": 77, "numeroDocumento": "VI001"}


def test_tarjeta_cargo_resuelve_el_resumen_por_idorigen_dividido_100(monkeypatch):
    llamado = {}
    monkeypatch.setattr(o.repository, "get_tarjeta_resumen_referencia",
                        lambda i: llamado.setdefault("id", i) and {"idResumen": i, "numeroDocumento": "X"})
    assert o.resolve_origen("Tarjeta cargo", 7709)["idResumen"] == 77
    assert llamado["id"] == 77


def test_tarjeta_pago_y_devolucion(monkeypatch):
    _repo(monkeypatch, get_tarjeta_pago_referencia={"idResumen": 468, "numeroDocumento": "VI38", "importe": 3195.96},
          get_tarjeta_cruce_referencia={"idCruce": 7, "idTarjeta": 1, "importe": 966654.2})
    assert o.resolve_origen("Tarjeta pago", 4023)["tipo"] == "tarjeta_resumen"
    cruce = o.resolve_origen("Tarjeta devolución", 7)
    assert cruce == {"tipo": "tarjeta_cruce", "idCruce": 7, "idTarjeta": 1, "importe": 966654.2}


def test_mercado_pago_se_resuelve_como_tesoreria(monkeypatch):
    _repo(monkeypatch, get_mercado_libre_referencia={"idMovimiento": 23, "fecha": "2024-09-04", "importe": -17185.82})
    r = o.resolve_origen("Mercado Pago", 23)
    assert r["tipo"] == "tesoreria" and r["medio"] == "mercado-libre" and r["idMovimiento"] == 23


def test_registro_inexistente_es_no_disponible(monkeypatch):
    _repo(monkeypatch, get_tarjeta_consumo_referencia=None)
    assert o.resolve_origen("Tarjeta consumo", 1)["tipo"] == "no_disponible"
