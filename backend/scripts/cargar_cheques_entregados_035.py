"""035 — Carga los cheques entregados (e-cheqs emitidos, endosos y cheques en papel) y los cruza con Galicia.

Fuentes (solo lectura): los PDF de `Documents/La Herencia/Administracion y gestion/Cuentas a pagar/Cheques electronicos`
y la planilla `Pagos Cheques Diferidos.xlsx` de esa carpeta. Escribe en `WC.dbo.ChequesEntregados` (re-ejecutable:
reemplaza lo cargado), con respaldo verificado.

Uso (desde backend/):
    python -m scripts.cargar_cheques_entregados_035 --verificar    # no escribe: cuenta, cruza e informa
    python -m scripts.cargar_cheques_entregados_035                # respaldo verificado y carga
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.auditoria_cuentas import echeqs

RAIZ = Path.home() / "Documents" / "La Herencia" / "Administracion y gestion" / "Cuentas a pagar" / "Cheques electronicos"
PLANILLA = RAIZ / "Pagos Cheques Diferidos.xlsx"

DDL = """
IF OBJECT_ID('dbo.ChequesEntregados', 'U') IS NULL
CREATE TABLE dbo.ChequesEntregados (
    IdEntrega int IDENTITY(1,1) NOT NULL CONSTRAINT PK_ChequesEntregados PRIMARY KEY,
    Tipo varchar(10) NOT NULL CONSTRAINT CK_ChequesEntregados_Tipo CHECK (Tipo IN ('emitido', 'endoso', 'papel')),
    Numero varchar(20) NULL,
    Importe money NOT NULL,
    FechaEntrega date NULL,
    FechaEntregaEstimada bit NOT NULL CONSTRAINT DF_ChequesEntregados_Est DEFAULT 0,
    FechaPago date NULL,
    Beneficiario varchar(150) NULL,
    CuitBeneficiario varchar(20) NULL,
    Descripcion varchar(250) NULL,
    Documento varchar(100) NULL,
    ImporteUsd money NULL,
    TcEmision decimal(18, 4) NULL,
    Estado varchar(40) NULL,
    Fuente varchar(12) NOT NULL,
    Archivo varchar(300) NULL,
    MedioMovimiento varchar(20) NULL,
    IdMovimiento int NULL,
    FechaCarga datetime2 NOT NULL CONSTRAINT DF_ChequesEntregados_Carga DEFAULT SYSDATETIME()
)
"""


def _movimientos_galicia() -> list[dict]:
    return [{"id": f["id"], "fecha": f["fecha"].date() if isinstance(f["fecha"], datetime) else f["fecha"], "descripcion": f["d"], "debito": f["deb"]}
            for f in fetch_all("SELECT IdMovimiento AS id, Fecha AS fecha, [Descripción] AS d, [Débitos] AS deb FROM dbo.[Movimientos Galicia] "
                               "WHERE [Débitos] IS NOT NULL AND [Débitos] > 0", ())]


def armar() -> tuple[list[dict], list[str], dict[int, dict]]:
    pdfs, ilegibles = echeqs.leer_carpeta(RAIZ)
    cheques = echeqs.fusionar(pdfs, echeqs.leer_planilla(PLANILLA))
    cruces = echeqs.cruzar_con_galicia(cheques, _movimientos_galicia())
    return cheques, ilegibles, cruces


def informe(cheques: list[dict], ilegibles: list[str], cruces: dict[int, dict]) -> None:
    from collections import Counter

    print(f"Cheques: {len(cheques)} {dict(Counter(c['tipo'] for c in cheques))}; fuentes {dict(Counter(c['fuente'] for c in cheques))}")
    print(f"Con fecha de entrega: {sum(1 for c in cheques if c.get('fechaEntrega'))} (estimadas por la fecha del archivo: {sum(1 for c in cheques if c.get('fechaEstimada'))})")
    print(f"Cruzados con un débito de Galicia: {len(cruces)}")
    print(f"PDF escaneados que no se pudieron leer ({len(ilegibles)}):")
    for x in ilegibles:
        print("   ", x)


def cargar(cheques: list[dict], cruces: dict[int, dict]) -> None:
    from src.features.vinculos.backup import backup_verificado

    print(f"Respaldo verificado: {backup_verificado('cheques-entregados-035')}")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        cur.execute(DDL)
        cur.execute("DELETE FROM dbo.ChequesEntregados")
        filas = []
        for i, c in enumerate(cheques):
            m = cruces.get(i)
            filas.append((
                c["tipo"], (c.get("numero") or "")[:20] or None, c["importe"], c.get("fechaEntrega"), 1 if c.get("fechaEstimada") else 0, c.get("fechaPago"),
                (c.get("beneficiario") or "")[:150] or None, (c.get("cuitBeneficiario") or "")[:20] or None, (c.get("descripcion") or "")[:250] or None,
                (c.get("documento") or "")[:100] or None, c.get("importeUsd"), c.get("tcEmision"), (c.get("estado") or "")[:40] or None, c["fuente"],
                (c.get("archivo") or "")[:300] or None, "galicia" if m else None, m["id"] if m else None))
        cur.executemany(
            "INSERT INTO dbo.ChequesEntregados (Tipo, Numero, Importe, FechaEntrega, FechaEntregaEstimada, FechaPago, Beneficiario, CuitBeneficiario, "
            "Descripcion, Documento, ImporteUsd, TcEmision, Estado, Fuente, Archivo, MedioMovimiento, IdMovimiento) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", filas)
        conn.commit()
        print("Cargadas", cur.execute("SELECT COUNT(*) FROM dbo.ChequesEntregados").fetchone()[0], "filas.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str]) -> None:
    _assert_target_is_wc()
    cheques, ilegibles, cruces = armar()
    informe(cheques, ilegibles, cruces)
    if "--verificar" in argv:
        print("Solo verificación: no se escribió nada.")
        return
    cargar(cheques, cruces)


if __name__ == "__main__":
    main(sys.argv[1:])
