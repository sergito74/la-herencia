# Implementation Plan: Aplicación de pagos y cobros (cuenta corriente)

**Branch**: `019-aplicacion-pagos-cobros` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/019-aplicacion-pagos-cobros/spec.md`

## Summary

Tabla nueva `AplicacionesPago` que vincula un movimiento bancario real (pago o cobro, cualquiera de los medios ya existentes en Tesorería) con uno o más documentos (compra o venta), con importe aplicado parcial permitido, sugerencia automática FIFO editable, e inmutabilidad (anular + recrear, nunca editar). Construye desde cero el lado de Ventas (hoy sin ningún equivalente a `vw_MovimientosCuenta_Base`), reusando el cálculo de importe ya existente (`ventas_hacienda.calcular_totales`, ya reutilizado en `flujo_caja/atribucion.py`). Reemplaza al matching exacto de `flujo_caja/atribucion.py` como fuente primaria de Rubro/Centro de Costos para movimientos posteriores al 2015-09-01.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript/Next.js 14 (frontend).

**Primary Dependencies**: ninguna nueva. Reutiliza `ventas_hacienda.repository.{get_venta_cabecera, get_lineas_venta, calcular_totales}` (ya usado en `flujo_caja/atribucion.py`), `Det_Compras`/`Compras` (ya usado ahí también), y el catálogo `MEDIOS`/`MEDIOS_CONFIG` de `tesoreria/repository.py` para identificar de qué tabla sale un movimiento aplicable.

**Storage**: SQL Server `WC`. Tabla nueva `AplicacionesPago` (ver data-model.md). No se toca `Compras`/`Det_Compras`/`Venta Hacienda`/`Venta Granos` ni ninguna tabla heredada — el estado de un documento se calcula siempre desde `AplicacionesPago`, nunca se persiste en la tabla del documento.

**Testing**: `pytest` (unit de sugerencia FIFO, validación de sobre-aplicación con tolerancia, cálculo de estado de documento; contract tests de los endpoints nuevos con `TestClient`, mismo patrón que 018).

**Target Platform**: Web local.

**Project Type**: Web application. Feature nuevo `backend/src/features/aplicaciones_pago/`; extensión de `flujo_caja/atribucion.py` para usar aplicaciones como fuente primaria; pantalla nueva de aplicación (posiblemente como panel dentro de Tesorería/Cuentas corrientes, a definir con `agroux-lead-product-architect` antes de construir la UI — este plan cubre el contrato de datos y la API, no el detalle de pantalla).

**Performance Goals**: volumen real chico (decenas de compras/ventas y movimientos por mes, confirmado en relevamientos previos de 017/018) — sin requerimiento de performance especial.

**Constraints**: constitución II — no se migra ni se aplica retroactivamente el historial 2015-2026 (fuera de alcance, Assumptions de spec.md); constitución IV — el estado de un documento nunca es un campo guardado, siempre se recalcula desde `AplicacionesPago` vigentes (FR-007); ninguna aplicación se borra ni edita, solo se anula (FR-005).

**Scale/Scope**: 1 tabla nueva, 1 feature backend nuevo, endpoints de sugerencia/confirmación/anulación/consulta de estado, extensión de `flujo_caja/atribucion.py` (no reescritura completa — el matching exacto queda como fallback para movimientos previos al corte).

## Constitution Check

- **I**: ✅ toda la información sale de `WC` (`AplicacionesPago` nueva + `Compras`/`Det_Compras`/`Venta Hacienda`/`Venta Granos` existentes), sin fuente paralela.
- **II**: ✅ `AplicacionesPago` es la única tabla nueva, no se modifica ninguna tabla heredada; las aplicaciones nunca se editan/borran, solo se anulan (append-only con estado).
- **III**: ✅ el objetivo es el proceso de negocio "saber qué deuda/crédito ya se cobró o pagó", no una grilla cruda — calcula estado, sugiere, valida consistencia.
- **IV**: ✅ estado de documento siempre recalculado desde las aplicaciones vigentes (FR-007); tolerancia de redondeo documentada y explícita (no oculta en el cálculo); anulación con motivo/usuario/fecha explícitos (FR-005/FR-011).
- **V**: ✅ contrato de API definido antes de implementación (contracts/api-aplicaciones-pago.md); tests de la lógica de sugerencia/validación antes/junto con el código.
- **VI**: ✅ especificado con el `financial-direction-specialist` (ver research.md), validado con el dueño (6 preguntas cerradas antes de esta spec).
- **VII (simplicidad)**: ✅ no se crea una vista SQL nueva tipo `vw_MovimientosCuenta_Base` para Ventas — se reusa el cálculo Python ya existente (`calcular_totales`) en vez de duplicar la fórmula de comisión/IVA/retenciones en SQL; el matching exacto de 018 v2 no se descarta, queda como fallback para movimientos anteriores al corte.
- **VIII**: ✅ sin nuevas dependencias de stack.

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/019-aplicacion-pagos-cobros/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api-aplicaciones-pago.md # Phase 1 output
└── tasks.md              # Phase 2 output (speckit-tasks, NOT created by speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   └── crear_tabla_aplicaciones_pago.py   # nuevo: AplicacionesPago
├── src/
│   └── features/
│       ├── aplicaciones_pago/
│       │   ├── __init__.py
│       │   ├── documentos.py        # documentos pendientes por contacto (Compras + Venta Hacienda/Granos), saldo pendiente
│       │   ├── sugerencia.py        # FIFO: dado un movimiento e importe, sugiere documentos hasta cubrirlo
│       │   ├── repository.py        # CRUD de AplicacionesPago (insert, anular, estado de documento/movimiento)
│       │   ├── router.py            # /api/aplicaciones-pago/*
│       │   └── schemas.py
│       └── flujo_caja/
│           └── atribucion.py        # + usa AplicacionesPago como fuente primaria (fallback: matching exacto actual)
└── tests/
    ├── test_aplicaciones_pago_sugerencia.py
    └── test_aplicaciones_pago_endpoints.py

frontend/src/
├── components/aplicaciones-pago/
│   └── AplicarPagoPanel.tsx         # sugerencia FIFO editable + confirmar (panel, no pantalla propia — se embebe donde se vea un movimiento, a definir con arquitecto de producto)
└── services/aplicacionesPagoApi.ts
```

**Structure Decision**: nuevo feature `backend/src/features/aplicaciones_pago/`, mismo criterio que los demás dominios. `flujo_caja/atribucion.py` se extiende (no se reescribe) para preferir `AplicacionesPago` sobre el matching exacto cuando existan aplicaciones vigentes para un movimiento.

## Complexity Tracking

*Sin violaciones.*
