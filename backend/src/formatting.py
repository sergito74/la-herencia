"""Formato de números y moneda para mensajes al usuario (igual que el frontend,
`frontend/src/lib/format.ts`): miles ".", decimales ",", "$" para pesos y "us$"
para dólares. `f"{x:,.2f}"` da el formato estadounidense ("1,234.50"): no usarlo
en textos que ve el usuario."""

from __future__ import annotations


def formatear_monto(valor: float, decimales: int = 2) -> str:
    texto = f"{abs(valor):,.{decimales}f}".replace(",", "\0").replace(".", ",").replace("\0", ".")
    negativo = valor < 0 and float(f"{abs(valor):.{decimales}f}") != 0
    return f"-{texto}" if negativo else texto


def formatear_moneda(valor: float, moneda: str = "Pesos") -> str:
    return f"{'us$' if moneda == 'Dolares' else '$'} {formatear_monto(valor)}"
