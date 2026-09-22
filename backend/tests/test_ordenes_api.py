"""Tests de negocio de Órdenes de Trabajo, sin tocar la base real (monkeypatch),
igual que test_remitos_api.py."""

from datetime import date

import pytest

from src.features.ordenes import repository
from src.features.ordenes.repository import RequiereConfirmacion


def _orden(distribuciones):
    return {
        "fecha": date(2026, 9, 22),
        "idTipoLabor": 1,
        "idContratistaContacto": None,
        "renglones": [{"idProducto": 100, "unidad": "LTS", "distribuciones": distribuciones}],
        "idRubro": None,
        "idCentroCostos": None,
        "observaciones": None,
    }


def _distribuciones():
    return [
        {"idLote": 1, "idCultivo": 1, "idCampania": 1, "dosisHa": 2, "superficie": 10, "aplicar": True},
        {"idLote": 2, "idCultivo": 2, "idCampania": 1, "dosisHa": 3, "superficie": 5, "aplicar": True},
    ]  # total = 20 + 15 = 35


def test_crear_orden_requiere_confirmacion_si_supera_el_stock(monkeypatch):
    monkeypatch.setattr(repository, "_existencia", lambda pid: 10.0)  # hay 10, la orden retira 35
    with pytest.raises(RequiereConfirmacion) as exc:
        repository.crear_orden(_orden(_distribuciones()), confirmar=False)
    assert "quedaría negativo" in exc.value.mensajes[0]


def test_crear_orden_confirmada_inserta_cabecera_renglon_distribucion_y_formulario(monkeypatch):
    monkeypatch.setattr(repository, "_existencia", lambda pid: 10.0)
    statements_ejecutados = []

    def fake_execute_write_transaction(statements):
        statements_ejecutados.extend(statements)
        # Simula los ids devueltos por cada OUTPUT INSERTED en orden:
        # [idOrden, idOrdenInsumo, idFormularioRetiro] (2 distribuciones no devuelven id)
        resultados = []
        idx_insumo = None
        for i, s in enumerate(statements):
            sql = s[0] if not callable(s) else s(resultados)[0]
            if "Ordenes_Trabajo (" in sql:
                resultados.append(501)
            elif "Ordenes_Trabajo_Insumos (" in sql:
                idx_insumo = i
                resultados.append(9001)
            elif "Ordenes_Trabajo_Distrib (" in sql:
                resultados.append(1)
            elif "Formularios_Retiro (" in sql:
                resultados.append(777)
        return resultados

    monkeypatch.setattr(repository, "execute_write_transaction", fake_execute_write_transaction)
    resultado = repository.crear_orden(_orden(_distribuciones()), confirmar=True)
    assert resultado["idOrden"] == 501
    assert resultado["idFormularioRetiro"] == 777
    assert len(statements_ejecutados) == 1 + 1 + 2 + 1  # cabecera + renglón + 2 distribuciones + formulario


def test_crear_orden_sin_lotes_aplicados_falla_validacion():
    datos = _orden([{"idLote": 1, "idCultivo": 1, "idCampania": 1, "dosisHa": 2, "superficie": 10, "aplicar": False}])
    with pytest.raises(ValueError):
        repository.crear_orden(datos, confirmar=True)


def test_crear_orden_dosis_o_superficie_invalida_falla_validacion():
    datos = _orden([{"idLote": 1, "idCultivo": 1, "idCampania": 1, "dosisHa": 0, "superficie": 10, "aplicar": True}])
    with pytest.raises(ValueError):
        repository.crear_orden(datos, confirmar=True)


def test_anular_orden_marca_estado_anulada_y_stock_queda_liberado(monkeypatch):
    """SC-004: anular una orden Planificada devuelve las capas FIFO consumidas.
    `calcular_stock` (stock_datos.py) excluye las órdenes con Estado='Anulada' de
    sus salidas, así que verificar que el UPDATE pone Estado='Anulada' es
    verificar que el stock se libera, sin duplicar el cálculo FIFO acá."""
    monkeypatch.setattr(
        repository,
        "obtener_orden",
        lambda id_orden: {"idOrden": id_orden, "estado": "Planificada", "insumos": [{"idProducto": 100, "cantidadTotal": 35.0, "devoluciones": []}]},
    )
    statements_ejecutados = []
    monkeypatch.setattr(repository, "execute_write_transaction", lambda stmts: statements_ejecutados.extend(stmts) or [1])

    repository.anular_orden(501, "Se canceló la labor por lluvia")

    sql, params = statements_ejecutados[0]
    assert "Estado = 'Anulada'" in sql
    assert params == ("Se canceló la labor por lluvia", 501)


def test_anular_orden_con_devolucion_previa_anula_tambien_el_ajuste_de_devolucion(monkeypatch):
    """Bug encontrado en T066: si la orden ya tenía una devolución parcial (que
    reingresó stock como un `Stock_Ajustes` aparte, no atado al estado de la
    orden), anular sin tocar ese ajuste duplicaba el reingreso — el stock quedaba
    más alto que antes de crear la orden. Anular debe anular también el ajuste."""
    monkeypatch.setattr(
        repository,
        "obtener_orden",
        lambda id_orden: {"idOrden": id_orden, "estado": "Planificada", "insumos": [{"idProducto": 100, "cantidadTotal": 35.0, "devoluciones": [{"idDevolucion": 1, "cantidad": 5.0}]}]},
    )
    statements_ejecutados = []
    monkeypatch.setattr(repository, "execute_write_transaction", lambda stmts: statements_ejecutados.extend(stmts) or [1, 1])

    repository.anular_orden(501, "Se canceló la labor por lluvia")

    assert len(statements_ejecutados) == 2
    sql, params = statements_ejecutados[1]
    assert "Stock_Ajustes" in sql and "Anulado = 1" in sql
    assert params[1] == "Devolución de orden de trabajo 501"


