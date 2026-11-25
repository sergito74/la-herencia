"""Cabezas y kg de un renglón de venta de hacienda (052 FR-009, research R4). Función pura.

En [Det_Ventas Hacienda] la `Unidad de medida` dice cómo se leyó la liquidación:
- Kilos: Cantidad = kg, Peso Total = cabezas (verificado con el PDF de 0003-00010318: 2 vacas de 440 kg).
- Unidades / Cabezas / toros: Cantidad = cabezas, Peso Total = kg (si > 0).
- Pesos: es un gasto o ajuste cargado como renglón; no es hacienda.
Si falta uno de los dos datos se estima con el peso típico de la categoría y se marca.
"""

from __future__ import annotations


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def unidad_es_kilos(unidad: str | None) -> bool:
    return (unidad or "").strip().lower().startswith("kilo")


def unidad_es_pesos(unidad: str | None) -> bool:
    return (unidad or "").strip().lower() == "pesos"


def cabezas_y_kg(cantidad, unidad: str | None, peso_total, peso_tipico: float | None) -> dict:
    """{'cabezas', 'kg', 'kgEstimado', 'cabezasEstimadas', 'esHacienda'}. Conserva el signo (correcciones)."""
    cant, peso = _f(cantidad), _f(peso_total)
    if unidad_es_pesos(unidad):
        return {"cabezas": 0, "kg": 0.0, "kgEstimado": False, "cabezasEstimadas": False, "esHacienda": False}
    signo = -1 if cant < 0 else 1
    if unidad_es_kilos(unidad):
        kg = cant
        if peso:
            cabezas = int(round(abs(peso))) * signo
            estimadas = False
        else:
            cabezas = int(round(abs(kg) / peso_tipico)) * signo if peso_tipico else 0
            estimadas = True
        return {"cabezas": cabezas, "kg": kg, "kgEstimado": False, "cabezasEstimadas": estimadas, "esHacienda": True}
    if peso and abs(peso) < abs(cant) and 40 <= abs(cant) / abs(peso) <= 1200:
        # Cargado al revés (Cantidad = kg, Peso Total = cabezas): kg por cabeza verosímil (PDF 0003-00006904: 1 ternera
        # de 170 kg cargada "Unidades 170 / Peso 1").
        return {"cabezas": int(round(abs(peso))) * signo, "kg": cant, "kgEstimado": False, "cabezasEstimadas": False,
                "esHacienda": True}
    cabezas = int(round(cant))
    if peso and abs(peso) > abs(cant):
        return {"cabezas": cabezas, "kg": abs(peso) * signo, "kgEstimado": False, "cabezasEstimadas": False,
                "esHacienda": True}
    kg = abs(cabezas) * (peso_tipico or 0.0) * signo
    return {"cabezas": cabezas, "kg": kg, "kgEstimado": True, "cabezasEstimadas": False, "esHacienda": True}
