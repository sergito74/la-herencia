# Implementation Plan: Contratos de pastaje

**Branch**: `main` (spec 039) | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/039-contratos-pastaje/spec.md`

## Summary
Módulo de ingresos por pastaje de Giamigli de Bolívar S.A. (establecimiento La Herencia): contratos con tarifas por categoría en kg de novillo, bitácora de hacienda, índice INMAG diario automático (nueva fuente `haciinfo000011`, tabla propia), liquidación mensual a mes vencido con PDF para el cliente, carga de facturas ARCA desde PDF con ND/NC vinculadas, integración con cuenta corriente, cobros, retenciones y consolidado de campaña (julio–junio). Ver [research.md](research.md).

## Technical Context
**Language/Version**: Python 3.13 (backend FastAPI), TypeScript/Next.js (frontend)
**Primary Dependencies**: FastAPI, pyodbc, reportlab, pdfplumber, requests; TanStack Query, Tailwind
**Storage**: SQL Server, base WC (tablas nuevas dbo.*Pastaje*, dbo.IndiceINMAG; rama nueva en vw_MovimientosCuenta_Base; CHECK ampliado)
**Testing**: pytest con pyodbc bloqueado y SQL simulado; lecturas reales de solo lectura; tsc; recorrido UI
**Target Platform**: PC Windows local (launcher), tarea programada de Windows diaria
**Project Type**: web application (backend + frontend)
**Performance Goals**: liquidación y preview < 2 s; actualización INMAG < 30 s
**Constraints**: Decimal sin float; redondeo solo en neto/IVA y precio promedio; escrituras solo WC con respaldo; no tocar gastos de pastaje históricos; IndiceNovillo pasa a solo histórico tras la aprobación de FR-019 (su error de cabezas ya fue corregido el 22/10/2026)
**Scale/Scope**: 1–5 contratos, ~250 índices/año, 12 liquidaciones/contrato/año

## Constitution Check
| Principio | Cumplimiento |
|---|---|
| I. SQL Server sistema de registro | Todo persiste en WC; PDFs referenciados |
| II. Protección de datos reales | Migración aditiva, respaldo COPY_ONLY verificado, guardia WC, gate de totales de la vista |
| III. Procesos antes que tablas | Flujo contrato → bitácora → liquidación → factura → cobro |
| IV. Trazabilidad financiera | Liquidación fijada con índices copiados; ND/NC vinculadas; auditoría por fila |
| V. Contract-first | contracts/api.md; tests de contrato antes de UI |
| VI. Especialistas | Consultados 06, 07, 01/04; revisión 08/09 para UI |
| VII. Simplicidad/reversible | Tablas propias, sin tocar arrendamientos; anulación en vez de borrado |
| VIII. Stack aprobado | Sin dependencias nuevas |
**Gate**: PASS (pre y post diseño).

## Project Structure
```text
specs/039-contratos-pastaje/  plan.md research.md data-model.md quickstart.md contracts/api.md tasks.md
backend/
  scripts/migrar_pastaje_039.py          # DDL + rama de vista + CHECK, con respaldo
  scripts/indice_inmag.py                # corrida diaria (CLI)
  scripts/instalar_indice_inmag.ps1      # tarea programada diaria (+ liquidaciones día 1)
  src/features/pastaje/
    router.py schemas.py repository.py service.py
    calculo.py         # cabezas-día, precio promedio, importes (puro, Decimal)
    inmag.py           # descarga/parseo haciinfo000011
    liquidacion_pdf.py # reportlab
    lector_factura.py  # pdfplumber, factura ARCA emitida
  src/features/aplicaciones_pago/documentos.py   # tipo 'Pastaje'
  src/features/recalculo_fifo/ejecuciones.py     # mapeo origen
  src/features/resultado_cultivo/                # Otros ingresos — Pastaje
  tests/test_pastaje_calculo_039.py tests/test_pastaje_contrato_039.py tests/test_pastaje_inmag_039.py tests/test_pastaje_factura_039.py
frontend/src/
  app/ventas/pastaje/page.tsx, [id]/page.tsx   # Condiciones (lista + ficha con pestañas)
  components/pastaje/*  services/pastajeApi.ts
  components/layout/NavHeader.tsx                 # entrada en menú Ventas
```
**Structure Decision**: web application existente; feature backend propio `pastaje` con cálculo puro testeable.

## Complexity Tracking
Sin violaciones.
