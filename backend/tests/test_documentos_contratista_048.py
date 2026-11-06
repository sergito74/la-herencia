"""048: vínculo factura de labor ↔ órdenes, reparto y NC que sigue a su factura (con mocks, sin escribir en WC)."""

from __future__ import annotations

import pytest

from src.features.imputacion import motor, repository as imp_repo
from src.features.ordenes import documentos_contratista as dc


def _reparto_base(monkeypatch, neto=1000.0, ordenes=(10, 11), dist=None, rubro_orden=None):
    monkeypatch.setattr(imp_repo, "ordenes_vinculadas_a_compra", lambda idc: list(ordenes))
    monkeypatch.setattr(imp_repo, "total_neto_compra",
                        lambda idc: {"moneda": "Pesos", "tipoDeCambio": None, "tipoDocumento": "Factura", "neto": neto})
    monkeypatch.setattr(imp_repo, "orden_trabajo_info",
                        lambda ido: {"idOrdenTrabajo": ido, "idRubro": rubro_orden.get(ido) if rubro_orden else None,
                                     "idCentroCostos": None, "fecha": None})
    dist = dist or {10: [{"idLote": 1, "idCultivo": 5, "idCampania": 9, "superficie": 1.0}],
                    11: [{"idLote": 2, "idCultivo": 6, "idCampania": 9, "superficie": 2.0}]}
    monkeypatch.setattr(imp_repo, "distribucion_de_orden", lambda ido: dist.get(ido, []))
    monkeypatch.setattr(motor, "_id_centro_adm_general", lambda: 77)


def test_reparto_cierra_al_centavo_con_varias_ordenes_y_cultivos(monkeypatch):
    _reparto_base(monkeypatch, neto=1000.0)
    fracciones, motivo = motor.evaluar_contratista(1)
    assert motivo is None
    assert round(sum(f["importe"] for f in fracciones), 2) == 1000.00
    assert [f["importe"] for f in fracciones] == [333.33, 666.67]


def test_orden_sin_cultivo_va_al_centro_de_costo(monkeypatch):
    _reparto_base(monkeypatch, neto=500.0, ordenes=(10,), rubro_orden={10: 3})
    fracciones, _ = motor.evaluar_contratista(1)
    assert fracciones == [{"idOrdenTrabajo": 10, "idCentroCosto": 77, "importe": 500.0}]


def test_distribucion_toma_la_superficie_del_lote_una_vez():
    import inspect
    fuente = inspect.getsource(imp_repo.distribucion_de_orden)
    assert "MAX(d.Superficie)" in fuente and "SUM(d.Superficie)" not in fuente


def test_nc_replica_proporciones_en_negativo(monkeypatch):
    monkeypatch.setattr(imp_repo, "factura_de_nota", lambda idnc: 500)
    monkeypatch.setattr(imp_repo, "reparto_contratista_vigente", lambda idc: "c1" if idc == 500 else None)
    monkeypatch.setattr(imp_repo, "total_neto_compra",
                        lambda idc: {"moneda": "Pesos", "tipoDeCambio": None, "tipoDocumento": "Nota de Crédito", "neto": 100.0})
    monkeypatch.setattr(imp_repo, "fracciones_de_corrida", lambda c: [
        {"idOrdenTrabajo": 10, "idLote": 1, "idCultivo": 5, "idCampania": 9, "idCentroCosto": None, "importe": 333.33},
        {"idOrdenTrabajo": 11, "idLote": 2, "idCultivo": 6, "idCampania": 9, "idCentroCosto": None, "importe": 666.67},
    ])
    fr = motor.evaluar_nota_relacionada(900)
    assert [f["importe"] for f in fr] == [-33.33, -66.67]
    assert round(sum(f["importe"] for f in fr), 2) == -100.00


def test_nc_sin_factura_con_reparto_no_imputa(monkeypatch):
    monkeypatch.setattr(imp_repo, "factura_de_nota", lambda idnc: None)
    assert motor.evaluar_nota_relacionada(900) == []


@pytest.fixture
def factura(monkeypatch):
    estado = {"vinculos": {10}, "escrito": [], "aprobadas": []}
    monkeypatch.setattr(dc, "_tipo", lambda idc: {"idCompra": idc, "idContacto": 467, "tipo": "Factura", "moneda": "Pesos", "tipoDeCambio": None})
    monkeypatch.setattr(dc, "es_documento_de_labor", lambda idc: True)
    monkeypatch.setattr(dc, "fetch_all", lambda sql, params=(): [{"id": i} for i in params[:-1]] if "Ordenes_Trabajo WHERE" in sql else [])
    monkeypatch.setattr(dc.imputacion_repository, "ordenes_vinculadas_a_compra", lambda idc: sorted(estado["vinculos"]))

    def escribir(stmts):
        for sql, p in stmts:
            estado["escrito"].append(sql)
            if sql.startswith("DELETE"):
                estado["vinculos"].discard(p[1])
            else:
                estado["vinculos"].add(p[0])
    monkeypatch.setattr(dc, "execute_write_transaction", escribir)
    monkeypatch.setattr(dc, "_guardar_aprobada", lambda idc, fr, u: estado["aprobadas"].append((idc, fr, u)))
    monkeypatch.setattr(dc.motor, "evaluar_contratista", lambda idc: ([{"idOrdenTrabajo": 10, "importe": 1.0}], None))
    monkeypatch.setattr(dc, "notas_relacionadas", lambda idc: [])
    monkeypatch.setattr(dc, "reparto", lambda idc, ido=None: [])
    return estado


def test_fijar_vinculos_agrega_quita_e_imputa_aprobado(factura, monkeypatch):
    monkeypatch.setattr(dc.imputacion_repository, "reparto_contratista_vigente", lambda idc: "c1")
    dc.fijar_vinculos(1, [11], "sergio")
    assert factura["vinculos"] == {11}
    assert factura["aprobadas"] and factura["aprobadas"][-1][2] == "sergio"


def test_destildar_todo_retira_la_imputacion(factura, monkeypatch):
    monkeypatch.setattr(dc.imputacion_repository, "reparto_contratista_vigente", lambda idc: "c1")
    dc.fijar_vinculos(1, [], "sergio")
    assert factura["vinculos"] == set()
    assert factura["aprobadas"][-1][1] == []  # corrida de retiro


def test_si_la_imputacion_falla_los_vinculos_vuelven(factura, monkeypatch):
    monkeypatch.setattr(dc, "recalcular", lambda idc, u: (_ for _ in ()).throw(RuntimeError("falla")))
    with pytest.raises(RuntimeError):
        dc.fijar_vinculos(1, [11], "sergio")
    assert factura["vinculos"] == {10}


def test_nc_no_se_vincula_a_ordenes(monkeypatch):
    monkeypatch.setattr(dc, "_tipo", lambda idc: {"idCompra": idc, "idContacto": 1, "tipo": "Nota de Crédito"})
    with pytest.raises(ValueError):
        dc.fijar_vinculos(1, [10], "sergio")


def test_orden_de_otro_contratista_se_rechaza(factura, monkeypatch):
    monkeypatch.setattr(dc, "fetch_all", lambda sql, params=(): [])
    with pytest.raises(ValueError):
        dc.fijar_vinculos(1, [99], "sergio")
