"""038: esquema aditivo. Sin argumentos solo inspecciona; --aplicar respalda y migra WC.

No inserta movimientos ni saldos. Cada ejecución de DDL tiene respaldo COPY_ONLY
con CHECKSUM verificado y transacción explícita. Nunca restaura automáticamente.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.db.connection import _assert_target_is_wc, get_connection
from src.features.vinculos.backup import backup_verificado


TABLES = {
    "OperacionesCajaEfectivo": """
        IdOperacion bigint IDENTITY PRIMARY KEY,
        ClaveIdempotencia uniqueidentifier NOT NULL UNIQUE,
        HuellaSolicitud char(64) NOT NULL,
        Tipo varchar(40) NOT NULL, Fecha date NOT NULL,
        Concepto nvarchar(255) NOT NULL, Cuenta varchar(20) NOT NULL CHECK(Cuenta IN ('A','B')),
        IdContacto int NULL REFERENCES dbo.Contactos(IdContacto),
        IdSocio int NULL REFERENCES dbo.Socios(IdSocio),
        Solicitud nvarchar(max) NOT NULL, Contexto nvarchar(max) NOT NULL,
        Estado varchar(12) NOT NULL DEFAULT 'Vigente' CHECK(Estado IN ('Vigente','Anulada')),
        Version bigint NOT NULL DEFAULT 0,
        Usuario varchar(60) NOT NULL, FechaCarga datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        MotivoAnulacion nvarchar(255) NULL, UsuarioAnulacion varchar(60) NULL,
        FechaAnulacion datetime2 NULL
    """,
    "EfectosOperacionCaja": """
        IdEfecto bigint IDENTITY PRIMARY KEY,
        IdOperacion bigint NOT NULL REFERENCES dbo.OperacionesCajaEfectivo(IdOperacion),
        TipoEfecto varchar(30) NOT NULL CHECK(TipoEfecto IN
          ('PagoEfectivo','Aplicacion','MovimientoSocio','AsientoParticular',
           'TraspasoTesoreria','GastoCaja','AjusteNoCobrado')),
        IdRegistro bigint NOT NULL, EsCreadoPorOperacion bit NOT NULL DEFAULT 1,
        Snapshot nvarchar(max) NULL,
        UNIQUE(IdOperacion,TipoEfecto,IdRegistro)
    """,
    "BancoOperacionCaja": """
        IdOperacion bigint NOT NULL REFERENCES dbo.OperacionesCajaEfectivo(IdOperacion),
        Medio varchar(20) NOT NULL CHECK(Medio IN ('bna','galicia','mercado-libre')),
        IdMovimiento bigint NOT NULL,
        PRIMARY KEY(IdOperacion,Medio,IdMovimiento)
    """,
    "GastoCajaEfectivo": """
        IdGasto bigint IDENTITY PRIMARY KEY,
        IdOperacion bigint NOT NULL UNIQUE REFERENCES dbo.OperacionesCajaEfectivo(IdOperacion),
        Fecha date NOT NULL, Concepto nvarchar(255) NOT NULL,
        ImportePesos decimal(19,2) NOT NULL CHECK(ImportePesos>0),
        ImporteUSD decimal(19,4) NULL,
        TipoCambio decimal(19,6) NULL CHECK(TipoCambio>0),
        FuenteCotizacion nvarchar(255) NULL, FechaCotizacion date NULL,
        Anulada bit NOT NULL DEFAULT 0,
        Usuario varchar(60) NOT NULL, FechaCarga datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        MotivoAnulacion nvarchar(255) NULL, UsuarioAnulacion varchar(60) NULL,
        FechaAnulacion datetime2 NULL,
        CHECK(ImporteUSD IS NULL OR (TipoCambio IS NOT NULL AND FuenteCotizacion IS NOT NULL
          AND FechaCotizacion IS NOT NULL))
    """,
    "RepartosGastoCaja": """
        IdReparto bigint IDENTITY PRIMARY KEY,
        IdGasto bigint NOT NULL REFERENCES dbo.GastoCajaEfectivo(IdGasto),
        IdRubro int NOT NULL REFERENCES dbo.Rubros(IdRubro),
        IdCentroCostos int NOT NULL,
        IdDestino int NULL REFERENCES dbo.DestinoCompras(IdDestino),
        IdCampania int NULL REFERENCES dbo.Campañas(IdCampaña),
        IdLote int NULL,
        ImportePesos decimal(19,2) NOT NULL CHECK(ImportePesos>0)
    """,
    "ArqueosCajaEfectivo": """
        IdArqueo bigint IDENTITY PRIMARY KEY,
        Caja varchar(20) NOT NULL CHECK(Caja IN ('GiamigliSA','CampoChica','CondominioLSC')),
        FechaCorte date NOT NULL, SecuenciaCorte bigint NOT NULL,
        Estado varchar(20) NOT NULL DEFAULT 'Borrador'
          CHECK(Estado IN ('Borrador','Confirmado','Invalidado','Desactualizado')),
        SaldoSistema decimal(19,2) NOT NULL, TotalContado decimal(19,2) NOT NULL,
        Diferencia decimal(19,2) NOT NULL,
        IdOperacionAjuste bigint NULL REFERENCES dbo.OperacionesCajaEfectivo(IdOperacion),
        IdArqueoAnterior bigint NULL REFERENCES dbo.ArqueosCajaEfectivo(IdArqueo),
        Version bigint NOT NULL DEFAULT 0,
        Usuario varchar(60) NOT NULL, FechaCarga datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        UsuarioConfirmacion varchar(60) NULL, FechaConfirmacion datetime2 NULL,
        MotivoInvalidacion nvarchar(255) NULL, UsuarioInvalidacion varchar(60) NULL,
        FechaInvalidacion datetime2 NULL
    """,
    "ArqueoDenominaciones": """
        IdArqueo bigint NOT NULL REFERENCES dbo.ArqueosCajaEfectivo(IdArqueo),
        Denominacion decimal(19,2) NOT NULL CHECK(Denominacion>0),
        Cantidad int NOT NULL CHECK(Cantidad>=0), PRIMARY KEY(IdArqueo,Denominacion)
    """,
    "ImportacionesCaja": """
        IdLote bigint IDENTITY PRIMARY KEY,
        Libro varchar(40) NOT NULL, HuellaArchivo char(64) NOT NULL,
        FechaCorte date NOT NULL, VersionParser int NOT NULL,
        Estado varchar(12) NOT NULL DEFAULT 'Preview' CHECK(Estado IN ('Preview','Confirmado')),
        Usuario varchar(60) NOT NULL, FechaCarga datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        Resoluciones nvarchar(max) NULL, FechaConfirmacion datetime2 NULL
    """,
    "FilasOrigenCaja": """
        IdFila bigint IDENTITY PRIMARY KEY,
        IdLote bigint NOT NULL REFERENCES dbo.ImportacionesCaja(IdLote),
        Hoja nvarchar(100) NOT NULL, NumeroFila int NOT NULL,
        Huella char(64) NOT NULL, DatosOriginales nvarchar(max) NOT NULL,
        Estado varchar(12) NOT NULL CHECK(Estado IN
          ('Nueva','Vinculada','Ambigua','Modificada','Excluida')),
        IdMovimiento int NULL REFERENCES dbo.MovimientosCajaEfectivo(IdMovimiento),
        IdOperacion bigint NULL REFERENCES dbo.OperacionesCajaEfectivo(IdOperacion),
        Motivo nvarchar(255) NULL, UsuarioResolucion varchar(60) NULL,
        FechaResolucion datetime2 NULL, UNIQUE(IdLote,Hoja,NumeroFila)
    """,
}


def _balances(cursor):
    cursor.execute(
        "SELECT Caja,COUNT_BIG(*),MAX(IdMovimiento),SUM(Importe) "
        "FROM dbo.MovimientosCajaEfectivo GROUP BY Caja ORDER BY Caja"
    )
    return [tuple(row) for row in cursor.fetchall()]


def _preconditions(cursor):
    if cursor.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
        raise RuntimeError("La migración solo admite WC")
    for table, column in (
        ("MovimientosCajaEfectivo", "IdMovimiento"),
        ("Pagos efectivo", "IdPagoEfectivo"),
        ("MovimientosCuentaSocio", "IdSocio"),
    ):
        if (
            cursor.execute("SELECT COL_LENGTH(?,?)", (f"dbo.[{table}]", column)).fetchone()[0]
            is None
        ):
            raise RuntimeError(f"Falta columna requerida: {table}.{column}")


def run(apply=False):
    _assert_target_is_wc()
    with get_connection() as conn:
        cursor = conn.cursor()
        _preconditions(cursor)
        before = _balances(cursor)
        existing = {r[0] for r in cursor.execute("SELECT name FROM sys.tables").fetchall()}
    if not apply:
        return {
            "modo": "inspeccion",
            "tablasPendientes": sorted(set(TABLES) - existing),
            "saldos": before,
        }
    backup = backup_verificado("cajas_038")
    evidence = Path(__file__).resolve().parents[2] / "backups" / "cajas-038-schema"
    evidence.mkdir(parents=True, exist_ok=True)
    # Persist verification evidence BEFORE any DDL, including failed attempts.
    log = evidence / f"migration-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%f}.json"
    record = {"backupVerificado": backup, "saldosAntes": before, "estado": "respaldado"}
    log.write_text(json.dumps(record, default=str, indent=2), encoding="utf-8")
    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()
        _preconditions(cursor)
        cursor.execute("BEGIN TRANSACTION")
        try:
            for table, definition in TABLES.items():
                # Object names are a fixed catalog, never supplied by the caller.
                if table not in existing:
                    cursor.execute(f"CREATE TABLE dbo.{table} ({definition})")
            for col, definition in {
                "IdOperacionCaja": "bigint NULL REFERENCES dbo.OperacionesCajaEfectivo(IdOperacion)",
                "Tipo": "varchar(40) NULL",
                "Anulada": "bit NOT NULL CONSTRAINT DF_Caja038_Anulada DEFAULT 0",
            }.items():
                if (
                    cursor.execute(
                        "SELECT COL_LENGTH('dbo.MovimientosCajaEfectivo',?)", (col,)
                    ).fetchone()[0]
                    is None
                ):
                    cursor.execute(
                        f"ALTER TABLE dbo.MovimientosCajaEfectivo ADD {col} {definition}"
                    )
            cursor.execute("ALTER TABLE dbo.[Pagos efectivo] ALTER COLUMN IdContacto int NULL")
            cursor.execute("""IF NOT EXISTS (SELECT 1 FROM sys.indexes
                WHERE name='UX_Caja038_PagoFisico')
                CREATE UNIQUE INDEX UX_Caja038_PagoFisico
                ON dbo.MovimientosCajaEfectivo(IdPagoEfectivo)
                WHERE IdPagoEfectivo IS NOT NULL AND IdOperacionCaja IS NOT NULL AND Anulada=0""")
            check = cursor.execute(
                "SELECT definition FROM sys.check_constraints "
                "WHERE name='CK_AplicacionesPago_TipoDocumento'"
            ).fetchone()
            if check and "Alquiler" not in check[0]:
                cursor.execute(
                    "ALTER TABLE dbo.AplicacionesPago DROP CONSTRAINT CK_AplicacionesPago_TipoDocumento"
                )
                cursor.execute(
                    "ALTER TABLE dbo.AplicacionesPago WITH CHECK ADD CONSTRAINT "
                    "CK_AplicacionesPago_TipoDocumento CHECK(TipoDocumento IN "
                    "('CompraDeuda','VentaHacienda','VentaGranos','Alquiler'))"
                )
            cursor.execute("""IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Caja038_EfectoPropio')
                CREATE UNIQUE INDEX UX_Caja038_EfectoPropio ON dbo.EfectosOperacionCaja(TipoEfecto,IdRegistro)
                WHERE EsCreadoPorOperacion=1""")
            cursor.execute("""IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Caja038_ArqueoAjuste')
                CREATE UNIQUE INDEX UX_Caja038_ArqueoAjuste ON dbo.ArqueosCajaEfectivo(IdOperacionAjuste)
                WHERE IdOperacionAjuste IS NOT NULL""")
            cursor.execute("""IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Caja038_Banco')
                CREATE INDEX IX_Caja038_Banco ON dbo.BancoOperacionCaja(Medio,IdMovimiento)""")
            cursor.execute("""CREATE OR ALTER VIEW dbo.vw_PagosEfectivoVigentes AS
                SELECT p.* FROM dbo.[Pagos efectivo] p WHERE NOT EXISTS (
                  SELECT 1 FROM dbo.EfectosOperacionCaja e JOIN dbo.OperacionesCajaEfectivo o
                  ON o.IdOperacion=e.IdOperacion WHERE e.TipoEfecto='PagoEfectivo'
                  AND e.EsCreadoPorOperacion=1 AND e.IdRegistro=p.IdPagoEfectivo AND o.Estado='Anulada')""")
            definition = cursor.execute(
                "SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))"
            ).fetchone()[0]
            if not definition:
                raise RuntimeError("No se pudo respaldar la definición de la vista central")
            (evidence / f"vista-antes-{log.stem}.sql").write_text(definition, encoding="utf-8")
            definition = re.sub(
                r"^\s*(?:CREATE(?:\s+OR\s+ALTER)?|ALTER)\s+VIEW\b",
                "CREATE OR ALTER VIEW",
                definition,
                count=1,
                flags=re.I,
            )
            if "BancoOperacionCaja" not in definition:
                definition = re.sub(
                    r"\bCREATE\s+VIEW\b", "ALTER VIEW", definition, count=1, flags=re.I
                )
                definition = definition.replace(
                    "dbo.[Pagos efectivo]", "dbo.vw_PagosEfectivoVigentes"
                )
                # Preserve the existing complete view; append exclusions after its final join.
                definition = (
                    definition.rstrip().rstrip(";")
                    + """
                WHERE NOT EXISTS (
                  SELECT 1 FROM dbo.BancoOperacionCaja b JOIN dbo.OperacionesCajaEfectivo op
                  ON op.IdOperacion=b.IdOperacion WHERE op.Estado='Vigente' AND (
                    (base.Origen='Banco Nacion' AND b.Medio='bna' AND b.IdMovimiento=base.IdOrigen) OR
                    (base.Origen='Galicia' AND b.Medio='galicia' AND b.IdMovimiento=base.IdOrigen) OR
                    (base.Origen='Mercado Pago' AND b.Medio='mercado-libre' AND b.IdMovimiento=base.IdOrigen) OR
                    (base.Origen=N'Conciliación Tesorería' AND EXISTS (
                      SELECT 1 FROM dbo.ConciliacionesTesoreria ct WHERE ct.IdConciliacion=base.IdOrigen
                      AND ct.Medio=b.Medio AND ct.IdMovimiento=b.IdMovimiento))
                  ))"""
                )
            if "AjusteNoCobrado" not in definition:
                definition = re.sub(
                    r"\bCREATE\s+VIEW\b", "ALTER VIEW", definition, count=1, flags=re.I
                )
                definition = (
                    definition.rstrip().rstrip(";")
                    + """
                AND NOT EXISTS (SELECT 1 FROM dbo.EfectosOperacionCaja e
                  JOIN dbo.OperacionesCajaEfectivo op ON op.IdOperacion=e.IdOperacion
                  WHERE e.TipoEfecto='AjusteNoCobrado' AND e.EsCreadoPorOperacion=1
                  AND op.Estado='Anulada' AND base.Origen='Ajuste Interno' AND base.IdOrigen=e.IdRegistro)"""
                )
            cursor.execute(definition)
            after = _balances(cursor)
            if before != after:
                raise RuntimeError("Los movimientos o saldos históricos cambiaron: rollback")
            cursor.execute("COMMIT TRANSACTION")
        except Exception:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION")
            record.update(estado="revertido", motivo="DDL fallido; transacción revertida")
            log.write_text(json.dumps(record, default=str, indent=2), encoding="utf-8")
            raise
    record.update(estado="aplicado", saldosDespues=after)
    log.write_text(json.dumps(record, default=str, indent=2), encoding="utf-8")
    return {**record, "evidencia": str(log)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=True, indent=2))
