"""Repositorio del tamiz 050: vigencia única, rubro sin regla y alcance por corte."""

from src.features.imputacion import repository, tamiz, tamiz_repository as repo


def test_una_sola_fila_vigente_por_renglon(monkeypatch):
    enviadas = []
    monkeypatch.setattr(repo, "execute_write_transaction", lambda s: enviadas.extend(s))
    repo.guardar_clasificaciones([{"idDetalleCompra": 7, "destino": "Estructura", "idParte": None, "idCultivo": None,
                                   "idCampania": None, "origen": "Rubro", "estado": "Aprobada", "motivo": None}])
    assert enviadas[0][0].startswith("UPDATE dbo.TamizRenglones SET Vigente = 0") and enviadas[0][1] == (7,)
    assert enviadas[1][0].startswith("INSERT INTO dbo.TamizRenglones")


def test_rubro_sin_regla_da_el_motivo():
    r = {"idDetalleCompra": 1, "idRubro": 123456, "producto": "x", "idFormulado": None,
         "idCultivo": None, "idCampania": None, "cantidad": 1, "precio": 1}
    res = tamiz.clasificar_renglon(r, {}, [], {"particular": None, "tieneInsumos": False})
    assert res["estado"] == "Pendiente" and res["motivo"] == "El rubro no tiene regla de imputación"


def test_alcance_por_corte_de_iddeuda(monkeypatch):
    monkeypatch.setattr(repo, "config", lambda: {"idDeudaCorte": 1000, "activo": False})
    monkeypatch.setattr(repo, "fetch_one", lambda *a: None)
    assert repo.compra_en_alcance(1001) is True
    assert repo.compra_en_alcance(1000) is False


def test_activado_los_renglones_recientes_estan_en_alcance_en_wc():
    # Lectura real: activado el 16/11/2026 (corte = IdDeuda máximo de ese día, alcance = compras desde el 12/05/2025).
    ids = [f["IdDetalleCompra"] for f in repository.fetch_all(
        "SELECT TOP 5 d.IdDetalleCompra FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra "
        "WHERE c.Fecha >= '2025-05-12' ORDER BY d.IdDetalleCompra DESC")]
    assert repository.ids_en_alcance(ids) == set(ids)
