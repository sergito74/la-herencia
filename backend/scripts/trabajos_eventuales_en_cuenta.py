"""Trabajos eventuales en la cuenta corriente del trabajador (2026-11-18, pedido de Sergio).

Un trabajo eventual sin liquidación es gasto de mano de obra de Giamigli, en negro. Se paga en efectivo de una caja o
desde la cuenta de un socio. En la cuenta del trabajador se tiene que ver el trabajo y el pago que lo cancela.

Agrega dos ramas a `vw_MovimientosCuenta_Base`:
- 'Trabajo eventual' (Deuda): la parte del trabajo que no está vinculada a una liquidación. Entran solo los trabajos
  pagados en efectivo o por un socio; los pagados por banco ya tienen su liquidación y su débito.
- 'Pago trabajo eventual' (Crédito): cada pago en efectivo (operación de caja vigente) o por socio (asiento no anulado).

Es idempotente y hace un respaldo verificado antes de cambiar algo.
Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.trabajos_eventuales_en_cuenta
"""

import re

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

RAMAS = """

UNION ALL

SELECT
    CAST(t.Fecha AS datetime) AS Fecha,
    t.IdContacto,
    ct.[Razon Social],
    CAST('Trabajo eventual' AS varchar(50)) AS Documento,
    CAST(LEFT(t.Descripcion, 50) AS varchar(50)) AS [Nro Documento],
    CAST(t.Total - ISNULL(tv.Vinculado, 0) AS money) AS Deuda,
    CAST(0 AS money) AS Credito,
    CAST('Trabajo eventual' AS varchar(50)) AS Origen,
    CAST(t.IdTrabajo AS bigint) AS IdOrigen
FROM dbo.TrabajosEventuales AS t
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = t.IdContacto
OUTER APPLY (SELECT SUM(x.Importe) AS Vinculado FROM dbo.TrabajosEventualesVinculos AS x WHERE x.IdTrabajo = t.IdTrabajo) AS tv
WHERE t.Total - ISNULL(tv.Vinculado, 0) > 0
  AND EXISTS (SELECT 1 FROM dbo.TrabajosEventualesPagos AS tp WHERE tp.IdTrabajo = t.IdTrabajo AND tp.Medio IN ('caja', 'socio'))

UNION ALL

SELECT
    CAST(tp.Fecha AS datetime) AS Fecha,
    t.IdContacto,
    ct.[Razon Social],
    CAST(CASE WHEN tp.Medio = 'caja' THEN 'Pago en efectivo' ELSE 'Pago por socio' END AS varchar(50)) AS Documento,
    CAST(ISNULL(so.Nombre, 'Caja') AS varchar(50)) AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(tp.Importe AS money) AS Credito,
    CAST('Pago trabajo eventual' AS varchar(50)) AS Origen,
    CAST(tp.IdPagoTrabajo AS bigint) AS IdOrigen
FROM dbo.TrabajosEventualesPagos AS tp
INNER JOIN dbo.TrabajosEventuales AS t ON t.IdTrabajo = tp.IdTrabajo
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = t.IdContacto
LEFT JOIN dbo.OperacionesCajaEfectivo AS oc ON oc.IdOperacion = tp.IdOperacion
LEFT JOIN dbo.MovimientosCuentaSocio AS mst ON mst.IdMovimiento = tp.IdMovimientoSocio
LEFT JOIN dbo.Socios AS so ON so.IdSocio = mst.IdSocio
WHERE tp.Medio IN ('caja', 'socio')
  AND (oc.IdOperacion IS NULL OR oc.Estado = 'Vigente')
  AND (mst.IdMovimiento IS NULL OR mst.Anulada = 0)
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
        if "'Pago trabajo eventual'" in definicion:
            print("Nada para hacer: la vista ya tiene los trabajos eventuales.")
            return
        if definicion.count(MARCA_FIN) != 1:
            raise RuntimeError("No se encontró el cierre de la unión en la vista.")
        print(f"Respaldo verificado: {backup_verificado('trabajos-eventuales-en-cuenta')}")
        nueva = re.sub(r"CREATE\s+VIEW", "ALTER VIEW", definicion.replace(MARCA_FIN, RAMAS + MARCA_FIN), count=1)
        cur.execute(nueva)
        print("Vista ampliada con trabajos eventuales y sus pagos.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
