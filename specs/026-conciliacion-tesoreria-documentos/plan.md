# Implementation Plan: Conciliación de Tesorería con documentos

**Branch**: `026-conciliacion-tesoreria-documentos` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/026-conciliacion-tesoreria-documentos/spec.md`

## Summary

Llevar a los 6 medios de Tesorería (bna, galicia, mercado-libre, efectivo, valores-propios, valores-recibidos) el mismo mecanismo de conciliación por documentos que ya tiene Tarjetas (008/009/025): buscador de documentos pendientes de Compras/Impuestos/Remuneraciones/Alquileres, sugerencias de combinaciones que cierran exacto, reparto proporcional para "cuota" (documentos elegidos que superan el importe del movimiento), "permite parcial" cuando se elige menos, y "aceptar diferencia con motivo" (incluido "Impuesto"). Técnicamente: reusar el módulo puro ya probado `tarjetas_resumenes/conciliacion_documentos.py` (medio-agnóstico por diseño — no sabe nada de tarjetas), extender el esquema insert-only de 023 (`ConciliacionesTesoreria`) para registrar a qué documento corresponde cada conciliación (hoy solo registra contacto+importe), y extender el router existente de búsqueda/vinculación análogo al de Tarjetas. La conciliación manual simple ya vigente (elegir contacto + tipear importe) se mantiene como alternativa (FR-009).

## Technical Context

**Language/Version**: Python 3.13 (backend, FastAPI), TypeScript/Next.js (frontend) — mismo stack que 023/024/025.

**Primary Dependencies**: FastAPI, pyodbc, TanStack Query, Tailwind — sin dependencias nuevas.

**Storage**: SQL Server, base `WC` (producción). Requiere: extender `ConciliacionesTesoreria` con 2 columnas nuevas nullable (`TipoOrigenDocumento`, `IdOrigenDocumento`) y una tabla nueva insert-only `ConciliacionesTesoreriaEstado` (mismo patrón que `Tarjetas_Resumenes_Lineas_Estado`, para "sin documento"/"diferencia aceptada"). No requiere `ALTER VIEW` — `ConciliacionesTesoreria` ya está integrada en `vw_MovimientosCuenta_Base` desde 023 y las columnas nuevas no cambian esa integración (son metadata del vínculo, no afectan el importe/contacto que ya lee la vista).

**Testing**: pytest (contract + repository), `tsc --noEmit` — mismo patrón que 023/024/025.

**Target Platform**: Web app interna, mismo backend/frontend que el resto del sistema.

**Project Type**: Web application (backend FastAPI + frontend Next.js ya existentes).

**Performance Goals**: Sin metas distintas al resto del sistema.

**Constraints**: No debe agregar una conexión directa del navegador a SQL Server. No debe escribir en `LaHerencia`. El cambio de esquema requiere backup verificado antes de aplicarse (Constitución Principio II). La conciliación manual simple de 023 sigue funcionando sin cambios (FR-009) — las filas viejas de `ConciliacionesTesoreria` quedan con `TipoOrigenDocumento`/`IdOrigenDocumento` en `NULL`, que es una respuesta válida (no un dato faltante).

**Scale/Scope**: 6 medios × 4 orígenes de documento (Compras, Impuestos, Remuneraciones, Alquileres/cuotas) — caso real motivador: 3 facturas de Mercado Libre (Compras) repartidas entre 2 movimientos (saldo ML + tarjeta, esta última ya cubierta por Tarjetas/025).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (SQL Server es el sistema de registro)**: Cumple. Toda escritura nueva va contra `WC`. Se preserva el nombre legacy `Alquileres`/`Detalle Cobro Alquiler` sin renombrar.
- **Principio II (Protección de datos reales)**: `ALTER TABLE ConciliacionesTesoreria ADD ...` + tabla nueva `ConciliacionesTesoreriaEstado` — cambio de esquema no trivial. GATE: requiere backup verificado de `WC` antes de aplicarse, con evidencia registrada antes del DDL; no requiere otra confirmación para esta implementación ya autorizada.
- **Principio III (Procesos de negocio, no tablas crudas)**: Cumple — se ofrece inline desde los listados de Tesorería ya existentes (`MovimientosPorMedio.tsx`), mismo flujo que 023/024.
- **Principio IV (Trazabilidad y significado financiero explícito)**: Cumple — cada conciliación queda con el documento de origen explícito (cuando corresponde), motivo de cualquier diferencia aceptada, usuario y fecha.
- **Principio V (Contrato primero, integración probada)**: Contrato definido en `contracts/` antes de tocar frontend; tests de contrato/repository análogos a 025.
- **Principio VI (Colaboración de especialistas)**: Los 4 orígenes de documento (Compras/Impuestos/Remuneraciones/Alquileres) se relevaron contra el código real de cada módulo antes de diseñar el buscador unificado (ver research.md §1) — no se asumió su forma.
- **Principio VII (Simplicidad, reversible)**: Reusa `conciliacion_documentos.py` tal cual (sin fork ni duplicación) porque ya es medio-agnóstico; reusa el patrón insert-only + tabla de estado ya validado por Tarjetas (`Tarjetas_Resumenes_Lineas_Estado`) en vez de inventar uno nuevo; extiende `ConciliacionesTesoreria` con columnas nullable en vez de crear una tabla de vínculo paralela, porque el saldo/estado ya se calcula sumando esas filas — separar la tabla duplicaría esa suma.
- **Principio VIII (Stack aprobado)**: Cumple, sin nuevas dependencias.

No hay violaciones que requieran `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/026-conciliacion-tesoreria-documentos/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── conciliacion-tesoreria-documentos-api.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── src/features/
│   ├── conciliacion_tesoreria/
│   │   ├── repository.py               # existente — se extiende: buscar_documentos,
│   │   │                                #   calcular_conciliacion (preview), vincular_lote,
│   │   │                                #   aceptar_diferencia, marcar_sin_documento, quitar_estado
│   │   ├── schemas.py                   # existente — se extiende con los schemas nuevos
│   │   └── router.py                    # existente — se extiende con los endpoints nuevos
│   └── tarjetas_resumenes/
│       └── conciliacion_documentos.py   # existente — REUSADO tal cual (import directo, sin cambios)
├── scripts/
│   └── extender_conciliaciones_tesoreria_documentos.py   # DDL (ALTER TABLE + CREATE TABLE), one-off, re-corrible
└── tests/
    ├── contract/
    │   └── test_conciliacion_tesoreria_documentos_api.py
    └── test_conciliacion_tesoreria_documentos_repository.py

