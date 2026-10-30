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
    ("factura", 2657): "telepeajeplus",
    ("factura", 328): "telepeajeplus",  # Telepeaje S.A.: mismo lector de 037 (proveedor "Telepeaje")
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
    from src.features.boveda.conectores.sancor import ID_CONTACTO as SANCOR

    if tipo == "factura" and id_contacto == SANCOR:
        return cargar_sancor(pdf, ruta)
    conector = lector_para(tipo, id_contacto)
    if conector is None:
        return None
    if id_contacto == 2657:
        proveedor = "Rutas Sur Atlantico S.A."
    doc = DocumentoPortal(clave=f"mail:{ruta}", fecha=fecha, tipo=tipo, proveedor=proveedor, bajar=lambda: pdf,
                          numero=numero, id_contacto=id_contacto)
    return carga.cargar(conector, doc, pdf, ruta)


def cargar_resumen(texto: str, pdf: bytes, ruta: str) -> dict | None:
    """Resumen de banco o tarjeta con lector probado; `None` si no hay lector para ese resumen."""
    from src.features.documentos_nuevos.lectores import visa_galicia

    if visa_galicia.es_visa_galicia(texto):
        return visa_galicia.cargar(pdf, ruta)
    return None


def cargar_sancor(pdf: bytes, ruta: str, *, simular: bool = False) -> dict:
    """Sancor por mail o Dropbox (30/10/2026): un PDF con una factura por póliza y una compra por cada una. Mismas
    validaciones que la bóveda (cierre al centavo, sin duplicar por número); el archivo queda como documento original
    de todas, como en las cargas a mano."""
    from src.features.boveda import repository as boveda
    from src.features.boveda.conectores.chrome_comun import _texto
    from src.features.boveda.conectores.sancor import ID_CONTACTO, facturas_del_pdf
    from src.features.compras import repository as compras

    conector = cargar_conectores()["sancor"]
    resultados = []
    for i in range(len(facturas_del_pdf(_texto(pdf)))):
        doc = DocumentoPortal(clave=f"mail:{ruta}#{i}", fecha=None, tipo="factura", proveedor="Sancor Seguros",
                              bajar=lambda: pdf, id_contacto=ID_CONTACTO)
        r = carga.cargar(conector, doc, pdf, ruta, simular=True)  # valida sin mirar el archivo compartido
        if r["estadoCarga"] == "cargado_auto" and not simular:
            leido = conector.leer_comprobante(doc, pdf)
            r = {**r, "motivo": None, "idCompra": compras.create_compra(
                {**leido.cabecera, "idContacto": ID_CONTACTO, "documentoOriginal": ruta}, leido.lineas, [])}
        elif r["estadoCarga"] == "ya_cargado" and not r.get("idCompra"):
            r["idCompra"] = boveda.compra_existente(ID_CONTACTO, r["numeroDocumento"], None)
        resultados.append(r)
    pendientes = [r for r in resultados if r["estadoCarga"] == "pendiente"]
    if pendientes:  # alguna no se pudo: el aviso queda para cargar a mano con el motivo
        return {**pendientes[0],
                "motivo": f"{len(pendientes)} de {len(resultados)} facturas sin cargar: {pendientes[0]['motivo']}"}
    cargadas = [r for r in resultados if r["estadoCarga"] == "cargado_auto"]
    return {**(cargadas or resultados)[0], "estadoCarga": "cargado_auto" if cargadas else "ya_cargado",
            "detalle": resultados}