def test_anular_orden_sin_motivo_falla():
    with pytest.raises(ValueError):
        repository.anular_orden(501, "   ")


def test_anular_orden_ya_anulada_falla(monkeypatch):
    monkeypatch.setattr(repository, "obtener_orden", lambda id_orden: {"estado": "Anulada"})
    with pytest.raises(ValueError):
        repository.anular_orden(501, "motivo")


# ------------------------------------------------------------------ Historia 2: devoluciones (T031)

def test_devolucion_valida_reingresa_stock(monkeypatch):
    monkeypatch.setattr(
        repository, "_renglon_insumo", lambda idi: {"idOrdenInsumo": idi, "idOrdenTrabajo": 501, "idProducto": 100, "cantidadTotal": 35.0, "devuelto": 0.0}
    )
    statements = []
    monkeypatch.setattr(repository, "execute_write_transaction", lambda stmts: statements.extend(stmts) or [1, 1])
    idx = repository.registrar_devolucion(9001, {"fecha": __import__("datetime").date(2026, 9, 22), "cantidad": 5, "observaciones": None})
    assert idx == 1
    assert len(statements) == 2
    ajuste_sql, ajuste_params = statements[1] if not callable(statements[1]) else statements[1]([1])
    assert "Stock_Ajustes" in ajuste_sql
    assert ajuste_params[1] == 100 and ajuste_params[2] == 5


def test_devolucion_mayor_a_lo_retirado_se_rechaza(monkeypatch):
    monkeypatch.setattr(
        repository, "_renglon_insumo", lambda idi: {"idOrdenInsumo": idi, "idOrdenTrabajo": 501, "idProducto": 100, "cantidadTotal": 35.0, "devuelto": 30.0}
    )
    with pytest.raises(ValueError):
        repository.registrar_devolucion(9001, {"fecha": __import__("datetime").date(2026, 9, 22), "cantidad": 10, "observaciones": None})


# ------------------------------------------------------------------ Historia 3: maquinaria (T037)

def test_costo_maquinaria_se_prorratea_por_superficie():
    distribuciones = [
        {"idLote": 1, "superficie": 10, "aplicar": True},
        {"idLote": 2, "superficie": 5, "aplicar": True},
    ]
    from src.features.ordenes import costeo

    r = costeo.costo_maquinaria(100.0, distribuciones)
    assert r["montoTotal"] == 1500.0  # 100 * 15 ha
    assert r["porLote"] == {1: 1000.0, 2: 500.0}


# ------------------------------------------------------------------ Historia 4: contratista (T043)

def test_costo_contratista_se_dolariza_con_tc_de_la_factura(monkeypatch):
    from src.features.ordenes import costeo

    monkeypatch.setattr(costeo, "fetch_one", lambda *a, **k: {"moneda": "Dolares", "tipoDeCambio": 1000.0, "neto": 50.0})
    r = costeo.costo_contratista(1, [{"idLote": 1, "superficie": 10, "aplicar": True}])
    assert r["montoPesos"] == 50000.0
    assert r["montoDolares"] == 50.0
    assert r["porLote"] == {1: 50000.0}


# ------------------------------------------------------------------ Historia 6: resultado por cultivo (T050)

def test_resultado_cultivo_no_exige_fecha_de_cierre(monkeypatch):
    from src.features.ordenes import resultado

    monkeypatch.setattr(resultado, "_filas_insumos", lambda *a: [])
    # Sin filas (campaña ya cosechada sin nuevas órdenes) no rompe, y no hay
    # ningún parámetro de "cerrar"/"reabrir" en la firma de la función.
    assert resultado.costo_por_cultivo_campania(id_campania=1) == []
    import inspect

    firma = inspect.signature(resultado.costo_por_cultivo_campania)
    assert "cerrado" not in firma.parameters and "reabrir" not in firma.parameters


# ------------------------------------------------------------------ Historia 5: órdenes sin cultivo (T056)

def test_orden_sin_cultivo_persiste_rubro_y_centro_costos(monkeypatch):
    monkeypatch.setattr(repository, "_existencia", lambda pid: 100.0)
    statements = []

    def fake_execute(stmts):
        statements.extend(stmts)
        resultados = []
        for s in stmts:
            sql = s[0] if not callable(s) else s(resultados)[0]
            if "Ordenes_Trabajo (" in sql:
                resultados.append(900)
            elif "Ordenes_Trabajo_Insumos (" in sql:
                resultados.append(1)
            elif "Ordenes_Trabajo_Distrib (" in sql:
                resultados.append(1)
            elif "Formularios_Retiro (" in sql:
                resultados.append(1)
        return resultados

    monkeypatch.setattr(repository, "execute_write_transaction", fake_execute)
    datos = _orden(_distribuciones())
    datos["idRubro"] = 7
    datos["idCentroCostos"] = 3
    repository.crear_orden(datos, confirmar=True)
    cab_sql, cab_params = statements[0]([])
    assert "IdRubro" in cab_sql and 7 in cab_params and 3 in cab_params
