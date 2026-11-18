"""18/11/2026: tablas de la lectura de órdenes de la planilla de Matías. Registra qué fecha de la planilla ya se cargó
como orden (con su huella, para avisar si Matías la cambia después) y el resultado de cada lectura.
Siembra las 4 órdenes que ya estaban cargadas a mano (05/03, 26/06, 02/09 y 20/10/2026). Solo WC. Re-corrible."""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

YA_CARGADAS = {"2026-03-05": 148, "2026-06-26": 150, "2026-09-02": 153, "2026-10-20": 162}


def main() -> None:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cur.execute("""IF OBJECT_ID('dbo.OrdenesPlanillaMatias') IS NULL
            CREATE TABLE dbo.OrdenesPlanillaMatias (
                Fecha date NOT NULL PRIMARY KEY,
                IdOrdenTrabajo int NOT NULL,
                Huella varchar(40) NULL,
                Creado datetime2 NOT NULL CONSTRAINT DF_OrdenesPlanillaMatias_Creado DEFAULT SYSDATETIME())""")
        cur.execute("""IF OBJECT_ID('dbo.OrdenesPlanillaMatiasLecturas') IS NULL
            CREATE TABLE dbo.OrdenesPlanillaMatiasLecturas (
                IdLectura int IDENTITY(1,1) PRIMARY KEY,
                Fecha datetime2 NOT NULL CONSTRAINT DF_OrdenesPlanillaMatiasLecturas_Fecha DEFAULT SYSDATETIME(),
                Resultado nvarchar(max) NOT NULL)""")
        for fecha, orden in YA_CARGADAS.items():
            cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.OrdenesPlanillaMatias WHERE Fecha = ?) "
                        "INSERT INTO dbo.OrdenesPlanillaMatias (Fecha, IdOrdenTrabajo, Huella) VALUES (?, ?, NULL)", (fecha, fecha, orden))
        conn.commit()
        print("ok")


if __name__ == "__main__":
    main()
