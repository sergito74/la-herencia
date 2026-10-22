"""039: esquema aditivo de pastaje. Sin argumentos solo inspecciona; --aplicar respalda y migra WC.

Crea tablas nuevas, agrega la rama 'Pastaje' a vw_MovimientosCuenta_Base (facturas y ND
a Credito del cliente, NC a Deuda, como las ventas) y amplía CK_AplicacionesPago_TipoDocumento.
Gate: conteo y totales Deuda/Credito de la vista idénticos antes y después (sin filas nuevas).
Respaldo COPY_ONLY con CHECKSUM verificado; transacción explícita; nunca restaura automáticamente.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.db.connection import _assert_target_is_wc, get_connection
from src.features.vinculos.backup import backup_verificado

AUDIT = (
    "CreadoPor nvarchar(100) NOT NULL, CreadoEn datetime2 NOT NULL DEFAULT SYSDATETIME(), "
    "ModificadoPor nvarchar(100) NULL, ModificadoEn datetime2 NULL, Version int NOT NULL DEFAULT 1"
)

TABLES = {
    "IndiceINMAG": """
        Fecha date NOT NULL PRIMARY KEY,
        Indice decimal(18,3) NOT NULL CHECK (Indice > 0),
        CabIngresadas int NULL,
        Origen varchar(10) NOT NULL CHECK (Origen IN ('auto','manual')),
        Fuente nvarchar(200) NULL,
        ObtenidoEn datetime2 NOT NULL DEFAULT SYSDATETIME(),
        Nota nvarchar(400) NULL,
        CONSTRAINT CK_IndiceINMAG_NotaManual CHECK (Origen = 'auto' OR LEN(ISNULL(Nota, '')) > 0)""",
    "IndiceINMAG_Historial": """
        IdHistorial int IDENTITY PRIMARY KEY,
        Fecha date NOT NULL,
        IndiceAnterior decimal(18,3) NULL,
        IndiceNuevo decimal(18,3) NOT NULL,
        Motivo nvarchar(400) NOT NULL,
        Usuario nvarchar(100) NOT NULL,
        Momento datetime2 NOT NULL DEFAULT SYSDATETIME()""",
    "ContratosPastaje": f"""
        IdContratoPastaje int IDENTITY PRIMARY KEY,
        IdContactoCliente int NOT NULL,
        IdEmpresaContacto int NOT NULL,
        IdEstablecimiento int NOT NULL,
        FechaInicio date NOT NULL,
        FechaFin date NULL,
        Modalidad varchar(20) NOT NULL DEFAULT 'mes_vencido' CHECK (Modalidad IN ('mes_vencido')),
        CondicionVenta varchar(20) NOT NULL DEFAULT 'contado' CHECK (CondicionVenta IN ('contado')),
        AlicuotaIva decimal(5,2) NOT NULL DEFAULT 21.00,
        CarpetaDocumentos nvarchar(400) NULL,
        ArchivoContrato nvarchar(400) NULL,
        ClausulaInfraestructura nvarchar(max) NULL,
        ClausulaSanidad nvarchar(max) NULL,
        ClausulaMortandad nvarchar(max) NULL,
        OtrasClausulas nvarchar(max) NULL,
        Estado varchar(12) NOT NULL DEFAULT 'vigente' CHECK (Estado IN ('vigente','finalizado','anulado')),
        MotivoEstado nvarchar(400) NULL,
        {AUDIT},
        CONSTRAINT CK_ContratosPastaje_Fechas CHECK (FechaFin IS NULL OR FechaFin >= FechaInicio)""",
    "PastajeTarifas": f"""
        IdTarifa int IDENTITY PRIMARY KEY,
        IdContratoPastaje int NOT NULL REFERENCES dbo.ContratosPastaje(IdContratoPastaje),
        IdTipoHacienda int NOT NULL,
        TipoTarifa varchar(12) NOT NULL CHECK (TipoTarifa IN ('kg_novillo','fijo_ars','fijo_usd')),
        Valor decimal(18,4) NOT NULL CHECK (Valor > 0),
        VigenteDesde date NOT NULL,
        {AUDIT},
        CONSTRAINT UQ_PastajeTarifas UNIQUE (IdContratoPastaje, IdTipoHacienda, VigenteDesde)""",
    "PastajeBitacora": f"""
        IdMovimiento int IDENTITY PRIMARY KEY,
        IdContratoPastaje int NOT NULL REFERENCES dbo.ContratosPastaje(IdContratoPastaje),
        Fecha date NOT NULL,
        Tipo varchar(12) NOT NULL CHECK (Tipo IN ('ingreso','egreso','muerte','faltante','nacimiento','destete','recuento')),
        IdTipoHacienda int NOT NULL,
        Cabezas int NOT NULL CHECK (Cabezas > 0),
        CabezasSistema int NULL,
        NumeroDTe varchar(40) NULL,
        Observacion nvarchar(400) NULL,
        Estado varchar(10) NOT NULL DEFAULT 'vigente' CHECK (Estado IN ('vigente','anulado')),
        MotivoAnulacion nvarchar(400) NULL,
        {AUDIT}""",
    "PastajeLiquidaciones": f"""
        IdLiquidacion int IDENTITY PRIMARY KEY,
        IdContratoPastaje int NOT NULL REFERENCES dbo.ContratosPastaje(IdContratoPastaje),
        Periodo date NOT NULL CHECK (DAY(Periodo) = 1),
        Tipo varchar(10) NOT NULL CHECK (Tipo IN ('mensual','ajuste')),
        IdLiquidacionOriginal int NULL REFERENCES dbo.PastajeLiquidaciones(IdLiquidacion),
        Estado varchar(12) NOT NULL DEFAULT 'borrador' CHECK (Estado IN ('borrador','confirmada','anulada')),
        PrecioPromedio decimal(18,2) NULL,
        KgTotal decimal(18,4) NOT NULL DEFAULT 0,
        Neto decimal(18,2) NOT NULL,
        Iva decimal(18,2) NOT NULL,
        Total decimal(18,2) NOT NULL,
        Moneda char(3) NOT NULL DEFAULT 'ARS',
        ArchivoPdf nvarchar(400) NULL,
        ConfirmadaPor nvarchar(100) NULL,
        ConfirmadaEn datetime2 NULL,
        {AUDIT},
        CONSTRAINT CK_PastajeLiq_Ajuste CHECK ((Tipo = 'ajuste' AND IdLiquidacionOriginal IS NOT NULL) OR (Tipo = 'mensual' AND IdLiquidacionOriginal IS NULL))""",
    "PastajeLiquidacionTramos": """
        IdTramo int IDENTITY PRIMARY KEY,
        IdLiquidacion int NOT NULL REFERENCES dbo.PastajeLiquidaciones(IdLiquidacion),
        IdTipoHacienda int NOT NULL,
        Desde date NOT NULL,
        Hasta date NOT NULL,
        Cabezas int NOT NULL,
        Dias int NOT NULL,
        TipoTarifa varchar(12) NOT NULL,
        ValorMes decimal(18,4) NOT NULL,
        Kg decimal(18,4) NOT NULL,
        Importe decimal(18,4) NOT NULL""",
    "PastajeLiquidacionIndices": """
        IdLiquidacion int NOT NULL REFERENCES dbo.PastajeLiquidaciones(IdLiquidacion),
        Fecha date NOT NULL,
        Indice decimal(18,3) NOT NULL,
        PRIMARY KEY (IdLiquidacion, Fecha)""",
    "PastajeComprobantes": f"""
        IdComprobante int IDENTITY PRIMARY KEY,
        IdContratoPastaje int NOT NULL REFERENCES dbo.ContratosPastaje(IdContratoPastaje),
        IdLiquidacion int NULL REFERENCES dbo.PastajeLiquidaciones(IdLiquidacion),
        Tipo varchar(12) NOT NULL CHECK (Tipo IN ('factura','nota_debito','nota_credito')),
        Letra char(1) NOT NULL,
        PuntoVenta int NOT NULL,
        Numero int NOT NULL,
        Fecha date NOT NULL,
        VtoPago date NULL,
        Cae varchar(20) NULL,
        VtoCae date NULL,
        CuitCliente varchar(11) NULL,
        PeriodoDesde date NULL,
        PeriodoHasta date NULL,
        Detalle nvarchar(1000) NULL,
        Neto decimal(18,2) NOT NULL,
        Iva decimal(18,2) NOT NULL,
        Total decimal(18,2) NOT NULL CHECK (Total > 0),
        IdComprobanteAsociado int NULL REFERENCES dbo.PastajeComprobantes(IdComprobante),
        IdCampania int NULL,
        IdEstablecimiento int NOT NULL,
        ArchivoPdf nvarchar(400) NULL,
        Estado varchar(10) NOT NULL DEFAULT 'vigente' CHECK (Estado IN ('vigente','anulado')),
        MotivoAnulacion nvarchar(400) NULL,
        {AUDIT},
        CONSTRAINT UQ_PastajeComprobantes UNIQUE (Tipo, Letra, PuntoVenta, Numero),
        CONSTRAINT CK_PastajeComp_Nota CHECK ((Tipo = 'factura' AND IdComprobanteAsociado IS NULL) OR (Tipo <> 'factura' AND IdComprobanteAsociado IS NOT NULL))""",
}

INDEXES = [
    "CREATE UNIQUE INDEX UX_PastajeLiq_Mensual ON dbo.PastajeLiquidaciones(IdContratoPastaje, Periodo) "
    "WHERE Tipo = 'mensual' AND Estado <> 'anulada'",
    "CREATE UNIQUE INDEX UX_PastajeComp_FacturaLiq ON dbo.PastajeComprobantes(IdLiquidacion) "
    "WHERE Tipo = 'factura' AND Estado = 'vigente' AND IdLiquidacion IS NOT NULL",
    "CREATE INDEX IX_PastajeBitacora_Contrato ON dbo.PastajeBitacora(IdContratoPastaje, Fecha)",
]

RAMA_PASTAJE = """

