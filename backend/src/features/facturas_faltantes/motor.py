"""044 — Motor del detector de facturas faltantes (lógica pura, sin SQL).

Reglas acordadas en specs/036/auditoria-aplicaciones-20261028.md §7 y research.md (044):
- el ciclo se aprende de la mediana de las distancias entre las últimas 12-24 facturas;
- los períodos se cuentan por secuencia de facturas (no por mes calendario): entre dos facturas separadas por n ciclos faltan
  n-1 períodos; dos facturas en el mismo período no tapan un faltante de otro;
- todo resultado es una alarma "a verificar", nunca un error confirmado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median

CICLOS = {30: "mensual", 60: "bimestral", 90: "trimestral"}
MINIMO_FACTURAS = 6
VENTANA_MESES = 24
TOLERANCIA = 0.25
PROPORCION_EN_RANGO = 0.7
CICLOS_PARA_BAJA = 3
CAMBIO_MONTO = 0.30


@dataclass
class Comprobante:
    fecha: date
    importe: float
    numero: str = ""
    id_deuda: int | None = None
    cantidad: int = 1


@dataclass
class Periodo:
    desde: date
    hasta: date
    esperada: date
    estado: str  # llego | pendiente | atrasada | baja | faltante
    monto_esperado: float | None = None
    comprobante: Comprobante | None = None
    cambio_monto: bool = False


@dataclass
class Perfil:
    ciclo: int | None
    fijado: bool = False
    sin_ciclo: bool = False
    margen: int | None = None
    dado_de_baja: bool = False


@dataclass
class Resultado:
    ciclo: int | None
    actual: Periodo | None
    faltantes: list[Periodo] = field(default_factory=list)


AGRUPAR_DIAS = 10


def agrupar(comprobantes: list[Comprobante]) -> list[Comprobante]:
    """Facturas que llegan juntas (varias pólizas, varias líneas) forman un solo envío del período."""
    grupos: list[Comprobante] = []
    for c in sorted(comprobantes, key=lambda x: x.fecha):
        if grupos and (c.fecha - grupos[-1].fecha).days < AGRUPAR_DIAS:
            g = grupos[-1]
            grupos[-1] = Comprobante(fecha=g.fecha, importe=g.importe + c.importe, numero=c.numero, id_deuda=c.id_deuda,
                                     cantidad=g.cantidad + 1)
        else:
            grupos.append(Comprobante(fecha=c.fecha, importe=c.importe, numero=c.numero, id_deuda=c.id_deuda))
    return grupos


def margen_de(ciclo: int, margen: int | None = None) -> int:
    return margen if margen is not None else (15 if ciclo <= 30 else 25)


def aprender_ciclo(fechas: list[date], hoy: date) -> int | None:
    """Ciclo en días (30/60/90) o None si no hay un ciclo claro."""
    limite = hoy - timedelta(days=VENTANA_MESES * 30)
    recientes = [c.fecha for c in agrupar([Comprobante(fecha=f, importe=0) for f in fechas if f >= limite])]
    if len(recientes) < MINIMO_FACTURAS:
        return None
    recientes = recientes[-24:]
    distancias = [(b - a).days for a, b in zip(recientes, recientes[1:]) if (b - a).days > 0]
    if not distancias:
        return None
    m = median(distancias)
    for ciclo in CICLOS:
        if abs(m - ciclo) <= ciclo * TOLERANCIA:
            # Las distancias "dobles" (un período faltante) y las de 0 (dos comprobantes juntos) no invalidan el ciclo.
            en_rango = [d for d in distancias if any(abs(d - k * ciclo) <= ciclo * TOLERANCIA for k in (1, 2, 3))]
            if len(en_rango) >= PROPORCION_EN_RANGO * len(distancias):
                return ciclo
    return None


def _monto_esperado(previos: list[Comprobante]) -> float | None:
    ultimos = [c.importe for c in previos if c.importe > 1][-3:]
    return round(median(ultimos), 2) if ultimos else None


def evaluar(comprobantes: list[Comprobante], perfil: Perfil, hoy: date, desde_historico: date | None = None) -> Resultado:
    """Períodos faltantes en la historia reciente y estado del período en curso."""
    ciclo = perfil.ciclo
    if perfil.sin_ciclo or not ciclo or not comprobantes:
        return Resultado(ciclo=None, actual=None)
    facturas = agrupar(comprobantes)
    marg = margen_de(ciclo, perfil.margen)
    faltantes: list[Periodo] = []
    for i, (a, b) in enumerate(zip(facturas, facturas[1:])):
        n = round((b.fecha - a.fecha).days / ciclo)
        for k in range(1, n):
            esperada = a.fecha + timedelta(days=k * ciclo)
            if desde_historico and esperada < desde_historico:
                continue
            faltantes.append(Periodo(desde=esperada - timedelta(days=ciclo // 2), hasta=esperada + timedelta(days=ciclo // 2),
                                     esperada=esperada, estado="faltante", monto_esperado=_monto_esperado(facturas[: i + 1])))
    ultima = facturas[-1]
    monto = _monto_esperado(facturas[:-1]) if len(facturas) > 1 else None
    if perfil.dado_de_baja:
        return Resultado(ciclo=ciclo, actual=None, faltantes=faltantes)
    esperada = ultima.fecha + timedelta(days=ciclo)
    if hoy < esperada - timedelta(days=ciclo // 2):
        # La última factura cubre el período en curso.
        cambio = bool(monto and abs(ultima.importe - monto) > CAMBIO_MONTO * monto)
        actual = Periodo(desde=ultima.fecha - timedelta(days=ciclo // 2), hasta=ultima.fecha + timedelta(days=ciclo // 2),
                         esperada=ultima.fecha, estado="llego", monto_esperado=monto, comprobante=ultima, cambio_monto=cambio)
    elif hoy > ultima.fecha + timedelta(days=CICLOS_PARA_BAJA * ciclo + marg):
        actual = Periodo(desde=esperada - timedelta(days=ciclo // 2), hasta=esperada + timedelta(days=ciclo // 2), esperada=esperada,
                         estado="baja", monto_esperado=_monto_esperado(facturas))
    else:
        estado = "pendiente" if hoy <= esperada + timedelta(days=marg) else "atrasada"
        actual = Periodo(desde=esperada - timedelta(days=ciclo // 2), hasta=esperada + timedelta(days=ciclo // 2), esperada=esperada,
                         estado=estado, monto_esperado=_monto_esperado(facturas))
    return Resultado(ciclo=ciclo, actual=actual, faltantes=faltantes)


def compatible(importe: float, candidatos: list[float], tolerancia: float = 0.01) -> bool:
    """¿El pago coincide con un comprobante o con la suma de hasta 3?"""
    c = [x for x in candidatos if x > 0][:30]
    if any(abs(x - importe) <= tolerancia for x in c):
        return True
    for i in range(len(c)):
        for j in range(i + 1, len(c)):
            if abs(c[i] + c[j] - importe) <= tolerancia:
                return True
            for k in range(j + 1, len(c)):
                if abs(c[i] + c[j] + c[k] - importe) <= tolerancia:
                    return True
    return False
