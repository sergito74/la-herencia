"""Agrega a `vw_MovimientosCuenta_Base` la rama faltante de `Venta
Hacienda`/`Det_Ventas Hacienda` (crédito al consignatario) — hallazgo real
2026-09-30: la vista nunca incluía el crédito de la venta en sí, solo los
pagos ya cobrados (BNA/Galicia/efectivo) y las retenciones, dejando la
cuenta de todo consignatario permanentemente en rojo aunque estuviera
saldada.

Fórmula validada al centavo contra la liquidación real de Brazzola y Cía.
SRL (20201111_BrazzolaYCia.pdf, IdVenta=78): Subtotal $180.000 − Comisión
3% ($5.400) − Gs Vs No Gravados ($2.025) = Neto Gravado $172.575; +IVA
10,5% ($18.120,37) −Ley de Sellos ($1.040,13) = Importe Neto $189.655,24,
que coincide EXACTO con los 3 pagos BNA ya cargados para esa cuenta.

Decisión confirmada con el usuario (2026-09-30): el comprador (ej. Semper,
Jose Luis) NO recibe ningún movimiento en ventas intermediadas por un
consignatario — no le paga a La Herencia, le paga al consignatario. Solo
se agrega la rama del consignatario acá.

Solo agrega una rama nueva al UNION ALL existente — ninguna rama actual se
modifica (mismo patrón que `crear_tabla_conciliaciones_tesoreria.py` al
extender esta misma vista para 023).

Backup verificado de `WC` requerido antes de correr (Constitución,
Principio II — cambio de esquema/vista).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.extender_vista_venta_hacienda
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

MARCADOR_RAMA_NUEVA = "CAST('Venta Hacienda' AS varchar(50)) AS Origen"

RAMA_VENTA_HACIENDA = """
UNION ALL

SELECT
    v.Fecha,
    v.IdConsignatario AS IdContacto,
    ct.[Razon Social],
    'Venta Hacienda' AS Documento,
    v.[Nro documento] AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(
        (ISNULL(subtotal.Total, 0) - (ISNULL(subtotal.Total, 0) * ISNULL(v.[Porc Comision], 0) / 100.0)
            - ISNULL(v.[Gs Vs No Gravados], 0))
        * (1 + ISNULL(v.AlicuotaIVA, 0) / 100.0)
        - ISNULL(v.[Ley de Sellos], 0) - ISNULL(v.[Vis Municipal], 0) - ISNULL(v.Balanza, 0)
        - ISNULL(v.Flete, 0) - ISNULL(v.[Gastos Varios], 0) - ISNULL(v.[Retencion Ganancias], 0)
        - ISNULL(v.[Retencion IVA], 0) - ISNULL(v.[Ingresos Brutos], 0) + ISNULL(v.Complemento, 0)
    AS money) AS Credito,
    CAST('Venta Hacienda' AS varchar(50)) AS Origen,
    CAST(v.IdVenta AS bigint) AS IdOrigen
FROM dbo.[Venta Hacienda] AS v
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = v.IdConsignatario
CROSS APPLY (
    SELECT SUM(d.Cantidad * (ISNULL(d.[Precio unitario (A)], 0) + ISNULL(d.[Precio unitario (B)], 0))) AS Total
    FROM dbo.[Det_Ventas Hacienda] d
    WHERE d.IdVenta = v.IdVenta
) AS subtotal
WHERE v.IdConsignatario IS NOT NULL

"""

MARCADOR_INSERCION = (
    "LEFT JOIN dbo.[Valores Recibidos] AS vr ON ct.Medio = 'valores-recibidos' AND vr.IdValor = ct.IdMovimiento\n"
)


def construir_nueva_definicion(definicion_actual: str) -> str:
    if MARCADOR_RAMA_NUEVA in definicion_actual:
        raise RuntimeError("La rama 'Venta Hacienda' ya existe en la vista — no se vuelve a agregar.")
    if MARCADOR_INSERCION not in definicion_actual:
        raise RuntimeError("No se encontró el punto de inserción esperado en la vista actual.")
    if definicion_actual.count(MARCADOR_INSERCION) != 1:
        raise RuntimeError("El punto de inserción no es único — revisar a mano antes de continuar.")

    nueva = definicion_actual.replace(MARCADOR_INSERCION, MARCADOR_INSERCION + RAMA_VENTA_HACIENDA, 1)
    nueva = nueva.replace("CREATE VIEW dbo.vw_MovimientosCuenta_Base", "ALTER VIEW dbo.vw_MovimientosCuenta_Base", 1)
    return nueva


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))")
        definicion_actual = cursor.fetchone()[0]

        nueva_definicion = construir_nueva_definicion(definicion_actual)
        cursor.execute(nueva_definicion)
        print("OK: rama 'Venta Hacienda' agregada a vw_MovimientosCuenta_Base.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