frontend/
├── src/
│   ├── components/tesoreria/
│   │   ├── ConciliarMovimiento.tsx      # existente — se extiende: buscador + reparto,
│   │   │                                #   con pestaña "manual" (FR-009) reusando el flujo actual
│   │   └── MovimientosPorMedio.tsx      # existente — sin cambios estructurales
│   └── services/
│       └── conciliacionTesoreriaApi.ts  # existente — se extiende con los endpoints nuevos
```

**Structure Decision**: se extiende `conciliacion_tesoreria/` en vez de crear un módulo nuevo — a diferencia de 024 (que tenía su propia tabla y reglas sin relación con 023), esto es fundamentalmente la MISMA conciliación de 023 con más capacidades sobre la misma tabla (`ConciliacionesTesoreria`), así que separarlo en otro módulo duplicaría `calcular_estado`/`esta_resuelto`. El módulo puro de cálculo (`conciliacion_documentos.py`) se importa directo desde `tarjetas_resumenes` — moverlo a un lugar común no aporta nada porque Python no tiene problema con el import cruzado entre features (ya pasa en otros módulos del sistema) y moverlo rompería 008/009/025 sin necesidad (Principio VII).

## Complexity Tracking

Sin violaciones de la Constitución que requieran justificación.

## Ajustes de revisión aprobados

El cambio de esquema también amplía CK_ConciliacionesTesoreria_Importe para NC con signo, confirmado por Sergio. Se incluye EstadoQuitado como revocación auditable. El motor puro se reutiliza con documentos_adapter.py; documentos.py concentra consultas/saldos compartidos con Tarjetas. Se extienden db/connection.py (contexto transaccional con bloqueo fijo), tarjetas_resumenes/repository.py (saldo compartido y guardas), traspasos_internos_tesoreria/repository.py (misma transacción), tesoreria/estado_resolucion.py y tipos frontend, más VincularTraspasoInterno.tsx. Sin dependencias nuevas. El historial de Tarjetas no se describe como insert-only: allí existen DELETE. Ver research §6–7 y las decisiones de spec.
