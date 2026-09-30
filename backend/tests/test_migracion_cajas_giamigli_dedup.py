"""Tests de la regla de deduplicación fecha+proveedor/contacto+importe
(027-migracion-cajas-giamigli, spec Clarifications / research.md §3).
Todos con `monkeypatch` sobre `fetch_one` — nunca tocan `WC` real."""

from __future__ import annotations

from datetime import date

from scripts.migracion_cajas_giamigli import dedup


def test_ya_existe_movimiento_socio_coincidencia_exacta(monkeypatch):
    monkeypatch.setattr(dedup, "fetch_one", lambda sql, params: {"x": 1})
    assert dedup.ya_existe_movimiento_socio(2, date(2025, 5, 12), 48841.02) is True


def test_ya_existe_movimiento_socio_sin_coincidencia(monkeypatch):
    monkeypatch.setattr(dedup, "fetch_one", lambda sql, params: None)
    assert dedup.ya_existe_movimiento_socio(2, date(2025, 5, 12), 48841.02) is False


def test_resolver_contacto_por_nombre_encontrado(monkeypatch):
    monkeypatch.setattr(dedup, "fetch_one", lambda sql, params: {"id": 419})
    assert dedup.resolver_contacto_por_nombre("El Luchador") == 419


def test_resolver_contacto_por_nombre_vacio_no_consulta(monkeypatch):
    llamado = []
    monkeypatch.setattr(dedup, "fetch_one", lambda sql, params: llamado.append(1) or {"id": 1})
    assert dedup.resolver_contacto_por_nombre(None) is None
    assert dedup.resolver_contacto_por_nombre("   ") is None
    assert llamado == []


def test_ya_existe_pago_efectivo_usa_valor_absoluto(monkeypatch):
    capturado = {}

    def fake_fetch_one(sql, params):
        capturado["params"] = params
        return {"x": 1}

    monkeypatch.setattr(dedup, "fetch_one", fake_fetch_one)
    assert dedup.ya_existe_pago_efectivo(419, date(2026, 4, 2), -83548.50) is True
    assert capturado["params"][2] == 83548.50


def test_ya_existe_movimiento_caja_idempotencia(monkeypatch):
    monkeypatch.setattr(dedup, "fetch_one", lambda sql, params: {"x": 1})
    assert dedup.ya_existe_movimiento_caja("GiamigliSA", date(2011, 2, 17), -1214.19, "AFIP") is True


def test_decidir_accion_proveedor_resuelve_y_coincide_es_duplicado(monkeypatch):
    from scripts.migracion_cajas_giamigli.lector_excel import FilaCaja
    from scripts.migracion_cajas_giamigli import migrar_caja_giamigli_sa as m

    monkeypatch.setattr(m.dedup, "resolver_contacto_por_nombre", lambda nombre: 419)
    monkeypatch.setattr(m.dedup, "ya_existe_pago_efectivo", lambda id_contacto, fecha, importe: True)
    fila = FilaCaja(numero_fila=10, fecha=date(2026, 4, 2), concepto="El Luchador", detalle=None, importe=-83548.50)
    accion, id_contacto = m.decidir_accion(fila)
    assert accion == "duplicado"
    assert id_contacto == 419


def test_decidir_accion_proveedor_no_resuelve_es_nuevo(monkeypatch):
    from scripts.migracion_cajas_giamigli.lector_excel import FilaCaja
    from scripts.migracion_cajas_giamigli import migrar_caja_giamigli_sa as m

    monkeypatch.setattr(m.dedup, "resolver_contacto_por_nombre", lambda nombre: None)
    fila = FilaCaja(numero_fila=11, fecha=date(2011, 2, 17), concepto="AFIP", detalle=None, importe=-1214.19)
    accion, id_contacto = m.decidir_accion(fila)
    assert accion == "nuevo"
    assert id_contacto is None


def test_decidir_accion_proveedor_resuelve_pero_no_coincide_es_nuevo(monkeypatch):
    from scripts.migracion_cajas_giamigli.lector_excel import FilaCaja
    from scripts.migracion_cajas_giamigli import migrar_caja_giamigli_sa as m

    monkeypatch.setattr(m.dedup, "resolver_contacto_por_nombre", lambda nombre: 419)
    monkeypatch.setattr(m.dedup, "ya_existe_pago_efectivo", lambda id_contacto, fecha, importe: False)
    fila = FilaCaja(numero_fila=12, fecha=date(2020, 1, 1), concepto="El Luchador", detalle=None, importe=-500.0)
    accion, id_contacto = m.decidir_accion(fila)
    assert accion == "nuevo"
    assert id_contacto == 419
