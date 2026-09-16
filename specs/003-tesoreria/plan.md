# Implementation Plan: Tesorería por banco, caja, valores y tarjetas (solo lectura)

**Branch**: `003-tesoreria` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-tesoreria/spec.md`

## Summary

Módulo web de solo lectura para consultar movimientos por medio de tesorería (Banco Nación, Banco Galicia, caja/efectivo, valores, tarjetas), cada uno respetando su propia forma de datos, mostrando la referencia (heurística, no clave directa) hacia la compra que probablemente originó cada movimiento. Incluye una funcionalidad acotada de carga de resúmenes por Excel, limitada a validación y previsualización (sin persistencia). Reutiliza la misma base técnica que compras (`specs/002-compras`): backend FastAPI de solo lectura sobre SQL Server, frontend Next.js/TanStack Query.

## Technical Context

**Language/Version**: Python 3.13 (backend) + TypeScript 5.x / Next.js (frontend) — mismas versiones que `specs/002-compras`

**Primary Dependencies**: FastAPI + Pydantic; pyodbc (DSN `SQL_LaHerencia`); `openpyxl` para Galicia (`.xlsx`) y `xlrd` para BNA (`.xls`, formato binario antiguo — confirmado 2026-09-16 contra archivo real) — validación/previsualización, sin escritura; Next.js, TanStack Query, Tailwind CSS

**Storage**: SQL Server `LaHerencia` (`Movimientos`, `Movimientos BNA`, `Movimientos Galicia`, `Pagos efectivo`, `Valores propios`, `Valores Recibidos`, `Tarjetas`, `Tarjetas_Resumenes`, `Tarjetas_Resumenes_Lineas`), lectura exclusiva; los archivos Excel subidos se procesan en memoria/temporalmente, sin persistir en SQL Server en esta spec

**Testing**: pytest + httpx (contract tests con fixtures); un archivo Excel de ejemplo versionado en `tests/fixtures/` para probar la validación de estructura

**Target Platform**: Igual que compras — aplicación web interna, backend Python + frontend Next.js

**Project Type**: Web application (frontend + backend), extiende la misma base de `specs/002-compras`

**Performance Goals**: Consulta de movimientos por medio percibida como instantánea (SC-001); previsualización de Excel en menos de 1 minuto (SC-004)

**Constraints**: Solo lectura respecto de la base real (FR-010); la carga de Excel NO persiste datos (FR-008); sin uso de columnas de imputación heredadas de los bancos (FR-006); soporte de lectura concurrente (FR-014)

**Scale/Scope**: ~9.400 movimientos BNA (volumen observado en el prototipo) más los demás medios; 6 medios de tesorería distintos, cada uno con su propio modelo de datos

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Resultado |
|---|---|---|
| I. SQL Server es la fuente de verdad | Lee exclusivamente tablas SQL Server existentes por medio de tesorería; el Excel subido no reemplaza SQL Server, solo se previsualiza. | Pass |
| II. Protección de datos reales | Todos los endpoints de consulta son GET; el endpoint de Excel valida/previsualiza sin escribir (FR-008/FR-010). | Pass |
| III. Procesos de negocio antes que tablas | Selección de medio → movimientos → referencia de origen, no una grilla genérica; cada banco respeta su propia forma (FR-002). | Pass |
| IV. Trazabilidad y significado financiero explícito | Deja explícito cuándo la referencia a compra es cierta, ausente o ambigua (FR-004/FR-005), en vez de fingir certeza. | Pass |
| V. Contrato primero, integración probada | Contrato de API definido en Fase 1 antes de UI; contract tests con fixtures, incluido un Excel de ejemplo. | Pass |
| VI. Colaboración de especialistas | Spec y plan construidos con input del agente financiero/administración de cuentas sobre las tablas y su semántica. | Pass |
| VII. Simplicidad y reversibilidad | Reutiliza la base de datos/backend de compras; no introduce persistencia de Excel (se deja explícitamente para una spec futura autorizada). | Pass |
| VIII. Stack aprobado | Mismo stack aprobado que compras, sin frameworks nuevos fuera de `openpyxl` (librería de lectura, no un framework alternativo). | Pass |

No hay violaciones que requieran justificación.

*Re-chequeo post-Fase 1 (2026-09-15): `data-model.md`, `contracts/tesoreria-api.md` y `quickstart.md` mantienen el módulo en solo lectura, sin escritura de Excel, y con la ambigüedad de coincidencia explícita en el contrato (no oculta). Los 8 principios siguen en Pass.*

## Project Structure

### Documentation (this feature)

```text
specs/003-tesoreria/
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
│   │   └── connection.py         # Reutilizada de specs/002-compras, sin cambios
│   ├── features/
│   │   ├── compras/               # Ya definido en specs/002-compras
│   │   └── tesoreria/
│   │       ├── router.py          # Endpoints FastAPI de tesorería (por medio + excel preview)
│   │       ├── repository.py      # Consultas por medio (BNA, Galicia, efectivo, valores, tarjetas)
│   │       ├── matching.py        # Heurística de coincidencia movimiento↔compra (IdContacto+fecha+importe)
│   │       ├── excel_import.py    # Parseo/validación de Excel (openpyxl), sin persistencia
│   │       └── schemas.py         # Modelos Pydantic
│   └── main.py
└── tests/
    └── contract/
        ├── test_tesoreria_api.py
        └── fixtures/
            └── resumen_ejemplo.xlsx

frontend/
├── src/
│   ├── app/
│   │   └── tesoreria/             # Selector de medio, listado de movimientos, carga de Excel
│   ├── components/
│   │   └── tesoreria/
│   └── services/
│       └── tesoreriaApi.ts
└── tests/
```

**Structure Decision**: Extiende la misma app `backend/` y `frontend/` creada para compras, agregando `features/tesoreria/` sin duplicar `db/connection.py`. La heurística de coincidencia queda aislada en `matching.py` para que sea reemplazable si en el futuro aparece una clave directa (evita esparcir esa lógica en el router).

## Complexity Tracking

*(Sin violaciones que justificar — tabla vacía.)*
