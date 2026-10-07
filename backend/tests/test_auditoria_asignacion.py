"""Asignar contacto a movimientos del banco sin contacto — 035 (T053). Validaciones puras y lectura; no escriben."""

import pytest

from src.features.auditoria_cuentas import asignacion as a


def test_validar_pedido_agrupa_por_medio():
    items = [{"medio": "bna", "idMovimiento": 5}, {"medio": "galicia", "idMovimiento": 9}, {"medio": "bna", "idMovimiento": 5}, {"medio": "bna", "idMovimiento": 2}]
    assert a.validar_pedido(items, 10, "Es de Fulano") == {"bna": [2, 5], "galicia": [9]}


@pytest.mark.parametrize("items,contacto,motivo,codigo", [
    ([], 1, "x", 422), ([{"medio": "bna", "idMovimiento": 1}], 1, " ", 422), ([{"medio": "bna", "idMovimiento": 1}], 0, "x", 422),
    ([{"medio": "efectivo", "idMovimiento": 1}], 1, "x", 422), ([{"medio": "bna", "idMovimiento": i} for i in range(a.MAX_MOVIMIENTOS + 1)], 1, "x", 422)])
def test_validar_pedido_rechaza(items, contacto, motivo, codigo):
    with pytest.raises(a.AsignacionError) as e:
        a.validar_pedido(items, contacto, motivo)
    assert e.value.codigo == codigo


def test_movimientos_sin_contacto_en_la_base_real_son_de_cualquier_monto_y_sin_regla():
    todos = a.movimientos_sin_contacto(limite=1000)
    assert todos and any(abs(m["importe"]) < 100_000 for m in todos)
    assert not any("LEY 25413" in (m["concepto"] or "").upper() for m in todos)
    uno = a.movimientos_sin_contacto(a.detectores.normalizar_concepto(todos[0]["concepto"]))
    assert uno and all(a.detectores.normalizar_concepto(m["concepto"]) == a.detectores.normalizar_concepto(todos[0]["concepto"]) for m in uno)
