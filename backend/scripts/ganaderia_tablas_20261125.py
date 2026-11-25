"""052 Módulo Ganadero, etapa 1 (T009–T010): tablas Gan*, columna Map_CultivoResultado.EsGanaderia y datos
iniciales. Idempotente. Simula por defecto; con --aplicar hace BACKUP DATABASE verificado y aplica en una
transacción. Uso (desde backend/): python -m scripts.ganaderia_tablas_20261125 [--aplicar]
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyodbc  # noqa: E402

from src.db.connection import CONNECTION_STRING, fetch_all, get_connection  # noqa: E402

TABLAS = {
    "GanCategoria": """CREATE TABLE dbo.GanCategoria (
        IdCategoria int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanCategoria PRIMARY KEY,
        Nombre nvarchar(60) NOT NULL CONSTRAINT UQ_GanCategoria_Nombre UNIQUE,
        IdTipoHacienda int NULL,
        Sexo char(1) NOT NULL CONSTRAINT CK_GanCategoria_Sexo CHECK (Sexo IN ('H','M')),
        CoefEV decimal(5,2) NOT NULL,
        PesoTipicoKg decimal(7,1) NOT NULL,
        Orden int NOT NULL,
        IdCategoriaSiguiente int NULL CONSTRAINT FK_GanCategoria_Sig REFERENCES dbo.GanCategoria(IdCategoria),
        EsReproductor bit NOT NULL CONSTRAINT DF_GanCategoria_Repr DEFAULT 0,
        Activo bit NOT NULL CONSTRAINT DF_GanCategoria_Activo DEFAULT 1)""",
    "GanCategoriaAlias": """CREATE TABLE dbo.GanCategoriaAlias (
        IdAlias int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanCategoriaAlias PRIMARY KEY,
        Texto nvarchar(80) NOT NULL CONSTRAINT UQ_GanCategoriaAlias UNIQUE,
        IdCategoria int NOT NULL CONSTRAINT FK_GanAlias_Cat REFERENCES dbo.GanCategoria(IdCategoria),
        EsTerceros bit NOT NULL CONSTRAINT DF_GanAlias_Terc DEFAULT 0)""",
    "GanMovimiento": """CREATE TABLE dbo.GanMovimiento (
        IdMovimiento int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanMovimiento PRIMARY KEY,
        Fecha date NOT NULL,
        Tipo nvarchar(20) NOT NULL CONSTRAINT CK_GanMovimiento_Tipo CHECK (Tipo IN ('Nacimiento','Compra','Venta','Muerte',
            'Consumo','CambioCategoria','PastajeEntrada','PastajeSalida','Traslado','AjusteRecuento')),
        IdCategoria int NOT NULL CONSTRAINT FK_GanMov_Cat REFERENCES dbo.GanCategoria(IdCategoria),
        IdCategoriaDestino int NULL CONSTRAINT FK_GanMov_CatDest REFERENCES dbo.GanCategoria(IdCategoria),
        Cabezas int NOT NULL,
        Kg decimal(12,1) NULL,
        KgEstimado bit NOT NULL CONSTRAINT DF_GanMov_KgEst DEFAULT 0,
        IdContactoDueno int NULL,
        IdEstablecimiento int NOT NULL,
        IdEstablecimientoDestino int NULL,
        IdDetalleVenta int NULL,
        IdContratoPastaje int NULL,
        IdCompra int NULL,
        Causa nvarchar(40) NULL,
        CausaDiagnostico nvarchar(40) NULL,
        Fuente nvarchar(120) NOT NULL,
        Motivo nvarchar(300) NULL,
        Anulado bit NOT NULL CONSTRAINT DF_GanMov_Anulado DEFAULT 0,
        CreadoPor nvarchar(60) NULL,
        CreadoEn datetime2 NOT NULL CONSTRAINT DF_GanMov_Creado DEFAULT SYSDATETIME())""",
    "GanRecuento": """CREATE TABLE dbo.GanRecuento (
        IdRecuento int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanRecuento PRIMARY KEY,
        Fecha date NOT NULL,
        IdEstablecimiento int NOT NULL,
        Origen nvarchar(20) NOT NULL CONSTRAINT CK_GanRecuento_Origen CHECK (Origen IN ('Recuento','Acta','Cierre','Planilla')),
        Archivo nvarchar(400) NULL,
        Observaciones nvarchar(300) NULL,
        Anulado bit NOT NULL CONSTRAINT DF_GanRec_Anulado DEFAULT 0,
        CreadoPor nvarchar(60) NULL,
        CreadoEn datetime2 NOT NULL CONSTRAINT DF_GanRec_Creado DEFAULT SYSDATETIME())""",
    "GanRecuentoDetalle": """CREATE TABLE dbo.GanRecuentoDetalle (
        IdRecuentoDetalle int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanRecuentoDetalle PRIMARY KEY,
        IdRecuento int NOT NULL CONSTRAINT FK_GanRecDet_Rec REFERENCES dbo.GanRecuento(IdRecuento),
        IdCategoria int NOT NULL CONSTRAINT FK_GanRecDet_Cat REFERENCES dbo.GanCategoria(IdCategoria),
        IdContactoDueno int NULL,
        Cabezas int NOT NULL,
        KgPromedio decimal(7,1) NULL,
        PrecioCabeza decimal(14,2) NULL,
        Moneda nvarchar(10) NULL)""",
    "GanRubroMapa": """CREATE TABLE dbo.GanRubroMapa (
        IdRubroMapa int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanRubroMapa PRIMARY KEY,
        RubroPlanilla nvarchar(60) NOT NULL,
        Grupo nvarchar(20) NOT NULL CONSTRAINT CK_GanRubroMapa_Grupo CHECK (Grupo IN ('Comercializacion','Directos',
            'Sanidad','Alimentacion','Estructura','CompraHacienda')),
        Orden int NOT NULL,
        IdRubro int NULL, IdDestino int NULL, IdCultivo int NULL)""",
    "GanForrajeRegla": """CREATE TABLE dbo.GanForrajeRegla (
        IdCultivo int NOT NULL CONSTRAINT PK_GanForrajeRegla PRIMARY KEY,
        Tratamiento nvarchar(10) NOT NULL CONSTRAINT CK_GanForraje_Trat CHECK (Tratamiento IN ('Consumo','Amortiza')),
        Anios int NOT NULL CONSTRAINT DF_GanForraje_Anios DEFAULT 1,
        DesfaseEjercicios int NOT NULL CONSTRAINT DF_GanForraje_Desfase DEFAULT 0,
        Observaciones nvarchar(200) NULL)""",
    "GanCalendarioCultivo": """CREATE TABLE dbo.GanCalendarioCultivo (
        IdCultivo int NOT NULL CONSTRAINT PK_GanCalendarioCultivo PRIMARY KEY,
        MesDesde tinyint NOT NULL, MesHasta tinyint NOT NULL)""",
    "GanSuperficieAjuste": """CREATE TABLE dbo.GanSuperficieAjuste (
        IdAjuste int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanSuperficieAjuste PRIMARY KEY,
        IdLote int NOT NULL, Ejercicio nvarchar(9) NOT NULL, MesesGanaderos decimal(4,1) NOT NULL,
        Motivo nvarchar(300) NOT NULL, Usuario nvarchar(60) NULL,
        Fecha datetime2 NOT NULL CONSTRAINT DF_GanSupAj_Fecha DEFAULT SYSDATETIME(),
        CONSTRAINT UQ_GanSuperficieAjuste UNIQUE (IdLote, Ejercicio))""",
    "GanReserva": """CREATE TABLE dbo.GanReserva (
        IdReserva int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanReserva PRIMARY KEY,
        Tipo nvarchar(10) NOT NULL CONSTRAINT CK_GanReserva_Tipo CHECK (Tipo IN ('Silo','Rollo')),
        Fecha date NOT NULL, IdLote int NULL, IdCultivo int NULL, IdCampania int NULL,
        Kg decimal(14,1) NOT NULL CONSTRAINT CK_GanReserva_Kg CHECK (Kg > 0),
        CostoPesos decimal(16,2) NOT NULL, CostoUSD decimal(14,2) NULL,
        Fuente nvarchar(120) NOT NULL, Observaciones nvarchar(300) NULL,
        Anulado bit NOT NULL CONSTRAINT DF_GanReserva_Anulado DEFAULT 0,
        CreadoPor nvarchar(60) NULL, CreadoEn datetime2 NOT NULL CONSTRAINT DF_GanReserva_Creado DEFAULT SYSDATETIME())""",
    "GanReservaConsumo": """CREATE TABLE dbo.GanReservaConsumo (
        IdConsumo int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanReservaConsumo PRIMARY KEY,
        IdReserva int NOT NULL CONSTRAINT FK_GanResCons_Res REFERENCES dbo.GanReserva(IdReserva),
        Fecha date NOT NULL, Kg decimal(14,1) NOT NULL CONSTRAINT CK_GanResCons_Kg CHECK (Kg > 0),
        Motivo nvarchar(300) NULL, Usuario nvarchar(60) NULL,
        Anulado bit NOT NULL CONSTRAINT DF_GanResCons_Anulado DEFAULT 0,
        CreadoEn datetime2 NOT NULL CONSTRAINT DF_GanResCons_Creado DEFAULT SYSDATETIME())""",
    "GanReparto": """CREATE TABLE dbo.GanReparto (
        IdReparto int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanReparto PRIMARY KEY,
        Concepto nvarchar(60) NOT NULL, Ejercicio nvarchar(9) NULL,
        PctGanaderia decimal(5,2) NOT NULL, PctEstructura decimal(5,2) NOT NULL, PctAgricultura decimal(5,2) NOT NULL,
        CONSTRAINT CK_GanReparto_Suma CHECK (PctGanaderia + PctEstructura + PctAgricultura = 100),
        CONSTRAINT UQ_GanReparto UNIQUE (Concepto, Ejercicio))""",
    "GanSuperficieCampo": """CREATE TABLE dbo.GanSuperficieCampo (
        IdSuperficie int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanSuperficieCampo PRIMARY KEY,
        AnioDesde int NOT NULL, AnioHasta int NULL,
        TotalHa decimal(8,2) NULL, HaGanaderasFijas decimal(8,2) NULL,
        Fuente nvarchar(200) NOT NULL,
        CONSTRAINT CK_GanSuperficieCampo CHECK (TotalHa IS NOT NULL OR HaGanaderasFijas IS NOT NULL))""",
    "GanControlAceptado": """CREATE TABLE dbo.GanControlAceptado (
        IdAceptado int IDENTITY(1,1) NOT NULL CONSTRAINT PK_GanControlAceptado PRIMARY KEY,
        Tipo nvarchar(40) NOT NULL, Clave nvarchar(200) NOT NULL, Motivo nvarchar(300) NOT NULL,
        Usuario nvarchar(60) NULL, Fecha datetime2 NOT NULL CONSTRAINT DF_GanCtrlAcep_Fecha DEFAULT SYSDATETIME(),
        Vigente bit NOT NULL CONSTRAINT DF_GanCtrlAcep_Vigente DEFAULT 1)""",
}

INDICES = [
    "CREATE UNIQUE INDEX UX_GanMovimiento_Venta ON dbo.GanMovimiento(IdDetalleVenta) WHERE IdDetalleVenta IS NOT NULL AND Anulado = 0",
    "CREATE INDEX IX_GanMovimiento_Fecha ON dbo.GanMovimiento(IdEstablecimiento, Fecha) INCLUDE (IdCategoria, Cabezas, IdContactoDueno, Anulado)",
    "CREATE UNIQUE INDEX UX_GanRecuentoDetalle ON dbo.GanRecuentoDetalle(IdRecuento, IdCategoria, IdContactoDueno)",
]

# (nombre, IdTipoHacienda, sexo, EV, kg típico, orden, siguiente, reproductor). Pesos típicos = supuesto inicial
# configurable (Configuración); EV de la planilla histórica de Sergio.
CATEGORIAS = [
    ("Terneras", 1, "H", 0.6, 190, 10, "Terneras 15 meses", 0),
    ("Terneros", 2, "M", 0.6, 200, 11, "Novillitos", 0),
    ("Terneras 15 meses", 1, "H", 0.7, 280, 20, "Vaquillonas 1-2", 0),
    ("Novillitos", 4, "M", 0.7, 300, 21, "Novillos", 0),
    ("Vaquillonas 1-2", 3, "H", 0.8, 330, 30, "Vaquillonas 2 dientes", 0),
    ("Vaquillonas 2 dientes", 3, "H", 0.8, 380, 31, "Vaquillonas preñadas", 1),
    ("Vaquillonas preñadas", 9, "H", 0.9, 400, 32, "Vacas 2° servicio", 1),
    ("Novillos", 4, "M", 0.7, 420, 33, None, 0),
    ("Toritos", 7, "M", 0.7, 350, 34, "Toros", 0),
    ("Vacas 2° servicio", 6, "H", 1.0, 420, 40, "Vacas", 1),
    ("Vacas", 6, "H", 1.0, 450, 41, None, 1),
    ("Vacas preñadas", 8, "H", 1.0, 480, 42, None, 1),
    ("Vacas conserva", 5, "H", 1.0, 400, 43, None, 0),
    ("Toros", 7, "M", 1.3, 750, 44, None, 1),
]

ALIAS = [  # texto de planillas, actas y mails → categoría (minúsculas comparan)
    ("Vacas", "Vacas", 0), ("Vaca", "Vacas", 0), ("Vacas 2° Servicio", "Vacas 2° servicio", 0),
    ("Vacas 2º Servicio", "Vacas 2° servicio", 0), ("Vaquillonas", "Vaquillonas 1-2", 0),
    ("Vaquillonas 1 ½ años", "Vaquillonas 1-2", 0), ("VAQ. 1-2", "Vaquillonas 1-2", 0),
    ("Vaquillonas 2 años", "Vaquillonas 2 dientes", 0), ("Vaquillonas 2d", "Vaquillonas 2 dientes", 0),
    ("Vaquillonas 2 dientes", "Vaquillonas 2 dientes", 0), ("Vaquillonas pr", "Vaquillonas preñadas", 0),
    ("Vaquillonas preñadas", "Vaquillonas preñadas", 0), ("Vacas preñadas", "Vacas preñadas", 0),
    ("Vacas conserva", "Vacas conserva", 0), ("Terneras 15 meses", "Terneras 15 meses", 0),
    ("Terneras 15 me", "Terneras 15 meses", 0), ("Terneras", "Terneras", 0), ("Terneros", "Terneros", 0),
    ("Novillitos", "Novillitos", 0), ("Novillo", "Novillos", 0), ("Novillos", "Novillos", 0),
    ("Toritos", "Toritos", 0), ("Toros", "Toros", 0), ("Terneras Miguel", "Vaquillonas 1-2", 1),
]

FORRAJES = [  # (IdCultivo, tratamiento, años, desfase de ejercicios campaña→consumo, observación)
    (9, "Consumo", 1, 0, "Avena del año N: se come abr-N/mar-N+1"),
    (2, "Consumo", 1, 1, "Maíz diferido N-1/N: se come en el ejercicio siguiente"),
    (5, "Consumo", 1, 0, "Sorgo: verdeo de verano / diferido"),
    (7, "Amortiza", 4, 0, "Pastura: amortiza desde el primer pastoreo; baja anticipada si se siembra agricultura"),
]
CALENDARIO = [(3, 11, 4), (4, 1, 4), (1, 10, 4), (6, 10, 3), (8, 6, 12), (11, 6, 12)]  # meses fuera de pastoreo

RUBROS = [  # (rubro de la planilla, grupo, orden, nombre del rubro de compra)
    ("Gastos comercialización", "Comercializacion", 10, "Gastos Comercializacion"),
    ("Flete hacienda", "Comercializacion", 11, "Flete hacienda"),
    ("Sellados", "Comercializacion", 12, "Sellados"),
    ("Compra de hacienda", "CompraHacienda", 15, "Hacienda"),
    ("Flete insumos", "Directos", 20, "Flete insumos"),
    ("Insumos generales", "Directos", 21, "Insumos Generales"),
    ("Insumos productivos", "Directos", 22, "Insumos productivos"),
    ("Personal eventual", "Directos", 23, "Personal Eventual"),
    ("Secado", "Directos", 24, "Secado"),
    ("Seguros laborales", "Directos", 25, "Seguros Laborales"),
    ("Servicio logística", "Directos", 26, "Servicio Logistica"),
    ("Disqueado", "Directos", 27, "Disqueado"),
    ("Combustible", "Directos", 28, "Combustible"),
    ("Mantenimiento instalaciones", "Directos", 29, "Mantenimiento Instalaciones"),
    ("Productos veterinarios", "Sanidad", 30, "Productos Veterinarios"),
    ("Inseminación", "Sanidad", 31, "Inseminacion"),
    ("Análisis laboratorio", "Sanidad", 32, "Analisis laboratorio"),
    ("Aranceles vacunación", "Sanidad", 33, "Aranceles Vacunacion"),
    ("Honorarios profesionales", "Sanidad", 34, "Honorarios Profesionales"),
    ("Honorarios laboratorio", "Sanidad", 35, "Honorarios Laboratorio"),
    ("Tacto/Ecografía", "Sanidad", 36, "Tacto/Ecografia"),
    ("Vacunas", "Sanidad", 37, "Vacunas"),
    ("Alimento feed lot", "Alimentacion", 40, "Alimento feed lot"),
    ("Alimento general", "Alimentacion", 41, "Alimento general"),
    ("Confección silo", "Alimentacion", 42, "Confeccion Silo"),
    ("Pastaje (pagado)", "Alimentacion", 43, "Pastaje"),
    ("Gastos de administración", "Estructura", 60, "Gastos de Administracion"),
    ("Honorarios administración", "Estructura", 61, "Honorarios Administracion"),
    ("Movilidad", "Estructura", 62, "Movilidad"),
    ("Financiamiento", "Estructura", 63, "Financiamiento"),
    ("Mantenimiento construcciones", "Estructura", 64, "Mantenimiento Construcciones"),
    ("Seguros generales", "Estructura", 65, "Seguros Generales"),
]


def _backup() -> str:
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        carpeta = cur.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[0]
        ruta = str(PureWindowsPath(carpeta) / f"WC_pre_ganaderia_052_{datetime.now():%Y%m%d_%H%M%S}.bak")
        cur.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        cur.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (ruta,))
        while cur.nextset():
            pass
        return ruta


def _existe(cur, tabla: str) -> bool:
    return cur.execute("SELECT OBJECT_ID(?)", (f"dbo.{tabla}",)).fetchone()[0] is not None


def aplicar(cur) -> None:
    for nombre, ddl in TABLAS.items():
        if not _existe(cur, nombre):
            cur.execute(ddl)
    for ix in INDICES:
        nombre = ix.split(" INDEX ")[1].split(" ON ")[0]
        if not cur.execute("SELECT 1 FROM sys.indexes WHERE name = ?", (nombre,)).fetchone():
            cur.execute(ix)
    if cur.execute("SELECT COL_LENGTH('dbo.Map_CultivoResultado', 'EsGanaderia')").fetchone()[0] is None:
        cur.execute("ALTER TABLE dbo.Map_CultivoResultado ADD EsGanaderia bit NOT NULL "
                    "CONSTRAINT DF_MapCultivo_EsGanaderia DEFAULT 0")
    # Sergio 25/11/2026: Sorgo, Maíz diferido, Avena y Pastura son ganaderos (rye grass y verdeos son destinos, no cultivos)
    cur.execute("UPDATE dbo.Map_CultivoResultado SET EsGanaderia = CASE WHEN IdCultivo IN (2, 5, 7, 9) THEN 1 ELSE 0 END")
    for nombre, tipo, sexo, ev, kg, orden, _sig, repr_ in CATEGORIAS:
        cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.GanCategoria WHERE Nombre = ?) INSERT INTO dbo.GanCategoria "
                    "(Nombre, IdTipoHacienda, Sexo, CoefEV, PesoTipicoKg, Orden, EsReproductor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (nombre, nombre, tipo, sexo, ev, kg, orden, repr_))
    for nombre, *_x, sig, _r in CATEGORIAS:
        if sig:
            cur.execute("UPDATE c SET IdCategoriaSiguiente = s.IdCategoria FROM dbo.GanCategoria c "
                        "JOIN dbo.GanCategoria s ON s.Nombre = ? WHERE c.Nombre = ?", (sig, nombre))
    for texto, cat, terc in ALIAS:
        cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.GanCategoriaAlias WHERE Texto = ?) INSERT INTO dbo.GanCategoriaAlias "
                    "(Texto, IdCategoria, EsTerceros) SELECT ?, IdCategoria, ? FROM dbo.GanCategoria WHERE Nombre = ?",
                    (texto, texto, terc, cat))
    for idc, trat, anios, desf, obs in FORRAJES:
        cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.GanForrajeRegla WHERE IdCultivo = ?) INSERT INTO dbo.GanForrajeRegla "
                    "(IdCultivo, Tratamiento, Anios, DesfaseEjercicios, Observaciones) VALUES (?, ?, ?, ?, ?)",
                    (idc, idc, trat, anios, desf, obs))
    for idc, desde, hasta in CALENDARIO:
        cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.GanCalendarioCultivo WHERE IdCultivo = ?) INSERT INTO "
                    "dbo.GanCalendarioCultivo (IdCultivo, MesDesde, MesHasta) VALUES (?, ?, ?)", (idc, idc, desde, hasta))
    if cur.execute("SELECT COL_LENGTH('dbo.GanReparto', 'IdContacto')").fetchone()[0] is None:
        cur.execute("ALTER TABLE dbo.GanReparto ADD IdContacto int NULL")
    cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.GanReparto WHERE Concepto = 'Personal permanente' AND Ejercicio IS NULL) "
                "INSERT INTO dbo.GanReparto (Concepto, Ejercicio, PctGanaderia, PctEstructura, PctAgricultura) "
                "VALUES ('Personal permanente', NULL, 70, 20, 10)")
    # Sergio 25/11/2026: el encargado del campo (único permanente del campo) es Marcelo Sierra, contacto 374.
    cur.execute("UPDATE dbo.GanReparto SET IdContacto = 374 WHERE Concepto = 'Personal permanente' AND IdContacto IS NULL")
    # Sergio 25/11/2026: total del campo = loteo vigente del plan 26/27 (402,1 ha); antes de 2021/22 (sin Plan agrícola
    # cargado y con lotes arrendados a terceros) las ha ganaderas son las de su planilla histórica.
    if not cur.execute("SELECT 1 FROM dbo.GanSuperficieCampo").fetchone():
        cur.execute("INSERT INTO dbo.GanSuperficieCampo (AnioDesde, AnioHasta, TotalHa, Fuente) VALUES "
                    "(2021, NULL, 402.1, 'Loteo vigente del plan agrícola 26/27')")
        for anio, ha in ((2015, 343.4), (2016, 264.8), (2017, 264.3), (2018, 223.9), (2019, 205.3), (2020, 229.3)):
            cur.execute("INSERT INTO dbo.GanSuperficieCampo (AnioDesde, AnioHasta, HaGanaderasFijas, Fuente) VALUES "
                        "(?, ?, ?, 'Planilla Historico Negocio Ganadero (Bolívar)')", (anio, anio, ha))
    for planilla, grupo, orden, rubro in RUBROS:
        cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.GanRubroMapa WHERE RubroPlanilla = ?) INSERT INTO dbo.GanRubroMapa "
                    "(RubroPlanilla, Grupo, Orden, IdRubro) SELECT ?, ?, ?, IdRubro FROM dbo.Rubros WHERE Rubro = ?",
                    (planilla, planilla, grupo, orden, rubro))


def main():
    faltan = [r for *_x, r in RUBROS if not fetch_all("SELECT 1 x FROM dbo.Rubros WHERE Rubro = ?", (r,))]
    existentes = [t for t in TABLAS if fetch_all("SELECT OBJECT_ID(?) i", (f"dbo.{t}",))[0]["i"]]
    print(f"Tablas a crear: {len(TABLAS) - len(existentes)} (ya existen: {existentes or 'ninguna'})")
    print(f"Rubros de compra no encontrados (se omiten): {faltan or 'ninguno'}")
    print("Cultivos ganaderos: Maíz diferido, Sorgo, Pastura, Avena")
    if "--aplicar" not in sys.argv:
        print("Simulación (usar --aplicar)")
        return
    ruta = _backup()
    print(f"BACKUP_VERIFICADO={ruta}")
    with get_connection(readonly=False) as cn:
        cn.autocommit = False
        cur = cn.cursor()
        try:
            aplicar(cur)
            cn.commit()
        except Exception:
            cn.rollback()
            raise
    for t in ("GanCategoria", "GanCategoriaAlias", "GanForrajeRegla", "GanCalendarioCultivo", "GanReparto", "GanRubroMapa"):
        print(t, fetch_all(f"SELECT COUNT(*) n FROM dbo.{t}")[0]["n"])
    print("EsGanaderia:", fetch_all("SELECT IdCultivo FROM dbo.Map_CultivoResultado WHERE EsGanaderia = 1"))


if __name__ == "__main__":
    main()
