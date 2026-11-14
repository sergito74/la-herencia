"""Tablas del tamiz por rubro e imputación progresiva (049 + 050).

Idempotente: crea lo que falta y recarga la tabla rubro→destino desde
specs/050-tamizado-imputacion-cultivos/tabla-rubros-destino.md (cerrada 14/11/2026).
Nunca corre contra `LaHerencia`. Toma backup verificado antes de escribir.

Uso (desde backend/):  python -m scripts.crear_tablas_tamiz_050
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

PARTES = [
    (1, "Semilla"), (2, "Fertilizantes"), (3, "Agroquímicos"), (4, "Labores"), (5, "Cosecha"),
    (6, "Fletes"), (7, "Seguro agrícola"), (8, "Asesoramiento/análisis"), (9, "Comercialización"),
]

# (IdRubro, Destino, IdParte, ReglaDepende) — tabla-rubros-destino.md
RUBROS = [
    # A cultivo · insumos de stock
    (2, "CultivoStock", 3, None),            # Herbicidas
    (2047893505, "CultivoStock", 3, None),   # Coadyuvantes
    (2047893469, "CultivoStock", 3, None),   # Insecticidas
    (2047893470, "CultivoStock", 3, None),   # Fungicidas
    (2047893449, "CultivoStock", 2, None),   # Fertilizantes
    (564800828, "CultivoStock", 1, None),    # Semillas
    (2047893471, "CultivoStock", 1, None),   # Inoculantes
    (2047893501, "CultivoStock", 6, "FleteInsumo"),  # Flete insumos: al costo del insumo
    # A cultivo · de una vez
    (2047893441, "Cultivo", 4, None),        # Fumigacion
    (-1677475049, "Cultivo", 4, None),       # Siembra
    (10, "Cultivo", 4, None),                # Fertilizacion
    (2047893475, "Cultivo", 4, None),        # Disqueado
    (12, "Cultivo", 5, None),                # Cosecha
    (2047893500, "Cultivo", 5, None),        # Control Cosecha
    (2047893499, "Cultivo", 8, None),        # Seguimiento cultivos
    (2047893504, "Cultivo", 8, None),        # Analisis PG
    (2047893474, "Cultivo", 7, None),        # Seguros Agricolas
    (2047893445, "Cultivo", 9, None),        # Gastos Comercializacion
    (2047893491, "Cultivo", 9, None),        # Flete granos
    (2047893476, "Cultivo", 9, None),        # Extraccion Grano
    (2047893494, "Cultivo", 9, None),        # Honorarios Laboratorio
    # Depende
    (2047893465, "Depende", None, "AnalisisLaboratorio"),
    (1768231871, "Depende", None, "Combustible"),
    (2047893443, "Depende", None, "Financiamiento"),
    (2047893452, "Depende", None, "SegunUsoOrden"),  # Insumos productivos (silobolsa, hilo, malla)
    # Ganadería
    (2047893453, "Ganaderia", None, None), (2047893466, "Ganaderia", None, None),
    (639489777, "Ganaderia", None, None), (2047893467, "Ganaderia", None, None),
    (2047893480, "Ganaderia", None, None),
    # Financiero
    (2047893509, "Financiero", None, None),
    # Estructura
    *[(r, "Estructura", None, None) for r in (
        2047893477, 2047893454, 2047893446, 5, 2047893444, 13, 2047893486, 21, 14, 2047893459,
        2047893455, 9, 2047893462, 2047893458, 2047893460, 2047893457, -1871846883, 8,
    )],
]

DDL = [
    """IF OBJECT_ID('dbo.PartesEstructuraCosto','U') IS NULL
    CREATE TABLE dbo.PartesEstructuraCosto (
        IdParte int NOT NULL PRIMARY KEY, Nombre nvarchar(50) NOT NULL UNIQUE, Orden int NOT NULL)""",
    """IF OBJECT_ID('dbo.PartesEstructuraCultivoInactivas','U') IS NULL
    CREATE TABLE dbo.PartesEstructuraCultivoInactivas (
        IdCultivo int NOT NULL, IdParte int NOT NULL REFERENCES dbo.PartesEstructuraCosto(IdParte),
        CONSTRAINT PK_PartesEstructuraCultivoInactivas PRIMARY KEY (IdCultivo, IdParte))""",
    """IF OBJECT_ID('dbo.TamizRubroDestino','U') IS NULL
    CREATE TABLE dbo.TamizRubroDestino (
        IdRubro int NOT NULL PRIMARY KEY,
        Destino varchar(20) NOT NULL CHECK (Destino IN ('CultivoStock','Cultivo','Depende','Ganaderia','Financiero','Estructura','NoImputa')),
        IdParte int NULL REFERENCES dbo.PartesEstructuraCosto(IdParte),
        ReglaDepende varchar(30) NULL,
        CONSTRAINT CK_TamizRubroDestino_Parte CHECK (Destino NOT IN ('CultivoStock','Cultivo') OR IdParte IS NOT NULL))""",
    """IF OBJECT_ID('dbo.TamizReglaProducto','U') IS NULL
    CREATE TABLE dbo.TamizReglaProducto (
        IdRegla int NOT NULL IDENTITY PRIMARY KEY, TextoNormalizado nvarchar(200) NULL, IdFormulado int NULL,
        Destino varchar(20) NULL, IdParte int NULL REFERENCES dbo.PartesEstructuraCosto(IdParte),
        Usuario nvarchar(100) NULL, FechaAlta datetime2 NOT NULL DEFAULT SYSDATETIME())""",
    """IF OBJECT_ID('dbo.ImputacionConfig','U') IS NULL
    CREATE TABLE dbo.ImputacionConfig (
        Id int NOT NULL PRIMARY KEY CHECK (Id = 1), IdDeudaCorte int NULL, FechaActivacion datetime2 NULL,
        Activo bit NOT NULL DEFAULT 0)""",
    """IF OBJECT_ID('dbo.ImputacionAlcance','U') IS NULL
    CREATE TABLE dbo.ImputacionAlcance (
        IdDetalleCompra int NOT NULL PRIMARY KEY,
        Motivo varchar(20) NOT NULL CHECK (Motivo IN ('Nuevo','StockSinImputar')),
        FechaAlta datetime2 NOT NULL DEFAULT SYSDATETIME())""",
    """IF OBJECT_ID('dbo.TamizRenglones','U') IS NULL
    CREATE TABLE dbo.TamizRenglones (
        IdTamiz int NOT NULL IDENTITY PRIMARY KEY, IdDetalleCompra int NOT NULL,
        Destino varchar(20) NULL CHECK (Destino IN ('CultivoStock','Cultivo','Depende','Ganaderia','Financiero','Estructura','NoImputa')),
        IdParte int NULL REFERENCES dbo.PartesEstructuraCosto(IdParte), IdCultivo int NULL, IdCampania int NULL,
        OrigenDecision varchar(15) NOT NULL CHECK (OrigenDecision IN ('Manual','Orden','Producto','Rubro','Revision')),
        Estado varchar(15) NOT NULL CHECK (Estado IN ('Aprobada','Pendiente')),
        Motivo nvarchar(200) NULL, FechaCalculo datetime2 NOT NULL DEFAULT SYSDATETIME(),
        Vigente bit NOT NULL DEFAULT 1, Usuario nvarchar(100) NULL)""",
    """IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_TamizRenglones_Vigente')
    CREATE UNIQUE INDEX UX_TamizRenglones_Vigente ON dbo.TamizRenglones (IdDetalleCompra) WHERE Vigente = 1""",
    """IF OBJECT_ID('dbo.VinculoRemitoPendiente','U') IS NULL
    CREATE TABLE dbo.VinculoRemitoPendiente (
        IdVinculoPend int NOT NULL IDENTITY PRIMARY KEY, IdDetalleRemito int NULL, IdDetalleCompra int NULL,
        Tipo varchar(15) NOT NULL DEFAULT 'remito', CandidatosJson nvarchar(max) NULL, Motivo nvarchar(200) NULL,
        FechaCalculo datetime2 NOT NULL DEFAULT SYSDATETIME(), Resuelto bit NOT NULL DEFAULT 0)""",
    """IF COL_LENGTH('dbo.ImputacionPropuestas','IdParte') IS NULL
    ALTER TABLE dbo.ImputacionPropuestas ADD IdParte int NULL""",
]


def main() -> None:
    _assert_target_is_wc()
    print("Backup:", backup_verificado("pre_tamiz_050"))
    with pyodbc.connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        for sql in DDL:
            cur.execute(sql)
        for id_parte, nombre in PARTES:
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM dbo.PartesEstructuraCosto WHERE IdParte=?) "
                "INSERT dbo.PartesEstructuraCosto (IdParte, Nombre, Orden) VALUES (?,?,?)",
                id_parte, id_parte, nombre, id_parte,
            )
        existentes = {r[0] for r in cur.execute("SELECT IdRubro FROM dbo.Rubros").fetchall()}
        faltan = [r[0] for r in RUBROS if r[0] not in existentes]
        if faltan:
            raise RuntimeError(f"Rubros inexistentes: {faltan}")
        cur.execute("DELETE dbo.TamizRubroDestino")
        cur.executemany("INSERT dbo.TamizRubroDestino (IdRubro, Destino, IdParte, ReglaDepende) VALUES (?,?,?,?)", RUBROS)
        cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.ImputacionConfig) INSERT dbo.ImputacionConfig (Id, Activo) VALUES (1, 0)")
        conn.commit()
        print("Partes:", cur.execute("SELECT COUNT(*) FROM dbo.PartesEstructuraCosto").fetchone()[0],
              "· Rubros:", cur.execute("SELECT COUNT(*) FROM dbo.TamizRubroDestino").fetchone()[0],
              "· Activo:", cur.execute("SELECT Activo FROM dbo.ImputacionConfig").fetchone()[0])


if __name__ == "__main__":
    main()