UNION ALL

SELECT -- pastaje-039
    pc.Fecha,
    cp.IdContactoCliente AS IdContacto,
    ct.[Razon Social],
    CAST(CASE pc.Tipo WHEN 'factura' THEN 'Factura Pastaje' WHEN 'nota_debito' THEN 'ND Pastaje' ELSE 'NC Pastaje' END AS varchar(50)) AS Documento,
    CAST(pc.Letra + ' ' + RIGHT('0000' + CAST(pc.PuntoVenta AS varchar(5)), 4) + '-' + RIGHT('00000000' + CAST(pc.Numero AS varchar(8)), 8) AS varchar(50)) AS [Nro Documento],
    CAST(CASE WHEN pc.Tipo = 'nota_credito' THEN pc.Total ELSE 0 END AS money) AS Deuda,
    CAST(CASE WHEN pc.Tipo = 'nota_credito' THEN 0 ELSE pc.Total END AS money) AS Credito,
    CAST('Pastaje' AS varchar(50)) AS Origen,
    CAST(pc.IdComprobante AS bigint) AS IdOrigen
FROM dbo.PastajeComprobantes AS pc
INNER JOIN dbo.ContratosPastaje AS cp ON cp.IdContratoPastaje = pc.IdContratoPastaje
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = cp.IdContactoCliente
WHERE pc.Estado = 'vigente'
"""

MARCA_FIN = "\n) AS base"


def _vista(cursor):
    cursor.execute(
        "SELECT COUNT_BIG(*), SUM(CAST(Deuda AS decimal(20,2))), SUM(CAST(Credito AS decimal(20,2))) "
        "FROM dbo.vw_MovimientosCuenta_Base"
    )
    return [str(x) for x in cursor.fetchone()]


def _check_tipo(cursor):
    row = cursor.execute(
        "SELECT definition FROM sys.check_constraints WHERE name='CK_AplicacionesPago_TipoDocumento'"
    ).fetchone()
    return row[0] if row else None


def _preconditions(cursor):
    if cursor.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
        raise RuntimeError("La migración solo admite WC")
    if _check_tipo(cursor) is None:
        raise RuntimeError("Falta CK_AplicacionesPago_TipoDocumento")


def run(apply=False):
    _assert_target_is_wc()
    with get_connection() as conn:
        cursor = conn.cursor()
        _preconditions(cursor)
        antes = _vista(cursor)
        existing = {r[0] for r in cursor.execute("SELECT name FROM sys.tables").fetchall()}
        definicion = cursor.execute(
            "SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))"
        ).fetchone()[0]
        check = _check_tipo(cursor)
    pendientes = {
        "tablas": sorted(set(TABLES) - existing),
        "ramaVista": "pastaje-039" not in definicion,
        "checkTipoDocumento": "Pastaje" not in check,
    }
    if not apply:
        return {"modo": "inspeccion", "pendiente": pendientes, "vista": antes, "check": check}
    if definicion.count(MARCA_FIN) != 1:
        raise RuntimeError("No se encontró un único cierre ') AS base' en la vista")
    evidencia = Path(__file__).resolve().parents[2] / "backups" / "pastaje-039-schema"
    evidencia.mkdir(parents=True, exist_ok=True)
    marca = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S%f}"
    (evidencia / f"vw_MovimientosCuenta_Base-antes-{marca}.sql").write_text(definicion, encoding="utf-8")
    backup = backup_verificado("pastaje_039")
    log = evidencia / f"migration-{marca}.json"
    record = {"backupVerificado": backup, "vistaAntes": antes, "checkAntes": check, "estado": "respaldado"}
    log.write_text(json.dumps(record, default=str, indent=2), encoding="utf-8")
    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()
        _preconditions(cursor)
        cursor.execute("BEGIN TRANSACTION")
        try:
            for table, ddl in TABLES.items():
                # Nombres de un catálogo fijo, nunca provistos por el usuario.
                if table not in existing:
                    cursor.execute(f"CREATE TABLE dbo.{table} ({ddl})")
            for ddl in INDEXES:
                nombre = ddl.split(" INDEX ")[1].split(" ")[0]
                if not cursor.execute("SELECT 1 FROM sys.indexes WHERE name=?", (nombre,)).fetchone():
                    cursor.execute(ddl)
            if pendientes["checkTipoDocumento"]:
                nuevo = check.strip()
                # ([TipoDocumento]='X' OR ...) -> agrega 'Pastaje'
                nuevo = nuevo[:-1] + " OR [TipoDocumento]='Pastaje')"
                cursor.execute("ALTER TABLE dbo.AplicacionesPago DROP CONSTRAINT CK_AplicacionesPago_TipoDocumento")
                cursor.execute(
                    f"ALTER TABLE dbo.AplicacionesPago WITH CHECK ADD CONSTRAINT CK_AplicacionesPago_TipoDocumento CHECK {nuevo}"
                )
            if pendientes["ramaVista"]:
                cuerpo = definicion.replace(MARCA_FIN, RAMA_PASTAJE + MARCA_FIN)
                i = cuerpo.upper().find("CREATE")
                cursor.execute(cuerpo[:i] + "CREATE OR ALTER " + cuerpo[i + len("CREATE"):].lstrip())
            despues = _vista(cursor)
            if antes != despues:
                raise RuntimeError(f"La vista cambió sin datos nuevos ({antes} -> {despues}): rollback")
            cursor.execute("COMMIT TRANSACTION")
        except Exception as exc:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION")
            record.update(estado="revertido", motivo=str(exc))
            log.write_text(json.dumps(record, default=str, indent=2), encoding="utf-8")
            raise
    record.update(estado="aplicado", vistaDespues=despues)
    log.write_text(json.dumps(record, default=str, indent=2), encoding="utf-8")
    return {**record, "evidencia": str(log)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=True, indent=2))
