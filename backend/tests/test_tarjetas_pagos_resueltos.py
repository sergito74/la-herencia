"""La resolución vigente excluye candidatos; la revocación los recupera."""
import sqlite3
from src.features.tarjetas import repository as r


def test_candidatos_respetan_ultima_resolucion_y_banco(monkeypatch):
    db = sqlite3.connect(":memory:")
    db.execute("ATTACH DATABASE ':memory:' AS dbo")
    db.execute("CREATE TABLE dbo.Tarjetas_Resumenes_Pagos (IdMovimientoOrigen INT, Origen TEXT)")
    db.execute("CREATE TABLE dbo.ConciliacionesTesoreriaEstado (IdEstado INT, IdMovimiento INT, Medio TEXT, Estado TEXT)")
    db.execute("INSERT INTO dbo.Tarjetas_Resumenes_Pagos VALUES (1,'BNA')")
    db.executemany("INSERT INTO dbo.ConciliacionesTesoreriaEstado VALUES (?,?,?,?)", [
        (1, 2, 'bna', 'SinDocumento'), (2, 3, 'bna', 'DiferenciaAceptada'),
        (3, 4, 'bna', 'SinDocumento'), (4, 4, 'bna', 'EstadoQuitado'),
        (5, 5, 'galicia', 'SinDocumento'),
    ])
    monkeypatch.setattr(r, "get_tarjeta", lambda _: {"banco": "Banco Nacion"})
    monkeypatch.setattr(r, "get_id_contacto_tarjeta", lambda _: 373)
    def fetch(sql, params=()):
        if "FROM dbo.[Movimientos BNA]" in sql:
            return [dict(idMovimiento=i, fecha="2026-10-06", importe=-100, concepto="Pago", numeroCuentaBancaria="1") for i in range(1, 7)]
        cursor = db.execute(sql, params)
        return [dict(zip([x[0] for x in cursor.description], row)) for row in cursor.fetchall()]
    monkeypatch.setattr(r, "fetch_all", fetch)
    try:
        assert [x["idMovimiento"] for x in r.get_pagos_candidatos(1)] == [4, 5, 6]
    finally:
        db.close()
