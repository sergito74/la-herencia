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
2. Con `regla_029` (regla aprobada el 29/10/2026, sección 12 de la auditoría
   de aplicaciones): pares de importe idéntico y combinaciones únicas de 2 o
   3 documentos (ver `emparejar`), y el reparto no deja que un pago adelantado
   salte más de un ciclo (`CICLO`): ese hueco queda a la vista como anticipo.
3. Reparto cronológico único (ver `reparto`), en orden de (vencimiento,
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
CICLO = 60             # regla_029: un pago no cubre documentos de más de un ciclo después
REPETIDOS = 3          # regla_029: importe que se repite tantas veces en ±1 ciclo (cuotas, abonos) → FIFO
COMBINACION_DIAS = 365
COMBINACION_CANDIDATOS = 20

TcFn = Callable[[date], "float | None"]


def _r(x: float) -> float:
    return round(x + 0.0, 2)


def _dias(a: dict, b: dict) -> int:
    """Días entre dos renglones tomando cada uno como el intervalo [emisión, vencimiento]: 0 si se superponen."""
    if a["vencimiento"] < b["fecha"]:
        return (b["fecha"] - a["vencimiento"]).days
    if b["vencimiento"] < a["fecha"]:
        return (a["fecha"] - b["vencimiento"]).days
    return 0


def _orden(item: dict) -> tuple:
    origen, ident, cuota = item["clave"]
    return (item["vencimiento"] or date.min, str(item.get("nro") or ""), origen, ident, cuota or 0)


class _Libro:
    def __init__(self, items: list[dict], tc: TcFn, regla_029: bool = False):
        self.items = sorted((dict(i) for i in items), key=_orden)
        for i in self.items:
            i["rem"] = float(i["importe"])
        self.tc = tc
        self.aplicaciones: list[dict] = []
        self.marcas: set[str] = set()
        self.regla_029 = regla_029

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

    def emparejar(self) -> None:
        """regla_029, antes del reparto. Distancia entre un pago y un documento: 0 si el
        pago cae entre la emisión y el vencimiento; si no, los días hasta el más cercano
        de los dos (`_dias`). Para cada renglón entero, por vencimiento:
        1) un documento del otro lado, entero y de importe idéntico: el de
           vencimiento más viejo (primero las vencidas), después el de número más bajo;
           si el importe se repite `REPETIDOS` veces en ±1 ciclo, lo decide el FIFO, salvo que haya
           uno solo del mismo día (compra pagada en el acto);
        2) si no, una única combinación de 2 o 3 documentos abiertos del otro
           lado (a menos de un año) que sume exacto; si hay más de una, nada.
           Una factura entera busca también la combinación de 2 o 3 pagos enteros."""
        from itertools import combinations
        enteros = lambda i: not i.get("suspendido") and i["rem"] > 0 and abs(i["rem"] - float(i["importe"])) <= TOLERANCIA_CENTAVOS
        for x in sorted(self.items, key=lambda i: (i["vencimiento"], _orden(i))):
            if not enteros(x):
                continue
            otros = [y for y in self.items if y["lado"] != x["lado"] and y["clase"] == "doc" and y is not x
                     and y["moneda"] == x["moneda"] and not y.get("suspendido") and y["rem"] > 0]
            if x["clase"] == "doc":
                otros = [y for y in otros if y["lado"] == "D"] if x["lado"] == "C" else []
            if x["clase"] == "doc" and x["lado"] == "D":   # factura pagada con 2 o 3 pagos que suman exacto
                otros = [y for y in self.items if y["lado"] == "C" and y["clase"] == "dinero" and y["moneda"] == x["moneda"]
                         and enteros(y)]
            iguales = [] if x["clase"] == "doc" and x["lado"] == "D" else [
                y for y in otros if enteros(y) and abs(y["rem"] - x["rem"]) <= 0.01]
            cerca = [y for y in iguales if _dias(x, y) <= CICLO]
            mismo_dia = [y for y in iguales if _dias(x, y) == 0]
            if len(mismo_dia) == 1:   # único pago entre emisión y vencimiento: no importa que el importe se repita
                iguales = mismo_dia
            if iguales and (len(cerca) < REPETIDOS or len(mismo_dia) == 1):
                # Sergio 29/10/2026: el pago va primero a la factura vencida más vieja; si ninguna venció, a la próxima a vencer
                orden = sorted(iguales, key=lambda y: (y["vencimiento"], str(y.get("nro") or "")))
                d, c = (orden[0], x) if x["lado"] == "C" else (x, orden[0])
                self._aplicar(d, c, None, "importe-identico")
                continue
            cand = sorted([y for y in otros if _dias(x, y) <= COMBINACION_DIAS and y["rem"] < x["rem"]],
                          key=lambda y: _dias(x, y))[:COMBINACION_CANDIDATOS]
            combos = [g for n in (2, 3) for g in combinations(cand, n) if abs(sum(y["rem"] for y in g) - x["rem"]) <= 0.01]
            if len(combos) == 1:
                for y in combos[0]:
                    d, c = (y, x) if x["lado"] == "C" else (x, y)
                    self._aplicar(d, c, None, "combinacion")
            elif len(combos) > 1:
                self.marcas.add("combinacion-ambigua")

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
            if (self.regla_029 and x["clase"] == "doc" and y["clase"] == "dinero"
                    and (x["fecha"] - y["fecha"]).days > CICLO):   # contra la emisión: pagar antes de vencer es normal
                self.marcas.add("hueco")   # pago adelantado más de un ciclo: queda como anticipo, no arrastra
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


def recalcular(items: list[dict], fijos: list[dict], tc: TcFn, hoy: date, regla_029: bool = False) -> dict:
    """Devuelve aplicaciones, pendientes y marcas de un contacto."""
    libro = _Libro(items, tc, regla_029)
    libro.fijos(fijos)
    if regla_029:
        libro.emparejar()
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
