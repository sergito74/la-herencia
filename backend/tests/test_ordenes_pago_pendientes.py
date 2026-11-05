"""Facturas a pagar (04-05/11/2026): con portal manda el portal; sin portal, lo que debe la cuenta son sus documentos
más nuevos; los pagos hechos que esperan el banco se descuentan; cuentas en cero, bancos y restos < $300 fuera."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.features.cuentas_corrientes import repository as cuentas
from src.features.ordenes_pago import comprobantes_emitidos
from src.features.ordenes_pago import repository as repo


def _f(id_, fecha, saldo):
    return {"idCompra": id_, "numero": f"0001-{id_:08d}", "fecha": fecha, "fechaVto": None, "moneda": "Pesos", "tc": None,
            "total": Decimal(saldo), "pagado": 0, "saldo": Decimal(saldo), "reservado": Decimal(0),
            "disponible": Decimal(saldo), "suspendida": False}


def _m(id_, fecha, deuda, origen="Compras"):
    return {"fecha": fecha, "documento": "Factura", "numeroDocumento": f"0001-{id_:08d}", "deuda": deuda,
            "credito": 0.0, "origenTipo": origen, "idOrigen": id_}


def test_listado(monkeypatch):
    monkeypatch.setattr(cuentas, "get_saldos_todos", lambda: [
        {"idContacto": 258, "razonSocial": "Cargill", "saldoParcial": -9_000_000.0},
        {"idContacto": 1, "razonSocial": "Sin portal", "saldoParcial": -1000.0},
        {"idContacto": 2, "razonSocial": "En cero", "saldoParcial": 0.0},
        {"idContacto": 3, "razonSocial": "Banco Galicia", "saldoParcial": -10_000.0},
        {"idContacto": 4, "razonSocial": "Pagado en camino", "saldoParcial": -5000.0},
        {"idContacto": 5, "razonSocial": "Resto", "saldoParcial": -1.22}])
    monkeypatch.setattr(repo, "_portal_pendientes", lambda: {258: [
        {"numero": "ND 1", "fecha": date(2026, 6, 10), "importe": Decimal("570.54"), "moneda": "Pesos"}]})
    monkeypatch.setattr(comprobantes_emitidos, "sincronizar", lambda: None)
    monkeypatch.setattr(comprobantes_emitidos, "esperando_banco", lambda: {4: [{"importe": Decimal(5000)}]})
    movs = {1: [_m(10, date(2017, 1, 1), 500.0), _m(11, date(2026, 9, 1), 800.0), _m(12, date(2026, 10, 1), 700.0)]}
    monkeypatch.setattr(cuentas, "get_movimientos", lambda c, *a, **k: (movs.get(c, [_m(99, date(2026, 1, 1), 9e6)]), 0))
    monkeypatch.setattr(repo, "facturas", lambda c, *a, **k: [])
    monkeypatch.setattr(repo, "medio_habitual", lambda c: "galicia")
    filas = repo._pendientes()
    assert [f["numero"] for f in filas if f["idContacto"] == 258] == ["ND 1"]  # manda el portal
    sin = sorted((f for f in filas if f["idContacto"] == 1), key=lambda f: f["fecha"])
    # debe 1000: la de octubre entera (700) y 300 de la de septiembre; la de 2017 está pagada
    assert [(f["idCompra"], f["saldo"]) for f in sin] == [(11, Decimal(300)), (12, Decimal(700))]
    assert not [f for f in filas if f["idContacto"] in (2, 3, 4, 5)]


def test_portal_descuenta_pago_en_camino(monkeypatch):
    monkeypatch.setattr(cuentas, "get_saldos_todos", lambda: [{"idContacto": 48, "razonSocial": "JyM", "saldoParcial": -300.0}])
    monkeypatch.setattr(repo, "_portal_pendientes", lambda: {48: [
        {"numero": "FT 1", "fecha": date(2026, 10, 1), "importe": Decimal(100), "moneda": "Pesos"},
        {"numero": "FT 2", "fecha": date(2026, 10, 20), "importe": Decimal(200), "moneda": "Pesos"}]})
    monkeypatch.setattr(comprobantes_emitidos, "sincronizar", lambda: None)
    monkeypatch.setattr(comprobantes_emitidos, "esperando_banco", lambda: {48: [{"importe": Decimal("100.01")}]})
    filas = repo._pendientes()
    assert [(f["numero"], f["saldo"]) for f in filas] == [("FT 2", Decimal("199.99"))]


def test_lee_comprobante_galicia(monkeypatch, tmp_path):
    import pdfplumber

    texto = ("Office Banking\nIdentificador de la operación: LRB4GGB549\nDatos del pago\nFecha de envío Monto\n"
             "04/11/2026 $ 326.399,92\nConcepto Descripción\nFactura 0545\nDatos del destinatario\nCUIT/CUIL Razón social\n"
             "20221852576 Miguel Basterrechea\n")

    class P:
        pages = [type("pg", (), {"extract_text": lambda self: texto})()]
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(pdfplumber, "open", lambda r: P())
    d = comprobantes_emitidos.leer_pdf(tmp_path / "x.pdf")
    assert d["Tipo"] == "transferencia" and d["Importe"] == Decimal("326399.92") and d["CuitDestino"] == "20221852576"
    assert d["Fecha"] == date(2026, 11, 4) and d["Concepto"] == "Factura 0545"
