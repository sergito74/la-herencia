# Implementation Plan: Cuentas corrientes por proveedor/cliente (solo lectura)

**Branch**: `004-cuentas-corrientes` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-cuentas-corrientes/spec.md`

## Summary

Módulo web de solo lectura para buscar un contacto, ver su saldo actual y sus movimientos de deuda/crédito, y navegar hacia el origen de cada movimiento (compra o tesorería) usando los campos `Origen`/`IdOrigen`, que en este módulo sí son una clave directa y confiable (a diferencia de la referencia heurística de tesorería→compra). Reutiliza la misma base técnica que compras y tesorería.

## Technical Context

**Language/Version**: Python 3.13 (backend) + TypeScript 5.x / Next.js (frontend) — mismas versiones que `specs/002-compras` y `specs/003-tesoreria`

**Primary Dependencies**: FastAPI + Pydantic; pyodbc (DSN `SQL_LaHerencia`); Next.js, TanStack Query, Tailwind CSS

**Storage**: SQL Server `LaHerencia` — `dbo.Contactos`, `dbo.vw_MovimientosCuenta_Base`, `dbo.vw_MovimientosCuenta_Saldo`; lectura exclusiva, sin escritura

**Testing**: pytest + httpx (contract tests con fixtures)

**Target Platform**: Igual que compras/tesorería — backend Python + frontend Next.js, uso interno

**Project Type**: Web application (frontend + backend), extiende la misma base de `specs/002-compras` y `specs/003-tesoreria`

**Performance Goals**: Saldo y movimientos de un contacto en menos de 30s percibidos por el usuario (SC-001); listados paginados sin degradación (implícito por volumen)

**Constraints**: Solo lectura (FR-010); saldo calculado por las vistas existentes, no recalculado (Assumptions); sin imputación propia (FR-009); soporte de lectura concurrente (FR-015)

**Scale/Scope**: Miles de movimientos de cuenta corriente (volumen observado en el prototipo); depende de que compras y tesorería existan como destino de navegación, pero no bloquea si aún no están implementados (Assumptions)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Resultado |
|---|---|---|
| I. SQL Server es la fuente de verdad | Usa `Contactos` y las vistas `vw_MovimientosCuenta_*` ya existentes, sin recalcular reglas de negocio propias. | Pass |
| II. Protección de datos reales | Todos los endpoints son GET; sin ninguna ruta de escritura (FR-010). | Pass |
| III. Procesos de negocio antes que tablas | Flujo: seleccionar contacto → saldo → movimientos → origen, no una grilla de la vista cruda. | Pass |
| IV. Trazabilidad y significado financiero explícito | `Origen`/`IdOrigen` como clave directa y explícita (clarificación 2026-09-15); deuda/crédito distinguidos visualmente (FR-013). | Pass |
| V. Contrato primero, integración probada | Contrato de API en Fase 1 antes de UI; contract tests con fixtures. | Pass |
| VI. Colaboración de especialistas | Construido con el contrato de datos ya documentado por el agente de administración de cuentas. | Pass |
| VII. Simplicidad y reversibilidad | Reutiliza `db/connection.py` de compras/tesorería; no duplica lógica de paginación ni de acceso a datos. | Pass |
| VIII. Stack aprobado | Mismo stack aprobado, sin dependencias nuevas más allá de las ya usadas en compras/tesorería. | Pass |

No hay violaciones que requieran justificación.

*Re-chequeo post-Fase 1 (2026-09-15): `data-model.md`, `contracts/cuentas-corrientes-api.md` y `quickstart.md` confirman que el módulo no calcula imputación propia y que la navegación hacia compras/tesorería es tolerante a que esos módulos no existan todavía. Los 8 principios siguen en Pass.*

## Project Structure

### Documentation (this feature)

```text
specs/004-cuentas-corrientes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── db/
│   │   └── connection.py              # Reutilizada, sin cambios
│   ├── features/
│   │   ├── compras/                    # specs/002-compras
│   │   ├── tesoreria/                  # specs/003-tesoreria
│   │   └── cuentas_corrientes/
│   │       ├── router.py               # Endpoints FastAPI de cuentas corrientes
│   │       ├── repository.py           # Consultas sobre Contactos y vw_MovimientosCuenta_*
│   │       ├── origen_resolver.py      # Resuelve Origen/IdOrigen → referencia a compra o tesorería
│   │       └── schemas.py
│   └── main.py
└── tests/
    └── contract/
        └── test_cuentas_corrientes_api.py

frontend/
├── src/
│   ├── app/
│   │   └── cuentas-corrientes/         # Buscador de contacto, saldo, movimientos, origen
│   ├── components/
│   │   └── cuentas-corrientes/
│   └── services/
│       └── cuentasCorrientesApi.ts
└── tests/
```

**Structure Decision**: Cuarto módulo de negocio (`features/cuentas_corrientes/`) sobre la misma app backend/frontend de compras y tesorería. `origen_resolver.py` centraliza la resolución de `Origen`/`IdOrigen` hacia compra o tesorería, en paralelo a `matching.py` de tesorería pero con lógica más simple (clave directa, no heurística).

## Complexity Tracking

*(Sin violaciones que justificar — tabla vacía.)*
