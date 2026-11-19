from src.features.tesoreria import auto_conciliacion as ac


def test_motivo_y_detalle_validos_para_sin_documento():
    from src.features.conciliacion_tesoreria.repository import _stmt_estado

    sql, params = _stmt_estado("bna", 1, "SinDocumento", "Impuesto", ac.DETALLE, None, ac.USUARIO)
    assert "ConciliacionesTesoreriaEstado" in sql and params[3] == "Impuesto"
    assert set(ac._MEDIOS) == {"bna", "galicia"}
