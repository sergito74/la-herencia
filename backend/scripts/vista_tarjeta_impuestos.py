"""Cuenta corriente: consumos de tarjeta vinculados a boletas de impuestos (2026-10-02).

025-conciliacion-tarjetas-impuestos permite vincular un consumo de tarjeta a
un pago de `dbo.Impuestos` (`Tarjetas_Resumenes_Lineas_Compras.IdImpuesto`),
pero `vw_MovimientosCuenta_Base` solo mostraba los vínculos con Compras: al
vincular la línea de ARBA del 29/02/2024 ($312.351,20, boleta 1047) el pago
desapareció de la cuenta del organismo (la rama 'Tarjeta sin imputar' ya no
la muestra porque está vinculada, y la rama 'Tarjetas' exige una compra).

Se agrega la rama 'Tarjeta impuesto': crédito al organismo de la boleta por
lo imputado. Idempotente, con respaldo verificado.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.vista_tarjeta_impuestos
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

RAMA = """

UNION ALL

SELECT
    t.FechaCompra AS Fecha,
    i.IdOrganismo AS IdContacto,
    ct.[Razon Social],
    CAST('Tarjeta' AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN v.ImporteImputado < 0 THEN -v.ImporteImputado ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN v.ImporteImputado > 0 THEN v.ImporteImputado ELSE CAST(0 AS money) END AS Credito,
    CAST('Tarjeta impuesto' AS varchar(50)) AS Origen,
    CAST(v.IdVinculo AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Lineas_Compras AS v
INNER JOIN dbo.Tarjetas_Resumenes_Lineas AS t ON t.IdLineaConsumo = v.IdLineaConsumo
LEFT JOIN dbo.Tarjetas_Resumenes AS rs ON rs.IdResumen = t.IdResumen
INNER JOIN dbo.Impuestos AS i ON i.IdImpuesto = v.IdImpuesto
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = i.IdOrganismo
WHERE v.IdImpuesto IS NOT NULL AND ISNULL(v.ImporteImputado, 0) <> 0
"""
MARCA_FIN = "\n\n) AS base\nOUTER APPLY ("


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        definicion = cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))").fetchone()[0]
        definicion = definicion.replace("\r\n", "\n")
        if "'Tarjeta impuesto'" in definicion:
            print("La vista ya incluye los consumos de tarjeta vinculados a impuestos.")
            return
        if definicion.count(MARCA_FIN) != 1:
            raise RuntimeError("No se encontró el cierre de la unión en la vista.")
        print(f"Respaldo verificado: {backup_verificado('vista-tarjeta-impuestos')}")
        cur.execute(definicion.replace(MARCA_FIN, RAMA + MARCA_FIN).replace("CREATE VIEW", "ALTER VIEW", 1))
        print("Vista ampliada con consumos de tarjeta vinculados a impuestos.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
