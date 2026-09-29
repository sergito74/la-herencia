# Implementation Plan: Vincular líneas de resumen de tarjeta a pagos de Impuestos

**Branch**: `025-conciliacion-tarjetas-impuestos` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/025-conciliacion-tarjetas-impuestos/spec.md`

## Summary

El buscador de documentos de la conciliación de tarjetas (008/009) solo encuentra registros de Compras — los pagos de Impuestos (AFIP, ARBA, Municipalidad, UATRE: 1.075 casos reales con organismo asignado) son invisibles, aunque también se pagan con tarjeta. Se extiende `Tarjetas_Resumenes_Lineas_Compras` con una columna `IdImpuesto` nullable (alternativa a `IdCompra`, ahora también nullable), se suma Impuestos al buscador y al mecanismo de vinculación/reparto ya existente (incluido el reparto proporcional agregado el 2026-09-29), y se agrega saldo pendiente para Impuestos (puede repartirse en varias líneas, a diferencia de Compras que no tiene ese control hoy). El módulo puro de cálculo (`conciliacion_documentos.py`) no cambia — Impuestos siempre está en pesos.

## Technical Context

**Language/Version**: Python 3.13 (backend, FastAPI), TypeScript/Next.js (frontend) — mismo stack que 008/009/023/024.

**Primary Dependencies**: FastAPI, pyodbc, TanStack Query, Tailwind — sin dependencias nuevas.

**Storage**: SQL Server, base `WC` (producción). Requiere `ALTER TABLE` sobre `Tarjetas_Resumenes_Lineas_Compras` (1.598 filas reales): `IdCompra` pasa a nullable, se agrega `IdImpuesto` nullable + FK + `CHECK` de exclusividad. Sin tabla nueva.

**Testing**: pytest (contract + repository, incluye no-regresión de Compras), `tsc --noEmit`.

**Target Platform**: Web app interna, mismo backend/frontend del resto del sistema.

**Project Type**: Web application (backend FastAPI + frontend Next.js ya existentes).

**Performance Goals**: Sin metas distintas al resto del sistema.

**Constraints**: No debe agregar una conexión directa del navegador a SQL Server. No debe escribir en `LaHerencia`. El `ALTER TABLE` sobre una tabla con 1.598 filas reales requiere backup verificado antes de aplicarse (Constitución Principio II).

**Scale/Scope**: 1.075 pagos de Impuestos con organismo asignado (AFIP 749, UATRE 153, Municipalidad de Bolivar 100, ARBA 73) pasan a ser candidatos vinculables. 1.598 vínculos de Compras existentes no se alteran.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I**: Cumple — toda escritura nueva va contra `WC`.
- **Principio II**: `ALTER TABLE` sobre una tabla real con 1.598 filas — GATE: requiere backup verificado antes de aplicarse (a confirmar con el usuario si se reusa un backup reciente o se toma uno nuevo, mismo criterio que 023/024).
- **Principio III**: Cumple — se extiende la pantalla de conciliación de tarjetas ya existente, no se crea una nueva.
- **Principio IV**: Cumple — cada vínculo sigue siendo trazable (`IdVinculo`, ahora con `origen` explícito en vez de asumir siempre Compras); FR-004 exige que la UI nunca lo muestre ambiguo.
- **Principio V**: Contrato definido en `contracts/api.md` antes de tocar frontend; tests de no-regresión explícitos para Compras (FR-007/SC-002).
- **Principio VI**: Diseño verificado contra el esquema real de `Impuestos` (sin columnas de moneda) antes de asumir que `conciliacion_documentos.py` necesitaba cambios — no los necesitó (research.md §3).
- **Principio VII**: Cambio aditivo sobre la tabla existente (no una tabla nueva, no un renombre) — menor superficie de cambio posible; se descartó extender retroactivamente el control de saldo pendiente a Compras por no ser parte de lo pedido y arriesgar una regresión en un mecanismo ya validado en producción.
- **Principio VIII**: Cumple, sin nuevas dependencias.

No hay violaciones que requieran `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/025-conciliacion-tarjetas-impuestos/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── src/features/tarjetas_resumenes/
│   ├── repository.py        # existente — buscar_documentos, get_documentos_por_ids,
│   │                         # vincular_compra(s)(_lote) extendidos; saldo_pendiente_impuesto nueva
│   ├── schemas.py            # existente — DocumentoCandidato/ImputacionDocumento extendidos
│   ├── router.py             # existente — request/response de los endpoints ya existentes
│   └── conciliacion_documentos.py   # SIN CAMBIOS (research.md §3)
├── scripts/
│   └── extender_vinculos_tarjetas_impuestos.py   # DDL del ALTER TABLE (one-off, re-corrible)
└── tests/
    ├── contract/
    │   └── test_tarjetas_resumenes_*.py   # existentes, extendidos con casos de Impuestos
    └── test_tarjetas_resumenes_repository.py   # existente, extendido

frontend/
├── src/
│   ├── components/tarjetas-conciliacion/
│   │   └── PanelConciliacion.tsx   # existente — muestra origen distinguido, saldoPendiente
│   └── services/
│       └── tarjetasResumenesApi.ts   # existente — DocumentoCandidato extendido, request de vincular actualizado
```

**Structure Decision**: se extienden los módulos ya existentes de 008/009 — no se crea ningún módulo backend ni componente frontend nuevo, porque esto no es un mecanismo distinto (a diferencia de 023/024): es el mismo mecanismo de conciliación de tarjetas, con un origen más de documento.

## Complexity Tracking

Sin violaciones de la Constitución que requieran justificación.
