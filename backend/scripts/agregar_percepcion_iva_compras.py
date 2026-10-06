"""Percepción de IVA al pie de Compras (006, FR-018).

Uso desde backend: .venv/Scripts/python.exe -m scripts.agregar_percepcion_iva_compras
Solo WC: backup COPY_ONLY verificado antes de DDL; columna y vistas en una
transacción. No reclasifica importes históricos. Conserva las definiciones
vigentes de las vistas, agregando únicamente el nuevo término al total.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

VISTAS = ("vw_Compras_ImporteDocumento", "vw_Cns_Total_Compra")
TERMINO_EXISTENTE = "+ ISNULL(c.[Ingresos Brutos], 0)"
TERMINO_NUEVO = "+ ISNULL(c.PercepcionIVA, 0)"


def extender_vista(definicion: str) -> str | None:
    declaracion = r"^\s*(?:CREATE\s+(?:OR\s+ALTER\s+)?|ALTER\s+)VIEW\b"
    if not re.match(declaracion, definicion, flags=re.IGNORECASE):
        raise ValueError("No se encontró la declaración de la vista.")
    if definicion.count(TERMINO_EXISTENTE) != 1:
        raise ValueError("Definición de totales inesperada; no se modifica la vista.")
    referencias = len(re.findall(r"\bPercepcionIVA\b", definicion, flags=re.IGNORECASE))
    if referencias == 1 and definicion.count(TERMINO_NUEVO) == 1:
        return None
    if referencias:
        raise ValueError("Definición de totales inesperada; no se modifica la vista.")
    nueva = definicion.replace(TERMINO_EXISTENTE, TERMINO_EXISTENTE + "\n        " + TERMINO_NUEVO)
    nueva, cambios = re.subn(declaracion,
                            "ALTER VIEW", nueva, count=1, flags=re.IGNORECASE)
    if cambios != 1:
        raise ValueError("No se encontró la declaración de la vista.")
    return nueva


def _totales(cursor) -> dict:
    return {
        "documentos": list(cursor.execute(
            "SELECT IdDeuda, ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento ORDER BY IdDeuda"
        ).fetchall()),
        "compras": list(cursor.execute(
            "SELECT IdDeuda, GranTotal FROM dbo.vw_Cns_Total_Compra ORDER BY IdDeuda"
        ).fetchall()),
    }


def main() -> None:
    _assert_target_is_wc()
    backup = backup_verificado("percepcion-iva-compras")
    print(f"Backup verificado: {backup}", flush=True)
    log = Path(__file__).resolve().parents[2] / "backups" / f"percepcion_iva_{datetime.now():%Y%m%d_%H%M%S}.json"
    log.parent.mkdir(exist_ok=True)
    registro = {"backup_verificado": backup, "estado": "preparado", "vistas_previas": {}}
    log.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cursor = conn.cursor()
        if cursor.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("La migración solo puede ejecutarse en WC.")
        cursor.execute("SET XACT_ABORT ON")
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        cursor.execute("BEGIN TRANSACTION")
        try:
            antes = _totales(cursor)
            columna = cursor.execute(
                "SELECT DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='Compras' AND COLUMN_NAME='PercepcionIVA'"
            ).fetchone()
            if columna is None:
                cursor.execute(
                    "ALTER TABLE dbo.Compras ADD PercepcionIVA money NOT NULL "
                    "CONSTRAINT DF_Compras_PercepcionIVA DEFAULT (0) WITH VALUES"
                )
            elif tuple(columna) != ("money", "NO"):
                raise ValueError("PercepcionIVA ya existe con un tipo o nulabilidad inesperados.")
            for nombre in VISTAS:
                definicion = cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID(?))", (f"dbo.{nombre}",)).fetchone()[0]
                if not definicion:
                    raise ValueError(f"No se pudo leer la vista dbo.{nombre}.")
                registro["vistas_previas"][nombre] = definicion
                nueva = extender_vista(definicion)
                if nueva:
                    cursor.execute(nueva)
            log.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
            if _totales(cursor) != antes:
                raise ValueError("La migración alteraría totales existentes; se revierte completa.")
            cursor.execute("COMMIT TRANSACTION")
        except Exception:
            cursor.execute("IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION")
            raise
    registro.update(estado="aplicado", documentos_verificados=len(antes["documentos"]),
                    compras_verificadas=len(antes["compras"]))
    log.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PercepcionIVA y vistas listas; totales históricos sin cambios. Registro: {log}")


if __name__ == "__main__":
    main()
