# Implementation Plan: Backfill de boletas de impuestos faltantes

**Branch**: `029-backfill-boletas-impuestos` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary

Agregar diagnóstico y propuesta revisable desde Impuestos, primero con comprobantes reales y luego con boletas generadas desde pagos. Todo el histórico; una boleta por pago totalmente descubierto; tipo genérico por organismo cuando no pueda inferirse. Las tres decisiones del usuario permanecen vigentes.

Crear boletas en `dbo.Impuestos` y registrar procedencia/lotes/vínculos documentales en tablas propias. Estos vínculos NO agregan movimientos contables: el pago ya existe. Reutilizar la transacción común de conciliación e incorporar los vínculos al saldo documental compartido de Tesorería/Tarjetas. No reutilizar AplicacionesPago (no soporta Impuestos).

## Technical Context

**Language/Version**: Python 3.13 y TypeScript 5.x (dependencias existentes).
**Primary Dependencies**: FastAPI, Pydantic, pyodbc; Next.js 14, React 18, Tailwind 3, TanStack Query 5.
**Storage**: SQL Server `WC` (producción); documentos locales existentes, sin copiarlos ni modificarlos.
**Testing**: pytest con fixtures/mocks, contratos HTTP autenticados, TypeScript y validación SQL de solo lectura. No pruebas de escritura sobre datos reales.
**Target Platform**: Windows, backend local y navegador.
**Project Type**: aplicación web existente.
**Performance Goals**: revisión por organismo en menos de 10 minutos (SC-005); paginación 50/200, máximo 200 pagos por confirmación, recorrido documental acotado y cancelable.
**Constraints**: backup verificado antes de DDL/carga/reversión; revisión humana de propuesta exacta; sin OCR; sin Access ni escrituras en LaHerencia; importes Decimal a centavos; no instalar dependencias.
**Scale/Scope**: seis organismos actuales; histórico completo desde 2010. Las cifras del adjunto son antecedentes, no inventario definitivo. WC se consultó solo para metadatos, vista y saldos agregados.

## Constitution Check

| Principio | Antes de investigación / después del diseño |
|---|---|
| I–II | Cumple: WC única base operativa; ninguna escritura en esta fase; respaldo verificado exigido para ejecución posterior. |
| III–IV | Cumple: diagnóstico → documento → revisión → confirmación; identidad del pago y origen histórico conservados; diferencia contable explícita. |
| V | Cumple a nivel diseño: esquema vigente leído en WC y contratos definidos; pruebas y validación funcional son puertas de implementación pendientes. |
| VI | Cumple: revisión especializada delegada de respaldo, tolerancias, integridad y reversión; decisiones incorporadas en research. |
| VII–VIII | Cumple: módulo acotado, stack existente, transacción común, reversión selectiva; sin nuevas dependencias. |

No excepciones constitucionales. Se actualiza agent-guidance para reflejar el corte ya aprobado en Constitución 1.4.0. No se cambia esa Constitución.

## Project Structure

Documentos: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md`, `checklists/requirements.md`. `tasks.md` contiene 39 tareas pendientes, organizadas por historia.

Rutas previstas:

- `backend/src/features/backfill_impuestos/{router,schemas,repository,diagnostico,propuesta,documentos}.py`: API, motor puro, lectura documental y confirmación.
- `backend/scripts/crear_tablas_backfill_impuestos.py`: migración idempotente con preflight y respaldo verificado, sin ejecución implícita al arrancar.
- `backend/src/features/impuestos/`: extender listado, filtros y metadatos; conservar GET existentes.
- `backend/src/features/conciliacion_tesoreria/documentos.py`: saldo compartido con vínculos 029; regresión de consumidores Tesorería y Tarjetas.
- `backend/src/features/cuentas_corrientes/`: enriquecer filas Impuestos con marca visible sin alterar importes ni vista SQL.
- `backend/src/main.py`: montar router usando autenticación y control de rol actuales.
- `frontend/src/app/finanzas/impuestos/backfill/page.tsx`, `frontend/src/components/impuestos/`, `frontend/src/services/backfillImpuestosApi.ts`: flujo por organismo y revisión por lotes.
- `backend/tests/test_backfill_impuestos_*.py`, `backend/tests/contract/test_backfill_impuestos_api.py`: verificaciones focalizadas futuras.

## Secuencia de implementación

1. Diagnóstico puro y consultas: inventariar todos los medios, identidad canónica, signo, respaldos y explicación del saldo. No crear deuda para resolver discrepancias.
2. Inventario documental: raíces permitidas Impuestos/Compras, alias explícitos de organismos y fecha; deduplicar archivos; diferenciar búsqueda completa de interrumpida.
3. Propuesta sin persistencia: reservas globales de capacidad, exclusiones, correcciones, selección manual de candidatos documentales, tipo genérico simbólico y vista previa exacta con huella del conjunto. Emitir preparación firmada para obtener respaldo local verificable por GET /respaldo antes de confirmar; las correcciones invalidan esa preparación.
4. Esquema aditivo y catálogo genérico: preparar migración y reversión, probar con conexiones simuladas y revisar antes de ejecutar en WC con backup.
5. Confirmación atómica e idempotente, integración del saldo documental y auditoría; corrección de tipo, adjunto posterior y reversión protegida.
6. UI, contratos, estados vacíos/error, regresión y pruebas focalizadas. Construir propuesta real de solo lectura para revisión del usuario antes de carga.

## Complexity Tracking

No desviaciones. Las tablas propias de vínculo son necesarias porque `ConciliacionesTesoreria` genera créditos en la vista y duplicaría pagos ya registrados. No se agrega un segundo libro contable.
