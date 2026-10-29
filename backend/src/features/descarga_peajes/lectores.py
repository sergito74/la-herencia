"""Lectores de los PDF de peaje (037, research.md R4).

Cada lector recibe el texto del PDF (pdfplumber) y devuelve un `Leido` con
los datos para cargar la compra igual que la carga manual histórica de ese
proveedor, o lanza `NoReconocido` con un motivo legible. La decisión de
cargar (que lo leído cierre contra el total impreso) la toma `carga.py`.

Convenciones tomadas de las compras ya cargadas en WC (2026):
- Renglones con el neto por concepto; precio unitario = importe / cantidad, IVA 21.
- Percepción de IVA (RG 3337 / 3 %) → `percepcionIva` (decisión de Sergio 2026-10-16: es crédito
  fiscal; antes se cargaba en `ingresosBrutos`). Percepciones de IIBB → `ingresosBrutos`.
- IVA no inscripto, RAE/redondeo, no gravado y contribución especial ferroviaria → `conceptosNoGravados`.
- Resumen de Telepeaje: renglón "Resumen peajes" en $0 (o "Intereses
  financieros" con su neto) y el impuesto de sellos en `leyDeSellos`.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime


class NoReconocido(Exception):
    """El PDF no tiene el formato esperado: el documento queda pendiente con este motivo."""


@dataclass
class Leido:
    numero: str
    fecha: date
    renglones: list[dict]
    total_impreso: float
    ingresos_brutos: float = 0.0
    percepcion_iva: float = 0.0
    conceptos_no_gravados: float = 0.0
    ley_de_sellos: float = 0.0
    avisos: list[str] = field(default_factory=list)


def texto_pdf(contenido: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def numero(valor: str) -> float:
    """Convierte importes en los formatos que usan los portales: `1.971,88`,
    `1,239.67`, `1074.38`, `0,00`."""
    v = valor.replace("$", "").replace(" ", "").strip()
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".") if v.rfind(",") > v.rfind(".") else v.replace(",", "")
    elif "," in v:
        v = v.replace(".", "").replace(",", ".")
    return round(float(v), 2)


IMPORTE = r"\d[\d.,]*[.,]\d{2}"


def _fecha(valor: str) -> date:
    for formato in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    raise NoReconocido(f"Fecha ilegible: {valor}")


def _buscar(patron: str, texto: str, que: str, flags: int = re.M) -> re.Match:
    m = re.search(patron, texto, flags)
    if not m:
        raise NoReconocido(f"No se encontró {que} en el PDF")
    return m


def _renglon(descripcion: str, cantidad: float, importe: float, unidad: str, iva: float = 21.0) -> dict:
    cantidad = cantidad or 1
    return {"descripcion": descripcion.strip(), "cantidad": cantidad, "precioUnitario": round(importe / cantidad, 4),
            "iva": iva, "unidad": unidad}


def _renglones_cant_desc_importe(bloque: str, unidad: str, excluir: tuple[str, ...] = ()) -> list[dict]:
    """Renglones `N DESCRIPCION IMPORTE`, también en dos columnas por línea."""
    renglones = []
    patron = re.compile(rf"(?:(\d+) )?([A-ZÁÉÍÓÚÑ][^$\n]*?) \$? ?({IMPORTE})(?= \d+ [A-Z]| [A-Z]{{3,}}| *$)", re.M)
    for linea in bloque.splitlines():
        for cant, desc, imp in patron.findall(linea):
            if any(x in desc.upper() for x in excluir):
                continue
            valor = numero(imp)
            if valor == 0:
                continue
            renglones.append(_renglon(desc, float(cant or 1), valor, unidad))
    return renglones


def _entre(texto: str, desde: str, hasta: str) -> str:
    i = texto.find(desde)
    if i < 0:
        raise NoReconocido(f"No se encontró la sección '{desde}'")
    j = texto.find(hasta, i + len(desde))
    return texto[i + len(desde): j if j >= 0 else None]


def _fila_numeros(linea: str) -> list[float]:
    return [numero(x) for x in re.findall(IMPORTE, linea)]


# --- Formatos -----------------------------------------------------------------

def leer_ausol_ceamse(texto: str, unidad: str, ceamse: bool = False) -> Leido:
    """Autopistas del Sol y CEAMSE (mismo sistema de facturación). Fila de totales:
    AUSOL  `Subtotal, Perc IB CABA, Subtotal, IVA, IVA no insc, RAE, Perc IB BsAs, Perc IVA RG 3337, TOTAL`;
    CEAMSE `Subtotal, Impuestos, Subtotal, IVA, IVA no insc, Perc IVA 3 %, Perc IB BsAs, TOTAL`."""
    nro = _buscar(r"^(\d{4,5}-\d{8})$", texto, "el número de factura").group(1)
    fecha = _fecha(_buscar(r"Fecha:\s*(\d{2}/\d{2}/\d{2,4})", texto, "la fecha").group(1))
    if "Cant Descripción Importe" not in texto:
        raise NoReconocido("No se encontró el detalle de pasadas")
    bloque = texto[texto.find("Cant Descripción Importe") + len("Cant Descripción Importe"):]
    filas = [ln for ln in bloque.splitlines() if re.fullmatch(rf"(?:{IMPORTE}\s*){{6,}}", ln.strip())]
    if not filas:
        raise NoReconocido("No se encontró la fila de totales")
    v = _fila_numeros(filas[0])
    lineas = bloque[:bloque.find(filas[0])]
    renglones = _renglones_cant_desc_importe(lineas, unidad)
    if ceamse:
        if len(v) != 8:
            raise NoReconocido(f"La fila de totales tiene {len(v)} importes (se esperaban 8)")
        perc_iva, iibb, otros = v[5], v[6], v[1] + v[4]
    else:
        if len(v) != 9:
            raise NoReconocido(f"La fila de totales tiene {len(v)} importes (se esperaban 9)")
        perc_iva, iibb, otros = v[7], v[1] + v[6], v[4] + v[5]
    return Leido(nro, fecha, renglones, v[-1], ingresos_brutos=round(iibb, 2), percepcion_iva=round(perc_iva, 2),
                 conceptos_no_gravados=round(otros, 2))


def leer_gco_cvsa_aubasa(texto: str, unidad: str) -> Leido:
    """GCO y Corredores Viales (Riccheri): `Subtotal, IVA, IVA no insc, Perc IIBB PBA, Perc IB CABA, TOTAL`.
    AUBASA: `Subtotal, IVA, IVA no insc, IVA RG 3337, Perc IIBB, TOTAL`."""
    nro = _buscar(r"^(?:A-)?(\d{4,5}-\d{8})$|(\d{4,5}-\d{8})$", texto, "el número de factura")
    nro = nro.group(1) or nro.group(2)
    fecha = _fecha(_buscar(r"Fecha(?: de Emisión)?:?\s*(\d{2}/\d{2}/\d{2,4})", texto, "la fecha").group(1))
    inicio = texto.find("Cantidad Descripción Importe")
    if inicio < 0:
        raise NoReconocido("No se encontró el detalle de pasadas")
    cab = re.search(r"^Subtotal IVA.*TOTAL$", texto, re.M)
    if not cab:
        raise NoReconocido("No se encontró la fila de totales")
    lineas = texto[inicio + len("Cantidad Descripción Importe"): cab.start()]
    lineas = "\n".join(ln for ln in lineas.splitlines() if not ln.startswith(("Medios de pago", "1er. Vto", "2do. Vto")))
    renglones = _renglones_cant_desc_importe(lineas, unidad)
    resto = texto[cab.end():].splitlines()
    fila = next((ln for ln in resto if len(_fila_numeros(ln)) >= 4), None)
    if fila is None:
        raise NoReconocido("No se encontraron los importes de totales")
    v = _fila_numeros(fila)
    if len(v) != 6:
        raise NoReconocido(f"La fila de totales tiene {len(v)} importes (se esperaban 6)")
    if "RG.3337" in texto[cab.start():cab.end()]:
        perc_iva, iibb = v[3], v[4]
    else:
        perc_iva, iibb = 0.0, v[3] + v[4]
    return Leido(nro, fecha, renglones, v[-1], ingresos_brutos=round(iibb, 2), percepcion_iva=round(perc_iva, 2),
                 conceptos_no_gravados=round(v[2], 2))


def leer_ausa(texto: str) -> Leido:
    nro = _buscar(r"FACTURA (\d{4}-\d{8})", texto, "el número de factura").group(1)
    fecha = _fecha(_buscar(r"Fecha:\s*(\d{2}/\d{2}/\d{4})", texto, "la fecha").group(1))
    lineas = _entre(texto, "Cantidad Descripción Importe", "La presente facturación")
    renglones = _renglones_cant_desc_importe(lineas, "PASADAS", excluir=("AJUSTE",))
    m = _buscar(r"^Gravado No Gravado IVA RG.212 RG 3337 IIBB CEF\n(.+)$", texto, "la fila de impuestos")
    gravado, no_gravado, _iva, rg3337, iibb, cef = _fila_numeros(m.group(1))[:6]
    total = numero(_buscar(r"^Total\n(" + IMPORTE + r")$", texto, "el total").group(1))
    return Leido(nro, fecha, renglones, total, ingresos_brutos=iibb, percepcion_iva=rg3337,
                 conceptos_no_gravados=round(no_gravado + cef, 2))


def leer_rutas_rs(texto: str) -> Leido:
    """Formato "Reporting Services" de Corredores Viales (tramos), Corresur y CV5:
    renglones con `$ 1,239.67` y un renglón `IVA 21%` aparte (se ignora: el IVA se recalcula)."""
    nro = _buscar(r"^(\d{4}-\d{8})$", texto, "el número de factura").group(1)
    fecha = _fecha(_buscar(r"^Fecha:\s*(\d{2}/\d{2}/\d{4})", texto, "la fecha").group(1))
    lineas = _entre(texto, "Cantidad Descripción Importe", "Importe Total")
    lineas = "\n".join(ln for ln in lineas.splitlines() if not ln.startswith("Son:"))
    renglones = _renglones_cant_desc_importe(lineas, "PEAJE", excluir=("IVA 21",))
    total = numero(_buscar(r"Importe Total:\s*\$?\s*(" + IMPORTE + ")", texto, "el total").group(1))
    return Leido(nro, fecha, renglones, total)


def leer_rutas_sur(texto: str) -> Leido:
    """Factura A vigente de Rutas Sur; conserva también el formato anterior."""
    if "Subtotal IVA Contenido Otros Impuestos" not in texto:
        return leer_rutas_rs(texto)
    if not re.search(r"CUIT:\s*30-?71945419-?0\b", texto):
        raise NoReconocido("El CUIT no corresponde a Rutas Sur Atlantico S.A.")
    nro = _buscar(r"^(\d{4}-\d{8})$", texto, "el número de factura").group(1)
    fecha = _fecha(_buscar(r"\bFecha\s+(\d{2}/\d{2}/\d{4})", texto, "la fecha").group(1))
    cab = _buscar(r"^Subtotal IVA Contenido Otros Impuestos Percepción IIBB PCIA Percepción IIBB CABA TOTAL$",
                  texto, "los títulos de impuestos")
    fila = _buscar(r"^\s*\$\s*(" + IMPORTE + r")(?:\s+\$\s*" + IMPORTE + r"){5}\s*$",
                   texto[cab.end():], "los seis totales")
    neto, iva, otros, provincia, caba, total = _fila_numeros(fila.group(0))
    bloque = _entre(texto[:cab.start()], "Cantidad Descripción Importe", "ARCA")
    renglones = _renglones_cant_desc_importe(bloque, "PEAJE")
    from decimal import Decimal, ROUND_HALF_UP
    centavo = Decimal("0.01")
    suma = sum((Decimal(str(r["cantidad"])) * Decimal(str(r["precioUnitario"]))).quantize(centavo, ROUND_HALF_UP)
               for r in renglones)
    if suma != Decimal(str(neto)) or (Decimal(str(neto)) * Decimal("0.21")).quantize(centavo, ROUND_HALF_UP) != Decimal(str(iva)):
        raise NoReconocido("El detalle o el IVA no coincide con los importes impresos")
    if sum(Decimal(str(v)) for v in (neto, iva, otros, provincia, caba)) != Decimal(str(total)):
        raise NoReconocido("Los impuestos y el neto no coinciden con el total impreso")
    return Leido(nro, fecha, renglones, total, ingresos_brutos=round(provincia + caba, 2),
                 conceptos_no_gravados=otros)


def leer_telepeaje(texto: str) -> Leido:
    nro = _buscar(r"Nº:\s*(\d{4}-\d{9})", texto, "el número de resumen").group(1)
    fecha = _fecha(_buscar(r"Cierre:\s*(\d{2}/\d{2}/\d{4})", texto, "la fecha de cierre").group(1))
    sellos = intereses = 0.0
    total = 0.0
    if "OTROS CONCEPTOS" in texto:
        bloque = _entre(texto, "OTROS CONCEPTOS", "Total otros conceptos")
        for ln in bloque.strip().splitlines():
            if m := re.match(r"Impuesto de Sellos \S+ \$ (" + IMPORTE + ")$", ln):
                sellos += numero(m.group(1))
            elif m := re.match(r"Intereses Financieros \S+ \$ (" + IMPORTE + ")$", ln):
                intereses += numero(m.group(1))
            elif ln.startswith("IVA 21%"):
                continue
            else:
                raise NoReconocido(f"Concepto del resumen no previsto: {ln.strip()}")
        total = numero(_buscar(r"Total otros conceptos \$ (" + IMPORTE + ")", texto, "el total de otros conceptos").group(1))
    renglon = (_renglon("Intereses financieros", 1, intereses, "RESUMEN") if intereses
               else _renglon("Resumen peajes", 1, 0.0, "RESUMEN"))
    return Leido(nro, fecha, [renglon], total, ley_de_sellos=round(sellos, 2))


def _exigir_factura(texto: str) -> None:
    """Solo se cargan facturas: una nota de crédito o débito leída como
    factura cerraría contra su propio total y quedaría con el signo al revés
    (revisión de dirección financiera, 2026-10-16)."""
    encabezado = texto[:600].upper()
    if re.search(r"NOTA\s+DE\s+(CR[EÉ]DITO|D[EÉ]BITO)", encabezado):
        raise NoReconocido("Es una nota de crédito o débito: se carga a mano")
    if "FACTURA" not in encabezado:
        raise NoReconocido("No dice FACTURA en el encabezado")


def leer(proveedor: str, texto: str) -> Leido:
    """Elige el lector según el proveedor (nombre estándar) y el formato."""
    if proveedor == "Telepeaje":
        return leer_telepeaje(texto)
    _exigir_factura(texto)
    if proveedor == "AutopistasDelSol":
        return leer_ausol_ceamse(texto, "PASADA")
    if proveedor == "Ceamse":
        return leer_ausol_ceamse(texto, "PEAJE", ceamse=True)
    if proveedor == "AUSA":
        return leer_ausa(texto)
    if proveedor in ("Corresur", "Rutas Sur Atlantico S.A."):
        return leer_rutas_sur(texto)
    if proveedor == "CV5":
        return leer_rutas_rs(texto)
    if proveedor == "CorredoresViales":
        return leer_rutas_rs(texto) if re.search(r"^Código: 1$", texto, re.M) else leer_gco_cvsa_aubasa(texto, "PASADA")
    if proveedor == "GrupoConcesionarioDelOeste":
        return leer_gco_cvsa_aubasa(texto, "PASADA")
    if proveedor == "AUBASA":
        return leer_gco_cvsa_aubasa(texto, "UNIDAD")
    raise NoReconocido(f"No hay lector para el proveedor {proveedor}")
