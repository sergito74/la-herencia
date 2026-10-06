"""Mercado Pago como banco: conducto y pagos propios — 034 (T044). Solo lectura sobre WC."""

from src.db.connection import fetch_all
from src.features.tesoreria import repository


def _movimientos():
    return repository.get_movimientos("mercado-libre", None, None, 1, 5000)[0]


def test_conducto_son_pares_con_ingreso_de_dinero():
    con = [m for m in _movimientos() if m["esConducto"]]
    assert len(con) % 2 == 0 and len(con) >= 60
    assert all(m["idOperacionPar"] == m["idOperacion"] for m in con)
    assert sum(m["importe"] for m in con) < 0.01 * len(con)  # cada par se anula


def test_pago_de_uatre_del_04_09_2024_no_es_conducto_y_suma_a_su_cuenta():
    pago = [m for m in _movimientos() if str(m["idOperacion"]) == "86673304977"]
    assert pago and not any(m["esConducto"] for m in pago)
    filas = fetch_all("SELECT Fecha, Deuda, Credito FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = 315 AND Origen = 'Mercado Pago'")
    assert len(filas) == 1


def test_la_vista_no_toma_los_conductos():
    ids = {m["idMovimiento"] for m in _movimientos() if m["esConducto"]}
    en_vista = {f["IdOrigen"] for f in fetch_all("SELECT IdOrigen FROM dbo.vw_MovimientosCuenta_Base WHERE Origen = 'Mercado Pago'")}
    assert not (ids & en_vista)


def test_saldo_de_la_billetera():
    ultimo = sorted(_movimientos(), key=lambda m: (m["fecha"], m["idMovimiento"]))[-1]
    assert abs(ultimo["saldo"] - 0.14) < 0.005
