"""Recordatorio de la Tasa Vial (Municipalidad de Bolívar): meses impares, sin boleta desde el mes anterior."""

from datetime import date

from src.features.boveda import repository, router

PORTAL = {"codigoConector": None, "idContacto": 72, "idCredencial": 14,
          "url": "https://tributaria.hacienda.bolivar.gob.ar/web_tributaria/paginas/webfrmconsulta_b.aspx"}


def test_avisa_en_mes_impar_sin_boleta(monkeypatch):
    monkeypatch.setattr(repository, "hay_tasa_vial", lambda org, desde: False)
    monkeypatch.setattr(repository, "dato_credencial", lambda idc, nombre: "123")
    texto = router.recordatorio(PORTAL, date(2026, 11, 3))
    assert "vence el 15/11/2026" in texto and "cuenta N° 123" in texto
    assert "venció" in router.recordatorio(PORTAL, date(2026, 11, 20))


def test_no_avisa_en_mes_par_ni_con_boleta_ni_a_otros(monkeypatch):
    desdes = []
    monkeypatch.setattr(repository, "hay_tasa_vial", lambda org, desde: desdes.append(desde) or True)
    assert router.recordatorio(PORTAL, date(2026, 10, 27)) is None
    assert router.recordatorio(PORTAL, date(2027, 1, 5)) is None and desdes == [date(2026, 12, 1)]
    monkeypatch.setattr(repository, "hay_tasa_vial", lambda org, desde: False)
    assert router.recordatorio({**PORTAL, "url": "https://www.miallianz.com.ar/priv"}, date(2026, 11, 3)) is None
