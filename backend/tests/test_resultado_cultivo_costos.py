"""Costo de un Cultivo/Campaña (costos.py), sin tocar la base real."""

from src.features.resultado_cultivo import costos


def test_costos_heredados_sin_destino_mapeado_devuelve_vacio(monkeypatch):
    monkeypatch.setattr(costos.mapeo, "idCultivo_a_destino", lambda idc: None)
    assert costos.costos_heredados(999, 32) == []


def test_costos_heredados_respeta_signo(monkeypatch):
    monkeypatch.setattr(costos.mapeo, "idCultivo_a_destino", lambda idc: 6)

    def fake_fetch_all(sql, params=()):
        if "vw_ResultadosCultivo_CostosBase" in sql:
            assert "ABS(c.Pesos) * c.Signo" in sql
            return [{"concepto": "Nota de crédito", "rubro": "Ajustes", "montoPesos": -100.0, "montoDolares": -1.0, "origen": "Compra", "idCompra": 1, "idDetalleCompra": 1}]
        return []

    monkeypatch.setattr(costos, "fetch_all", fake_fetch_all)
    lineas = costos.costos_heredados(3, 32)
    assert lineas[0]["montoPesos"] == -100.0



def test_maquinaria_usa_estimado_manual_y_no_duplica_lote_por_insumo(monkeypatch):
    def fake(sql, params=()):
        if "Ordenes_Trabajo_Distrib d" in sql:
            return [dict(idOrdenInsumo=i, idOrdenTrabajo=501, idProducto=100,
                         cantidadTotal=10, cantidadAsignada=10, idLote=7, superficie=20)
                    for i in [1, 2]]
        if "Ordenes_Trabajo_Maquinaria" in sql:
            return [dict(IdOrdenTrabajo=501, CostoPorHectarea=1500, TipoCambioBna=1000)]
        return []
    monkeypatch.setattr(costos, "fetch_all", fake)
    monkeypatch.setattr(costos, "calcular_stock", lambda _: {})
    lineas = costos.costo_ordenes_trabajo(3, 32)
    assert len(lineas) == 1
    assert lineas[0]["montoPesos"] == 30000
    assert lineas[0]["montoDolares"] == 30


def test_contratista_consulta_imputacion_y_excluye_facturas_duplicadas(monkeypatch):
    def fake(sql, params):
        assert params == (3, 32)
        assert "m.IdCultivo = ? AND d.IdCampaña = ?" in sql
        assert "NOT EXISTS" in sql and "b.IdCompra = d.IdCompra" in sql
        assert "Superficie" not in sql
        return [dict(concepto="Contratista", montoPesos=1000, montoDolares=10,
                     idCompra=888, idDetalleCompra=42, idOrdenTrabajo=501)]
    monkeypatch.setattr(costos, "fetch_all", fake)
    assert costos.costos_contratista(3, 32)[0]["idDetalleCompra"] == 42


def test_contratista_sin_insumos_usa_factura(monkeypatch):
    monkeypatch.setattr(costos, "fetch_all", lambda *args: [])
    factura = [dict(concepto="Contratista", montoPesos=1000)]
    monkeypatch.setattr(costos, "costos_contratista", lambda *_: factura)
    assert costos.costo_ordenes_trabajo(3, 32) == factura
