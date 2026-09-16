# Implementation Plan: Compras como fuente de verdad de imputación (solo lectura)

**Branch**: `002-compras` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-compras/spec.md`

## Summary

Módulo web de solo lectura para buscar compras, ver el detalle de cada línea (incluida su imputación: rubro, centro de costo, destino) y navegar hacia los movimientos de cuenta corriente/tesorería que cada compra generó, usando `IdOrigen` como clave de trazabilidad. Backend Python (FastAPI) expone un contrato de API tipado y de solo lectura sobre SQL Server; frontend Next.js/TypeScript consume ese contrato vía TanStack Query. Compras se convierte en la fuente de verdad de imputación para todo el sistema (compras, tesorería, cuentas corrientes).

## Technical Context

**Language/Version**: Python 3.13 (backend) + TypeScript 5.x / Next.js (App Router) (frontend)

**Primary Dependencies**: FastAPI + Pydantic (backend, contratos tipados); pyodbc con DSN `SQL_LaHerencia` (acceso SQL Server de solo lectura); Next.js, TanStack Query, Tailwind CSS (frontend)

**Storage**: SQL Server `LaHerencia` (existente, `Compras`, `Det_Compras`, `Rubros`, `Contactos`), acceso exclusivamente de lectura vía backend Python — el navegador nunca se conecta directo a SQL Server

**Testing**: pytest + httpx (contract tests de la API contra fixtures, sin escribir en la base real); `next build`/type-check como verificación de compilación del frontend

**Target Platform**: Aplicación web interna (backend Python + frontend Next.js), uso en red local/LAN de La Herencia

**Project Type**: Web application (frontend + backend separados)

**Performance Goals**: Búsqueda y listado percibidos como instantáneos (SC-001: <30s incluye tiempo de decisión del usuario; la respuesta de API debe ser sub-segundo en condiciones normales); listados paginados para no degradar con miles de registros (SC-005)

**Constraints**: Solo lectura (FR-010); sin acceso a Access/DataSet/TableAdapter (constitución, principio I); consultas parametrizadas y acotadas (constitución, principio V); soporte de sesiones de lectura concurrentes sin bloqueos (FR-014)

**Scale/Scope**: ~6.400 compras y su detalle asociado (volumen observado en el prototipo), un solo módulo de esta spec (compras), pensado para compartir capa de datos con tesorería (`specs/003-tesoreria`) y cuentas corrientes (`specs/004-cuentas-corrientes`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Resultado |
|---|---|---|
| I. SQL Server es la fuente de verdad | Usa exclusivamente tablas/vistas SQL Server existentes (`Compras`, `Det_Compras`, `Rubros`, `Contactos`); no se tocan Access ni DataSet. | Pass |
| II. Protección de datos reales | Todos los endpoints son GET/solo lectura; no hay rutas de escritura en esta spec (FR-010). | Pass |
| III. Procesos de negocio antes que tablas | Las pantallas siguen el flujo buscar → detalle/imputación → trazabilidad, no una grilla cruda de tablas. | Pass |
| IV. Trazabilidad y significado financiero explícito | Usa `IdOrigen` como clave explícita de trazabilidad (clarificación 2026-09-15); imputación mostrada a nivel de línea. | Pass |
| V. Contrato primero, integración probada | Fase 1 define contrato de API antes de implementar UI; pytest valida el contrato. | Pass |
| VI. Colaboración de especialistas | Spec construida con input de agentes SQL, financiero y administración de cuentas (ver historial de conversación). | Pass |
| VII. Simplicidad y reversibilidad | Un solo proyecto backend + un solo frontend, sin abstracciones especulativas; estructura reutilizable para los 3 módulos relacionados sin duplicarla. | Pass |
| VIII. Stack aprobado | Python + SQL Server + Next.js + TypeScript + Tailwind + TanStack Query, sin introducir ASP.NET ni otro framework. | Pass |

No hay violaciones que requieran justificación. `Complexity Tracking` queda vacío.

*Re-chequeo post-Fase 1 (2026-09-15): el diseño de `data-model.md`, `contracts/compras-api.md` y `quickstart.md` no introduce escritura, no usa Access/DataSet, mantiene el contrato tipado y la trazabilidad por `IdOrigen`. Los 8 principios siguen en Pass.*

## Project Structure

### Documentation (this feature)

```text
specs/002-compras/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── db/
│   │   └── connection.py        # Conexión pyodbc de solo lectura (DSN SQL_LaHerencia), compartida entre módulos
│   ├── features/
│   │   └── compras/
│   │       ├── router.py        # Endpoints FastAPI de compras
│   │       ├── repository.py    # Consultas SQL parametrizadas (Compras, Det_Compras, Rubros)
│   │       └── schemas.py       # Modelos Pydantic (contrato tipado)
│   └── main.py                   # App FastAPI
└── tests/
    └── contract/
        └── test_compras_api.py   # Contract tests contra fixtures (sin escribir en la base real)

frontend/
├── src/
│   ├── app/
│   │   └── compras/              # Rutas Next.js del módulo de compras (listado, detalle)
│   ├── components/
│   │   └── compras/              # Componentes de búsqueda, listado, detalle e imputación
│   └── services/
│       └── comprasApi.ts         # Cliente TanStack Query del contrato de compras
└── tests/
    └── (verificación de compilación/type-check; sin suite E2E en esta fase)
```

**Structure Decision**: Aplicación web con backend y frontend separados (Opción 2 del template). `backend/src/db/connection.py` queda como capa compartida de acceso a SQL Server para no duplicarla cuando se implementen tesorería y cuentas corrientes; cada módulo de negocio vive en su propia carpeta bajo `backend/src/features/` y `frontend/src/app/` para mantener los tres módulos relacionados pero independientes, conforme al principio de simplicidad (VII).

## Complexity Tracking

*(Sin violaciones que justificar — tabla vacía.)*
