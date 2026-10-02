"""Arma la entrada del motor FIFO por contacto (032, T007).

La fuente es `vw_MovimientosCuenta_Base`, el libro de la cuenta corriente.
Cada fila tiene Deuda o Crédito, y de ahí sale el lado del renglón:

- **Documentos**: compras con sus cuotas de `[Vencimiento Compras]`,
  ventas, impuestos, sueldos y alquileres.
- **Dinero**: bancos, efectivo, tarjetas, valores, retenciones y
  conciliaciones de tesorería.

Las asignaciones fijas salen de:

- la tarjeta (`Tarjetas_Resumenes_Lineas_Compras`): 'cadena';
- la conciliación de tesorería con documento: 'cadena' si es un cheque
  propio, 'eleccion' en los demás medios;
- las aplicaciones `manual` vigentes: 'eleccion' (FR-024);
- los documentos relacionados de compras: 'nota-origen' cuando uno de los
  dos es una nota de crédito.

Solo entran renglones desde el 19/04/2010 (FR-027). Los renglones sin fecha
quedan como excepción de datos. Los contactos con un duplicado confirmado
se unifican (FR-019).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from src.db.connection import fetch_all

INICIO = date(2010, 4, 19)

DOCUMENTOS = {"Compras", "Alquileres", "Impuestos", "Remuneraciones", "Venta Granos", "Venta Hacienda",
              "Cobro Seguro", "Ajuste Interno"}

# Origen de la vista ↔ códigos de AplicacionesPago / vínculos de 031.
TIPO_DOC_VISTA = {"CompraDeuda": "Compras", "VentaGranos": "Venta Granos", "VentaHacienda": "Venta Hacienda",
                  "Impuesto": "Impuestos", "Remuneracion": "Remuneraciones"}
ORIGEN_MOV_VISTA = {"bna": "Banco Nacion", "galicia": "Galicia", "efectivo": "Pagos efectivo"}
TIPO_TESORERIA = {"Compras": "Compras", "Impuestos": "Impuestos", "Remuneraciones": "Remuneraciones"}


def _dia(valor) -> date | None:
    if valor is None:
        return None
    return valor.date() if isinstance(valor, datetime) else valor


def normalizar_origen(origen: str) -> str:
    # La vista guarda "Conciliación Tesorería" con acentos que el driver
    # puede devolver mal codificados.
    return "Conciliacion Tesoreria" if origen.startswith("Concili") else origen


def _in(ids) -> tuple[str, tuple]:
    ids = tuple(ids)
    return ",".join("?" * len(ids)), ids


def _en_lotes(sql_fmt: str, ids: list, tam: int = 500) -> list[dict]:
    filas: list[dict] = []
    for i in range(0, len(ids), tam):
        marcas, params = _in(ids[i:i + tam])
        filas += fetch_all(sql_fmt.format(marcas), params)
    return filas


# Entidades que no emiten facturas por lo que se les paga: el FIFO no
# aplica (decisión de Sergio, 2026-10-01). Sus cuentas se revisan aparte.
EXCLUIDOS = {
    # Organismos y entidades oficiales
    119: "AFIP", 12: "ARBA", 72: "Municipalidad de Bolívar", 422: "Municipalidad de Tapalqué", 250: "SENASA",
    315: "UATRE", 447: "Ministerio de Desarrollo Agrario", 351: "Ministerio de Trabajo BA",
    563: "Consejo de Ciencias Económicas", 247: "Colegio de Escribanos",
    # Bancos y tarjetas
    518: "Banco Galicia", 369: "Banco Nación", 503: "Corporativa Nación", 373: "AgroNación", 533: "Galicia Rural",
    532: "Visa Galicia", 372: "Mastercard BNA",
    # Familia y empresa propia
    375: "Sergio Giamberardini", 564: "Virginia Giamberardini", 390: "Albina Iglina", 386: "Giamigli de Bolívar",
    46: "Irma Miranda",  # empleada de casas particulares de Albina: se le paga desde cuentas particulares
}


def contactos_todos() -> list[int]:
    return [f["id"] for f in fetch_all(
        "SELECT DISTINCT IdContacto AS id FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto IS NOT NULL")
        if f["id"] not in EXCLUIDOS]


def unificaciones() -> dict[int, int]:
    """Duplicado → principal, solo los confirmados."""
    try:
        return {f["d"]: f["p"] for f in fetch_all(
            "SELECT IdContacto AS d, IdContactoPrincipal AS p FROM dbo.ContactoDuplicado WHERE Estado = 'confirmado'")}
    except Exception:
        return {}


def armar(id_contactos: list[int]) -> dict[int, dict]:
    """{idContacto: {nombre, items, fijos, excepcionesDatos}}."""
    unif = unificaciones()
    principales = sorted({unif.get(c, c) for c in id_contactos})
    pedidos = sorted(set(principales) | {d for d, p in unif.items() if p in principales})
    if not pedidos:
        return {}

    filas = _en_lotes(
        "SELECT Fecha AS fecha, IdContacto AS idContacto, [Razon Social] AS nombre, Documento AS documento, "
        "[Nro Documento] AS nro, Deuda AS deuda, Credito AS credito, Origen AS origen, IdOrigen AS idOrigen "
        "FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto IN ({})", pedidos)

    ids_compra = sorted({f["idOrigen"] for f in filas if f["origen"] == "Compras"})
    compras = {f["id"]: f for f in _en_lotes(
        "SELECT IdDeuda AS id, Moneda AS moneda, [Tipo de Cambio] AS tc, [Ajusta Tipo Cambio] AS ajusta, "
        "Suspendida AS suspendida FROM dbo.Compras WHERE IdDeuda IN ({})", ids_compra)} if ids_compra else {}
    cuotas: dict[int, list[date]] = defaultdict(list)
    for f in (_en_lotes("SELECT IdCompra AS id, [Fecha de vencimiento] AS v FROM dbo.[Vencimiento Compras] "
                        "WHERE IdCompra IN ({})", ids_compra) if ids_compra else []):
        if f["v"] is not None:
            cuotas[f["id"]].append(_dia(f["v"]))

    resultado: dict[int, dict] = {p: {"nombre": None, "items": [], "fijos": [], "excepcionesDatos": []}
                                  for p in principales}
    for f in filas:
        contacto = unif.get(f["idContacto"], f["idContacto"])
        destino = resultado.get(contacto)
        if destino is None:
            continue
        if f["idContacto"] == contacto and f["nombre"]:
            destino["nombre"] = f["nombre"]
        origen = normalizar_origen(f["origen"])
        deuda, credito = float(f["deuda"] or 0), float(f["credito"] or 0)
        if abs(deuda) < 0.005 and abs(credito) < 0.005:
            continue
        fecha = _dia(f["fecha"])
        if fecha is None:
            destino["excepcionesDatos"].append(f"{origen} {f['idOrigen']} sin fecha")
            continue
        if fecha < INICIO:
            continue
        lado, importe = ("D", deuda) if abs(deuda) >= abs(credito) else ("C", credito)
        if importe < 0:  # importe negativo en un lado equivale al otro lado
            lado, importe = ("C" if lado == "D" else "D"), -importe
        base = {"lado": lado, "clase": "doc" if origen in DOCUMENTOS else "dinero", "fecha": fecha,
                "nro": str(f["nro"] or ""), "moneda": "ARS", "tcDoc": None, "suspendido": False,
                "ajustaTc": False, "documento": f["documento"]}
        if origen == "Compras":
            c = compras.get(f["idOrigen"], {})
            if c.get("moneda") == "Dolares":
                base["moneda"] = "USD"
                base["tcDoc"] = float(c["tc"]) if (c.get("tc") or 0) > 1 else None
            base["suspendido"] = bool(c.get("suspendida"))
            base["ajustaTc"] = bool(c.get("ajusta"))
            vencs = sorted(v for v in cuotas.get(f["idOrigen"], []) if v)
            if lado == "D" and len(vencs) > 1:
                parte = round(importe / len(vencs), 2)
                for n, v in enumerate(vencs, start=1):
                    monto = parte if n < len(vencs) else round(importe - parte * (len(vencs) - 1), 2)
                    destino["items"].append(dict(base, clave=(origen, f["idOrigen"], n), vencimiento=max(v, fecha),
                                                 importe=monto))
                continue
            venc = max(vencs[0], fecha) if (vencs and lado == "D") else fecha
            destino["items"].append(dict(base, clave=(origen, f["idOrigen"], None), vencimiento=venc, importe=importe))
            continue
        destino["items"].append(dict(base, clave=(origen, f["idOrigen"], None), vencimiento=fecha, importe=importe))

    # Proveedores que documentan la diferencia de cambio con notas de débito
    # o crédito "Ajusta tipo de cambio" (FR-006): el pago en pesos se convierte
    # al TC de la factura, porque la diferencia ya está en esa nota.
    for r in resultado.values():
        if any(i.get("ajustaTc") for i in r["items"]):
            for i in r["items"]:
                if i["moneda"] == "USD" and i.get("tcDoc"):
                    i["usarTcDoc"] = True

    _agregar_fijos(resultado, unif)
    return resultado


def _agregar_fijos(resultado: dict[int, dict], unif: dict[int, int]) -> None:
    claves_por_contacto = {c: {i["clave"][:2] for i in r["items"]} for c, r in resultado.items()}

    def agregar(credito: tuple, debito: tuple, importe: float, regla: str) -> None:
        for c, claves in claves_por_contacto.items():
            if credito in claves and debito in claves:
                resultado[c]["fijos"].append({"credito": credito, "debito": debito, "importe": abs(float(importe)),
                                              "regla": regla})
                return

    # Cadena tarjeta → factura: el renglón 'Tarjetas' de la vista es el IdVinculo.
    for f in fetch_all("SELECT IdVinculo AS id, IdCompra AS compra, ImporteImputado AS imp "
                       "FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdCompra IS NOT NULL"):
        agregar(("Tarjetas", f["id"]), ("Compras", f["compra"]), f["imp"] or 0, "cadena")

    # Conciliación de tesorería con documento: el renglón es el IdConciliacion.
    for f in fetch_all("SELECT IdConciliacion AS id, Medio AS medio, TipoOrigenDocumento AS tipo, "
                       "IdOrigenDocumento AS doc, Importe AS imp FROM dbo.ConciliacionesTesoreria "
                       "WHERE TipoOrigenDocumento IS NOT NULL AND IdOrigenDocumento IS NOT NULL"):
        tipo = TIPO_TESORERIA.get(f["tipo"], f["tipo"])
        agregar(("Conciliacion Tesoreria", f["id"]), (tipo, f["doc"]), f["imp"] or 0,
                "cadena" if f["medio"] == "valores-propios" else "eleccion")

    # Elecciones manuales vigentes (FR-024).
    for f in fetch_all("SELECT OrigenMovimiento AS om, IdMovimientoOrigen AS idm, TipoDocumento AS td, "
                       "IdDocumentoAplicado AS idd, ImporteAplicado AS imp FROM dbo.AplicacionesPago "
                       "WHERE Anulada = 0 AND Origen = 'manual'"):
        origen = ORIGEN_MOV_VISTA.get(f["om"])
        tipo = TIPO_DOC_VISTA.get(f["td"])
        if origen and tipo:
            agregar((origen, f["idm"]), (tipo, f["idd"]), f["imp"] or 0, "eleccion")

    # Nota de crédito ↔ factura de origen.
    for c, r in resultado.items():
        lados = {i["clave"][:2]: i["lado"] for i in r["items"]}
        importes = defaultdict(float)
        for i in r["items"]:
            importes[i["clave"][:2]] += i["importe"]
        r["_lados"], r["_importes"] = lados, importes
    for f in fetch_all("SELECT IdCompra AS a, IdCompraRelacionada AS b FROM dbo.CompraDocumentosRelacionados"):
        for c, r in resultado.items():
            ka, kb = ("Compras", f["a"]), ("Compras", f["b"])
            if ka in r["_lados"] and kb in r["_lados"] and r["_lados"][ka] != r["_lados"][kb]:
                nc, fac = (ka, kb) if r["_lados"][ka] == "C" else (kb, ka)
                r["fijos"].append({"credito": nc, "debito": fac, "importe": r["_importes"][nc], "regla": "nota-origen"})
    for r in resultado.values():
        r.pop("_lados", None)
        r.pop("_importes", None)
