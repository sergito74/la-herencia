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


def test_sin_corte_nada_esta_en_alcance_en_wc():
    # Lectura real: hoy ImputacionConfig.IdDeudaCorte está vacío y ImputacionAlcance sin filas.
    ids = [f["IdDetalleCompra"] for f in repository.fetch_all("SELECT TOP 5 IdDetalleCompra FROM dbo.Det_Compras ORDER BY IdDetalleCompra DESC")]
    assert repository.ids_en_alcance(ids) == set()
