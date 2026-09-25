"""Corrige `vw_MovimientosCuenta_Base` en WC: agrega el origen "Tarjetas",
ausente desde siempre (confirmado idéntico en `LaHerencia`, no es un bug
introducido por ninguna feature nuestra — ver hallazgo 2026-09-25,
reportado por Sergio sobre el proveedor "2JM").

La vista tenía 12 orígenes (Compras, Alquileres, Impuestos, Remuneraciones,
Galicia, Banco Nacion, Pagos efectivo, Valores Recibidos x2, Retenciones
x3) y ninguno leía `Tarjetas_Resumenes_Lineas`. Impacto medido: 111
proveedores, 1.682 líneas, $39.476.823 históricos nunca reflejados como
pago en ninguna cuenta corriente.

**Diseño del fix — v3, reescrito 2026-09-26 (caso real "Agüero Shamaim
SRL")**: las versiones anteriores (v1: match por `Nro Documento`; v2:
+ fallback por fecha+importe) usaban una heurística propia en la vista,
sin saber que **ya existe una tabla real y activamente usada** para esto:
`Tarjetas_Resumenes_Lineas_Compras` (vínculo línea de consumo ↔ compra,
con `ImporteImputado` parcial — el mecanismo real del módulo de tarjetas,
008/009, con 1.417 vínculos ya cargados). Esa heurística no soportaba el
caso real reportado por Sergio: un resumen de tarjeta (MercadoLibre,
$130.145,77) que agrupa el cobro de **varios proveedores distintos**, del
cual solo una parte ($23.868) corresponde a la factura de "Agüero Shamaim
SRL" — la heurística de fecha+importe exacto nunca iba a encontrar ese
caso, porque el importe de la línea nunca es igual al de una sola factura.

**Diseño correcto**: cada fila de `Tarjetas_Resumenes_Lineas_Compras` es
una imputación real (parcial o total) de una línea de consumo contra una
`Compra` — igual en espíritu a `AplicacionesPago` (019/020), pero para el
módulo de tarjetas. El contacto sale de la `Compra` (`IdCompra` →
`Compras.IdContacto`), no de `Tarjetas_Resumenes_Lineas.IdContacto` (que
en los casos de resumen agrupado, como MercadoLibre, viene vacío — el
gasto no pertenece a un único proveedor). Ya cubre 1.416 de 1.679 líneas
de tarjeta con contacto (84%), incluidos los casos de "2JM" y "ACA
Bolivar" ya resueltos con la heurística anterior (mismo `IdCompra`, mismo
importe — confirmado antes de reemplazarla). Las líneas de tarjeta sin
ningún vínculo cargado (ej. Carrefour, YPF, compras pagadas al instante
sin factura aparte) siguen fuera de la vista a propósito: no hay con qué
generar un crédito real.

**Hallazgo aparte, no corregido acá**: el vínculo de Agüero Shamaim
(`IdVinculo 3007`) tiene `ImporteImputado = $130.145,77` (el importe
*completo* del resumen), cuando la factura real vale $23.868 — parece un
error de carga en la pantalla de vínculos del módulo de tarjetas (cargó
el total de la línea en vez de la porción real). Corregir ese vínculo es
una acción de datos que le corresponde al usuario, no a este script.

Solo modifica `WC` — nunca `LaHerencia` (protegida, Principio II). Esto
significa que, a partir de ahora, el saldo de estos contactos en `WC` va
a diferir del de `LaHerencia` a propósito (WC corregido, LaHerencia con
el bug heredado) hasta que alguien corrija la vista real en producción —
una decisión explícita del usuario (2026-09-25), no un efecto no
controlado.

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.agregar_tarjetas_a_vista_cuenta_corriente
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_ALTER_VISTA = """
ALTER VIEW dbo.vw_MovimientosCuenta_Base
AS

SELECT
    c.Fecha,
    c.IdContacto,
    ct.[Razon Social],
    c.[Tipo documento] AS Documento,
    c.[Nro Documento],
    CASE WHEN tc.GranTotal > 0 THEN tc.GranTotal ELSE 0 END AS Deuda,
    CASE WHEN tc.GranTotal < 0 THEN -tc.GranTotal ELSE 0 END AS Credito,
    CAST('Compras' AS varchar(50)) AS Origen,
    CAST(c.IdDeuda AS bigint) AS IdOrigen
