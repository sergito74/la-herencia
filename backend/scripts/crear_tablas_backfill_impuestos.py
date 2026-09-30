"""029: migración aditiva explícita; backup siempre verificado antes del DDL."""
import argparse
from src.db.connection import get_connection
from src.features.backfill_impuestos import respaldo

DDL = """
CREATE TABLE dbo.BackfillImpuestosLotes (
 IdLote uniqueidentifier NOT NULL PRIMARY KEY,
 IdOrganismo int NOT NULL REFERENCES dbo.Contactos(IdContacto),
 Estado varchar(20) NOT NULL CHECK(Estado IN ('confirmado','revertido')),
 HuellaPropuesta char(64) NOT NULL, HashSolicitud char(64) NOT NULL,
 Usuario nvarchar(100) NOT NULL, Fecha datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 BackupId nvarchar(100) NOT NULL, Cantidad int NOT NULL CHECK(Cantidad>0),
 Total decimal(19,2) NOT NULL CHECK(Total>0),
 FechaReversion datetime2 NULL,UsuarioReversion nvarchar(100) NULL
);
CREATE TABLE dbo.BackfillImpuestosBoletas (
 IdRegistro bigint IDENTITY PRIMARY KEY,
 IdLote uniqueidentifier NOT NULL REFERENCES dbo.BackfillImpuestosLotes(IdLote),
 IdImpuesto int NULL REFERENCES dbo.Impuestos(IdImpuesto),IdImpuestoHistorico int NOT NULL,
 OrigenCreacion varchar(20) NOT NULL CHECK(OrigenCreacion IN ('comprobante','generada')),
 TieneComprobante bit NOT NULL,ArchivoHash char(64) NULL,
 SnapshotCreacion nvarchar(max) NOT NULL CHECK(ISJSON(SnapshotCreacion)=1),
 Version rowversion NOT NULL
);
CREATE UNIQUE INDEX UX_BackfillBoleta ON dbo.BackfillImpuestosBoletas(IdImpuesto) WHERE IdImpuesto IS NOT NULL;
CREATE UNIQUE INDEX UX_BackfillArchivo ON dbo.BackfillImpuestosBoletas(ArchivoHash) WHERE ArchivoHash IS NOT NULL AND IdImpuesto IS NOT NULL;
CREATE TABLE dbo.BackfillImpuestosVinculos (
 IdVinculo bigint IDENTITY PRIMARY KEY,
 IdLote uniqueidentifier NOT NULL REFERENCES dbo.BackfillImpuestosLotes(IdLote),
 Medio varchar(20) NOT NULL CHECK(Medio IN ('bna','galicia','mercado-libre','efectivo','valores-propios','valores-recibidos')),
 IdMovimiento bigint NOT NULL,IdOrganismo int NOT NULL REFERENCES dbo.Contactos(IdContacto),
 IdImpuesto int NOT NULL REFERENCES dbo.Impuestos(IdImpuesto),
 Importe decimal(19,2) NOT NULL CHECK(Importe>0),HuellaPago char(64) NOT NULL,
 CONSTRAINT UX_BackfillPago UNIQUE(Medio,IdMovimiento)
);
CREATE TABLE dbo.BackfillImpuestosEventos (
 IdEvento bigint IDENTITY PRIMARY KEY,
 IdLote uniqueidentifier NOT NULL REFERENCES dbo.BackfillImpuestosLotes(IdLote),
 IdRegistro bigint NULL REFERENCES dbo.BackfillImpuestosBoletas(IdRegistro),
 Tipo varchar(20) NOT NULL CHECK(Tipo IN ('confirmar','adjuntar','cambiar_tipo','revertir')),
 Usuario nvarchar(100) NOT NULL,Fecha datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 Antes nvarchar(max) NULL CHECK(Antes IS NULL OR ISJSON(Antes)=1),
 Despues nvarchar(max) NOT NULL CHECK(ISJSON(Despues)=1)
);
"""

def migrate():
    from src.features.backfill_impuestos.repository import schema_ready
    if schema_ready(): return dict(estado='ya_existe')
    evidence=respaldo.crear(respaldo.preparar('migrar','029-v1','operador-local'))
    with get_connection(readonly=False) as conn:
        cur=conn.cursor();cur.execute('BEGIN TRANSACTION')
        try:
            cur.execute(DDL)
            while cur.nextset(): pass
            cur.execute('COMMIT TRANSACTION')
        except Exception:
            cur.execute('IF @@TRANCOUNT>0 ROLLBACK TRANSACTION');raise
    return dict(estado='creado',backupId=evidence['backupId'],ruta=evidence['ruta'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--backup-only',action='store_true');parser.add_argument('--preparacion');parser.add_argument('--migrate',action='store_true')
    args=parser.parse_args()
    if args.backup_only and args.preparacion and not args.migrate:
        print({'backupId':respaldo.crear(args.preparacion)['backupId']})
    elif args.migrate and not args.backup_only and not args.preparacion: print(migrate())
    else: parser.error('Elegí --migrate o --backup-only --preparacion TOKEN')
if __name__=='__main__': main()
