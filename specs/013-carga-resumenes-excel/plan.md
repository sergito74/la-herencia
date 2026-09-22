# Implementation Plan: Confirmar la carga de resúmenes bancarios (BNA/Galicia) desde Excel

**Branch**: `013-carga-resumenes-excel` | **Date**: 2026-09-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/013-carga-resumenes-excel/spec.md`

## Summary

Completa la Historia 3 de 003-tesoreria (hoy solo preview de Excel BNA/Galicia, sin persistir) agregando la confirmación real: reprocesar el archivo subido, detectar movimientos duplicados contra lo ya cargado del mismo banco, y persistir solo los nuevos en `WC`, dejando trazabilidad de qué archivo/carga originó cada movimiento vía dos tablas nuevas de infraestructura (`CargasResumenBancario`, `CargasResumenBancario_Movimientos`). Reusa el parseo existente de `excel_import.py` y el componente `CargaExcel.tsx`.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript/Next.js 14 (frontend) — mismo stack que 003/012.

**Primary Dependencies**: FastAPI, `openpyxl` (Galicia), `xlrd` (BNA) — ya presentes, sin dependencias nuevas. Frontend: TanStack Query, componente `CargaExcel.tsx` existente.

**Storage**: SQL Server, base `WC` (única, per constitución). Tablas existentes `Movimientos BNA`/`Movimientos Galicia` (solo `INSERT`, sin cambio de esquema) + 2 tablas nuevas.

**Testing**: `pytest` (backend, mock de `pyodbc`/`connection.py` igual que el resto del proyecto) + `tsc --noEmit` (frontend).

**Target Platform**: Web local (Windows), mismo entorno que el resto del sistema.

**Project Type**: Web application (backend FastAPI + frontend Next.js), extendiendo el feature existente `backend/src/features/tesoreria/`.

**Performance Goals**: confirmar un resumen mensual (cientos de filas) en menos de 5 segundos — no hay requisito de alto volumen (research.md, Assumptions).

**Constraints**: escritura exclusiva contra `WC` (constitución I/II); nunca contra `LaHerencia` ni `.accdb`.

**Scale/Scope**: 2 endpoints nuevos + 1 extensión de endpoint existente + 2 tablas nuevas + extensión de un componente frontend existente.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I/II (WC como working copy)**: ✅ toda escritura nueva es contra `WC`; `LaHerencia`/`.accdb` no se tocan. Las tablas reales `Movimientos BNA`/`Movimientos Galicia` sólo reciben `INSERT`, sin `ALTER`.
- **III (proceso de negocio)**: ✅ completa un proceso ya existente (tesorería, 003) en vez de exponer una tabla nueva aislada.
- **IV (trazabilidad)**: ✅ es el objetivo central de la spec (Historia 4, FR-007/008/009) — cada movimiento importado queda vinculado a su carga y archivo de origen.
- **V (contract-first)**: ✅ contrato en `contracts/carga-resumenes-api.md` antes de implementar; tests de contrato + unitarios de deduplicación antes/junto con el código.
- **VII (simplicidad)**: ✅ reusa `excel_import.py`, `execute_write_transaction` y el patrón de tabla nueva ya usado en 009 (`Tarjetas_Resumenes_Lineas_Estado`) — no se introduce ningún mecanismo nuevo de locking/infraestructura.
- **VIII (stack aprobado)**: ✅ Python/FastAPI + SQL Server + Next.js/TypeScript/TanStack Query, sin nuevas dependencias.

Sin violaciones — no hace falta Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/013-carga-resumenes-excel/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── carga-resumenes-api.md
└── tasks.md              # generado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   └── crear_tablas_carga_resumenes.py   # nuevo, idempotente (patrón de 009)
├── src/features/tesoreria/
│   ├── excel_import.py        # existente, sin cambios en el parseo
│   ├── confirmacion_carga.py  # nuevo: deduplicación + persistencia transaccional
│   ├── repository.py          # extendido: cargas, vínculo movimiento↔carga, idCarga en listados
│   ├── router.py              # extendido: POST /excel/confirmar, POST /excel/previsualizar-confirmacion, GET /{medio}/cargas
│   └── schemas.py             # extendido: schemas de confirmación/resumen/carga
└── tests/
    ├── test_tesoreria_confirmacion_carga.py   # nuevo: deduplicación, conteos, transacción
    └── test_tesoreria_cargas_endpoints.py     # nuevo: contrato de los 3 endpoints

frontend/
├── src/components/tesoreria/
│   └── CargaExcel.tsx         # extendido: paso de confirmación con conteo nuevo/omitido
└── src/services/
    └── tesoreriaApi.ts        # extendido: confirmarCarga, previsualizarConfirmacion, fetchCargas
```

**Structure Decision**: extiende el feature existente `backend/src/features/tesoreria/` (mismo patrón que 003) en vez de crear un feature nuevo — es la continuación directa de esa spec, comparte router, schemas y el parseo de Excel. Un módulo nuevo (`confirmacion_carga.py`) separa la lógica de deduplicación/persistencia del parseo puro (`excel_import.py`), manteniendo cada archivo con una sola responsabilidad.

## Complexity Tracking

*Sin violaciones — sección no aplica.*
