"""035 — Esquema de la auditoría de cuentas corrientes (solo en `WC`).

Crea, de forma idempotente:
  * dbo.AuditoriaParametros                (plazo máximo, umbral, anticipo)
  * dbo.AuditoriaCorrecciones              (una fila por corrección por regla)
  * dbo.AuditoriaCorreccionesCuentas       (una fila por cuenta incluida)
  * dbo.SaldosReferenciaAccessDetalle      (fila a fila de la referencia del Access, hasta el corte)

Uso (desde backend/):
    python -m scripts.crear_esquema_auditoria_035 --verificar   # no escribe
    python -m scripts.crear_esquema_auditoria_035               # respaldo verificado y creación
    python -m scripts.crear_esquema_auditoria_035 --revertir    # borra las tablas nuevas (si están vacías de uso)
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

TABLAS = ("AuditoriaCorreccionesCuentas", "AuditoriaCorrecciones", "AuditoriaParametros", "SaldosReferenciaAccessDetalle",
          "AuditoriaConocidos", "AuditoriaRevisionesHistorial", "AuditoriaRevisiones")

DDL = [
    """
    IF OBJECT_ID('dbo.AuditoriaParametros', 'U') IS NULL
    CREATE TABLE dbo.AuditoriaParametros (
        Clave varchar(60) NOT NULL CONSTRAINT PK_AuditoriaParametros PRIMARY KEY,
        Valor varchar(60) NOT NULL,
        Usuario varchar(60) NULL,
        Fecha datetime2 NOT NULL CONSTRAINT DF_AuditoriaParametros_Fecha DEFAULT SYSDATETIME()
    )
    """,
    """
    IF OBJECT_ID('dbo.AuditoriaCorrecciones', 'U') IS NULL
    CREATE TABLE dbo.AuditoriaCorrecciones (
        IdCorreccion int IDENTITY(1,1) NOT NULL CONSTRAINT PK_AuditoriaCorrecciones PRIMARY KEY,
        Regla varchar(60) NOT NULL,
        Estado varchar(20) NOT NULL CONSTRAINT CK_AuditoriaCorrecciones_Estado
            CHECK (Estado IN ('simulada', 'aplicada', 'revertida', 'descartada')),
        Parametros nvarchar(max) NULL,
        Usuario varchar(60) NULL,
        Fecha datetime2 NOT NULL CONSTRAINT DF_AuditoriaCorrecciones_Fecha DEFAULT SYSDATETIME(),
        UsuarioAplicacion varchar(60) NULL,
        FechaAplicacion datetime2 NULL,
        Respaldo varchar(260) NULL,
        UsuarioReversion varchar(60) NULL,
        FechaReversion datetime2 NULL,
        Resumen nvarchar(max) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.AuditoriaCorreccionesCuentas', 'U') IS NULL
    CREATE TABLE dbo.AuditoriaCorreccionesCuentas (
        IdCorreccion int NOT NULL,
        IdContacto int NOT NULL,
        Tildada bit NOT NULL CONSTRAINT DF_AuditoriaCorreccionesCuentas_Tildada DEFAULT 0,
        SaldoAntes money NULL,
        SaldoDespues money NULL,
        IdsAplicacion nvarchar(max) NULL,
        Detalle nvarchar(max) NULL,
        CONSTRAINT PK_AuditoriaCorreccionesCuentas PRIMARY KEY (IdCorreccion, IdContacto),
        CONSTRAINT FK_AuditoriaCorreccionesCuentas_Correccion FOREIGN KEY (IdCorreccion)
            REFERENCES dbo.AuditoriaCorrecciones (IdCorreccion)
    )
    """,
    """
    IF OBJECT_ID('dbo.SaldosReferenciaAccessDetalle', 'U') IS NULL
    CREATE TABLE dbo.SaldosReferenciaAccessDetalle (
        Origen varchar(60) NOT NULL,
        IdOrigen bigint NOT NULL,
        IdContacto int NOT NULL,
        Fecha datetime2 NULL,
        Deuda decimal(19, 4) NOT NULL,
        Credito decimal(19, 4) NOT NULL,
        FechaCarga datetime2 NOT NULL CONSTRAINT DF_SaldosRefAccessDet_Fecha DEFAULT SYSDATETIME()
    )
    """,
    """
    IF OBJECT_ID('dbo.AuditoriaConocidos', 'U') IS NULL
    CREATE TABLE dbo.AuditoriaConocidos (
        IdConocido int IDENTITY(1,1) NOT NULL CONSTRAINT PK_AuditoriaConocidos PRIMARY KEY,
        Tipo varchar(30) NOT NULL CONSTRAINT CK_AuditoriaConocidos_Tipo CHECK (Tipo IN ('concepto-movimiento', 'cuenta', 'tc-pactado')),
        Clave varchar(200) NOT NULL,
        ImporteRef money NULL,
        Motivo varchar(300) NOT NULL,
        Usuario varchar(60) NULL,
        Fecha datetime2 NOT NULL CONSTRAINT DF_AuditoriaConocidos_Fecha DEFAULT SYSDATETIME(),
        Activo bit NOT NULL CONSTRAINT DF_AuditoriaConocidos_Activo DEFAULT 1,
        UsuarioBaja varchar(60) NULL,
        FechaBaja datetime2 NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.AuditoriaRevisiones', 'U') IS NULL
    CREATE TABLE dbo.AuditoriaRevisiones (
        IdContacto int NOT NULL CONSTRAINT PK_AuditoriaRevisiones PRIMARY KEY,
        SaldoEsperado varchar(20) NULL CONSTRAINT CK_AuditoriaRevisiones_Esperado CHECK (SaldoEsperado IN ('cero', 'puede-tener-saldo')),
        Estado varchar(20) NOT NULL CONSTRAINT DF_AuditoriaRevisiones_Estado DEFAULT 'pendiente'
            CONSTRAINT CK_AuditoriaRevisiones_Estado CHECK (Estado IN ('pendiente', 'revisada')),
        FechaRevision datetime2 NULL,
        Usuario varchar(60) NULL,
        Nota varchar(500) NULL,
        SaldoAlRevisar money NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.AuditoriaRevisionesHistorial', 'U') IS NULL
    CREATE TABLE dbo.AuditoriaRevisionesHistorial (
        IdHistorial int IDENTITY(1,1) NOT NULL CONSTRAINT PK_AuditoriaRevisionesHistorial PRIMARY KEY,
        IdContacto int NOT NULL,
        Accion varchar(40) NOT NULL,
        Detalle nvarchar(max) NULL,
        Usuario varchar(60) NULL,
        Fecha datetime2 NOT NULL CONSTRAINT DF_AuditoriaRevisionesHistorial_Fecha DEFAULT SYSDATETIME()
    )
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SaldosRefAccessDet' AND object_id = OBJECT_ID('dbo.SaldosReferenciaAccessDetalle'))
    CREATE INDEX IX_SaldosRefAccessDet ON dbo.SaldosReferenciaAccessDetalle (IdContacto, Origen, IdOrigen)
    """,
]

# Reglas iniciales de conceptos de movimientos sin contacto que son normales (se pueden agregar y dar de baja desde la pantalla).
CONCEPTOS_INICIALES = {
    "LEY 25413": "Impuesto al débito y crédito bancario",
    "COMISION": "Comisión del banco",
    "FIMA": "Fondo común de inversión propio",
    "PLAZO FIJO": "Plazo fijo propio",
    "P.FIJO": "Plazo fijo propio",
    "GIAMIGLI": "Transferencia entre cuentas propias",
    "30712114602": "Transferencia con el CUIT propio",
    "MIS TIT": "Transferencia entre cuentas propias",
    "O/BCO": "Transferencia entre bancos propios",
    "DEP.EFECTIVO": "Depósito de efectivo",
    "DEP EFECTIVO": "Depósito de efectivo",
}

PARAMETROS_INICIALES = {"plazoMaximoMeses": "24", "umbralPesos": "300", "anticipoDias": "60"}


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

    print(f"Respaldo verificado: {backup_verificado('esquema-auditoria-035')}")
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        for sql in DDL:
            cur.execute(sql)
        for clave, valor in PARAMETROS_INICIALES.items():
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM dbo.AuditoriaParametros WHERE Clave = ?) "
                "INSERT INTO dbo.AuditoriaParametros (Clave, Valor, Usuario) VALUES (?, ?, 'esquema-035')",
                clave, clave, valor,
            )
        for clave, motivo in CONCEPTOS_INICIALES.items():
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM dbo.AuditoriaConocidos WHERE Tipo = 'concepto-movimiento' AND Clave = ?) "
                "INSERT INTO dbo.AuditoriaConocidos (Tipo, Clave, Motivo, Usuario) VALUES ('concepto-movimiento', ?, ?, 'esquema-035')",
                clave, clave, motivo,
            )
        conn.commit()
        for t in TABLAS:
            n = cur.execute(f"SELECT COUNT(*) FROM dbo.{t}").fetchone()[0]
            print(f"dbo.{t}: {n} filas")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def revertir() -> None:
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        usadas = cur.execute("SELECT COUNT(*) FROM dbo.AuditoriaCorrecciones").fetchone()[0] \
            if cur.execute("SELECT OBJECT_ID('dbo.AuditoriaCorrecciones', 'U')").fetchone()[0] else 0
        if usadas:
            raise SystemExit(f"Hay {usadas} correcciones registradas: no se borran las tablas.")
        for t in TABLAS:
            cur.execute(f"IF OBJECT_ID('dbo.{t}', 'U') IS NOT NULL DROP TABLE dbo.{t}")
        conn.commit()
        print("Tablas de la auditoría eliminadas.")
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
    else:
        aplicar()


if __name__ == "__main__":
    main(sys.argv[1:])
