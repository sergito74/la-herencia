"""034 (T010): el contacto de cada tarjeta se lee de la tabla explícita, con la regla de 008 como respaldo."""
import pytest

from src.features.tarjetas import repository as r


def _preparar(monkeypatch, *, tabla_existe, fila_tabla, por_nombre, tarjeta=True):
    monkeypatch.setattr(r, "get_tarjeta", lambda _: {"nombre": "AgroNacion"} if tarjeta else None)

    def fetch_one(sql, params=()):
        if "OBJECT_ID" in sql:
            return {"existe": 123 if tabla_existe else None}
        if "dbo.TarjetasContacto" in sql:
            return fila_tabla
        if "dbo.Contactos" in sql:
            return por_nombre
        raise AssertionError(sql)

    monkeypatch.setattr(r, "fetch_one", fetch_one)


def test_usa_la_tabla_explicita_cuando_hay_fila(monkeypatch):
    _preparar(monkeypatch, tabla_existe=True, fila_tabla={"IdContacto": 373}, por_nombre={"IdContacto": 999})
    assert r.get_id_contacto_tarjeta(1) == 373


def test_sin_fila_en_la_tabla_cae_a_la_regla_por_nombre(monkeypatch):
    _preparar(monkeypatch, tabla_existe=True, fila_tabla=None, por_nombre={"IdContacto": 373})
    assert r.get_id_contacto_tarjeta(1) == 373


def test_sin_la_tabla_usa_la_regla_por_nombre(monkeypatch):
    _preparar(monkeypatch, tabla_existe=False, fila_tabla=None, por_nombre={"IdContacto": 373})
    assert r.get_id_contacto_tarjeta(1) == 373


def test_tarjeta_sin_contacto_devuelve_none(monkeypatch):
    _preparar(monkeypatch, tabla_existe=True, fila_tabla=None, por_nombre=None)
    assert r.get_id_contacto_tarjeta(1) is None


def test_tarjeta_inexistente_devuelve_none(monkeypatch):
    _preparar(monkeypatch, tabla_existe=True, fila_tabla={"IdContacto": 373}, por_nombre=None, tarjeta=False)
    assert r.get_id_contacto_tarjeta(99) is None
