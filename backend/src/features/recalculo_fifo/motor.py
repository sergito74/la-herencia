"""Motor FIFO puro de 032 (sin base de datos).

Cada contacto es un libro con dos lados, el mismo que arma la vista
`vw_MovimientosCuenta_Base`:

- Lado 'D' (Deuda): compras, impuestos, sueldos, y los cobros recibidos.
- Lado 'C' (Crédito): pagos, retenciones, notas de crédito, ventas.

Un renglón del lado D se cancela con uno del lado C. El orden es este:

1. Asignaciones fijas, en el orden recibido: cadena real de tarjeta o
   cheque, elección explícita y nota de crédito con su factura de origen.
   Una fija que pide más de lo disponible se recorta. Si es una elección,
   el contacto queda marcado 'manual-ajustado' (FR-024) y el exceso vuelve
   al reparto.
2. Reparto cronológico único (ver `reparto`), en orden de (vencimiento,
   nro de comprobante, origen, id). Las facturas suspendidas no entran.

La regla de cada par se deduce de las clases. Documento contra documento
es 'compensacion'. Dinero contra dinero es 'reintegro'. Dinero anterior al
documento es 'anticipo'. Lo demás es 'fifo'.

Monedas: cada renglón conserva la suya. Si el par mezcla USD y pesos, se
calcula en USD, con el TC BNA vendedor del día anterior a la fecha del
renglón de dinero (FR-026). Entre dos documentos se usa el más nuevo. Si falta la cotización, se usa el TC de la
factura y se marca 'tc-implicito'. Cuando un documento USD se paga en
pesos, la diferencia contra el TC de la factura queda en
`diferenciaCambio` (FR-006).
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Callable

TOLERANCIA_CENTAVOS = 0.005
DIAS_ANTICIPO = 60
TOLERANCIA_CIERRE = 0.005

TcFn = Callable[[date], "float | None"]


def _r(x: float) -> float:
    return round(x + 0.0, 2)


def _orden(item: dict) -> tuple:
    origen, ident, cuota = item["clave"]
    return (item["vencimiento"] or date.min, str(item.get("nro") or ""), origen, ident, cuota or 0)


class _Libro:
    def __init__(self, items: list[dict], tc: TcFn):
        self.items = sorted((dict(i) for i in items), key=_orden)
        for i in self.items:
            i["rem"] = float(i["importe"])
        self.tc = tc
        self.aplicaciones: list[dict] = []
        self.marcas: set[str] = set()

    # --- conversión -----------------------------------------------------
    def _tc_par(self, a: dict, b: dict) -> float:
        usd = a if a["moneda"] == "USD" else b
        if usd.get("usarTcDoc") and usd.get("tcDoc"):
            return float(usd["tcDoc"])
        dinero = [i for i in (a, b) if i["clase"] == "dinero"]
        fecha = dinero[0]["fecha"] if len(dinero) == 1 else max(a["fecha"], b["fecha"])
        valor = self.tc(fecha - timedelta(days=1)) if fecha else None
        if valor:
            return float(valor)
        self.marcas.add("tc-implicito")
        return float(usd.get("tcDoc") or 1.0)

    def _aplicar(self, d: dict, c: dict, tope_ars: float | None, regla: str | None) -> float:
        """Aplica entre d (lado D) y c (lado C) lo máximo posible, o hasta
        `tope_ars`. Devuelve lo aplicado en pesos."""
        mezcla = d["moneda"] != c["moneda"]
        tc = self._tc_par(d, c) if "USD" in (d["moneda"], c["moneda"]) else 1.0
        def a_comun(item):  # moneda común: USD si alguno es USD
            return item["rem"] / tc if (mezcla and item["moneda"] == "ARS") else item["rem"]
        x = min(a_comun(d), a_comun(c))
        comun_usd = mezcla or d["moneda"] == "USD"
        if tope_ars is not None:
            x = min(x, tope_ars / tc if comun_usd else tope_ars)
        if x <= TOLERANCIA_CENTAVOS:
            return 0.0
        for item in (d, c):
            item["rem"] -= x * tc if (mezcla and item["moneda"] == "ARS") else x
            if item["rem"] < TOLERANCIA_CENTAVOS:
                item["rem"] = 0.0
        ars = x * tc if comun_usd else x
        doc, otro = (d, c) if d["clase"] == "doc" or c["clase"] != "doc" else (c, d)
        if regla is None:
            if d["clase"] == "doc" and c["clase"] == "doc":
                regla = "compensacion"
            elif d["clase"] == "dinero" and c["clase"] == "dinero":
                regla = "reintegro"
            elif otro["fecha"] < doc["fecha"]:
                regla = "anticipo"
                if (doc["fecha"] - otro["fecha"]).days > DIAS_ANTICIPO:
                    self.marcas.add("anticipo-largo")
            else:
                regla = "fifo"
            if regla == "fifo" and (d.get("ajustaTc") or c.get("ajustaTc")):
                regla = "ajuste-tc"
        dif = 0.0
        if doc["moneda"] == "USD" and otro["moneda"] == "ARS" and doc.get("tcDoc"):
            dif = _r(x * (tc - float(doc["tcDoc"])))
        # El documento es el "débito" del vínculo (lo que se cancela). Entre
        # dos documentos o dos dineros, el del lado D.
        self.aplicaciones.append({
            "debito": doc["clave"], "credito": otro["clave"],
            "importeAplicado": _r(x if doc["moneda"] == "USD" else ars), "moneda": doc["moneda"],
            "importeArs": _r(ars), "tipoCambio": tc if comun_usd else None, "diferenciaCambio": dif, "regla": regla,
            "fechaCredito": otro["fecha"], "fechaVencimiento": doc["vencimiento"],
        })
        return ars

    # --- pasos ----------------------------------------------------------
    def fijos(self, fijos: list[dict]) -> None:
        por_doc: dict[tuple, list[dict]] = {}
        for i in self.items:
            por_doc.setdefault(i["clave"][:2], []).append(i)
        for f in fijos:
            creditos = por_doc.get(tuple(f["credito"])[:2], [])
            debitos = por_doc.get(tuple(f["debito"])[:2], [])
            if not creditos or not debitos:
                continue
            pedido = float(f["importe"])
            restante = pedido
            for c in creditos:
                for d in debitos:
                    if restante <= TOLERANCIA_CENTAVOS:
                        break
                    if c["lado"] == d["lado"] or c["rem"] <= 0 or d["rem"] <= 0 or d.get("suspendido"):
                        continue
                    lado_d, lado_c = (d, c) if d["lado"] == "D" else (c, d)
                    restante -= self._aplicar(lado_d, lado_c, restante, f["regla"])
            if f["regla"] == "eleccion":
                total_doc = sum(float(d["importe"]) * (float(d.get("tcDoc") or 1.0) if d["moneda"] == "USD" else 1.0)
                                for d in debitos)
                if pedido > total_doc + max(1.0, total_doc * TOLERANCIA_CIERRE):
                    self.marcas.add("manual-ajustado")

    def reparto(self) -> None:
        """Un solo recorrido cronológico (FR-001, FR-007). Cada renglón llega
        en su vencimiento (documentos) o en su fecha (dinero) y se cruza con
        lo pendiente del otro lado *a esa fecha*:

        - un documento compensa primero los documentos pendientes del otro
          lado y después el dinero adelantado (anticipos);
        - el dinero cancela primero los documentos pendientes del otro lado y
          después, si sobra, el dinero del otro lado (reintegro).

        Lo que no se cancela queda pendiente, esperando renglones posteriores."""
        pendientes = {(lado, clase): [] for lado in "DC" for clase in ("doc", "dinero")}
        for x in self.items:
            if x.get("suspendido") or x["rem"] <= 0:
                continue
            otro = "C" if x["lado"] == "D" else "D"
            for clase in ("doc", "dinero"):
                if x["clase"] == "dinero" and clase == "dinero":
                    continue  # el reintegro va en una segunda vuelta, al final
                self._contra(x, pendientes[(otro, clase)])
            if x["rem"] > 0:
                pendientes[(x["lado"], x["clase"])].append(x)
        # Reintegros: dinero contra dinero, solo con lo que no encontró documento.
        dinero_d = [i for i in pendientes[("D", "dinero")] if i["rem"] > 0]
        dinero_c = [i for i in pendientes[("C", "dinero")] if i["rem"] > 0]
        for x in dinero_d:
            self._contra(x, dinero_c)
        if any(a["regla"] == "reintegro" for a in self.aplicaciones):
            self.marcas.add("reintegro")

    def _contra(self, x: dict, cola: list[dict]) -> None:
        for y in cola:
            if x["rem"] <= 0:
                return
            if y["rem"] <= 0:
                continue
            d, c = (x, y) if x["lado"] == "D" else (y, x)
            self._aplicar(d, c, None, None)


def _ars(item: dict, tc: TcFn) -> float:
    if item["moneda"] != "USD":
        return item["rem"]
    return item["rem"] * float(item.get("tcDoc") or tc(item["fecha"] - timedelta(days=1)) or 1.0)


def huella(aplicaciones: list[dict]) -> str:
    partes = sorted(f"{a['credito']}|{a['debito']}|{a['importeAplicado']:.2f}|{a['regla']}" for a in aplicaciones)
    return hashlib.sha256("\n".join(partes).encode()).hexdigest()


def recalcular(items: list[dict], fijos: list[dict], tc: TcFn, hoy: date) -> dict:
    """Devuelve aplicaciones, pendientes y marcas de un contacto."""
    libro = _Libro(items, tc)
    libro.fijos(fijos)
    libro.reparto()
    pend_d = sum(_ars(i, tc) for i in libro.items if i["lado"] == "D" and i["clase"] == "doc" and i["rem"] > 0)
    pend_c = sum(_ars(i, tc) for i in libro.items if i["lado"] == "C" and i["clase"] == "doc" and i["rem"] > 0)
    dinero_c = [i for i in libro.items if i["rem"] > 0 and i["clase"] == "dinero"]
    anticipo = sum(_ars(i, tc) for i in dinero_c)
    viejos = [i for i in dinero_c if (hoy - i["fecha"]).days > DIAS_ANTICIPO]
    total_dinero = sum(float(i["importe"]) for i in libro.items if i["clase"] == "dinero")
    if sum(_ars(i, tc) for i in viejos) > max(1.0, total_dinero * TOLERANCIA_CIERRE):
        libro.marcas.add("pago-de-mas")
    if any(i.get("suspendido") for i in libro.items):
        libro.marcas.add("factura-suspendida")
    return {
        "aplicaciones": libro.aplicaciones,
        "pendienteDebitos": _r(pend_d),
        "pendienteCreditos": _r(pend_c),
        "anticipoAbierto": _r(anticipo),
        "marcas": sorted(libro.marcas),
        "huella": huella(libro.aplicaciones),
        "items": libro.items,
    }
