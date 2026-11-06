# Implementation Plan: Vínculo de órdenes de trabajo con documentos del contratista

**Branch**: `main` | **Date**: 2026-11-06 (revisado: simplificación D1) | **Spec**: [spec.md](spec.md)

## Summary

El vínculo se hace en el formulario de Compras, con un panel "Órdenes de trabajo" (lista tildable de las órdenes del contratista) que se guarda con endpoints propios, igual que "Documentos relacionados". Al guardar, se imputa el documento con el motor 017 (reparto por superficie, sin los rubros de insumos y otros negocios) y queda aprobado. Las NC/ND toman las proporciones de su factura cuando se relacionan en el panel existente. La orden de trabajo pasa a mostrar sus documentos en solo lectura. El Resultado por cultivo lee el reparto y excluye de la carga manual exactamente lo repartido. Se suma un listado de facturas de labor sin orden.

## Technical Context

**Language/Version**: Python 3.13 (FastAPI); TypeScript / Next.js

**Primary Dependencies**: FastAPI, pyodbc, openpyxl; Next.js, Tailwind, TanStack Query

**Storage**: WC: `dbo.OrdenesContratistaFacturas` (se agregan usuario, fecha y UNIQUE), `dbo.CompraDocumentosRelacionados` (existente), `dbo.ImputacionPropuestas` (017, sin cambios)

**Testing**: pytest con mocks; `tsc` y lint

**Target Platform / Project Type**: web app local (launcher `LaHerencia.ps1`)

**Performance Goals**: el panel de órdenes carga en menos de 2 s

**Constraints**: saldos iguales al centavo; el reparto cierra al centavo

**Scale/Scope**: 12 contratistas, 152 órdenes, 91 facturas de labor, 6 NC

## Constitution Check

| Principio | Cumplimiento |
|-----------|--------------|
| I/II Datos | Solo WC; DDL mínimo (2 columnas + UNIQUE) con backup verificado previo, en un script re-corrible. |
| III Proceso | El vínculo vive donde se carga el documento (Compras); la orden y el Resultado lo consumen. |
| IV Trazabilidad | Usuario y fecha en el vínculo; el reparto conserva orden, lote, cultivo y campaña; enlaces a `/compras/{id}/editar`. |
| V Contrato | [contracts/api.md](contracts/api.md) antes de la UI; tests de contrato. |
| VII Simplicidad | Sin propuestas guardadas, sin pantalla de revisión, sin tabla de descartes. |
| VIII Stack | Sin cambios. |

**Gate**: PASA.

## Project Structure

```text
backend/
├── scripts/vinculos_contratista_048.py              # backup + ALTER (re-corrible)
├── src/features/ordenes/documentos_contratista.py   # NUEVO: labor, órdenes del contratista, fijar_vinculos, recalcular NC, sin_orden
├── src/features/compras/router.py                   # GET/PUT /api/compras/{id}/ordenes-trabajo; hook al relacionar NC/ND
├── src/features/compras/repository.py               # al agregar/quitar relacionados, recalcular la NC/ND
├── src/features/ordenes/router.py + repository.py   # la orden expone sus documentos (solo lectura); se quitan POST/DELETE factura-contratista
├── src/features/imputacion/motor.py, repository.py  # neto repartible sin rubros excluidos; NC con proporciones de su factura
├── src/features/resultado_cultivo/costos.py, resultado.py  # reparto aprobado; excluye lo repartido; deja la tabla vieja
└── tests/ordenes/, tests/resultado_cultivo/
frontend/src/
├── components/compras/OrdenesTrabajoPanel.tsx       # NUEVO
├── components/compras/CompraForm.tsx                # incluye el panel; aviso "sin orden" al guardar
├── app/produccion/ordenes/[idOrden]/page.tsx        # sección de documentos en solo lectura
├── app/produccion/contratistas/sin-orden/page.tsx   # NUEVO: listado + Excel
└── services/comprasApi.ts, ordenesApi.ts
```

## Complexity Tracking

Sin violaciones.
