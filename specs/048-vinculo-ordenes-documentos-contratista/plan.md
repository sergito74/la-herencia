# Implementation Plan: Vínculo de órdenes de trabajo con documentos del contratista

**Branch**: `main` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/048-vinculo-ordenes-documentos-contratista/spec.md`

## Summary

Hoy el vínculo orden–documento del contratista no se usa: pide un número interno, no dispara la imputación y el Resultado lee otra tabla. El plan:

1. Reemplaza el campo numérico por una lista tildable de documentos de labor del contratista, con sugerencias.
2. Calcula las propuestas factura→órdenes al vuelo (sin guardarlas) y guarda solo lo confirmado o descartado.
3. Al confirmar, genera y aprueba la imputación con el motor 017, repartiendo por superficie el neto de los renglones que no son insumos. Las NC/ND siguen a su factura.
4. Hace que el Resultado por cultivo lea esa imputación y deje de contar, para esos documentos, la carga manual de sus renglones de labor.

Se suma una pantalla de revisión del histórico por contratista, con el detalle de las facturas "sin orden".

## Technical Context

**Language/Version**: Python 3.13 (backend FastAPI), TypeScript / Next.js (frontend)

**Primary Dependencies**: FastAPI, pyodbc, openpyxl; Next.js, Tailwind, TanStack Query

**Storage**: SQL Server `WC`: `dbo.OrdenesContratistaFacturas` (ampliada), `dbo.OrdenesContratistaDescartes` (nueva), `dbo.ImputacionPropuestas` (017, sin cambios de esquema)

**Testing**: pytest con fixtures/mocks (sin escribir en WC); `tsc`/lint del frontend

**Target Platform**: servidor local Windows (launcher `LaHerencia.ps1`), navegador

**Project Type**: web application (backend + frontend)

**Performance Goals**: la lista de una orden y la revisión de un contratista responden en menos de 2 s (el contratista más grande tiene ~40 órdenes y ~40 facturas)

**Constraints**: saldos de cuentas corrientes iguales al centavo (FR-009); el reparto cierra al centavo (SC-002); nada se vincula sin confirmación (D1)

**Scale/Scope**: 12 contratistas, 152 órdenes ejecutadas, 91 facturas de labor y 6 NC desde 2015

## Constitution Check

| Principio | Cumplimiento |
|-----------|--------------|
| I. WC es la base de registro | Todo se lee y escribe en WC; `LaHerencia` no se toca. |
| II. Protección de datos | Hay DDL (ALTER + tabla nueva): backup verificado de las tablas afectadas antes de aplicarlo, con un script re-corrible con respaldo, como `scripts/contratos_canje_046.py`. Tests con mocks. |
| III. Proceso de negocio | Flujo orden → documentos → reparto → resultado, y revisión por contratista. |
| IV. Trazabilidad | Cada vínculo guarda usuario y fecha; el reparto conserva orden, lote, cultivo y campaña; el Resultado enlaza a la compra (`/compras/{id}/editar`). |
| V. Contrato primero | `contracts/api.md` antes de la UI; tests de contrato de los endpoints. |
| VI. Dominio | Rubros de labor vs. insumos definidos con Sergio (clarify 06/11). |
| VII. Simplicidad | Las propuestas no se persisten; se reutiliza el motor 017 y la tabla de vínculos existente. La tabla vieja `Ordenes_Trabajo_Contratista_Factura` (vacía) deja de leerse. |
| VIII. Stack | Python + SQL Server + Next.js/TS + Tailwind + TanStack Query. |

**Gate**: PASA. Re-chequeado después del diseño: sin cambios.

## Project Structure

### Documentation (this feature)

```text
specs/048-vinculo-ordenes-documentos-contratista/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── facturas-sin-orden-20261106-v2.xlsx   (insumo de la revisión, no versionar)
```

### Source Code

```text
backend/
├── scripts/vinculos_contratista_048.py          # DDL con respaldo, re-corrible
├── src/features/ordenes/
│   ├── documentos_contratista.py                # NUEVO: candidatos, propuestas, confirmar/descartar, reparto
│   ├── repository.py                            # vincular/desvincular → delega en documentos_contratista
│   └── router.py                                # endpoints de la orden y de la revisión
├── src/features/imputacion/motor.py             # evaluar_contratista: neto sin insumos; NC sigue a su factura
├── src/features/resultado_cultivo/costos.py     # contratista desde ImputacionPropuestas aprobadas; excluye carga manual
├── src/features/resultado_cultivo/resultado.py  # deja de leer la tabla vieja
├── src/features/documentos_nuevos/...           # aviso de factura de labor sin orden (FR-008b)
└── tests/ordenes/test_documentos_contratista.py

frontend/src/
├── app/produccion/ordenes/[idOrden]/page.tsx    # lista tildable en lugar del NumberInput
├── app/produccion/contratistas/revision/page.tsx  # NUEVO: revisión por contratista + detalle "sin orden"
├── components/ordenes/DocumentosContratistaPanel.tsx  # NUEVO
└── services/ordenesApi.ts
```

**Structure Decision**: web application existente; el módulo `ordenes` concentra el vínculo y `resultado_cultivo` lo consume.

## Complexity Tracking

Sin violaciones a la Constitución.
