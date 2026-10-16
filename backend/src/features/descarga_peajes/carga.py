"""Carga automática en Compras de un comprobante de peaje bajado (037, FR-017/018/019).

Solo crea la compra si: el formato es reconocido, el proveedor tiene contacto
asignado, lo leído cierra contra el total impreso (tolerancia `TOLERANCIA`,
redondeo por renglón de los proveedores) y no existe ya una compra del mismo
proveedor con el mismo número (o con este archivo como documento original).
En cualquier otro caso no crea nada y devuelve el motivo. Usa el repositorio
de Compras: mismas validaciones y la misma transacción que el alta manual.
"""

from __future__ import annotations

from src.features.compras import repository as compras
from src.features.descarga_peajes import lectores, repository

TOLERANCIA = 0.05

# Clasificación de todas las cargas de peajes (research.md R4).
RUBRO_VIATICOS = 2047893477
CENTRO_COSTO = 3
DESTINO = 1
CAMPANIA = "No Aplica"


def _fmt(v: float) -> str:
    entero, dec = f"{v:,.2f}".split(".")
    return f"${entero.replace(',', '.')},{dec}"


def armar_compra(leido: lectores.Leido, id_contacto: int, ruta: str) -> tuple[dict, list[dict]]:
    cabecera = {
        "idContacto": id_contacto, "fecha": leido.fecha.isoformat(), "tipo": "A", "tipoDocumento": "Factura",
        "numeroDocumento": leido.numero, "moneda": "Pesos", "tipoDeCambio": 1.0, "ajustaTipoCambio": False,
        "documentoOriginal": ruta,
    }
    for campo in compras.CAMPOS_IMPORTE_CABECERA:
        cabecera[campo] = 0.0
    cabecera["ingresosBrutos"] = leido.ingresos_brutos
    cabecera["percepcionIva"] = leido.percepcion_iva
    cabecera["conceptosNoGravados"] = leido.conceptos_no_gravados
    cabecera["leyDeSellos"] = leido.ley_de_sellos
    lineas = [{
        "productoServicio": r["descripcion"][:50], "cantidad": r["cantidad"], "precioUnitario": r["precioUnitario"],
        "iva": r["iva"], "unidad": r["unidad"], "idCentroCosto": CENTRO_COSTO, "idDestino": DESTINO,
        "idRubro": RUBRO_VIATICOS, "campaña": CAMPANIA, "ajusteFinanciero": False,
    } for r in leido.renglones]
    return cabecera, lineas


def cargar(proveedor: str, id_contacto: int | None, contenido_pdf: bytes, ruta: str, *, simular: bool = False) -> dict:
    """Devuelve `{estadoCarga, motivo, idCompra, numeroDocumento, totalImpreso}`."""
    resultado = {"estadoCarga": "pendiente", "motivo": None, "idCompra": None, "numeroDocumento": None,
                 "totalImpreso": None}
    try:
        leido = lectores.leer(proveedor, lectores.texto_pdf(contenido_pdf))
    except lectores.NoReconocido as e:
        resultado["motivo"] = f"Formato no reconocido: {e}"
        return resultado
    except Exception as e:  # PDF dañado o ilegible
        resultado["motivo"] = f"No se pudo leer el PDF: {e.__class__.__name__}"
        return resultado
    resultado["numeroDocumento"] = leido.numero
    resultado["totalImpreso"] = leido.total_impreso

    if not id_contacto:
        resultado["motivo"] = f"El concesionario no tiene proveedor asignado en Compras ({proveedor})"
        return resultado

    existente = repository.compra_existente(id_contacto, leido.numero, None if simular else ruta)
    if existente:
        resultado.update(estadoCarga="ya_cargado", idCompra=existente)
        return resultado

    if not leido.renglones:
        resultado["motivo"] = "No se encontraron renglones en el comprobante"
        return resultado
    cabecera, lineas = armar_compra(leido, id_contacto, ruta)
    calculado = compras.calcular_totales(lineas, cabecera)["importeTotal"]
    if abs(calculado - leido.total_impreso) > TOLERANCIA:
        resultado["motivo"] = f"No cierra: calculado {_fmt(calculado)}, impreso {_fmt(leido.total_impreso)}"
        return resultado

    if simular:
        resultado["estadoCarga"] = "cargado_auto"
        resultado["motivo"] = "Simulación: se cargaría"
        return resultado
    try:
        resultado["idCompra"] = compras.create_compra(cabecera, lineas, [])
    except ValueError as e:
        resultado["motivo"] = f"El alta de Compras lo rechazó: {e}"
        return resultado
    resultado["estadoCarga"] = "cargado_auto"
    return resultado
