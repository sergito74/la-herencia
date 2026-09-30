"""Corrige el `[Nro Documento]` de las ramas Galicia y Banco Nacion de
`vw_MovimientosCuenta_Base`, que salía en notación científica (ej.
"2.40732e+007" en vez de "24073169").

Causa: `Movimientos BNA.[Nro# Comprobante]` y `Movimientos Galicia.[Número
de Comprobante]` son columnas `float`, y en SQL Server `CAST(float AS
varchar)` pasa a notación científica a partir de 7 dígitos. Se reemplaza
por la conversión vía `decimal(38,0)`, la misma que ya usaba la rama de
`Pagos efectivo` de esta vista.

Solo cambia esas dos expresiones — ninguna otra rama se modifica.

Backup verificado de `WC` requerido antes de correr (Constitución,
Principio II — cambio de esquema/vista).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.corregir_nro_documento_bancos_en_vista
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

REEMPLAZOS = [
    (
        "CAST(g.[Número de Comprobante] AS varchar(50)) AS [Nro Documento]",
        "CONVERT(varchar(50), CONVERT(decimal(38,0), g.[Número de Comprobante])) AS [Nro Documento]",
    ),
    (
        "CAST(b.[Nro# Comprobante] AS varchar(50)) AS [Nro Documento]",
        "CONVERT(varchar(50), CONVERT(decimal(38,0), b.[Nro# Comprobante])) AS [Nro Documento]",
    ),
]


def construir_nueva_definicion(definicion_actual: str) -> str:
    nueva = definicion_actual
    for viejo, nuevo in REEMPLAZOS:
        if nueva.count(viejo) != 1:
            raise RuntimeError(f"Se esperaba exactamente una ocurrencia de: {viejo}")
        nueva = nueva.replace(viejo, nuevo, 1)
    return nueva.replace("CREATE VIEW dbo.vw_MovimientosCuenta_Base", "ALTER VIEW dbo.vw_MovimientosCuenta_Base", 1)


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))")
        definicion_actual = cursor.fetchone()[0]
        cursor.execute(construir_nueva_definicion(definicion_actual))
        print("OK: [Nro Documento] de Galicia y Banco Nacion corregido en vw_MovimientosCuenta_Base.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
