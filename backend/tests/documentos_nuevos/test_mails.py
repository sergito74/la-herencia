"""Marca de mails (043, T018): solo lo posterior a la marca; primera corrida sin barrer historia."""

from __future__ import annotations

from datetime import datetime

from src.features.documentos_nuevos import mails


class _Adjuntos:
    def __init__(self, n):
        self.Count = n

    def Item(self, i):
        raise AssertionError("no debería abrir adjuntos")


class _Mail:
    def __init__(self, recibido, adjuntos=0):
        self.ReceivedTime = recibido
        self.Attachments = _Adjuntos(adjuntos)
        self.EntryID, self.Subject, self.SenderName = f"id-{recibido:%H%M}", "asunto", "x"


class _Items(list):
    def Sort(self, *a):
        self.sort(key=lambda m: m.ReceivedTime, reverse=True)


class _Store:
    DisplayName = "Outlook"

    def __init__(self, mails_):
        self._items = _Items(mails_)

    def GetDefaultFolder(self, n):
        return type("F", (), {"Items": self._items})()


def test_primera_corrida_fija_la_marca_sin_leer():
    ahora = datetime(2026, 10, 28, 7, 0)
    a = mails._leer_almacen(_Store([_Mail(datetime(2026, 10, 1))]), lambda n: None, ahora)
    assert a.mails == [] and a.ultimo == ahora


def test_solo_posteriores_a_la_marca():
    marca = datetime(2026, 10, 28, 7, 0)
    store = _Store([_Mail(datetime(2026, 10, 28, 6, 0)), _Mail(datetime(2026, 10, 28, 9, 0)),
                    _Mail(datetime(2026, 10, 28, 11, 30))])
    a = mails._leer_almacen(store, lambda n: marca, datetime(2026, 10, 28, 14, 0))
    assert a.ultimo == datetime(2026, 10, 28, 11, 30)
    assert a.mails == []  # sin adjuntos no se entregan, pero la marca avanza igual


def test_sin_mails_nuevos_la_marca_no_retrocede():
    marca = datetime(2026, 10, 28, 7, 0)
    a = mails._leer_almacen(_Store([_Mail(datetime(2026, 10, 27))]), lambda n: marca, datetime(2026, 10, 28, 14))
    assert a.ultimo == marca


def test_con_tope_la_marca_queda_en_el_ultimo_procesado(monkeypatch):
    monkeypatch.setattr(mails, "MAXIMO_POR_ALMACEN", 2)
    marca = datetime(2026, 10, 28, 7, 0)
    store = _Store([_Mail(datetime(2026, 10, 28, h, 0)) for h in (8, 9, 10, 11)])
    a = mails._leer_almacen(store, lambda n: marca, datetime(2026, 10, 28, 14))
    assert a.ultimo == datetime(2026, 10, 28, 9, 0)  # 10 y 11 quedan para la próxima corrida
