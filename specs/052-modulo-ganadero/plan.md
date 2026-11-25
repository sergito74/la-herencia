# Implementation Plan: Módulo Ganadero

**Branch**: `052-modulo-ganadero` (se trabaja en main; push autorizado) | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)
**Input**: especificación de `specs/052-modulo-ganadero/spec.md`, revisada por los agentes 01–12, más las respuestas de Sergio del 24 y 25/11/2026.

## Summary
Módulo de gestión ganadera con menú propio. La **etapa 1** (esta entrega de tareas) tiene tres partes:
1. **Resultado ganadero por ejercicio**, igual a la planilla histórica de Sergio:
   - ventas (A/B), comercialización, costos imputados (fuente 050 por fracción) y forrajes a costo de producción;
   - ha ganaderas efectivas por meses, MB/ha y EV/ha;
   - los forrajes salen del Resultado de cultivos.
2. **Stock de hacienda por eventos:**
   - importación del stock histórico;
   - movimientos (las ventas generan el suyo solas) y recuentos;
   - existencia por categoría, dueño y campo.
3. **Controles base** con marca "revisado y aceptado": ventas, consignatario, stock, imputación y pastaje.

Quedan para la **etapa 2**: la valuación al cierre (NRV, producción/tenencia) y sanidad (plan, aplicaciones con baja de stock, trabajos veterinarios, observados). Los indicadores de cría van a la **etapa 3**.

## Technical Context
**Language/Version**: Python 3.13 (FastAPI), TypeScript (Next.js App Router)
**Primary Dependencies**: FastAPI, pyodbc, pydantic; Next.js, TanStack Query, Tailwind
**Storage**: SQL Server `WC` (producción). Las tablas nuevas llevan el prefijo `Gan`. Se reusan `[Venta Hacienda]`, `[Det_Ventas Hacienda]`, `[Tipo Hacienda]`, `Establecimientos`, `ImputacionPropuestas`, `TamizRenglones`, `PlanAgricola`, `Ordenes_*`, `Datos Cosecha`, `Lotes`, `[Dolar BNA]`, `Map_CultivoResultado`, `Stock_Bajas`, `ContratosPastaje` y `PastajeLiquidaciones`.
**Testing**: pytest (`backend/tests/ganaderia/`) con datos simulados; contrato de API; `npm run build`/typecheck del frontend.
**Target Platform**: aplicación web local (launcher LaHerencia.ps1); en la etapa 2 también desde el celular (recuento, aplicación).
**Project Type**: web (backend + frontend)
**Performance Goals**: el resultado de 10 ejercicios en < 3 s.
**Constraints**: nada interno en pantalla; formato de números local; respaldo verificado antes del DDL y de la importación; el saldo de las cuentas no cambia.
**Scale/Scope**: unas 150 ventas, unos 500 movimientos por año, 40 lotes y 20 ejercicios.

## Constitution Check
| Principio | Cumplimiento |
|---|---|
| I. WC es la fuente | Todo se lee y escribe en WC. No se toca LaHerencia ni Access. |
| II. Protección de datos | Respaldo antes del DDL `Gan*`, del cambio en `Map_CultivoResultado` y de la importación del stock histórico. Scripts re-corribles que simulan antes de aplicar. Las pruebas no escriben en WC. |
| III. Proceso antes que tablas | Las pantallas siguen el recorrido resultado → rubro → comprobante y stock → movimiento → documento. |
| IV. Trazabilidad | Cada cifra del resultado se abre hasta la fracción o el comprobante. Cada movimiento guarda su fuente (venta, acta, recuento, planilla). Moneda y TC explícitos. |
| V. Contrato primero | Primero `contracts/api-ganaderia.md`, después la UI. Pruebas de contrato y de las reglas (ha efectivas, kg por unidad de medida, fracciones). |
| VI. Especialistas | La spec revisada por 01–12 está en spec.md y propuesta-especialistas. |
| VII. Simplicidad | Se reusan `VIGENTE_050`, `Stock_Bajas`, el FIFO, el componente de la marca, el flujo de caja con filtro, `PlanAgricola`. No hay motores paralelos. |
| VIII. Stack | FastAPI + Next.js + TanStack Query. |

**Gate: PASS.** No hay excepciones.

**Re-check post-diseño: PASS.** El único cambio sobre algo existente es la columna de `Map_CultivoResultado` (FR-004). Se protege con la prueba SC-005 (el costo total no cambia).

## Project Structure
### Documentation
```
specs/052-modulo-ganadero/
├── spec.md, propuesta-especialistas-20261124.md
├── plan.md, research.md, data-model.md, quickstart.md
└── contracts/api-ganaderia.md
```
### Source Code
```
backend/src/features/ganaderia/
├── router.py        # /api/ganaderia/*
├── schemas.py
├── categorias.py    # catálogo, alias, unidad de medida → cabezas/kg (FR-009)
├── resultado.py     # cuadro por ejercicio/campaña (FR-002/003/004/005/012/016)
├── superficie.py    # ha ganaderas efectivas (FR-013)
├── stock.py         # movimientos, existencia, recuentos (FR-006/007)
├── controles.py     # FR-011 + marca aceptada
└── repository.py
backend/scripts/ganaderia_tablas_20261125.py          # DDL Gan* + columna EsGanaderia en Map_CultivoResultado
backend/scripts/ganaderia_stock_historico_20261125.py # importación FR-007 (simula / --aplicar)
backend/tests/ganaderia/
frontend/src/app/ganaderia/{resultado,stock,controles,configuracion}/page.tsx
frontend/src/components/ganaderia/*
frontend/src/components/ui/MarcaRevisado.tsx          # extraído de stock/ControlCierre.tsx
```
**Structure Decision:** feature por módulo, igual que `resultado_cultivo` y `remitos`. Toca código existente en cinco lugares:
- `resultado_cultivo/resultado.py:207-235`: excluye los cultivos con `EsGanaderia`. También `formularios_access.py` (VERDEOS).
- `ventas_hacienda/repository.py`: el alta, la edición y la baja de una venta generan o actualizan el movimiento.
- `flujo_caja/router.py`: agrega el filtro `centroCosto` en `/por-rubro`.
- `NavHeader.tsx`: menú Ganadería.
- `stock/ControlCierre.tsx`: usa `MarcaRevisado`.

## Complexity Tracking
No hay violaciones que justificar.
