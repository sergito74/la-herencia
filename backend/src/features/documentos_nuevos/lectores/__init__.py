"""Lectores de comprobantes que llegan por mail (043, research R4).

Un lector se registra por (tipo, emisor) y solo si ya fue probado contra cargas reales hechas a mano: la carga
automática tiene que imputar igual y cerrar al centavo. Se reusan los lectores de la bóveda (042), que cargan con
`boveda.carga.cargar`. Todo lo que no tiene lector queda "para cargar a mano".

Resúmenes de tarjeta: Visa Galicia (`visa_galicia`), validado contra los 26 resúmenes cargados a mano que cierran
al centavo. Los demás resúmenes se guardan y se avisan en Tesorería para importarlos a mano.

Facturas de Agrovet (`agrovet`), validado contra las facturas cargadas a mano.

Allianz no está: su número de comprobante (póliza y endoso) sale del portal, no del PDF; llega por la bóveda.
"""

from __future__ import annotations

from src.features.boveda import carga
from src.features.boveda.conectores import DocumentoPortal, cargar_conectores

# (tipo, IdContacto del emisor) → código del conector de la bóveda cuyo lector se usa.
LECTORES: dict[tuple[str, int], str] = {
    ("factura", 71): "movistar",
}


def lector_para(tipo: str | None, id_contacto: int | None):
    from src.features.documentos_nuevos.lectores.agrovet import ID_CONTACTO as AGROVET, LectorAgrovet

    if tipo == "factura" and id_contacto == AGROVET:
        return LectorAgrovet()
    codigo = LECTORES.get((tipo or "", id_contacto or 0))
    return cargar_conectores().get(codigo) if codigo else None


def cargar(tipo: str, id_contacto: int, proveedor: str, numero: str | None, fecha, pdf: bytes, ruta: str) -> dict | None:
    """Intenta la carga con el lector registrado. `None` si no hay lector; si no, el resultado de
    `boveda.carga.cargar` (`estadoCarga`, `motivo`, `idCompra`, ...)."""
    conector = lector_para(tipo, id_contacto)
    if conector is None:
        return None
    doc = DocumentoPortal(clave=f"mail:{ruta}", fecha=fecha, tipo=tipo, proveedor=proveedor, bajar=lambda: pdf,
                          numero=numero, id_contacto=id_contacto)
    return carga.cargar(conector, doc, pdf, ruta)


def cargar_resumen(texto: str, pdf: bytes, ruta: str) -> dict | None:
    """Resumen de banco o tarjeta con lector probado; `None` si no hay lector para ese resumen."""
    from src.features.documentos_nuevos.lectores import visa_galicia

    if visa_galicia.es_visa_galicia(texto):
        return visa_galicia.cargar(pdf, ruta)
    return None
