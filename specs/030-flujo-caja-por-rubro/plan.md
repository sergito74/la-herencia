# Implementation Plan: Flujo de caja por Rubro

**Branch**: `030-flujo-caja-por-rubro` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/030-flujo-caja-por-rubro/spec.md`

## Summary

Pantalla en Finanzas que muestra el flujo de caja real con el formato de la hoja "Cash Flow 1" de Sergio: saldo inicial por cuenta, ingresos por rubro, egresos por centro de costo con subtotales, una sección de movimientos entre cuentas propias y el saldo final. Las columnas son períodos (semana, mes, trimestre o año) y la moneda es ARS o USD. Cada celda abre el detalle de los movimientos que la componen, y la vista se exporta a Excel.

El backend `GET /api/flujo-caja/por-rubro` (018 v2) ya existe, pero hay que cambiar tres cosas para cumplir la spec aclarada:

1. **Reparto:** hoy un pago aplicado a documentos de varios rubros va entero al de mayor peso. Debe repartirse por importe aplicado, y el remanente sin aplicar debe ir a "Pendiente de aplicar".
2. **Traspasos internos:** hoy se descartan. Deben mostrarse en tres filas propias.
3. **Saldo inicial:** hoy es un único total. Debe darse por cuenta: Nación, Galicia cuenta corriente y FIMA.

Se agregan la conversión a dólares por movimiento con la cotización del día, un endpoint de detalle por celda y la exportación a Excel.

## Technical Context

**Language/Version**: Python 3.11 (backend) y TypeScript/Next.js (frontend), ambos existentes.

**Primary Dependencies**: FastAPI, pyodbc, openpyxl (ya usado en `cuentas_corrientes/exportacion.py`) y TanStack Query. No se agrega nada nuevo.

**Storage**: SQL Server `WC`, solo lectura. No hay tablas nuevas. Se leen `Movimientos BNA`, `Movimientos Galicia`, `CuentasBancarias`, `AplicacionesPago`, compras y ventas para el rubro, y `Dolar BNA` para la cotización.

**Testing**: pytest con funciones puras de reparto, clasificación interna, conversión a USD y agregación, más contract tests del router con monkeypatch. Además, verificación de totales contra `WC` real (quickstart).

**Target Platform**: Windows, navegador de escritorio.

**Project Type**: web application. Se extiende el módulo `flujo_caja` en backend y se agrega una pantalla nueva.

**Performance Goals**: 12 meses en vista mensual se calculan y se muestran en pocos segundos (SC-004: consulta y exportación en menos de 1 minuto). Se recalcula siempre, sin caché (FR-009).

**Constraints**:
- No se cambia la regla de atribución de rubros de 019, salvo el reparto por importe aplicado, que pide la spec.
- No se cambia la clasificación de internos de 018 (`clasificacion.py`).
- No se escribe nada.

**Scale/Scope**: ~7.000 movimientos bancarios en total; el rango típico es de 12 a 24 meses. Hay 2 endpoints nuevos (detalle y exportación) y 1 endpoint extendido (moneda y estructura nueva). La pantalla es una sola, con un panel lateral de detalle.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. SQL Server es el sistema de registro**: solo lectura contra `WC`. Cumple.
- **II. Protección de datos reales**: sin escrituras ni cambios de esquema; no requiere backup. Cumple.
- **III. Procesos de negocio, no tablas crudas**: la pantalla sigue el proceso real de Sergio (su Cash Flow): del resumen por rubro, al detalle, a aplicar lo pendiente. Cumple.
- **IV. Trazabilidad y significado financiero**:
  - La moneda y el tipo de cambio se muestran por movimiento en el detalle.
  - Lo no aplicado y los traspasos internos quedan como filas propias, nunca ocultas.
  - Cada celda es trazable hasta sus movimientos.
  - Cumple.
- **V. Contract-first**: el contrato está en `contracts/api.md` antes de la UI, con tests de las funciones puras y del router. Cumple.
- **VI. Colaboración de especialistas**: los criterios financieros (cotización, reparto, traspasos) los decidió Sergio en `/speckit-clarify`. Cumple.
- **VII. Simplicidad**: se extienden el módulo y el endpoint existentes, y la exportación reusa el patrón openpyxl de cuentas corrientes. Cumple.
- **VIII. Stack aprobado**: sin agregados. Cumple.

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/030-flujo-caja-por-rubro/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
└── tasks.md             # Phase 2 ($speckit-tasks)
```

### Source Code (repository root)

```text
backend/src/features/flujo_caja/
├── atribucion.py      # atribuir_desde_aplicaciones -> devuelve PARTES (rubro, centro, importe), no un ganador
├── clasificacion.py   # + tipo_interno(): "Colocación FIMA" / "Rescate FIMA" / "Traspaso entre bancos"
│                      # + emparejar_traspasos(): lado Galicia de un traspaso BNA (mismo importe, ≤ 3 días); sin pareja → sinContraparte
├── cotizacion.py      # NUEVO: cotización BNA vendedor divisa del día, con fallback de 7 días
├── repository.py      # partes por movimiento, agregación con sección de internos, saldo por cuenta, detalle de celda
├── exportacion.py     # NUEVO: xlsx de la vista (mismo patrón que cuentas_corrientes/exportacion.py)
├── router.py          # por-rubro: + moneda; + GET por-rubro/detalle; + GET por-rubro/exportar
└── schemas.py         # respuesta extendida: saldos por cuenta, internos, avisos de tipo de cambio

backend/tests/
├── test_flujo_caja_rubro_partes.py        # reparto, remanente, internos, conversión USD
└── contract/test_flujo_caja_por_rubro_api.py

frontend/src/
├── app/finanzas/flujo-caja-rubro/page.tsx
├── components/flujo-caja/FlujoCajaRubro.tsx         # tabla + controles
├── components/flujo-caja/DetalleCeldaRubro.tsx      # panel de movimientos de una celda
└── services/flujoCajaApi.ts                         # + fetchPorRubro, fetchDetalleRubro, urlExportarPorRubro
```

La navegación agrega "Flujo de caja por rubro" en Finanzas, junto a "Flujo de caja real".

**Structure Decision**: se extiende el módulo `flujo_caja` (018) en el mismo lugar. La unidad de cálculo pasa de "movimiento con un rubro" a "parte de movimiento": un movimiento produce una o más partes, cada una con rubro, centro de costo, importe y cotización. Así, el reparto, la agregación, el detalle y la exportación salen de la misma lista de partes, y la suma de cada celda es exactamente la de su detalle (FR-006).

## Complexity Tracking

*Sin violaciones de la Constitución: sección no aplica.*