FROM dbo.Compras AS c
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = c.IdContacto
INNER JOIN dbo.vw_Cns_Total_Compra AS tc
    ON tc.IdDeuda = c.IdDeuda

UNION ALL

SELECT
    a.Fecha,
    a.IdContacto,
    ct.[Razon Social],
    'Contrato Arrendamiento' AS Documento,
    'SIN NUMERO' AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    a.[Importe total del contrato] AS Credito,
    CAST('Alquileres' AS varchar(50)) AS Origen,
    CAST(a.IdAlquiler AS bigint) AS IdOrigen
FROM dbo.Alquileres AS a
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = a.IdContacto

UNION ALL

SELECT
    i.Fecha,
    i.IdOrganismo AS IdContacto,
    ct.[Razon Social],
    ti.[Nombre Impuesto] AS Documento,
    i.[Numero de documento] AS [Nro Documento],
    CASE WHEN i.Importe > 0 THEN i.Importe ELSE 0 END AS Deuda,
    CASE WHEN i.Importe < 0 THEN -i.Importe ELSE 0 END AS Credito,
    CAST('Impuestos' AS varchar(50)) AS Origen,
    CAST(i.IdImpuesto AS bigint) AS IdOrigen
FROM dbo.Impuestos AS i
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = i.IdOrganismo
INNER JOIN dbo.[Tipo Impuesto] AS ti
    ON ti.IdTipoImpuesto = i.IdTipoImpuesto

UNION ALL

SELECT
    r.[Fecha de pago] AS Fecha,
    r.IdContacto,
    ct.[Razon Social],
    'Recibo Sueldo' AS Documento,
    r.[Periodo liquidado] AS [Nro Documento],
    CASE
        WHEN (
            ISNULL(r.[Sueldo basico], 0) +
            ISNULL(r.[Antiguedad], 0) +
            ISNULL(r.[Adic futuros aumentos], 0) +
            ISNULL(r.[Dia Gremio], 0) +
            ISNULL(r.[Aguinaldo], 0) +
            ISNULL(r.[Vacaciones], 0) +
            ISNULL(r.[Ajuste], 0) +
            ISNULL(r.[Ajuste No Remunerativo], 0) +
            ISNULL(r.[Redondeo], 0) +
            ISNULL(r.[Bonificacion adicional], 0) -
            ISNULL(r.[Jubilacion], 0) -
            ISNULL(r.[Ley 19032], 0) -
            ISNULL(r.[Obra Social], 0) -
            ISNULL(r.[Obra Social Acuerdos], 0) -
            ISNULL(r.[Servicio de Sepelio], 0) -
            ISNULL(r.[Aporte Sindical], 0)
        ) > 0
        THEN (
            ISNULL(r.[Sueldo basico], 0) +
            ISNULL(r.[Antiguedad], 0) +
            ISNULL(r.[Adic futuros aumentos], 0) +
            ISNULL(r.[Dia Gremio], 0) +
            ISNULL(r.[Aguinaldo], 0) +
            ISNULL(r.[Vacaciones], 0) +
            ISNULL(r.[Ajuste], 0) +
            ISNULL(r.[Ajuste No Remunerativo], 0) +
            ISNULL(r.[Redondeo], 0) +
            ISNULL(r.[Bonificacion adicional], 0) -
            ISNULL(r.[Jubilacion], 0) -
            ISNULL(r.[Ley 19032], 0) -
            ISNULL(r.[Obra Social], 0) -
            ISNULL(r.[Obra Social Acuerdos], 0) -
            ISNULL(r.[Servicio de Sepelio], 0) -
            ISNULL(r.[Aporte Sindical], 0)
        )
        ELSE 0
    END AS Deuda,
    CASE
        WHEN (
            ISNULL(r.[Sueldo basico], 0) +
            ISNULL(r.[Antiguedad], 0) +
            ISNULL(r.[Adic futuros aumentos], 0) +
            ISNULL(r.[Dia Gremio], 0) +
            ISNULL(r.[Aguinaldo], 0) +
            ISNULL(r.[Vacaciones], 0) +
            ISNULL(r.[Ajuste], 0) +
            ISNULL(r.[Ajuste No Remunerativo], 0) +
            ISNULL(r.[Redondeo], 0) +
            ISNULL(r.[Bonificacion adicional], 0) -
            ISNULL(r.[Jubilacion], 0) -
            ISNULL(r.[Ley 19032], 0) -
            ISNULL(r.[Obra Social], 0) -
            ISNULL(r.[Obra Social Acuerdos], 0) -
            ISNULL(r.[Servicio de Sepelio], 0) -
            ISNULL(r.[Aporte Sindical], 0)
        ) < 0
        THEN -(
            ISNULL(r.[Sueldo basico], 0) +
            ISNULL(r.[Antiguedad], 0) +
            ISNULL(r.[Adic futuros aumentos], 0) +
            ISNULL(r.[Dia Gremio], 0) +
            ISNULL(r.[Aguinaldo], 0) +
            ISNULL(r.[Vacaciones], 0) +
            ISNULL(r.[Ajuste], 0) +
            ISNULL(r.[Ajuste No Remunerativo], 0) +
            ISNULL(r.[Redondeo], 0) +
            ISNULL(r.[Bonificacion adicional], 0) -
            ISNULL(r.[Jubilacion], 0) -
            ISNULL(r.[Ley 19032], 0) -
            ISNULL(r.[Obra Social], 0) -
            ISNULL(r.[Obra Social Acuerdos], 0) -
            ISNULL(r.[Servicio de Sepelio], 0) -
            ISNULL(r.[Aporte Sindical], 0)
        )
        ELSE 0
    END AS Credito,
    CAST('Remuneraciones' AS varchar(50)) AS Origen,
    CAST(r.IdSalario AS bigint) AS IdOrigen
