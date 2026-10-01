"""031 — lotes de corrección: backup obligatorio, ambiguos sin elegir,
formato del motivo y reversión. Base de datos simulada: no escribe en WC."""

from __future__ import annotations

import pytest

from src.features.vinculos import lotes

ITEMS = [
    {"idItem": 1, "accion": "anular", "idAplicacion": 100, "origenMovimiento": "bna", "idMovimientoOrigen": 1,
     "tipoDocumento": "CompraDeuda", "idDocumento": 10, "importe": 500.0, "motivo": "El pago es 900 días anterior a la factura"},
    {"idItem": 2, "accion": "reemplazo", "idAplicacion": None, "origenMovimiento": "bna", "idMovimientoOrigen": 2,
     "tipoDocumento": "CompraDeuda", "idDocumento": 10, "importe": 500.0, "motivo": "Otro pago"},
]


@pytest.fixture
def db(monkeypatch):
    estado = {"estado": "propuesto", "ambiguos": 0, "escrito": None}
    monkeypatch.setattr(lotes, "_lote", lambda i: {"idLote": i, "estado": estado["estado"]})
    monkeypatch.setattr(lotes, "resumen_lote", lambda i: {"grupos": [], "ambiguosSinElegir": estado["ambiguos"]})

    def fetch(sql, params=()):
        if "IdAplicacionCreada AS idAplicacionCreada" in sql:
            return [{"accion": "anular", "idAplicacion": 100, "idAplicacionCreada": None},
                    {"accion": "reemplazo", "idAplicacion": None, "idAplicacionCreada": 555}]
        return [dict(i) for i in ITEMS]

    def escribir(statements):
        resueltos, res = [], []
        for s in statements:
            sql, params = s(res) if callable(s) else s
            resueltos.append((sql, params))
            res.append(555 if "OUTPUT" in sql else 1)
        estado["escrito"] = resueltos
        return res

    monkeypatch.setattr(lotes, "fetch_all", fetch)
    monkeypatch.setattr(lotes, "execute_write_transaction", escribir)
    return estado


def test_sin_backup_verificado_no_escribe(db):
    def falla(etiqueta):
        raise RuntimeError("backup falló")

    with pytest.raises(RuntimeError):
        lotes.aplicar(7, "sergio", backup=falla)
    assert db["escrito"] is None


def test_ambiguos_sin_elegir_da_conflicto(db):
    db["ambiguos"] = 1
    with pytest.raises(lotes.LoteConflicto):
        lotes.aplicar(7, "sergio", backup=lambda e: "x.bak")


def test_lote_no_propuesto_da_conflicto(db):
    db["estado"] = "aplicado"
    with pytest.raises(lotes.LoteConflicto):
        lotes.aplicar(7, "sergio", backup=lambda e: "x.bak")


def test_aplicar_anula_con_prefijo_del_lote_y_crea_con_origen_031(db):
    r = lotes.aplicar(7, "sergio", backup=lambda e: "C:/b/x.bak")
    assert r == {"anuladas": 1, "creadas": 1, "backup": "C:/b/x.bak"}
    sqls = db["escrito"]
    assert sqls[0][1][0].startswith("031:7: El pago es 900 días")
    insert = next(p for s, p in sqls if s.startswith("INSERT INTO dbo.AplicacionesPago"))
    assert insert[6] == "correccion-031"
    assert any("IdAplicacionCreada" in s and p == (555, 2) for s, p in sqls)
    assert "Estado = 'aplicado'" in sqls[-1][0]


def test_revertir_reactiva_solo_las_del_lote_y_anula_las_creadas(db):
    db["estado"] = "aplicado"
    r = lotes.revertir(7, "sergio")
    sqls = db["escrito"]
    assert sqls[0][1] == (100, "031:7:%") and "Anulada = 0" in sqls[0][0]
    assert sqls[1][1][2] == 555 and "Anulada = 1" in sqls[1][0]
    assert r == {"reactivadas": 1, "anuladas": 1}
