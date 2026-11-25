# Auditoría de dolarización (T004): 25/11/2026

Este informe revisa cada lugar del sistema que pasa importes a US$. Es solo lectura: no se cambió nada.

## Costos y resultados: se unifican
| Lugar | Hoy | Variante |
|---|---|---|
| `vw_TC_BNA_PorCompra` (la usan `vw_Costos_BaseLineas`, `vw_ResultadosCultivo_CostosBase`, `vw_CnsComprasDolarBNA`, `resultado_cultivo/costos.py` `_USD_SQL`) | compras en pesos → BNA comprador divisa | **mismo día** (`Fecha <= fecha`) |
| `resultado_cultivo/costos.py:64` (helper) | comprador divisa | mismo día |
| `resultado_cultivo/costos.py:343` (gastos de caja sin US$ guardado) | comprador divisa | mismo día |
| `cajas_efectivo/service.py` `SQL_VALUAR_GASTO_CAJA` | comprador divisa | **día hábil anterior** (`Fecha < fecha`) |
| `ventas_granos/lector_lpg.py` (LPG sin TC) | comprador divisa | día hábil anterior |
| `resultado_cultivo/precio_mercado.py` | comprador divisa | día hábil anterior |
| Comprobantes en US$ | su `[Tipo de Cambio]` | — |
| "Ajusta TC" | 0 US$ | — |

**Hallazgo:** todo el sistema usa la misma cotización (BNA comprador divisa), pero con dos fechas distintas: el mismo día del comprobante, o el día hábil anterior.

**Impacto de pasar las compras al día hábil anterior** (compras en pesos desde 07/2023):

| Campaña | Compras | Con TC distinto | US$ mismo día | US$ día anterior | Dif. US$ | Dif. % |
|---|---|---|---|---|---|---|
| 2023/24 | 394 | 242 | 72.851 | 73.012 | +161 | 0,22% |
| 2024/25 | 418 | 318 | 110.782 | 110.894 | +112 | 0,10% |
| 2025/26 | 449 | 337 | 71.833 | 71.851 | +18 | 0,03% |
| 2026/27 (parcial) | 187 | 137 | 34.044 | 34.063 | +19 | 0,06% |

## No se tocan (tienen otra función)
| Lugar | Cotización | Motivo |
|---|---|---|
| `auditoria_cuentas/bimonetaria.py` | vendedor divisa, día anterior | conciliación de cuentas corrientes en US$; la deuda va al TC del comprobante, regla 036 |
| `flujo_caja/cotizacion.py` | vendedor divisa | proyección del flujo; queda documentado |
| `cuentas_socios/valuacion.py` y `repository.py` | Prom_billete | valuación de saldos de socios en US$, no son costos; queda documentado |
| `cotizaciones/router.py` | todas | solo muestra la tabla de cotizaciones |
| Planilla histórica ganadera | Prom_billete | fuente externa; la diferencia se muestra aparte (SC-001a) |

## Decisión pendiente (Sergio)
Falta elegir la fecha única de la cotización: mismo día o día hábil anterior.

## Decisión y aplicación (25/11/2026)
- **Decisión de Sergio:** para todos los centros se usa el **día hábil anterior**.
- **Cambios aplicados:**
  - `vw_TC_BNA_PorCompra`: pasa a `Fecha < fecha AND Comp_Divisa > 0` (script `backend/scripts/dolar_gestion_vista_20261125.py`; definición anterior en `backups/vw_TC_BNA_PorCompra-antes-20261125.sql`).
  - Módulo común `backend/src/features/cotizaciones/dolar_gestion.py`.
  - `resultado_cultivo/costos.py` (`_bna`, gastos de caja) y `precio_mercado.py` ahora lo usan.
  - `lector_lpg.py` y `cajas_efectivo/service.py` ya aplicaban la misma regla. Se dejan como están (SQL equivalente) y se pasarán al módulo común cuando se toquen.
- **Resultado de cultivos antes y después:**
  - Los **pesos y las ventas no cambian.**
  - El costo en US$ sube +32,11 en 2023/24, +24,41 en 2024/25 y +29,21 en 2025/26. Por cultivo va de −2,07 a +16,82 US$.
- **Pruebas:** `tests/ganaderia/test_dolar_gestion.py` (5) y las del resultado, costos, precios, LPG y caja (255) pasan.
