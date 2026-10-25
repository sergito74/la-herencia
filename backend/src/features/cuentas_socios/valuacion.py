"""036, Sergio 25/10/2026: mitad US$/mitad kg también antes de 2020.

La serie de novillo continúa INML (Liniers) con INMAG. Billetes USD y
Mutuo2018 conservan su tratamiento específico fuera de esta fórmula.
"""

from decimal import Decimal, ROUND_HALF_UP

from src.db.connection import fetch_one

def proporciones(fecha):
    return (0.5, 0.5)


def calcular(importe, fecha, dolar, novillo=None):
    importe, dolar = Decimal(str(importe)), Decimal(str(dolar))
    if dolar <= 0 or novillo is None or Decimal(str(novillo)) <= 0:
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
        "SELECT TOP 1 Fecha fecha,Indice valor FROM dbo.IndiceINMAG "  # 039 FR-019: INMAG, índice único
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
        "fuenteNovillo": "IndiceINMAG.Indice",
    }


def dolares_a_fecha(importe, fecha):
    """Billetes USD: íntegramente USD, sin kg; equivalencia nominal separada."""
    dol = fetch_one(
        "SELECT TOP 1 Fecha fecha,Prom_billete valor FROM dbo.[Dolar BNA] "
        "WHERE Fecha<=? AND Prom_billete>0 ORDER BY Fecha DESC", (fecha,),
    )
    if not dol:
        raise ValueError("No hay dólar BNA disponible a la fecha para la equivalencia del socio.")
    usd = Decimal(str(importe))
    return {"importeUSD": usd, "importeKgCarne": Decimal(0),
            "importePesos": (usd * Decimal(str(dol["valor"]))).quantize(Decimal(".01"), rounding=ROUND_HALF_UP),
            "dolar": dol, "novillo": None, "fuenteDolar": "Dolar BNA.Prom_billete", "monedaOrigen": "Dolares"}
