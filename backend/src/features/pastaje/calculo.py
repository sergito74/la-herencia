"""039: cálculo puro de la liquidación mensual de pastaje (sin base de datos).

Reglas (spec 039): cabezas por día calendario; el día de ingreso se cobra y el
de egreso/muerte/faltante no (el evento rige desde su fecha); las crías cobran
desde el destete; recuento no cambia cabezas. Precio = promedio simple del INMAG
de los días con hacienda e índice publicado, redondeado a centavos. Sin redondeo
intermedio en kg; neto e IVA a centavos.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


class SinIndice(ValueError):
    pass


@dataclass(frozen=True)
class Movimiento:
    fecha: date
    tipo: str
    categoria: int
    cabezas: int


@dataclass(frozen=True)
class Tarifa:
    categoria: int
    tipo: str  # kg_novillo | fijo_ars | fijo_usd
    valor: Decimal
    desde: date


@dataclass
class Tramo:
    categoria: int
    desde: date
    hasta: date
    cabezas: int
    dias: int
    valor_mes: Decimal
    tipo: str
    kg: Decimal = Decimal(0)
    importe: Decimal = Decimal(0)


@dataclass
class Liquidacion:
    periodo: date
    dias_mes: int
    tramos: list[Tramo] = field(default_factory=list)
    indices: list[tuple[date, Decimal]] = field(default_factory=list)
    precio: Decimal | None = None
    kg: Decimal = Decimal(0)
    neto: Decimal = Decimal(0)
    iva: Decimal = Decimal(0)
    total: Decimal = Decimal(0)
    moneda: str = "ARS"


def _r(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def _estado(movs: list[Movimiento], dia: date) -> tuple[dict[int, int], dict[int, int]]:
    """(cobrables, crías al pie sin destetar) por categoría al `dia`. Las bajas de una categoría
    con crías sin destetar descuentan primero esas crías, que todavía no cobraban."""
    cob: dict[int, int] = {}
    crias: dict[int, int] = {}
    for m in sorted((m for m in movs if m.fecha <= dia), key=lambda m: m.fecha):
        c = m.categoria
        if m.tipo == "nacimiento":
            crias[c] = crias.get(c, 0) + m.cabezas
        elif m.tipo == "destete":
            crias[c] = crias.get(c, 0) - m.cabezas
            cob[c] = cob.get(c, 0) + m.cabezas
        elif m.tipo == "ingreso":
            cob[c] = cob.get(c, 0) + m.cabezas
        elif m.tipo in ("egreso", "muerte", "faltante"):
            de_crias = min(m.cabezas, max(crias.get(c, 0), 0)) if m.tipo != "egreso" else 0
            crias[c] = crias.get(c, 0) - de_crias
            cob[c] = cob.get(c, 0) - (m.cabezas - de_crias)
    return cob, crias


def cabezas_por_dia(movs: list[Movimiento], dia: date) -> dict[int, int]:
    """Cabezas cobrables por categoría vigentes en `dia` (eventos con fecha <= dia)."""
    return {k: v for k, v in _estado(movs, dia)[0].items() if v}


def validar_bitacora(movs: list[Movimiento]) -> None:
    """Ninguna categoría puede quedar con cabezas negativas en ninguna fecha; crías destetadas <= nacidas."""
    for d in sorted({m.fecha for m in movs}):
        neg = {k: v for k, v in cabezas_por_dia(movs, d).items() if v < 0}
        if neg:
            raise ValueError(f"La bitácora deja cabezas negativas el {d:%d/%m/%Y}: {neg}")
        crias = {k: v for k, v in _estado(movs, d)[1].items() if v < 0}
        if crias:
            raise ValueError(f"Al {d:%d/%m/%Y} hay más destetes que crías nacidas sin destetar: {crias}")


def _tarifa(tarifas: list[Tarifa], cat: int, dia: date) -> Tarifa:
    vig = [t for t in tarifas if t.categoria == cat and t.desde <= dia]
    if not vig:
        raise ValueError(f"No hay tarifa vigente para la categoría {cat} al {dia:%d/%m/%Y}.")
    return max(vig, key=lambda t: t.desde)


def liquidar(
    periodo: date,
    movs: list[Movimiento],
    tarifas: list[Tarifa],
    indices: dict[date, Decimal],
    alicuota: Decimal = Decimal("21"),
    hasta: date | None = None,
) -> Liquidacion:
    """Liquida el mes de `periodo`. `hasta` limita el cálculo (estimado del mes en curso)."""
    ini = periodo.replace(day=1)
    dias_mes = calendar.monthrange(ini.year, ini.month)[1]
    fin = ini.replace(day=dias_mes)
    if hasta is not None:
        fin = min(fin, hasta)
    liq = Liquidacion(periodo=ini, dias_mes=dias_mes)
    vivos = [m for m in movs]
    abiertos: dict[tuple, Tramo] = {}
    dias_con_hacienda: list[date] = []
    d = ini
    while d <= fin:
        cab = cabezas_por_dia(vivos, d)
        if cab:
            dias_con_hacienda.append(d)
        claves = set()
        for cat, n in sorted(cab.items()):
            t = _tarifa(tarifas, cat, d)
            clave = (cat, n, t.tipo, t.valor)
            claves.add(clave)
            tr = abiertos.get(clave)
            if tr and tr.hasta == d - timedelta(days=1):
                tr.hasta, tr.dias = d, tr.dias + 1
            else:
                tr = Tramo(cat, d, d, n, 1, t.valor, t.tipo)
                liq.tramos.append(tr)
                abiertos[clave] = tr
        d += timedelta(days=1)
    tipos = {t.tipo for t in liq.tramos}
    if "fijo_usd" in tipos and tipos - {"fijo_usd"}:
        raise ValueError("Un contrato no puede mezclar tarifas en US$ y en pesos en el mismo mes.")
    liq.moneda = "USD" if tipos == {"fijo_usd"} else "ARS"
    if "kg_novillo" in tipos:
        liq.indices = [(x, indices[x]) for x in dias_con_hacienda if indices.get(x) is not None]
        if not liq.indices:
            raise SinIndice(f"No hay índice INMAG publicado en los días con hacienda de {ini:%m/%Y}.")
        liq.precio = _r(sum(v for _, v in liq.indices) / len(liq.indices))
    bruto = Decimal(0)
    for tr in liq.tramos:
        prop = Decimal(tr.cabezas * tr.dias) / dias_mes
        if tr.tipo == "kg_novillo":
            tr.kg = tr.valor_mes * prop
            tr.importe = tr.kg * liq.precio
            liq.kg += tr.kg
        else:
            tr.importe = tr.valor_mes * prop
        bruto += tr.importe
    liq.neto = _r(bruto)
    liq.iva = _r(liq.neto * alicuota / 100)
    liq.total = liq.neto + liq.iva
    return liq


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def texto_factura(liq: Liquidacion, nombres: dict[int, str]) -> list[str]:
    """Una línea por categoría: 'Servicio de pastaje de 70 Vaquillonas del 25 al 30 de septiembre de 2026'."""
    grupos: list[list] = []
    for t in sorted(liq.tramos, key=lambda t: (t.categoria, t.desde)):
        g = grupos[-1] if grupos else None
        if g and g[0] == t.categoria and g[1] == t.cabezas and g[3] + timedelta(days=1) == t.desde:
            g[3] = t.hasta
        else:
            grupos.append([t.categoria, t.cabezas, t.desde, t.hasta])
    return [f"Servicio de pastaje de {cab} {nombres.get(cat, cat)} del {d0.day} al {d1.day} de {MESES[d0.month - 1]} de {d0.year}"
            for cat, cab, d0, d1 in grupos]


def campania(periodo: date) -> str:
    """Campaña ganadera julio–junio: septiembre 2026 → '2026/2027'."""
    a = periodo.year if periodo.month >= 7 else periodo.year - 1
    return f"{a}/{a + 1}"
