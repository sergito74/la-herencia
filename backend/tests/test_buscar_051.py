from src.features.buscar import router as R


def test_menos_de_dos_letras_no_busca():
    assert R.buscar("a") == []


def test_numero_corto_pone_ordenes_primero(monkeypatch):
    def fake(sql, params=()):
        if "FROM dbo.Ordenes_Trabajo o" in sql:
            return [{"id": 164, "f": "2026-11-05", "e": "Ejecutada", "l": "Siembra"}]
        if "dbo.Compras" in sql:
            return [{"id": 9, "nro": "0003-00221641", "td": "Factura", "f": "2026-01-01", "p": "X"}]
        return []
    monkeypatch.setattr(R, "fetch_all", fake)
    r = R.buscar("164")
    assert r[0]["tipo"] == "Órdenes" and r[1]["tipo"] == "Compras"
    assert all(x["tipo"] != "Órdenes" for x in R.buscar("6A"))
