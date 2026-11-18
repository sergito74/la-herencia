from src.features.inicio import service as S


def test_una_fuente_rota_no_tumba_el_inicio(monkeypatch):
    def rota():
        raise RuntimeError("base caída")
    pend = [("ok", lambda: {"cantidad": 2, "importe": 10.0}, ("x", "cosas pendientes"), "/a"),
            ("cero", lambda: {"cantidad": 0}, ("y", "nada"), "/b"),
            ("rota", rota, ("z", "zetas"), "/c")]
    monkeypatch.setattr(S, "PENDIENTES", pend)
    for n in ("_bancos_saldo", "_deuda_proveedores", "_stock", "_cajas", "_flujo", "_campania"):
        monkeypatch.setattr(S, n, lambda: {})
    d = S.calcular()
    claves = [p["clave"] for p in d["pendientes"]]
    assert claves == ["ok", "rota"]  # lo que da 0 no se muestra; lo que falla queda marcado
    assert d["pendientes"][0]["texto"] == "cosas pendientes" and d["pendientes"][1]["error"]
