"""Tests de `buscar_archivo_recibo` — matching de recibos de sueldo por
CamelCase contra nombres de archivo reales muy inconsistentes entre años
(ver docstring en repository.py). Usa un directorio temporal, no lee el
disco real ni la base de datos.
"""

from __future__ import annotations

from datetime import date

from src.features.remuneraciones import repository


def _crear_recibo(base, anio: int, nombre_archivo: str) -> None:
    carpeta = base / str(anio)
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / nombre_archivo).write_bytes(b"%PDF-1.4")


def test_matchea_nombre_con_espacios(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "CARPETA_RECIBOS", str(tmp_path))
    _crear_recibo(tmp_path, 2026, "2026 01 Sergio Giamberardini.pdf")

    resultado = repository.buscar_archivo_recibo(date(2026, 1, 15), "Sergio Giamberardini")

    assert resultado is not None
    assert resultado.name == "2026 01 Sergio Giamberardini.pdf"


def test_matchea_nombre_pegado_con_guion_bajo(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "CARPETA_RECIBOS", str(tmp_path))
    _crear_recibo(tmp_path, 2025, "2025 11_MarceloSierra.pdf")

    resultado = repository.buscar_archivo_recibo(date(2025, 11, 30), "Marcelo Sierra")

    assert resultado is not None
    assert resultado.name == "2025 11_MarceloSierra.pdf"


def test_matchea_pese_a_nombre_intermedio_faltante_en_el_archivo(tmp_path, monkeypatch):
    """"Armando Mori" en el archivo vs "Armando Oscar Mori" en Contactos —
    caso real confirmado contra el disco 2026-09-30."""
    monkeypatch.setattr(repository, "CARPETA_RECIBOS", str(tmp_path))
    _crear_recibo(tmp_path, 2024, "2024 01_ArmandoMori.pdf")

    resultado = repository.buscar_archivo_recibo(date(2024, 1, 31), "Armando Oscar Mori")

    assert resultado is not None
    assert resultado.name == "2024 01_ArmandoMori.pdf"


def test_no_matchea_archivo_de_otro_empleado_aunque_comparta_mes(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "CARPETA_RECIBOS", str(tmp_path))
    _crear_recibo(tmp_path, 2024, "2024 01_IrmaMiranda.pdf")

    resultado = repository.buscar_archivo_recibo(date(2024, 1, 31), "Armando Oscar Mori")

    assert resultado is None


def test_devuelve_none_si_no_hay_archivo(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "CARPETA_RECIBOS", str(tmp_path))

    resultado = repository.buscar_archivo_recibo(date(2024, 1, 31), "Sergio Giamberardini")

    assert resultado is None


def test_devuelve_none_si_hay_mas_de_un_candidato_ambiguo(tmp_path, monkeypatch):
    """Nunca elige uno al azar (mismo criterio que
    tesoreria/matching.py::_resolver_contacto_por_texto)."""
    monkeypatch.setattr(repository, "CARPETA_RECIBOS", str(tmp_path))
    _crear_recibo(tmp_path, 2024, "2024 01_Marcelo Sierra.pdf")
    _crear_recibo(tmp_path, 2024, "2024 01_Marcelo Sierra (copia).pdf")

    resultado = repository.buscar_archivo_recibo(date(2024, 1, 31), "Marcelo Sierra")

    assert resultado is None
