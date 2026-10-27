"""Carga automática en Compras de un comprobante bajado de un portal (042, FR-020, research.md R5).

Generaliza `descarga_peajes/carga.py` a todos los portales. Solo crea la
compra si: el conector reconoce el formato, el documento tiene proveedor
(`IdContacto`), cada renglón tiene rubro y centro de costo, el total
calculado con las reglas de Compras es **igual al centavo** al total impreso
(Sergio 27/10/2026: sin tolerancia) y no existe ya una compra del mismo
proveedor y número (o con este archivo como documento original). Si no, no
crea nada y devuelve el motivo. Nunca crea pagos, asientos ni ajustes.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from src.features.boveda import repository
from src.features.boveda.conectores import Conector, DocumentoPortal
from src.features.compras import repository as compras

TIPOS_COMPROBANTE = {"factura", "nota_credito", "nota_debito"}


def _fmt(v) -> str:
    entero, dec = f"{float(v):,.2f}".split(".")
    return f"${entero.replace(',', '.')},{dec}"


def cargar(conector: Conector, doc: DocumentoPortal, pdf: bytes, ruta: str, *, simular: bool = False) -> dict:
    """Devuelve `{estadoCarga, motivo, idCompra, numeroDocumento, totalImpreso}`."""
    resultado = {"estadoCarga": "pendiente", "motivo": None, "idCompra": None,
                 "numeroDocumento": doc.numero, "totalImpreso": doc.total}
    if doc.tipo not in TIPOS_COMPROBANTE:
        return {**resultado, "estadoCarga": "no_aplica"}
    if not conector.tiene_carga_compras:
        return {**resultado, "motivo": "Lector no implementado para este portal: cargar a mano"}
    try:
        leido = conector.leer_comprobante(doc, pdf)
    except Exception as e:  # PDF dañado o ilegible
        return {**resultado, "motivo": f"No se pudo leer el PDF: {e.__class__.__name__}"}
    if leido is None:
        return {**resultado, "motivo": "Formato no reconocido"}
    resultado["numeroDocumento"] = leido.numero
    resultado["totalImpreso"] = leido.total_impreso

    id_contacto = leido.cabecera.get("idContacto") or doc.id_contacto
    if not id_contacto:
        return {**resultado, "motivo": f"El proveedor no tiene contacto asignado en Compras ({doc.proveedor})"}

    existente = repository.compra_existente(id_contacto, leido.numero, None if simular else ruta)
    if existente:
        return {**resultado, "estadoCarga": "ya_cargado", "idCompra": existente}

    if not leido.lineas:
        return {**resultado, "motivo": "No se encontraron renglones en el comprobante"}
    if any(not l.get("idRubro") or not l.get("idCentroCosto") for l in leido.lineas):
        return {**resultado, "motivo": "Falta rubro o centro de costo para este proveedor: cargar a mano"}

    cabecera = {**leido.cabecera, "idContacto": id_contacto, "documentoOriginal": ruta}
    centavo = Decimal("0.01")
    calculado = Decimal(str(compras.calcular_totales(leido.lineas, cabecera)["importeTotal"])).quantize(centavo, ROUND_HALF_UP)
    impreso = Decimal(str(leido.total_impreso)).quantize(centavo, ROUND_HALF_UP)
    if calculado != impreso:
        return {**resultado, "motivo": f"No cierra al centavo: calculado {_fmt(calculado)}, impreso {_fmt(impreso)}, "
                                       f"diferencia {_fmt(calculado - impreso)}"}
    if simular:
        return {**resultado, "estadoCarga": "cargado_auto", "motivo": "Simulación: se cargaría"}
    try:
        resultado["idCompra"] = compras.create_compra(cabecera, leido.lineas, [])
    except ValueError as e:
        return {**resultado, "motivo": f"El alta de Compras lo rechazó: {e}"}
    resultado["estadoCarga"] = "cargado_auto"
    return resultado
