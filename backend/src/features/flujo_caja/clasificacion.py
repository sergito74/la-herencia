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
    if not _PATRON_TITULAR_PROPIO_BNA.search(concepto):
        return False
    return CUIT_EMPRESA in concepto.replace("-", "").replace(" ", "")


def _es_interno_galicia(grupo_conceptos: str | None) -> bool:
    if not grupo_conceptos:
        return False
    return "inversiones" in grupo_conceptos.casefold()


def es_interno(banco: str, concepto: str | None, grupo_conceptos: str | None = None) -> bool:
    """`banco` es 'BNA' o 'Galicia' (mismo valor que `CuentasBancarias.Banco`)."""
    if banco == "BNA":
        return _es_interno_bna(concepto)
    if banco == "Galicia":
        return _es_interno_galicia(grupo_conceptos)
    return False
