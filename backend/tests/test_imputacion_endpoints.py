"""Tests de negocio de aprobación/recálculo del motor de imputación (017)."""

from __future__ import annotations

import pytest

from src.features.imputacion import motor, repository
from src.features.imputacion.repository import CorridaNoVigente


def test_aprobar_sin_cambios(monkeypatch):
    llamadas = []
    monkeypatch.setattr(repository, "detalle_compra_de_corrida", lambda idc: 900)
    monkeypatch.setattr(repository, "corrida_vigente", lambda idd: "corrida-1")
    monkeypatch.setattr(repository, "execute_write_transaction", lambda stmts: llamadas.extend(stmts) or [1] * len(stmts))

    repository.aprobar_corrida("corrida-1")

    assert llamadas, "no se ejecutó ningún statement"
    assert "Aprobada" in llamadas[-1][0]


def test_aprobar_con_correccion_actualiza_referencia(monkeypatch):
    llamadas = []
    monkeypatch.setattr(repository, "detalle_compra_de_corrida", lambda idc: 900)
    monkeypatch.setattr(repository, "corrida_vigente", lambda idd: "corrida-1")
    monkeypatch.setattr(repository, "execute_write_transaction", lambda stmts: llamadas.extend(stmts) or [1] * len(stmts))
    referencias_guardadas = []
    monkeypatch.setattr(
        repository,
        "actualizar_referencia",
        lambda idp, es_ganaderia, idc, idcamp: referencias_guardadas.append((idp, es_ganaderia, idc, idcamp)),
    )
    monkeypatch.setattr(
        repository,
        "info_fraccion",
        lambda idp: {"idProducto": 500, "esGanaderia": False} if idp == 5 else None,
    )

    repository.aprobar_corrida("corrida-1", correcciones=[{"idPropuesta": 5, "idCultivo": 21, "idCampania": 31}])

    assert referencias_guardadas == [(500, False, 21, 31)]


def test_aprobar_corrida_no_vigente_lanza_error(monkeypatch):
    monkeypatch.setattr(repository, "detalle_compra_de_corrida", lambda idc: 900)
    monkeypatch.setattr(repository, "corrida_vigente", lambda idd: "corrida-2")

    with pytest.raises(CorridaNoVigente):
        repository.aprobar_corrida("corrida-1")


def test_cambio_fuente_genera_corrida_nueva_sin_pisar_aprobada(monkeypatch):
    guardadas = []
    monkeypatch.setattr(motor, "calcular_propuesta_insumo", lambda idd: [{"importe": 100.0, "idCultivo": 20, "idCampania": 30}])
    monkeypatch.setattr(repository, "corrida_vigente", lambda idd: "corrida-vieja-aprobada")
    monkeypatch.setattr(
        repository,
        "guardar_corrida",
        lambda origen, idd, fracciones: guardadas.append((origen, idd, fracciones)) or "corrida-nueva",
    )
    monkeypatch.setattr(repository, "marcar_stock_sin_consumir_aprobada", lambda fs: fs)

    nueva = motor.recalcular_si_corresponde(900)

    assert nueva == "corrida-nueva"
    assert len(guardadas) == 1
    origen, idd, fracciones = guardadas[0]
    assert origen == "Insumo" and idd == 900
    assert all(f.get("estado", "Pendiente") == "Pendiente" for f in fracciones)


def test_aprobar_corrida_guarda_usuario(monkeypatch):
    llamadas = []
    monkeypatch.setattr(repository, "detalle_compra_de_corrida", lambda idc: 900)
    monkeypatch.setattr(repository, "corrida_vigente", lambda idd: "corrida-1")
    monkeypatch.setattr(repository, "execute_write_transaction", lambda stmts: llamadas.extend(stmts) or [1])

    repository.aprobar_corrida("corrida-1", usuario="sergio")

    sql, params = llamadas[-1]
    assert "UsuarioAprobacion" in sql
    assert params == ("sergio", "corrida-1")


def test_aprobar_lote_procesa_cada_corrida_independiente(monkeypatch):
    from src.features.imputacion import router
    from src.features.imputacion.repository import CorridaNoVigente
    from src.features.imputacion.schemas import AprobarLoteIn

    def fake_aprobar(id_corrida, correcciones=None, usuario=None):
        if id_corrida == "mala":
            raise CorridaNoVigente("ya no es vigente")

    monkeypatch.setattr(repository, "aprobar_corrida", fake_aprobar)

    class FakeState:
        usuario = None

    class FakeRequest:
        state = FakeState()

    import asyncio

    resultado = asyncio.run(router.aprobar_lote(AprobarLoteIn(idCorridas=["buena-1", "mala", "buena-2"]), FakeRequest()))

    assert resultado.aprobadas == 2
    assert resultado.fallidas == 1
    assert [r.ok for r in resultado.resultados] == [True, False, True]
