# Implementation Plan: Impuestos, remuneraciones, arrendamientos y ventas de hacienda (solo lectura)

**Branch**: `005-egresos-y-ventas-menores` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-egresos-y-ventas-menores/spec.md`

## Summary

Cuatro módulos web de solo lectura (Impuestos/Retenciones, Remuneraciones, Arrendamientos, Ventas de Hacienda) que cierran 5 de los 6 estados `fuera_de_alcance` que hoy devuelve `origen_resolver.py` de `specs/004-cuentas-corrientes`. Cada dominio expone su propia consulta de solo lectura (liquidación/contrato/venta + su detalle asociado), y `origen_resolver.py` se amplía para resolver `Origen` ∈ {`Impuestos`, `Retenciones`, `Remuneraciones`, `Alquileres`, `Ret. Ventas Hacienda`} hacia una referencia real en el dominio correspondiente, en vez de `fuera_de_alcance`. Reutiliza la misma base técnica que compras/tesorería/cuentas corrientes.

## Technical Context

**Language/Version**: Python 3.13 (backend) + TypeScript 5.x / Next.js (frontend) — mismas versiones que `specs/002-004`

**Primary Dependencies**: FastAPI + Pydantic; pyodbc (DSN `SQL_LaHerencia`); Next.js, TanStack Query, Tailwind CSS

**Storage**: SQL Server `LaHerencia` — `dbo.Impuestos`, `dbo.[Tipo Impuesto]`, `dbo.Retenciones`, `dbo.Remuneraciones`, `dbo.[Pagos Remuneraciones]`, `dbo.Alquileres`, `dbo.[Detalles del alquiler]`, `dbo.[Detalle Cobro Alquiler]`, `dbo.[Venta Hacienda]`, `dbo.[Det_Ventas Hacienda]`, `dbo.[Retenciones Ventas Hacienda]`, `dbo.[Tipo Hacienda]`, más `dbo.Contactos` (ya usada por 004); lectura exclusiva, sin escritura

**Testing**: pytest + httpx (contract tests con fixtures), mismo patrón que `test_cc_*.py`

**Target Platform**: Igual que compras/tesorería/cuentas corrientes — backend Python + frontend Next.js, uso interno

**Project Type**: Web application (frontend + backend), extiende la misma app de `specs/002-004`

**Performance Goals**: Detalle de un movimiento conocido en menos de 30s (SC-001); listados paginados sin degradación

**Constraints**: Solo lectura (FR-008); sin imputación cruzada entre dominios (FR-007); soporte de lectura concurrente (FR-011, mismo patrón que FR-015 de 004)

**Scale/Scope**: Volumen comparable a compras/tesorería/cuentas corrientes (confirmado: 1076 filas en `Impuestos`, 631 en `Remuneraciones`, 5 en `Alquileres`, decenas en `Venta Hacienda` — volumen bajo-medio, sin riesgo de escala)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Resultado |
|---|---|---|
| I. SQL Server es la fuente de verdad | Usa las tablas reales ya confirmadas contra `INFORMATION_SCHEMA`/datos (ver spec.md Assumptions), sin recalcular reglas de negocio propias. | Pass |
| II. Protección de datos reales | Todos los endpoints son GET; sin ninguna ruta de escritura (FR-008). | Pass |
| III. Procesos de negocio antes que tablas | Flujo por dominio: listar/filtrar → detalle → asociados (pagos/cobros/retenciones), no una grilla de la tabla cruda. | Pass |
| IV. Trazabilidad y significado financiero explícito | `IdOrigen` como clave primaria directa hacia cada tabla (confirmado contra datos reales, sin intermediarios); fechas, importes y contacto explícitos en cada dominio. | Pass |
| V. Contrato primero, integración probada | Contrato de API en Fase 1 antes de UI; contract tests con fixtures, igual que 002-004. | Pass |
| VI. Colaboración de especialistas | Alcance y estructura (consignatario/comprador, liquidación/pago) resueltos en `/speckit-clarify` contra datos reales antes de diseñar el contrato. | Pass |
| VII. Simplicidad y reversibilidad | Reutiliza `db/connection.py`/`db/pagination.py` sin cambios; extiende `origen_resolver.py` existente en vez de duplicar lógica de resolución. | Pass |
| VIII. Stack aprobado | Mismo stack aprobado, sin dependencias nuevas. | Pass |

No hay violaciones que requieran justificación.

*Re-chequeo post-Fase 1 (2026-09-16): `data-model.md`, `contracts/egresos-y-ventas-menores-api.md` y `quickstart.md` confirman que ningún dominio calcula imputación cruzada y que los 4 nuevos `origen.tipo` siguen el mismo patrón que `compra`/`tesoreria` de 004. Los 8 principios siguen en Pass.*

## Project Structure

### Documentation (this feature)

```text
specs/005-egresos-y-ventas-menores/
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
│   ├── db/                                     # Reutilizada, sin cambios
│   ├── features/
│   │   ├── compras/                            # specs/002-compras
│   │   ├── tesoreria/                          # specs/003-tesoreria
│   │   ├── cuentas_corrientes/                 # specs/004-cuentas-corrientes
│   │   │   └── origen_resolver.py              # AMPLIADO: +4 tipos de origen (impuesto/retencion/remuneracion/arrendamiento/venta_hacienda)
│   │   ├── impuestos/
│   │   │   ├── router.py
│   │   │   ├── repository.py
│   │   │   └── schemas.py
│   │   ├── remuneraciones/
│   │   │   ├── router.py
│   │   │   ├── repository.py
│   │   │   └── schemas.py
│   │   ├── arrendamientos/
│   │   │   ├── router.py
│   │   │   ├── repository.py
│   │   │   └── schemas.py
│   │   └── ventas_hacienda/
│   │       ├── router.py
│   │       ├── repository.py
│   │       └── schemas.py
│   └── main.py
└── tests/
    └── contract/
        ├── test_impuestos_*.py
        ├── test_remuneraciones_*.py
        ├── test_arrendamientos_*.py
        ├── test_ventas_hacienda_*.py
        └── test_cc_origen.py                   # AMPLIADO: nuevos casos de origen

