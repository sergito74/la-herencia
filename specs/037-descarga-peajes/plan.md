# Implementation Plan: Descarga y carga automática de comprobantes de peajes

**Branch**: `037-descarga-peajes` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/037-descarga-peajes/spec.md`

## Summary

El script `backend/scripts/descargar_peajes.py` (commit 663a8ba) pasa a ser un módulo del backend, `features/descarga_peajes`, que baja comprobantes de TelepeajePlus, TelePASE, CEAMSE y AUBASA. Lee cada PDF con un lector por formato y lo carga solo en Compras con `create_compra`, siempre que lo leído cierre contra el total impreso y no esté duplicado. Cada ejecución, cada portal y cada documento quedan registrados en `WC`. Se dispara desde el botón "Descargar ahora" de la nueva pantalla Compras › Descarga de peajes, en un hilo en segundo plano, o desde la tarea semanal de Windows (mismo servicio, origen `semanal`). Un lock de SQL Server impide dos ejecuciones simultáneas. El menú muestra un contador de pendientes y errores. Detalle en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13 (backend/.venv); TypeScript (Next.js 14)

**Primary Dependencies**: FastAPI, pyodbc, pdfplumber (existentes); **nuevas**: playwright (usa el Chrome instalado), keyring. Frontend: TanStack Query, Tailwind

**Storage**: SQL Server `WC`: 3 tablas nuevas `DescargaPeajes_*`; escribe compras en `dbo.Compras`/`Det_Compras` a través del repositorio existente. PDFs en la carpeta de Dropbox de Compras

**Testing**: pytest (lectores contra PDFs reales leídos de Dropbox, skip si faltan, nunca versionados; contratos de API con servicio y repositorio simulados); `npm run build` / `tsc` para el frontend

**Target Platform**: PC de Sergio (Windows 11) — backend local lanzado por `launcher/LaHerencia.ps1` y tarea programada de Windows

**Project Type**: Web app (backend FastAPI + frontend Next.js)

**Performance Goals**: descarga completa de los 4 portales en < 5 min (SC-001); polling del avance cada 2 s

**Constraints**: solo lectura en los portales; las credenciales nunca salen del Administrador de credenciales de Windows; una sola ejecución a la vez; respaldo verificado antes de crear el esquema; cerrar exacto (±$0,05) para cargar

**Scale/Scope**: unos 6 a 10 documentos por mes; 1 usuario

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
| --- | --- |
| I. WC sistema de registro | ✅ Registro y compras en `WC`; no toca `LaHerencia` ni Access |
| II. Protección de datos | ✅ Respaldo verificado antes del DDL; las compras se crean con el repositorio y las validaciones del alta; la carga solo se hace si el total cierra y no hay duplicado; los tests no escriben en `WC` |
| III. Proceso de negocio | ✅ Pantalla dentro de Compras: descargar → ver resultado → ir a la compra o cargar lo pendiente |
| IV. Trazabilidad | ✅ Documento ↔ ejecución ↔ compra (`IdCompra`), PDF como documento original, motivo de cada pendiente |
| V. Contrato primero | ✅ [contracts/api.md](contracts/api.md) antes de la UI; tests de lectores y de API |
| VI. Especialistas | ✅ Criterios de carga tomados de las cargas manuales reales (finanzas/administración); revisión de checkpoint con el agente de dirección financiera antes del merge |
| VII. Simplicidad / reversible | ✅ Hilo + polling, sin colas; `--revertir` del esquema; sin columnas nuevas en tablas existentes; credenciales fuera del repo |
| VIII. Stack aprobado | ✅ Python/FastAPI/SQL Server/Next.js/TS/Tailwind/TanStack Query. Playwright y keyring son librerías de Python de backend, no otro framework |
| Seguridad | ✅ Las credenciales no se guardan ni se loguean; `estado` solo expone booleanos; el `POST` está bloqueado para el rol `Lectura` |

Excepción de política registrada: el acceso a los 4 portales externos fue autorizado explícitamente por Sergio el 2026-10-16 (doble confirmación), solo para leer y descargar.

**Re-check post-diseño**: sin violaciones; Complexity Tracking vacío.

## Project Structure

### Documentation (this feature)

```text
specs/037-descarga-peajes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── requirements.txt                         # + playwright, keyring
├── scripts/
│   ├── crear_esquema_descarga_peajes_037.py # DDL idempotente + respaldo + --revertir + --importar-manifiesto
│   ├── descargar_peajes.py                  # queda como entrada CLI: --origen semanal, --dry-run
│   └── instalar_descarga_peajes.ps1         # usa .venv y --origen semanal
├── src/features/descarga_peajes/
│   ├── portales.py      # login y listado por portal (código actual) + mapeo de proveedores
│   ├── lectores.py      # un lector de PDF por formato → datos de compra
│   ├── carga.py         # validación de cierre, duplicados y create_compra
│   ├── servicio.py      # ejecutar(origen, usuario): lock, portales, registro
│   ├── repository.py    # tablas DescargaPeajes_*, revalidación de pendientes
│   ├── configuracion.py # credenciales (solo existencia) y estado de la tarea (schtasks)
│   ├── schemas.py
│   └── router.py        # /api/descarga-peajes/*
├── src/main.py                              # include_router
└── tests/
    ├── fixtures/peajes/                     # casos.json; los PDFs se leen de Dropbox (no se versionan: datos personales)
    ├── test_descarga_peajes_lectores.py
    └── contract/test_descarga_peajes_api.py

frontend/src/
├── app/compras/descarga-peajes/page.tsx
├── components/descarga-peajes/              # EstadoConfiguracion, EjecucionEnCurso, Historial, DocumentosLista
├── services/descargaPeajesApi.ts
├── components/layout/NavHeader.tsx          # Compras con submenú + contador
└── app/compras/nueva/page.tsx               # acepta ?documentoOriginal=
```

**Structure Decision**: Web app con la estructura existente, un módulo nuevo por feature en `backend/src/features/` y rutas/componentes/servicios en `frontend/src/`, igual que los módulos 030–036.

## Complexity Tracking

Sin violaciones.
