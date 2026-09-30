"""Tests de la lógica de alta de liquidación de remuneraciones (028) —
fórmula de importe neto, chequeo de duplicado, alta y nombrado/guardado
de recibo. Pura lógica y `monkeypatch` sobre `src.db.connection` /
`repository.CARPETA_RECIBOS` — nunca toca `WC` real ni el disco real.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.features.remuneraciones import repository
from src.features.remuneraciones.schemas import NuevaLiquidacionRequest


def test_calcular_importe_neto_resta_descuentos():
    conceptos = {
        "[Sueldo basico]": 85096.38,
        "Jubilacion": 18631.02,
        "[Obra Social]": 5081.19,
        "[Aporte Sindical]": 3471.43,
    }

    assert repository.calcular_importe_neto(conceptos) == pytest.approx(57912.74, abs=0.01)


def test_calcular_importe_neto_todo_en_cero():
    assert repository.calcular_importe_neto({}) == 0


def test_existe_liquidacion_periodo_encuentra_mismo_texto_exacto(monkeypatch):
    def fake_fetch_one(sql, params):
        assert params == (46, "Septiembre 2026")
        return {"IdSalario": 1829633233}

    monkeypatch.setattr(repository, "fetch_one", fake_fetch_one)

    assert repository.existe_liquidacion_periodo(46, "Septiembre 2026") == 1829633233


def test_existe_liquidacion_periodo_no_normaliza_mes_y_anio(monkeypatch):
    """research.md §3: "Noviembre 2025" y "30/11/2025" son textos
    distintos aunque describan el mismo mes calendario — no cuentan como
    el mismo período."""

    def fake_fetch_one(sql, params):
        assert params == (46, "30/11/2025")
        return None

    monkeypatch.setattr(repository, "fetch_one", fake_fetch_one)

    assert repository.existe_liquidacion_periodo(46, "30/11/2025") is None


def test_crear_liquidacion_inserta_positivo_y_devuelve_neto(monkeypatch):
    calls = {}

    def fake_execute_insert_returning_id(sql, params):
        calls["sql"] = sql
        calls["params"] = params
        return 1829633234

    monkeypatch.setattr(repository, "execute_insert_returning_id", fake_execute_insert_returning_id)

    request = NuevaLiquidacionRequest(
        idContacto=46,
        fechaPago=date(2026, 9, 30),
        periodoLiquidado="Septiembre 2026",
        sueldoBasico=85096.38,
        jubilacion=18631.02,
        obraSocial=5081.19,
        aporteSindical=3471.43,
    )

    resultado = repository.crear_liquidacion(request)

    assert resultado == {"idSalario": 1829633234, "importeNeto": pytest.approx(57912.74, abs=0.01)}
    assert "OUTPUT INSERTED.IdSalario" in calls["sql"]
    # Los conceptos van tal cual al INSERT — siempre positivos, sin restar acá.
    assert 85096.38 in calls["params"]
    assert 18631.02 in calls["params"]


def test_nombre_archivo_recibo_formato_estandarizado():
    assert (
        repository.nombre_archivo_recibo(date(2026, 9, 30), "Armando Oscar Mori")
        == "2026 09 Armando Oscar Mori.pdf"
    )


def test_guardar_recibo_escribe_archivo_y_columna(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "CARPETA_RECIBOS", str(tmp_path))

    calls = {}

    def fake_execute_write(sql, params):
        calls["sql"] = sql
        calls["params"] = params
        return 1

    monkeypatch.setattr(repository, "execute_write", fake_execute_write)

    ruta = repository.guardar_recibo(1829633233, date(2026, 9, 30), "Armando Oscar Mori", b"%PDF-1.4 contenido")

    assert ruta == "Personal\\Recibos\\2026\\2026 09 Armando Oscar Mori.pdf"
    archivo = tmp_path / "2026" / "2026 09 Armando Oscar Mori.pdf"
    assert archivo.read_bytes() == b"%PDF-1.4 contenido"
    assert calls["params"] == (ruta, 1829633233)


def test_guardar_recibo_rechaza_archivo_que_no_es_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "CARPETA_RECIBOS", str(tmp_path))

    with pytest.raises(ValueError):
        repository.guardar_recibo(1829633233, date(2026, 9, 30), "Armando Oscar Mori", b"no es un pdf")
