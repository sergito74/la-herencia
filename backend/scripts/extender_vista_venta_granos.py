"""Agrega a `vw_MovimientosCuenta_Base` la rama faltante de `Venta
Granos`/`Det_Ventas Granos` (crédito al comprador/consignatario) — mismo
hallazgo del backlog post-025 (ver memoria `project_backlog_post_tarjetas_
impuestos`): la vista nunca incluía el crédito de la venta de granos en
sí, dejando la cuenta corriente del comprador incompleta.

Fórmula: la misma ya confirmada contra el formulario Access real en
`src/features/ventas_granos/repository.py::calcular_totales` (importe
neto a percibir = operación c/IVA − retenciones − percepciones −
deducciones + ajustes en el subtotal).

Validada al centavo contra 2 liquidaciones reales de Cargill (comprador
real, tabla `Venta Granos.IdConsignatario` guarda al comprador pese al
nombre heredado):
  - IdVenta=186 (COE 330124735433, 03/01/2024): SQL $9.854.837,2377 vs
    PDF "Pago según condiciones" $9.854.837,27 (sin deducciones).
  - IdVenta=218 (COE 330129123229, 30/07/2025, con deducción de
    $606,57): SQL $837.845,8827 vs PDF "Importe Neto a Pagar"
    $837.845,88 — exacto al centavo.

Nota (hallazgo de datos, fuera de alcance acá): IdVenta=218 no tiene
cargado el campo `Retencion IVA` pese a que el PDF muestra una retención
IVA RG 4310/2018 de $79.671,95 — por eso el importe neto calculado
coincide con "Importe Neto a Pagar" (antes de esa retención) y no con
"Pago según condiciones" (después). Mismo patrón que boletas de
impuestos faltantes; no se backfillea en este script.

Gotcha SQL: `Factor`, `Cantidad vendida` y `AlicuotaIVA` en `Venta Granos`
son `real` (precisión simple). En T-SQL `real` tiene MAYOR precedencia de
tipo que `money`, así que al operar con columnas money sin castear
explícitamente, SQL Server degrada las columnas money a precisión simple
antes de multiplicar — introduce errores de hasta ~$0,20 en montos de
cientos de miles. Se castea todo a `float` (doble precisión, igual que
Python) antes de operar, para que la aritmética coincida con
`calcular_totales()`.

Solo agrega una rama nueva al UNION ALL existente — ninguna rama actual
se modifica (mismo patrón que `extender_vista_venta_hacienda.py`).

Backup verificado de `WC` requerido antes de correr (Constitución,
Principio II — cambio de esquema/vista).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.extender_vista_venta_granos
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

MARCADOR_RAMA_NUEVA = "CAST('Venta Granos' AS varchar(50)) AS Origen"

RAMA_VENTA_GRANOS = """
UNION ALL

SELECT
    v.Fecha,
    v.IdConsignatario AS IdContacto,
    ct.[Razon Social],
    'Venta Granos' AS Documento,
    v.[Nro Documento] AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(
        (
            (CAST(ISNULL(v.[Cantidad vendida], 0) AS float)
                * ((CAST(ISNULL(v.[Precio unitario], 0) AS float) * CAST(ISNULL(v.Factor, 100) AS float) / 100.0
                    - CAST(ISNULL(v.Flete, 0) AS float)) / 1000.0))
            + ISNULL(aj.SumaAjustes, 0)
        ) * (1 + CAST(ISNULL(v.AlicuotaIVA, 0) AS float) / 100.0)
        - (CAST(ISNULL(v.[Ret IG], 0) AS float) + CAST(ISNULL(v.[Retencion IVA], 0) AS float)
            + CAST(ISNULL(v.Percepciones, 0) AS float) + CAST(ISNULL(v.[Otra Retenciones], 0) AS float))
        - ISNULL(ded.TotalDeducciones, 0)
    AS money) AS Credito,
    CAST('Venta Granos' AS varchar(50)) AS Origen,
    CAST(v.IdVenta AS bigint) AS IdOrigen
FROM dbo.[Venta Granos] AS v
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = v.IdConsignatario
OUTER APPLY (
    SELECT SUM(CAST(a.Importe AS float)) AS SumaAjustes
    FROM dbo.[Venta Granos_Ajustes] a
    WHERE a.IdVenta = v.IdVenta
) AS aj
OUTER APPLY (
    SELECT SUM(
        (CAST(d.[Base Calculo] AS float) * CAST(ISNULL(d.Porc, 0) AS float) / 100.0)
        + (CAST(d.[Base Calculo] AS float) * CAST(ISNULL(d.Porc, 0) AS float) / 100.0)
            * CAST(ISNULL(d.Alicuota, 0) AS float) / 100.0
    ) AS TotalDeducciones
    FROM dbo.[Venta Granos_Deducciones] d
    WHERE d.IdVenta = v.IdVenta
) AS ded
WHERE v.IdConsignatario IS NOT NULL

"""

MARCADOR_INSERCION = (
    "LEFT JOIN dbo.[Valores Recibidos] AS vr ON ct.Medio = 'valores-recibidos' AND vr.IdValor = ct.IdMovimiento\n"
)


def construir_nueva_definicion(definicion_actual: str) -> str:
    if MARCADOR_RAMA_NUEVA in definicion_actual:
        raise RuntimeError("La rama 'Venta Granos' ya existe en la vista — no se vuelve a agregar.")
    if MARCADOR_INSERCION not in definicion_actual:
        raise RuntimeError("No se encontró el punto de inserción esperado en la vista actual.")
    if definicion_actual.count(MARCADOR_INSERCION) != 1:
        raise RuntimeError("El punto de inserción no es único — revisar a mano antes de continuar.")

    nueva = definicion_actual.replace(MARCADOR_INSERCION, MARCADOR_INSERCION + RAMA_VENTA_GRANOS, 1)
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
        print("OK: rama 'Venta Granos' agregada a vw_MovimientosCuenta_Base.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
