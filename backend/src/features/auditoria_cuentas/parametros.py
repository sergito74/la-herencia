"""Parámetros de la auditoría (plazo, umbral, anticipo) guardados en `dbo.AuditoriaParametros` — 035 (research D8)."""

from __future__ import annotations

from src.db.connection import execute_write, fetch_all

POR_DEFECTO = {"plazoMaximoMeses": 24, "umbralPesos": 300, "anticipoDias": 60}


def obtener() -> dict[str, int]:
    valores = dict(POR_DEFECTO)
    try:
        for f in fetch_all("SELECT Clave, Valor FROM dbo.AuditoriaParametros", ()):
            if f["Clave"] in valores:
                valores[f["Clave"]] = int(f["Valor"])
    except Exception:
        pass  # sin tabla todavía: rigen los valores iniciales
    return valores


def guardar(cambios: dict[str, int], usuario: str) -> dict[str, int]:
    for clave, valor in cambios.items():
        if clave not in POR_DEFECTO:
            raise ValueError(f"Parámetro desconocido: {clave}")
        if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
            raise ValueError(f"{clave} debe ser un entero positivo")
    for clave, valor in cambios.items():
        execute_write(
            "UPDATE dbo.AuditoriaParametros SET Valor = ?, Usuario = ?, Fecha = SYSDATETIME() WHERE Clave = ?",
            (str(valor), usuario, clave),
        )
    return obtener()