frontend/
├── src/
│   ├── app/
│   │   ├── impuestos/
│   │   ├── remuneraciones/
│   │   ├── arrendamientos/
│   │   └── ventas-hacienda/
│   ├── components/
│   │   ├── impuestos/
│   │   ├── remuneraciones/
│   │   ├── arrendamientos/
│   │   └── ventas-hacienda/
│   ├── components/layout/NavHeader.tsx          # AMPLIADO: +1 submenú "Otros movimientos" (4 entradas)
│   ├── app/page.tsx                              # AMPLIADO: jerarquía de 2 niveles (ver Nota UX)
│   ├── components/cuentas-corrientes/OrigenMovimiento.tsx  # AMPLIADO: +5 casos de origen
│   └── services/
│       ├── impuestosApi.ts
│       ├── remuneracionesApi.ts
│       ├── arrendamientosApi.ts
│       └── ventasHaciendaApi.ts
└── tests/
```

**Structure Decision**: Cuatro módulos de negocio nuevos (`features/impuestos/`, `.../remuneraciones/`, `.../arrendamientos/`, `.../ventas_hacienda/`), cada uno independiente y con su propio contrato, sobre la misma app backend/frontend de compras/tesorería/cuentas corrientes. Se eligieron 4 features separadas (en vez de una sola `egresos_menores`) porque cada dominio tiene su propia forma de datos y ciclo de vida (liquidación+pago, contrato+cobro, venta+detalle+retención) sin relación estructural entre sí más allá de compartir `Contactos` — agruparlas artificialmente violaría el principio VII (simplicidad: no forzar una abstracción común donde no la hay). `origen_resolver.py` de 004 se amplía (no se duplica) porque ya es el punto único de resolución de `Origen`/`IdOrigen` para cuentas corrientes. Regla de navegación (adoptada tras el gap de UX detectado en la sesión anterior): cada módulo agrega su entrada a `NavHeader.tsx` y a la home como parte de sus propias tareas de Setup, no como tarea separada al final.

**Nota UX (consulta a `08-agro-erp-frontend-specialist`, 2026-09-16)**: con 7 módulos totales, un nav plano ya no es usable a diario. Se adopta un primer nivel de navegación con `Tesorería`, `Cuentas corrientes`, `Compras` como entradas top-level (como hoy), y un nuevo submenú desplegable **"Otros movimientos"** que agrupa Impuestos, Remuneraciones, Arrendamientos y Ventas de Hacienda — nombre elegido explícitamente en vez de "Egresos" porque Arrendamientos y Ventas de Hacienda son ingresos, no egresos. La home replica la misma jerarquía: fila destacada (Tesorería, Cuentas Corrientes, Compras) y una sección secundaria más compacta para los 4 módulos nuevos. Terminología de UI a mantener consistente (ya reflejada en `spec.md`/`data-model.md`/contrato): **"Arrendamiento"** (no "Alquiler") en toda etiqueta visible pese a que la tabla SQL se llame `Alquileres`; **"Consignatario"** (cabecera de venta) vs. **"Comprador"** (línea de detalle) en Ventas de Hacienda; **"Liquidación"** (Remuneraciones) vs. **"Pago"** (Pagos Remuneraciones) como sección de detalle. `OrigenMovimiento.tsx` se amplía con 5 nuevos `case` explícitos (mismo patrón que `compra`/`tesoreria`), sin una rama genérica de "otros". Pendiente de escalar a `04-integrated-agro-management-engineer` antes de fijar el filtro por defecto de Ventas de Hacienda: si "campaña" tiene el mismo sentido en ganadería que en agricultura, o si el corte natural ahí es otro (ej. ejercicio fiscal) — no bloquea esta fase, se resuelve en `/speckit-tasks` o al implementar el filtro.

## Complexity Tracking

*(Sin violaciones que justificar — tabla vacía.)*
