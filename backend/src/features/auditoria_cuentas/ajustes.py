"""Nota de ajuste cargada desde la revisión de una cuenta — 035 (FR-021).

Una nota de débito o de crédito "SIN DOCUMENTO" con la marca de ajuste y una sola línea por el importe (neto de IVA).
El saldo de la cuenta cambia por ese importe y la nota queda identificada como ajuste, con su motivo en el historial.
"""

from __future__ import annotations

from datetime import date

from src.features.compras import repository as compras

IVA_AJUSTE = 21.0
TIPOS = {"debito": "Nota de Débito", "credito": "Nota de Crédito"}


class AjusteError(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


def validar(tipo: str, importe: float, motivo: str, moneda: str, fecha: date) -> None:
    if tipo not in TIPOS:
        raise AjusteError(422, "El tipo debe ser débito o crédito")
    if not importe or importe <= 0:
        raise AjusteError(422, "El importe debe ser mayor que cero")
    if not (motivo or "").strip():
        raise AjusteError(422, "Falta el motivo")
    if moneda not in ("Pesos", "Dolares"):
        raise AjusteError(422, "La moneda debe ser Pesos o Dolares")
    if fecha > date.today():
        raise AjusteError(422, "La fecha no puede ser futura")


def neto_de_iva(importe_total: float, iva: float = IVA_AJUSTE) -> float:
    return round(importe_total / (1 + iva / 100), 4)


def cargar_nota_ajuste(id_contacto: int, tipo: str, fecha: date, importe: float, moneda: str, motivo: str,
                       tipo_de_cambio: float | None = None) -> int:
    validar(tipo, importe, motivo, moneda, fecha)
    cabecera = {"fecha": fecha, "idContacto": id_contacto, "tipo": "A", "tipoDocumento": TIPOS[tipo], "numeroDocumento": "SIN DOCUMENTO",
                "moneda": moneda, "tipoDeCambio": tipo_de_cambio if moneda == "Dolares" else 1, "ajustaTipoCambio": False}
    # la columna Det_Compras.[Producto/Servicio] admite 50 caracteres
    # una nota de crédito se guarda con importe negativo (así la vista de saldos la lee como crédito)
    signo = -1 if tipo == "credito" else 1
    linea = {"productoServicio": f"Ajuste de cuenta: {motivo.strip()}"[:50], "cantidad": 1, "precioUnitario": signo * neto_de_iva(importe),
             "iva": IVA_AJUSTE}
    try:
        return compras.create_compra(cabecera, [linea], [])
    except ValueError as exc:
        raise AjusteError(422, str(exc)) from exc
