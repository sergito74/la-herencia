# Implementation Plan: Motor de auto-clasificación de Rubro/Centro de Costos/Cultivo/Campaña

**Branch**: `017-imputacion-automatica-costos` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-imputacion-automatica-costos/spec.md`

## Summary

Motor nuevo que, para facturas de insumo ya vinculadas a un remito con consumo real en Órdenes de Trabajo (010/011) y facturas de contratista vinculadas a una o más Órdenes, calcula automáticamente cómo repartir su costo entre Agricultura/Ganadería y Cultivo/Campaña — como propuesta pendiente de aprobación, nunca aplicada sola. Corre en modo paralelo/benchmark contra el motor de costeo heredado (spec 012, `vw_ResultadoCultivo_Campaña`) sin reemplazarlo. Reutiliza el FIFO ya implementado en `remitos/stock_fifo.py` (no lo reimplementa) y generaliza a N a N el vínculo factura de contratista↔Orden que hoy existe pero es 1 a 1 (`Ordenes_Trabajo_Contratista_Factura`).

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript/Next.js 14 (frontend).

**Primary Dependencies**: ninguna nueva — reutiliza `remitos/stock_fifo.py` (FIFO ya implementado), `ordenes/costeo.py`/`distribucion.py` (prorrateo por superficie ya implementado), FastAPI, pyodbc.

**Storage**: SQL Server `WC`. 3 tablas nuevas (`ImputacionPropuestas`, `OrdenesContratistaFacturas`, `ImputacionReferencias`) — ver data-model.md. Ninguna tabla/vista existente se modifica (FR-016).

**Testing**: `pytest` (unit del cálculo de reparto, con datos de `WC` mockeados; contract tests de los endpoints nuevos con `TestClient`/`httpx.AsyncClient`, mismo patrón que 010/011).

**Target Platform**: Web local.

**Project Type**: Web application. Nuevo feature `backend/src/features/imputacion/`; extensión de `backend/src/features/ordenes/` (vínculo N a N de contratista); nueva pantalla de revisión de propuestas en frontend.

**Performance Goals**: recalcular una corrida al vuelo (reusando `calcular_stock`) es aceptable a los volúmenes reales confirmados (cientos de renglones — spec 010/011); el resultado se persiste en `ImputacionPropuestas` para que listar propuestas no dispare el FIFO completo en cada request (research.md).

**Constraints**: constitución II — tablas nuevas son infraestructura de esta app en `WC`, no tocan `LaHerencia`/`.accdb`. El motor NUNCA escribe en `Det_Compras.IdCentroCostos/IdRubro/IdCampaña` (clasificación manual, queda intacta como benchmark) ni en las vistas del motor heredado (FR-016).

**Scale/Scope**: 1 feature backend nuevo (`imputacion`), 3 tablas nuevas, extensión de 1 endpoint existente de Órdenes (contratista N a N), 1 pantalla de revisión/aprobación en frontend, 1 vista de comparación contra el motor heredado.

## Constitution Check

- **I/II**: ✅ tablas nuevas en `WC`, ninguna escritura a `LaHerencia`/`.accdb`; el motor lee `Det_Compras` y las vistas heredadas pero nunca las escribe.
- **III**: ✅ el proceso de negocio (imputar el costo real de un insumo/contratista a su campaña) es el objetivo central del módulo — no es una exposición cruda de tablas.
- **IV**: ✅ cada fracción de propuesta expone su origen trazable (remito, capa FIFO, Orden, renglón de distribución) — FR-013.
- **V**: ✅ contrato de API definido antes de implementación (contracts/api-imputacion.md); tests de cálculo de reparto y de los endpoints nuevos antes/junto con el código.
- **VI**: ✅ especificado con 4 agentes especialistas (producción agrícola, dirección financiera, SQL Server, mismo relevamiento previo) — 28 preguntas de clarificación resueltas con el usuario.
- **VII (simplicidad)**: ✅ reutiliza el FIFO y el prorrateo por superficie ya implementados en vez de reescribirlos; generaliza la tabla de vínculo contratista existente en vez de crear una paralela; "aprendizaje simple" reusa el patrón ya validado de sugerencia por texto histórico (spec 006) en vez de introducir ML.
- **VIII**: ✅ sin nuevas dependencias de stack.

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/017-imputacion-automatica-costos/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── api-imputacion.md # Phase 1 output
└── tasks.md              # Phase 2 output (speckit-tasks, NOT created by speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   └── crear_tablas_imputacion.py   # nuevo: ImputacionPropuestas, OrdenesContratistaFacturas, ImputacionReferencias
├── src/
│   └── features/
│       ├── imputacion/
│       │   ├── __init__.py
│       │   ├── motor.py             # calcula el reparto (reusa remitos.stock_fifo + ordenes.distribucion)
│       │   ├── repository.py        # lee/escribe ImputacionPropuestas, ImputacionReferencias
│       │   ├── router.py            # /api/imputacion/*
│       │   └── schemas.py
│       └── ordenes/
│           ├── repository.py        # + vincular_factura_contratista N a N (sobre OrdenesContratistaFacturas)
│           └── router.py            # + POST/DELETE /api/ordenes/{id}/factura-contratista
├── main.py                          # + imputacion_router
└── tests/
    ├── test_imputacion_motor.py
    └── test_imputacion_endpoints.py

frontend/src/
├── app/imputacion/
│   ├── page.tsx                     # listado de propuestas pendientes/requiereIntervencion
│   └── comparacion/page.tsx         # comparación por Cultivo/Campaña (Historia 5)
├── components/imputacion/
│   ├── PropuestaCard.tsx            # reparto propuesto + trazabilidad + aprobar/corregir
│   └── ComparacionCultivoCampania.tsx
└── services/imputacionApi.ts
```

**Structure Decision**: nuevo feature `backend/src/features/imputacion/`, mismo criterio que los demás dominios de negocio (`src/features/*`). No se toca `src/features/remitos/` (se reutiliza `stock_fifo`/`calcular_stock` importándolos, sin modificarlos); `src/features/ordenes/` se extiende mínimamente para generalizar el vínculo de contratista a N a N, reusando la misma tabla renombrada en vez de agregar una paralela.

## Complexity Tracking

*Sin violaciones.*

## Corrección de rendimiento — 2026-09-24

Las llamadas ODBC, FIFO y Excel del router de imputación se ejecutan mediante `run_in_threadpool`, conservando el lock de check+insert de corridas. Esto permite atender otras peticiones mientras SQL trabaja. Se valida atención concurrente y ausencia de corridas duplicadas. El launcher usa `npm run start` por defecto, con build previo; `-Dev` conserva el arranque de desarrollo. Los fallos de sondeo se registran sin matar procesos; permanece el cierre por inactividad o cierre de pestañas reportados por la API. No cambian contratos ni fórmulas.
