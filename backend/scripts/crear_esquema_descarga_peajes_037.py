"""037 — Esquema de la descarga de comprobantes de peajes (solo en `WC`).

Crea, de forma idempotente:
  * dbo.DescargaPeajes_Ejecuciones        (una fila por corrida manual o semanal)
  * dbo.DescargaPeajes_EjecucionPortales  (resultado de cada portal en cada corrida)
  * dbo.DescargaPeajes_Documentos         (cada PDF bajado, con su estado de carga en Compras)

Uso (desde backend/):
    python -m scripts.crear_esquema_descarga_peajes_037 --verificar            # no escribe
    python -m scripts.crear_esquema_descarga_peajes_037                        # respaldo verificado y creación
    python -m scripts.crear_esquema_descarga_peajes_037 --importar-manifiesto  # marca como 'historico' lo ya bajado
    python -m scripts.crear_esquema_descarga_peajes_037 --revertir             # borra las tablas si no hubo ejecuciones

`--importar-manifiesto` lee Dropbox\\...\\Compras\\_descargas_portales.json (la
lista de claves que usaba el script anterior, 98 al 2026-10-16) y las inserta
como documentos `historico`, para que el módulo no vuelva a bajarlas.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

TABLAS = ("DescargaPeajes_Documentos", "DescargaPeajes_EjecucionPortales", "DescargaPeajes_Ejecuciones")
MANIFIESTO = Path.home() / "Dropbox" / "Giamigli de Bolivar SA" / "Compras" / "_descargas_portales.json"

DDL = [
    """
    IF OBJECT_ID('dbo.DescargaPeajes_Ejecuciones', 'U') IS NULL
    CREATE TABLE dbo.DescargaPeajes_Ejecuciones (
        IdEjecucion int IDENTITY(1,1) NOT NULL CONSTRAINT PK_DescargaPeajes_Ejecuciones PRIMARY KEY,
        Origen varchar(10) NOT NULL CONSTRAINT CK_DescargaPeajes_Ejecuciones_Origen CHECK (Origen IN ('manual', 'semanal')),
        Usuario varchar(60) NULL,
        Inicio datetime2 NOT NULL CONSTRAINT DF_DescargaPeajes_Ejecuciones_Inicio DEFAULT SYSDATETIME(),
        Fin datetime2 NULL,
        Estado varchar(15) NOT NULL CONSTRAINT CK_DescargaPeajes_Ejecuciones_Estado
            CHECK (Estado IN ('en_curso', 'completa', 'con_errores', 'incompleta', 'salteada')),
        Mensaje nvarchar(400) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.DescargaPeajes_EjecucionPortales', 'U') IS NULL
    CREATE TABLE dbo.DescargaPeajes_EjecucionPortales (
        IdEjecucion int NOT NULL CONSTRAINT FK_DescargaPeajes_EjecucionPortales_Ejecucion
            REFERENCES dbo.DescargaPeajes_Ejecuciones (IdEjecucion),
        Portal varchar(20) NOT NULL CONSTRAINT CK_DescargaPeajes_EjecucionPortales_Portal
            CHECK (Portal IN ('TelepeajePlus', 'TelePASE', 'CEAMSE', 'AUBASA')),
        Estado varchar(15) NOT NULL CONSTRAINT CK_DescargaPeajes_EjecucionPortales_Estado
            CHECK (Estado IN ('pendiente', 'en_curso', 'ok', 'error', 'sin_credenciales')),
        Nuevos int NOT NULL CONSTRAINT DF_DescargaPeajes_EP_Nuevos DEFAULT 0,
        Existentes int NOT NULL CONSTRAINT DF_DescargaPeajes_EP_Existentes DEFAULT 0,
        Cargados int NOT NULL CONSTRAINT DF_DescargaPeajes_EP_Cargados DEFAULT 0,
        Pendientes int NOT NULL CONSTRAINT DF_DescargaPeajes_EP_Pendientes DEFAULT 0,
        Error nvarchar(400) NULL,
        CONSTRAINT PK_DescargaPeajes_EjecucionPortales PRIMARY KEY (IdEjecucion, Portal)
    )
    """,
    """
    IF OBJECT_ID('dbo.DescargaPeajes_Documentos', 'U') IS NULL
    CREATE TABLE dbo.DescargaPeajes_Documentos (
        IdDocumento int IDENTITY(1,1) NOT NULL CONSTRAINT PK_DescargaPeajes_Documentos PRIMARY KEY,
        Clave varchar(120) NOT NULL CONSTRAINT UQ_DescargaPeajes_Documentos_Clave UNIQUE,
        Portal varchar(20) NOT NULL CONSTRAINT CK_DescargaPeajes_Documentos_Portal
            CHECK (Portal IN ('TelepeajePlus', 'TelePASE', 'CEAMSE', 'AUBASA')),
        Proveedor varchar(40) NOT NULL,
        IdContacto int NULL,
        FechaDocumento date NULL,
        NumeroDocumento varchar(30) NULL,
        TotalImpreso decimal(18,2) NULL,
        Ruta nvarchar(400) NULL,
        IdEjecucion int NULL CONSTRAINT FK_DescargaPeajes_Documentos_Ejecucion
            REFERENCES dbo.DescargaPeajes_Ejecuciones (IdEjecucion),
        EstadoCarga varchar(20) NOT NULL CONSTRAINT CK_DescargaPeajes_Documentos_EstadoCarga
            CHECK (EstadoCarga IN ('cargado_auto', 'ya_cargado', 'pendiente', 'historico')),
        Motivo nvarchar(300) NULL,
        IdCompra int NULL,
        Creado datetime2 NOT NULL CONSTRAINT DF_DescargaPeajes_Documentos_Creado DEFAULT SYSDATETIME()
    )
    """,
]

PORTAL_POR_PREFIJO = {"tp": "TelepeajePlus", "ts": "TelePASE", "ceamse": "CEAMSE", "aubasa": "AUBASA"}


def _conexion(autocommit: bool = True):
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=autocommit)
    if conn.cursor().execute("SELECT DB_NAME()").fetchone()[0] != "WC":
        conn.close()
        raise RuntimeError("Solo sobre WC")
    return conn


def verificar() -> None:
    conn = _conexion()
    try:
        cur = conn.cursor()
        for t in TABLAS:
            existe = cur.execute("SELECT OBJECT_ID(?, 'U')", f"dbo.{t}").fetchone()[0] is not None
            print(f"dbo.{t}: {'existe' if existe else 'se creará'}")
        print("Solo verificación: no se escribió nada.")
    finally:
        conn.close()


def aplicar() -> None:
    from src.features.vinculos.backup import backup_verificado

    print(f"Respaldo verificado: {backup_verificado('esquema-descarga-peajes-037')}")
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        for sql in DDL:
            cur.execute(sql)
        conn.commit()
        for t in TABLAS:
            print(f"dbo.{t}: {cur.execute(f'SELECT COUNT(*) FROM dbo.{t}').fetchone()[0]} filas")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def importar_manifiesto() -> None:
    claves = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        nuevas = 0
        for clave in claves:
            portal = PORTAL_POR_PREFIJO[clave.split("-", 1)[0]]
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM dbo.DescargaPeajes_Documentos WHERE Clave = ?) "
                "INSERT INTO dbo.DescargaPeajes_Documentos (Clave, Portal, Proveedor, EstadoCarga, Motivo) "
                "VALUES (?, ?, 'desconocido', 'historico', 'Bajado antes del módulo 037')",
                clave, clave, portal,
            )
            nuevas += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM dbo.DescargaPeajes_Documentos WHERE EstadoCarga = 'historico'").fetchone()[0]
        print(f"Manifiesto: {len(claves)} claves; {nuevas} insertadas ahora; {total} documentos 'historico' en total.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def revertir() -> None:
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        existe = cur.execute("SELECT OBJECT_ID('dbo.DescargaPeajes_Ejecuciones', 'U')").fetchone()[0]
        usadas = cur.execute("SELECT COUNT(*) FROM dbo.DescargaPeajes_Ejecuciones").fetchone()[0] if existe else 0
        if usadas:
            raise SystemExit(f"Hay {usadas} ejecuciones registradas: no se borran las tablas.")
        for t in TABLAS:
            cur.execute(f"IF OBJECT_ID('dbo.{t}', 'U') IS NOT NULL DROP TABLE dbo.{t}")
        conn.commit()
        print("Tablas de la descarga de peajes eliminadas.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str]) -> None:
    if "--verificar" in argv:
        verificar()
    elif "--revertir" in argv:
        revertir()
    elif "--importar-manifiesto" in argv:
        importar_manifiesto()
    else:
        aplicar()


if __name__ == "__main__":
    main(sys.argv[1:])
