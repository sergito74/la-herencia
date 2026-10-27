"""Reglas de clasificación de movimientos internos (018, research.md §1).

Un movimiento "interno" mueve fondos entre posiciones propias de la empresa
(entre cuentas, o hacia/desde una inversión financiera) y no es ingreso ni
egreso real del negocio agropecuario — se excluye del neto operativo pero
nunca se oculta (FR-002/FR-009).

Reglas angostas a propósito (research.md §1): priorizan no clasificar de más
(un pago real de proveedor marcado como interno por error) sobre no
clasificar de menos. Cualquier caso que no matchee queda "operativo" por
default.
"""

from __future__ import annotations

import re

# CUIT real de la empresa (confirmado contra la constancia de CBU de Galicia,
# 2026-09-24) — usado para distinguir una transferencia entre cuentas propias
# de una transferencia a un tercero con concepto similar.
CUIT_EMPRESA = "30712114602"

_PATRON_TITULAR_PROPIO_BNA = re.compile(
    r"MIS TIT|DIS TIT|TRANSF\.?\s*INT\.?\s*DIST\.?\s*TITULAR", re.IGNORECASE
)


def _es_interno_bna(concepto: str | None) -> bool:
    if not concepto:
        return False
    if "CRED BE O BCO-M" in concepto.upper():
        return True
    if not _PATRON_TITULAR_PROPIO_BNA.search(concepto):
        return False
    return CUIT_EMPRESA in concepto.replace("-", "").replace(" ", "")


def _es_interno_galicia(grupo_conceptos: str | None, concepto: str | None = None) -> bool:
    if grupo_conceptos and "inversiones" in grupo_conceptos.casefold():
        return True
    if concepto and "FIMA" in concepto.upper():
        return True
    return False


COLOCACION_FIMA = "Colocación FIMA"
RESCATE_FIMA = "Rescate FIMA"
CONSTITUCION_PLAZO_FIJO = "Constitución Plazo Fijo"
VENCIMIENTO_PLAZO_FIJO = "Vencimiento Plazo Fijo"
TRASPASO_ENTRE_BANCOS = "Traspaso entre bancos"
TIPOS_INTERNOS = (
    COLOCACION_FIMA,
    RESCATE_FIMA,
    CONSTITUCION_PLAZO_FIJO,
    VENCIMIENTO_PLAZO_FIJO,
    TRASPASO_ENTRE_BANCOS,
)
DIAS_PAREJA_TRASPASO = 3


def _es_plazo_fijo(concepto: str | None) -> bool:
    if not concepto:
        return False
    c = concepto.upper()
    return "PLAZO FIJO" in c or "P.FIJO" in c or "902002" in c or "912002" in c


def _es_interno_caja_efectivo(concepto: str | None, cuenta_caja: str | None = None) -> bool:
    if not concepto:
        return False
    c = concepto.upper()
    if "CAJA CHICA CAMPO" in c:
        return True
    if "RETIRO EFECTIVO GALICIA" in c or "RETIRO CAJERO" in c:
        return True
    if cuenta_caja in ("CampoChica", "Campo Chica") and "APORTE EFECTIVO" in c:
        return True
    return False


def es_interno(banco: str, concepto: str | None, grupo_conceptos: str | None = None) -> bool:
    """`banco` es 'BNA', 'Galicia' o 'Caja Efectivo'."""
    if _es_plazo_fijo(concepto):
        return True
    if banco == "BNA":
        return _es_interno_bna(concepto)
    if banco == "Galicia":
        return _es_interno_galicia(grupo_conceptos, concepto)
    if banco == "Caja Efectivo":
        return _es_interno_caja_efectivo(concepto, grupo_conceptos)
    return False


def tipo_interno(banco: str, importe: float, concepto: str | None, grupo_conceptos: str | None = None) -> str | None:
    """Fila de "Movimientos entre cuentas propias" (030) de un movimiento
    interno según `es_interno`; `None` si el movimiento es operativo."""
    if _es_plazo_fijo(concepto):
        return CONSTITUCION_PLAZO_FIJO if importe < 0 else VENCIMIENTO_PLAZO_FIJO
    if banco == "Galicia" and _es_interno_galicia(grupo_conceptos, concepto):
        return COLOCACION_FIMA if importe < 0 else RESCATE_FIMA
    if banco == "BNA" and _es_interno_bna(concepto):
        return TRASPASO_ENTRE_BANCOS
    if banco == "Caja Efectivo" and _es_interno_caja_efectivo(concepto, grupo_conceptos):
        return TRASPASO_ENTRE_BANCOS
    return None


def _dia(fecha):
    return fecha.date() if hasattr(fecha, "date") else fecha


def emparejar_traspasos(movimientos: list[dict]) -> None:
    """La regla de 018 solo reconoce el lado BNA de un traspaso BNA ↔ Galicia.
    Para que el lado Galicia no infle ingresos/egresos operativos, se lo busca
    (signo opuesto, mismo importe, ≤ 3 días, el más cercano, cada uno una
    sola vez) y se lo marca como el mismo traspaso. Sin pareja → la pata BNA
    queda con `sinContraparte=True`. Modifica `movimientos` en el lugar."""
    usados: set[int] = set()
    galicia = [
        (i, m) for i, m in enumerate(movimientos) if m["banco"] == "Galicia" and not m.get("tipoInterno")
    ]
    for m in movimientos:
        if m.get("tipoInterno") != TRASPASO_ENTRE_BANCOS or m["banco"] != "BNA":
            continue
        candidatos = [
            (abs((_dia(g["fecha"]) - _dia(m["fecha"])).days), i)
            for i, g in galicia
            if i not in usados
            and abs(round(g["importe"], 2) + round(m["importe"], 2)) < 0.005
            and abs((_dia(g["fecha"]) - _dia(m["fecha"])).days) <= DIAS_PAREJA_TRASPASO
        ]
        if not candidatos:
            m["sinContraparte"] = True
            continue
        _, i = min(candidatos)
        usados.add(i)
        movimientos[i]["esInterno"] = True
        movimientos[i]["tipoInterno"] = TRASPASO_ENTRE_BANCOS
