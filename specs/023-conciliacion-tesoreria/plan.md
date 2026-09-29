# Implementation Plan: Conciliación de Tesorería

**Branch**: `023-conciliacion-tesoreria` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-conciliacion-tesoreria/spec.md`

## Summary

Permitir, desde los listados de Tesorería (BNA, Galicia, Mercado Libre, Efectivo, Valores propios, Valores recibidos), asignar manualmente uno o más contactos a un movimiento sin contacto reconocido, generando un efecto real (debe/haber) en la cuenta corriente de cada contacto — con soporte de reparto incremental entre varios contactos y sin duplicar movimientos ya reconocidos por otro origen automático. Técnicamente: una tabla nueva insert-only (`ConciliacionesTesoreria`) registra cada asignación (total o parcial); `vw_MovimientosCuenta_Base` se extiende con nuevas ramas UNION para que esas conciliaciones se reflejen en cuentas corrientes igual que Compras/Impuestos/etc.; y `022-reasignacion-contacto` se extiende para poder corregir una conciliación ya aplicada (mismo mecanismo de override, orígenes nuevos).

## Technical Context

**Language/Version**: Python 3.13 (backend, FastAPI), TypeScript/Next.js (frontend) — mismo stack que el resto del sistema.

**Primary Dependencies**: FastAPI, pyodbc (vía `src/db/connection.py`), TanStack Query, Tailwind — sin dependencias nuevas.

**Storage**: SQL Server, base `WC` (producción desde el cutover 2026-09-25 — Constitución Principio I). Requiere: 1 tabla nueva (`ConciliacionesTesoreria`), y un `ALTER VIEW` de `vw_MovimientosCuenta_Base` para sumar las ramas de conciliación manual y, para Valores propios y Mercado Libre (hoy ausentes de la vista), una rama nueva por medio.

**Testing**: pytest (backend, contract + repository tests contra `WC` de solo lectura donde sea posible), `tsc --noEmit` (frontend). Mismo patrón que 022.

**Target Platform**: Web app interna (navegador de escritorio), backend en la misma PC que la base SQL Server.

**Project Type**: Web application (backend FastAPI + frontend Next.js ya existentes).

**Performance Goals**: Sin metas de carga distintas al resto del sistema (uso interno, un puñado de usuarios concurrentes). El cálculo de "saldo pendiente" por movimiento debe resolverse dentro del mismo tiempo de respuesta ya aceptable en los listados de Tesorería existentes (consulta agregada simple, sin recorrer todo el histórico en el cliente).

**Constraints**: No debe agregar una conexión directa del navegador a SQL Server (Constitución). No debe escribir en `LaHerencia` (frozen). Todo cambio de esquema no trivial en `WC` (tabla nueva + `ALTER VIEW`) requiere backup verificado antes de aplicarse (Constitución Principio II, ahora que `WC` es producción).

**Scale/Scope**: Volumen real medido contra `WC` (2026-09-28) — movimientos sin contacto reconocido hoy: BNA 34, Galicia 113, Mercado Libre 75 (Mercado Libre no está ni presente hoy en `vw_MovimientosCuenta_Base`); Efectivo 0 (ya tiene contacto en el 100% de sus filas); Valores propios 1.142 filas en total y la tabla no tiene ninguna columna de contacto (0% reconocido, medio ausente por completo de la vista hoy); Valores recibidos 17 filas totales, mayormente ya cubiertas por las vistas de endoso existentes. 6 medios cubiertos (Tarjetas excluido, FR-002).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (SQL Server es el sistema de registro)**: Cumple. Toda escritura nueva va contra `WC`; no se toca `LaHerencia`.
- **Principio II (Protección de datos reales)**: `WC` es producción desde el cutover — el `ALTER VIEW` de `vw_MovimientosCuenta_Base` y la tabla nueva son un cambio de esquema no trivial. GATE: requiere backup verificado de `WC` antes de aplicarse, documentado en `tasks.md`, y confirmación explícita del usuario antes de ejecutar el `ALTER VIEW` en producción (no alcanza con la autorización ya dada para escrituras de datos ordinarias).
- **Principio III (Procesos de negocio, no tablas crudas)**: Cumple — la pantalla sigue el flujo ya existente de Tesorería (selección de medio → filtro → línea → conciliar), no expone una tabla cruda nueva.
- **Principio IV (Trazabilidad y significado financiero explícito)**: Cumple — cada conciliación queda con `IdContacto`, `IdOrigen`/medio, importe, usuario y fecha; el estado (sin conciliar/parcial/completo) se deriva de esos datos, nunca se oculta.
- **Principio V (Contrato primero, integración probada)**: Se define el contrato de la API (`contracts/`) antes de tocar el frontend; se agregan tests de contrato/repository análogos a los de 022.
- **Principio VI (Colaboración de especialistas)**: Diseño de la vista y del reparto revisado contra datos reales de `WC` (ver Scale/Scope) antes de escribir el plan, no solo contra la spec.
- **Principio VII (Simplicidad, revisabilidad, cambio reversible)**: Se reutiliza el patrón insert-only ya validado en 021/022 (`MovimientosCuentaSocio`/`ReasignacionesContacto`) en vez de inventar uno nuevo; el `ALTER VIEW` es aditivo (nuevas ramas `UNION ALL`), no reescribe las ramas existentes.
- **Principio VIII (Stack aprobado)**: Cumple — Python/FastAPI/SQL Server/Next.js/TanStack Query, sin nuevas dependencias.

No hay violaciones que requieran `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/023-conciliacion-tesoreria/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/             # Phase 1 output
│   └── conciliacion-tesoreria-api.md
├── checklists/
│   └── requirements.md
└── tasks.md               # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
backend/
├── src/features/
│   ├── tesoreria/
│   │   ├── repository.py        # existente — se agrega estado "conciliado" a get_movimientos
│   │   ├── schemas.py           # existente — se agrega estadoConciliacion/saldoPendiente
│   │   ├── matching.py          # existente, sin cambios (referencia de origen sigue igual)
│   │   └── router.py            # existente — nuevos endpoints de conciliación (ver contracts/)
│   ├── conciliacion_tesoreria/  # NUEVO — igual patrón que reasignacion_contacto
│   │   ├── __init__.py
│   │   ├── repository.py        # alta de conciliaciones (simples/parciales), cálculo de saldo pendiente
│   │   ├── schemas.py
│   │   └── router.py
│   └── reasignacion_contacto/
│       └── repository.py        # existente — ORIGENES_SOPORTADOS se extiende (FR-008a)
├── scripts/
│   └── crear_tabla_conciliaciones_tesoreria.py   # DDL de la tabla nueva + ALTER VIEW (one-off, re-corrible)
└── tests/
    ├── contract/
    │   └── test_conciliacion_tesoreria_api.py
    ├── test_conciliacion_tesoreria_repository.py
    └── test_reasignacion_contacto_repository.py   # existente — casos nuevos para los orígenes agregados

