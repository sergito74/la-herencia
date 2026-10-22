"""Regla histórica 036: antes de 16/03/2020 US$; luego mitad US$/mitad kg."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from src.db.connection import fetch_one

INICIO_NOVILLO = date(2020, 3, 16)


def proporciones(fecha):
    return (0.0, 1.0) if fecha < INICIO_NOVILLO else (0.5, 0.5)


def calcular(importe, fecha, dolar, novillo=None):
    importe, dolar = Decimal(str(importe)), Decimal(str(dolar))
    if dolar <= 0 or (fecha >= INICIO_NOVILLO and (novillo is None or Decimal(str(novillo)) <= 0)):
        raise ValueError("Falta cotización válida para valuar la operación.")
    parte_kg, parte_usd = proporciones(fecha)
    usd = importe * Decimal(str(parte_usd)) / dolar
    kg = importe * Decimal(str(parte_kg)) / Decimal(str(novillo)) if parte_kg else Decimal(0)
    return {
        "importeUSD": usd.quantize(Decimal(".0001"), rounding=ROUND_HALF_UP),
        "importeKgCarne": kg.quantize(Decimal(".001"), rounding=ROUND_HALF_UP),
    }


def a_fecha(importe, fecha):
    dol = fetch_one(
        "SELECT TOP 1 Fecha fecha,Prom_billete valor FROM dbo.[Dolar BNA] "
        "WHERE Fecha<=? AND Prom_billete>0 ORDER BY Fecha DESC",
        (fecha,),
    )
    nov = fetch_one(
        "SELECT TOP 1 Fecha fecha,Indice valor FROM dbo.IndiceNovillo "
        "WHERE Fecha<=? AND Indice>0 ORDER BY Fecha DESC",
        (fecha,),
    )
    if not dol:
        raise ValueError("No hay dólar BNA disponible a la fecha.")
    result = calcular(importe, fecha, dol["valor"], nov["valor"] if nov else None)
    return {
        **result,
        "dolar": dol,
        "novillo": nov,
        "fuenteDolar": "Dolar BNA.Prom_billete",
        "fuenteNovillo": "IndiceNovillo.Indice",
    }
