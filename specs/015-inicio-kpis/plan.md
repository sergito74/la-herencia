# Implementation Plan: Inicio con indicadores reales del negocio

**Branch**: `015-inicio-kpis` | **Date**: 2026-09-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-inicio-kpis/spec.md`

## Summary

Reemplaza el placeholder "Producción — próximamente" y el menú de Finanzas desactualizado de la pantalla de inicio por contenido real, y agrega 3 indicadores (deuda total a proveedores, tarjetas pendientes de conciliar, resultado de campaña actual) calculados exclusivamente a partir de endpoints ya existentes (014, 009, 012) — sin backend nuevo.

## Technical Context

**Language/Version**: TypeScript/Next.js 14 (solo frontend — no hay cambios de backend en esta spec).

**Primary Dependencies**: TanStack Query, servicios ya existentes (`cuentasCorrientesApi`, nuevo cliente mínimo para `tarjetas-resumenes/pendientes` y `resultado-cultivo`, `arrendamientosApi`).

**Storage**: N/A — sin cambios de esquema ni queries nuevas.

**Testing**: sin tests de backend (no hay backend nuevo); verificación manual de `tsc --noEmit` y comparación de los 3 indicadores contra sus endpoints fuente.

**Target Platform**: Web, mismo entorno.

**Project Type**: Web application — solo `frontend/src/app/page.tsx` y componentes nuevos.

**Performance Goals**: los 3 indicadores cargan en paralelo, sin bloquearse entre sí (SC-001).

**Constraints**: ningún indicador fabrica un número no respaldado por un endpoint real (constitución IV, FR-004).

**Scale/Scope**: 1 página modificada, 2-3 componentes nuevos, 1 cliente API nuevo mínimo (o extensión de los ya existentes si ya cubren lo necesario).

## Constitution Check

- **III (proceso de negocio)**: ✅ mejora la navegación central del sistema, corrigiendo contenido que hoy desinforma sobre qué está migrado.
- **IV (trazabilidad)**: ✅ es el requisito central de esta spec — cada indicador debe rastrearse a un endpoint real (FR-004).
- **V (contract-first)**: N/A parcial — no hay contrato de API nuevo (sin backend), se reusan los contratos ya publicados de 009/012/014.
- **VII (simplicidad)**: ✅ no se crea un endpoint agregador nuevo por 3 números — se calculan en el cliente a partir de datos ya paginados/expuestos, evitando una capa de backend innecesaria para esta escala.

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/015-inicio-kpis/
├── plan.md
├── quickstart.md
└── tasks.md
```

(Sin `research.md`/`data-model.md`/`contracts/` — no aplica, feature sin backend nuevo ni entidades nuevas.)

### Source Code (repository root)

```text
frontend/src/
├── app/page.tsx                          # reescrito: Producción real, Finanzas con Tarjetas, 3 KPIs nuevos
├── components/inicio/
│   ├── DeudaTotalKpi.tsx                  # nuevo
│   ├── TarjetasPendientesKpi.tsx          # nuevo
│   └── ResultadoCampaniaKpi.tsx           # nuevo
└── services/
    └── tarjetasResumenesApi.ts            # extendido con fetchPendientesTotal si no existe ya un cliente reusable
```

**Structure Decision**: los 3 indicadores viven en `components/inicio/`, cada uno responsable de su propio fetch + estado de error independiente (FR-005) — ningún componente compartido de "dashboard genérico", consistente con que esta es la única pantalla que los necesita hoy.

## Complexity Tracking

*Sin violaciones — sección no aplica.*
