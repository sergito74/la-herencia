from datetime import date
import pytest
from src.features.tarjetas_resumenes import repository as r

@pytest.fixture
def edicion(monkeypatch):
    linea = {"idLineaConsumo": 7, "fechaCompra": date(2026, 9, 1), "detalle": "Consumo", "importe": 100,
             "idContacto": 20, "comprasVinculadas": [{"idVinculo": 8}], "estadoLinea": None}
    monkeypatch.setattr(r, "validar_resumen", lambda *args: [])
    monkeypatch.setattr(r, "get_lineas", lambda _: [linea])
    monkeypatch.setattr(r, "get_resumen_detalle", lambda _: {"idTarjeta": 1})
    monkeypatch.setattr(r, "get_pagos", lambda _: [])
    statements = []
    monkeypatch.setattr(r, "execute_write_transaction", lambda values: statements.extend(values))
    cabecera = {"idTarjeta": 1, "codigo": "A", "fechaCierre": date(2026,9,20), "fechaVencimiento": date(2026,10,1)}
    return linea, cabecera, statements

def test_edicion_conserva_linea_y_conciliacion(edicion):
    linea, cab, statements = edicion
    r.update_resumen.__wrapped__(1, cab, [{**linea, "detalle": "Detalle corregido"}])
    sql = " ".join(s[0] for s in statements)
    assert "UPDATE dbo.Tarjetas_Resumenes_Lineas" in sql
    assert "DELETE" not in sql and "INSERT" not in sql
    assert statements[-1][1][-2:] == (1, 7)

@pytest.mark.parametrize("cambio", ["importe", "eliminar", "ajena", "duplicada"])
def test_edicion_rechaza_perdida_de_conciliacion_o_ids_invalidos(edicion, cambio):
    linea, cab, statements = edicion
    nuevas = {"importe": [{**linea, "importe": 101}], "eliminar": [],
              "ajena": [{**linea, "idLineaConsumo": 99}], "duplicada": [linea, linea]}[cambio]
    with pytest.raises(ValueError):
        r.update_resumen.__wrapped__(1, cab, nuevas)
    assert statements == []

def test_puede_agregar_y_quitar_lineas_no_conciliadas(edicion):
    linea, cab, statements = edicion
    linea["comprasVinculadas"] = []
    nueva = {**linea, "idLineaConsumo": None}
    r.update_resumen.__wrapped__(1, cab, [nueva])
    assert any("DELETE FROM dbo.Tarjetas_Resumenes_Lineas" in s[0] for s in statements)
    assert any("INSERT INTO dbo.Tarjetas_Resumenes_Lineas" in s[0] for s in statements)
