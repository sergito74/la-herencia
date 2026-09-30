"""En la cuenta corriente, las filas de pagos con tarjeta muestran como
`[Nro Documento]` el código del resumen de la tarjeta (ej. "11959252",
"VI00000000030528267"), no el número de la factura que pagan — pedido del
usuario (2026-09-30), regla para todas las cuentas. La factura ya se ve en
su propia fila ("Factura") y en el link de Origen.

Solo cambia la rama `Tarjetas` de `vw_MovimientosCuenta_Base`: la columna
y un LEFT JOIN a `Tarjetas_Resumenes` (LEFT para no perder ninguna fila).

Backup verificado de `WC` requerido antes de correr (Constitución,
Principio II — cambio de vista).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.nro_documento_tarjeta_es_resumen
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc


def construir_nueva_definicion(definicion_actual: str) -> str:
    nl = "\r\n" if "\r\n" in definicion_actual else "\n"
    reemplazos = [
        (
            f"    'Tarjeta' AS Documento,{nl}    c.[Nro Documento],",
            f"    'Tarjeta' AS Documento,{nl}    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],",
        ),
        (
            f"    ON t.IdLineaConsumo = v.IdLineaConsumo{nl}INNER JOIN dbo.Compras AS c",
            f"    ON t.IdLineaConsumo = v.IdLineaConsumo{nl}LEFT JOIN dbo.Tarjetas_Resumenes AS rs{nl}"
            f"    ON rs.IdResumen = t.IdResumen{nl}INNER JOIN dbo.Compras AS c",
        ),
    ]
    nueva = definicion_actual
    for viejo, nuevo in reemplazos:
        if nueva.count(viejo) != 1:
            raise RuntimeError(f"Se esperaba exactamente una ocurrencia de: {viejo!r}")
        nueva = nueva.replace(viejo, nuevo, 1)
    return nueva.replace("CREATE VIEW dbo.vw_MovimientosCuenta_Base", "ALTER VIEW dbo.vw_MovimientosCuenta_Base", 1)


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))")
        cursor.execute(construir_nueva_definicion(cursor.fetchone()[0]))
        print("OK: las filas de Tarjeta muestran el código del resumen en [Nro Documento].")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