FROM dbo.Remuneraciones AS r
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = r.IdContacto

UNION ALL

SELECT
    g.Fecha,
    CAST(g.IdContacto AS int) AS IdContacto,
    ct.[Razon Social],
    'Resumen Bancario' AS Documento,
    CAST(g.[Número de Comprobante] AS varchar(50)) AS [Nro Documento],
    ISNULL(g.[Créditos], 0) AS Deuda,
    ISNULL(g.[Débitos], 0) AS Credito,
    CAST('Galicia' AS varchar(50)) AS Origen,
    CAST(g.IdMovimiento AS bigint) AS IdOrigen
FROM dbo.[Movimientos Galicia] AS g
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = CAST(g.IdContacto AS int)

UNION ALL

SELECT
    b.[Fecha / Hora Mov#] AS Fecha,
    CAST(b.IdContacto AS int) AS IdContacto,
    ct.[Razon Social],
    'Resumen Bancario' AS Documento,
    CAST(b.[Nro# Comprobante] AS varchar(50)) AS [Nro Documento],
    CASE WHEN ISNULL(b.Importe, 0) > 0 THEN b.Importe ELSE 0 END AS Deuda,
    CASE WHEN ISNULL(b.Importe, 0) < 0 THEN -b.Importe ELSE 0 END AS Credito,
    CAST('Banco Nacion' AS varchar(50)) AS Origen,
    CAST(b.IdMovimientoBNA AS bigint) AS IdOrigen
FROM dbo.[Movimientos BNA] AS b
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = CAST(b.IdContacto AS int)

UNION ALL

SELECT
    pe.Fecha,
    pe.IdContacto,
    ct.[Razon Social],
    COALESCE(NULLIF(LTRIM(RTRIM(pe.Caja)), ''), NULLIF(LTRIM(RTRIM(pe.Cuenta)), ''), 'Pago efectivo') AS Documento,
    CASE
        WHEN pe.[Numero documento] IS NULL THEN NULL
        ELSE CONVERT(varchar(50), CONVERT(decimal(38,0), pe.[Numero documento]))
    END AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(pe.[Importe imputado] AS money) AS Credito,
    CAST('Pagos efectivo' AS varchar(50)) AS Origen,
    CAST(pe.IdPagoEfectivo AS bigint) AS IdOrigen
FROM dbo.[Pagos efectivo] AS pe
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = pe.IdContacto
WHERE pe.IdContacto IS NOT NULL
  AND ISNULL(pe.[Importe imputado], 0) <> 0

UNION ALL

SELECT
    vrp.Fecha,
    vrp.IdContacto,
    vrp.[Razon Social],
    vrp.Documento,
    CAST(vrp.[Nro Documento] AS varchar(50)) AS [Nro Documento],
    CAST(vrp.Deuda AS money) AS Deuda,
    CAST(vrp.Credito AS money) AS Credito,
    CAST('Pagos Valores Recibidos' AS varchar(50)) AS Origen,
    CAST(vr.IdValor AS bigint) AS IdOrigen
FROM dbo.vw_CnsPagosValoresRecibidos AS vrp
INNER JOIN dbo.[Valores Recibidos] AS vr
    ON vr.[Numero Valor] = vrp.[Nro Documento]
   AND vr.[Fecha Endoso] = vrp.Fecha
   AND vr.IdReceptor = vrp.IdContacto

UNION ALL

SELECT
    vrc.Fecha,
    vrc.IdContacto,
    vrc.[Razon Social],
    vrc.Documento,
    CAST(vrc.[Nro Documento] AS varchar(50)) AS [Nro Documento],
    CAST(vrc.Deuda AS money) AS Deuda,
    CAST(vrc.Credito AS money) AS Credito,
    CAST('Cobros Valores Recibidos' AS varchar(50)) AS Origen,
    CAST(vr.IdValor AS bigint) AS IdOrigen
FROM dbo.vw_CnsCobrosValoresRecibidos AS vrc
INNER JOIN dbo.[Valores Recibidos] AS vr
    ON vr.[Numero Valor] = vrc.[Nro Documento]
   AND vr.[Fecha Endoso] = vrc.Fecha
   AND vr.IdEmisor = vrc.IdContacto
   AND vr.Destino = 'Endoso a tercero'

UNION ALL

SELECT
    rig.Fecha,
    rig.IdContacto,
    rig.[Razon Social],
    rig.Documento,
    rig.[Nro Documento],
    CAST(rig.Deuda AS money) AS Deuda,
    CAST(rig.Credito AS money) AS Credito,
    CAST('Ret. IVA Granos' AS varchar(50)) AS Origen,
    rig.IdOrigen
FROM dbo.vw_CnsRetencionesIVAGranos AS rig

UNION ALL

SELECT
    r.Fecha,
    r.IdContacto,
    ct.[Razon Social],
    'Retención' AS Documento,
    r.[Numero Certificado] AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(r.Importe AS money) AS Credito,
    CAST('Retenciones' AS varchar(50)) AS Origen,
    CAST(r.IdRetencionSQL AS bigint) AS IdOrigen
FROM dbo.Retenciones AS r
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = r.IdContacto
WHERE r.IdContacto IS NOT NULL
  AND ISNULL(r.Importe, 0) <> 0

UNION ALL

SELECT
    rvh.Fecha,
    rvh.IdContacto,
    ct.[Razon Social],
    COALESCE(NULLIF(LTRIM(RTRIM(rvh.Documento)), ''), 'Retención Ventas Hacienda') AS Documento,
    rvh.[Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(rvh.Importe AS money) AS Credito,
    CAST('Ret. Ventas Hacienda' AS varchar(50)) AS Origen,
    CAST(rvh.Id AS bigint) AS IdOrigen
FROM dbo.[Retenciones Ventas Hacienda] AS rvh
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = rvh.IdContacto
WHERE rvh.IdContacto IS NOT NULL
  AND ISNULL(rvh.Importe, 0) <> 0

UNION ALL

SELECT
    t.FechaCompra AS Fecha,
    c.IdContacto,
    ct.[Razon Social],
    'Tarjeta' AS Documento,
    c.[Nro Documento],
    CASE WHEN -ISNULL(v.ImporteImputado, 0) > 0 THEN -v.ImporteImputado ELSE 0 END AS Deuda,
    CASE WHEN -ISNULL(v.ImporteImputado, 0) < 0 THEN v.ImporteImputado ELSE 0 END AS Credito,
    CAST('Tarjetas' AS varchar(50)) AS Origen,
    CAST(v.IdVinculo AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Lineas_Compras AS v
INNER JOIN dbo.Tarjetas_Resumenes_Lineas AS t
    ON t.IdLineaConsumo = v.IdLineaConsumo
INNER JOIN dbo.Compras AS c
    ON c.IdDeuda = v.IdCompra
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = c.IdContacto
WHERE ISNULL(v.ImporteImputado, 0) <> 0;
"""


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(DDL_ALTER_VISTA)
        print("OK: dbo.vw_MovimientosCuenta_Base actualizada con el origen 'Tarjetas' (solo líneas con Compra asociada).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
