# Implementation Plan: Conciliación manual de consumos de tarjeta

**Branch**: `009-conciliacion-tarjetas` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Nota**: este plan se escribe **retroactivamente**. El backend y el frontend ya estaban implementados en commits previos (`b454c23`, `2e3b906`, `6ec8b30`, `fc74311`, entre otros) antes de que existiera `spec.md` formal; no hubo `/speckit-plan` ni `/speckit-tasks` en su momento. Este documento describe la arquitectura tal como quedó construida, verificada de punta a punta el 2026-09-22 (ver `validation.md`).

## Summary

Módulo de conciliación manual: sobre las líneas de consumo de resúmenes de tarjeta (008) que no matchearon solas con Compras, ofrece una bandeja de pendientes y un panel dividido para vincular una o varias líneas con uno o varios documentos (Factura/NC/ND, incluso de proveedores distintos), aceptar una diferencia con motivo, o marcar la línea como "sin documento / no aplica". Un documento en dólares se pesifica con su propio tipo de cambio; la diferencia de cotización contra la tarjeta se cubre con notas `Ajusta Tipo Cambio` del proveedor. Escribe exclusivamente contra `WC`.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript / Next.js (frontend) — mismo stack que el resto del sistema.

**Primary Dependencies**: FastAPI; `backend/src/db/connection.py` (conexión SQL Server existente, forzada contra `WC`); reutiliza `backend/src/features/tarjetas/repository.py` (auto-vínculo de pagos) y las tablas de 008 (`Tarjetas_Resumenes_Cabecera/Lineas`, `Tarjetas_Resumenes_Lineas_Compras`). Frontend: Next.js + TanStack Query + Tailwind, mismo patrón que 010/011/012.

**Storage**: SQL Server, base `WC` exclusivamente. Lee de `Det_Compras`/`Compras` (documentos), `CompraDocumentosRelacionados` (notas de ajuste asociadas a su factura), `Tarjetas_Resumenes_*` (008). Escribe en `Tarjetas_Resumenes_Lineas_Compras` (vínculo línea↔compra, ya existente de 008) y en la tabla nueva de esta feature, `dbo.Tarjetas_Resumenes_Lineas_Estado` (`IdLineaConsumo` PK, `Estado` `SinDocumento`|`DiferenciaAceptada`, `Motivo`, `Detalle` nullable, `ImporteDiferencia` money nullable). El `PUT`/`DELETE` de un resumen (008) recrea sus líneas y por lo tanto borra también sus filas de estado, igual que ya hacía con los vínculos.

**Testing**: pytest para backend — `backend/tests/test_conciliacion_documentos.py` (cálculo puro: pesificación, tolerancia, combinaciones exactas, notas de ajuste) y `backend/tests/test_conciliacion_endpoints.py` (endpoints con `TestClient`, sin tocar `WC`); 21 tests, verde. Verificación manual con datos reales de `WC` documentada en `validation.md`.

**Target Platform**: Aplicación web interna, uso administrativo/contable (quien reconcilia los resúmenes de tarjeta contra Compras cada cierre).

**Performance Goals**: Uso interno sin metas de throughput. La bandeja pagina (25/página por defecto) sobre el universo de líneas pendientes (hoy 281 reales); las sugerencias exactas se calculan en el propio SELECT de `pendientes`, sin N+1.

**Constraints**: Toda escritura exclusivamente contra `WC` (regla de oro del proyecto, ver `.specify/memory/agent-guidance.md`); conciliación exacta en pesos con tolerancia ±$0,10 (ya no se tolera desvío de tipo de cambio); sin auditoría (no se registra quién/cuándo, solo el estado actual, reversible); la bandeja nunca aplica nada sin confirmación explícita del usuario (ni siquiera "aceptar exactas", que muestra vista previa primero).

**Scale/Scope**: 6 historias de usuario (spec.md). Datos reales verificados 2026-09-22: 281 líneas pendientes, 35 con sugerencia exacta previsualizable, 175 documentos marcados `Ajusta Tipo Cambio` (166 NC/ND en pesos de proveedores con facturas en dólares), `CompraDocumentosRelacionados` con 0 filas (ninguna nota vinculada a su factura todavía en datos reales).

## Constitution Check

*Gate re-verificado retroactivamente el 2026-09-22, no antes de la implementación.*