frontend/
├── src/
│   ├── components/tesoreria/
│   │   ├── MovimientosPorMedio.tsx   # existente — columna/badge de estado de conciliación
│   │   └── ConciliarMovimiento.tsx   # NUEVO — panel/modal de conciliación (simple o reparto)
│   └── services/
│       └── conciliacionTesoreriaApi.ts   # NUEVO
```

**Structure Decision**: Web application ya existente (backend FastAPI por feature-módulo en `backend/src/features/`, frontend Next.js por ruta/componente/servicio en `frontend/src/`). Este feature agrega un módulo backend nuevo (`conciliacion_tesoreria/`, mismo patrón que `reasignacion_contacto/` de 022) en vez de mezclar su lógica dentro de `tesoreria/`, porque tiene su propia tabla, sus propias reglas de reparto/estado y su propio ciclo de vida — `tesoreria/` se mantiene como el módulo de lectura de movimientos por medio, sin gestionar conciliaciones. No se crean módulos frontend nuevos por separado: la conciliación se ofrece inline desde los listados de Tesorería ya existentes (Principio III — el flujo es "ver movimientos → conciliar el que corresponda", no una pantalla aparte desconectada del contexto).

## Complexity Tracking

Sin violaciones de la Constitución que requieran justificación — ver Constitution Check.