| Principio | Cumplimiento |
|---|---|
| I. SQL Server es el sistema de registro | ✅ Todo pasa por el backend FastAPI existente contra `WC`; no se toca Access. |
| II. Protección de datos reales | ✅ `connection.py` fuerza `WC`; verificado en vivo con `DB_NAME()`. Ninguna escritura contra `LaHerencia`. |
| III. Procesos de negocio, no tablas crudas | ✅ La bandeja y el panel siguen el proceso real de quien concilia: ver pendientes → abrir línea → elegir documento(s) o motivo, no un CRUD de la tabla de estado. |
| IV. Trazabilidad y significado financiero explícito | ✅ Cada vínculo referencia el documento real (`idCompra`, tipo, número, proveedor); el motivo de "sin documento"/"diferencia aceptada" queda explícito; nunca oculta el desvío en dólares (lo muestra como pista). |
| V. Contrato SQL/API primero, con pruebas | ✅ `conciliacion_documentos.py` (cálculo puro) tiene tests unitarios separados de `router.py`/`repository.py` (tests de endpoint). |
| VI. Colaboración de especialistas | ⚠️ No documentado formalmente al momento de la implementación original (no hubo `/speckit-plan`). `spec.md` sí registra hallazgos de datos reales acordados con el usuario el 2026-09-22. |
| VII. Simplicidad y reversibilidad | ✅ Una tabla nueva mínima (`Tarjetas_Resumenes_Lineas_Estado`), reutiliza `Tarjetas_Resumenes_Lineas_Compras` de 008 tal cual; todo vínculo/estado se puede quitar (`DELETE`), verificado en `validation.md`. |
| VIII. Stack aprobado | ✅ Python/FastAPI + SQL Server + Next.js/TypeScript/Tailwind/TanStack Query. |

Sin violaciones bloqueantes. El único desvío de proceso (falta de `/speckit-plan`/`/speckit-tasks` original) es el motivo de este documento retroactivo.

## Project Structure

### Documentation (this feature)

```text
specs/009-conciliacion-tarjetas/
├── spec.md          # Ya existía (2026-09-22)
├── plan.md          # Este archivo (retroactivo)
├── tasks.md          # Retroactivo, todo [X] salvo lo pendiente
├── quickstart.md      # Retroactivo, escenarios de verificación reproducibles
└── validation.md      # Resultado de la verificación end-to-end del 2026-09-22
```

### Source Code (repository root)

```text
backend/
├── src/features/tarjetas_resumenes/
│   ├── router.py                  # Endpoints /api/tarjetas-resumenes (008 + esta feature)
│   ├── repository.py              # get_pendientes, get_candidatos_linea, calcular_conciliacion,
│   │                               #   vincular_compra/_lote, proponer_reparto, conciliar_reparto,
│   │                               #   marcar_sin_documento, quitar_estado, aceptar_exactas, buscar_documentos
│   ├── conciliacion_documentos.py # Cálculo puro: pesificación, tolerancia ±$0.10, combinaciones,
│   │                               #   detección de notas "Ajusta Tipo Cambio" y TC implícito
│   ├── reporte_conciliacion.py    # Export .xlsx (Resúmenes/Conciliación/Pagos/Proveedores sin CUIT/Ayuda)
│   └── schemas.py                 # Pydantic: PendientesResponse, CandidatosLineaResponse,
│                                   #   ConciliacionPreviewResponse, RepartoPropuestaResponse, etc.
└── tests/
    ├── test_conciliacion_documentos.py  # 21 tests (cálculo puro + endpoints) — ver conteo real en validation.md
    └── test_conciliacion_endpoints.py

frontend/src/
├── app/finanzas/tarjetas/conciliacion/page.tsx   # Historia 1: bandeja de pendientes
├── components/tarjetas-conciliacion/
│   ├── BandejaConciliacion.tsx        # Filtros tarjeta/proveedor/período, orden por sugerencia exacta
│   ├── PanelConciliacion.tsx          # Historias 2-6: panel dividido, reparto editable, aceptar
│   │                                   #   diferencia, sin documento, notas de ajuste TC
│   └── BotonExportarConciliacion.tsx  # Historia de exportación (reporte_conciliacion.py)
```

**Structure Decision**: Módulo hermano de `tarjetas_resumenes/` (008), sin paquete backend propio — vive junto al resto de resúmenes de tarjeta porque opera sobre las mismas tablas y el mismo router. Frontend en su propio directorio `tarjetas-conciliacion/`, mismo patrón que 010/011/012. Una sola tabla nueva (`Tarjetas_Resumenes_Lineas_Estado`), sin script de migración de datos (no hay backfill: las líneas históricas simplemente aparecen "pendientes" hasta que alguien las concilia).
