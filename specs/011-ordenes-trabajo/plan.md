# Implementation Plan: Órdenes de Trabajo

**Branch**: `011-ordenes-trabajo` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-ordenes-trabajo/spec.md`

## Summary

Migrar el módulo Órdenes de Trabajo (Access `FrmOrdenTrabajo` + `FrmAsignarInsumoACultivos`) a la web app sobre `WC`, como continuación directa de Remitos (010). Una orden se planifica antes de ejecutarse: cabecera (fecha, tipo de labor, contratista o maquinaria propia), renglones de insumo con su cantidad total, y renglones de distribución por Lote/Cultivo/Campaña con dosis/ha, que deben cerrar exactamente contra lo retirado. Al guardar se descuenta stock por FIFO (reutilizando el costeo de Remitos) y se emite un Formulario de Retiro con numeración propia. El costo de insumos, maquinaria propia (cargada a mano por orden) y contratistas (vía su factura de Compras) se imputa a Cultivo/Campaña y se conecta con el motor de costeo heredado (`vw_ResultadoCultivo_Campaña` y vistas relacionadas) para poder consultar el costo total por Cultivo/Campaña.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript / Next.js (frontend) — mismo stack que el resto del sistema.

**Primary Dependencies**: FastAPI (backend), Next.js + TanStack Query + Tailwind CSS (frontend); `pyodbc`/conexión SQL Server ya existente en `backend/src/db/connection.py`; reutiliza `backend/src/features/remitos/stock_fifo.py`, `stock_datos.py` y `costeo.py` de 010-remitos sin modificarlos (solo se importan sus funciones).

**Storage**: SQL Server, base `WC` exclusivamente (nunca `LaHerencia`). Tablas heredadas de solo lectura: `Ordenes`, `Ordenes_Detalles`, `Ordenes_Detalles_Distrib`, `Ordenes_Lotes`, `Lotes`, `Cultivos`, `Campañas`, `Tipo Labores`, `Contactos`, `Map_Rubro_TipoLabor`. Tablas nuevas: ver Phase 1 / `data-model.md`.

**Testing**: pytest para backend (contra datos de solo lectura o fixtures, nunca escritura real sin autorización), verificación de compilación TypeScript/Next build para frontend, igual que 010-remitos (`backend/tests/test_remitos_api.py`, `test_stock_fifo.py` como referencia de patrón).

**Target Platform**: Aplicación web interna (oficina, escritorio), mismo público que Remitos — sin requerimiento de uso táctil de campo (decidido en clarificación: administración carga la orden).

**Project Type**: Web application (backend FastAPI + frontend Next.js), feature dentro del monorepo existente.

**Performance Goals**: Sin metas especiales de throughput (uso interno, decenas de órdenes/mes); listar y calcular el costo de una orden debe responder en tiempos de UI interactivos (<2s) igual que Remitos.

**Constraints**: Toda escritura exclusivamente contra `WC` (Principio I/II de la constitución); no modificar vistas/tablas heredadas, solo leerlas o reemplazarlas por consultas propias cuando su convención (ej. signo de `vw_Cns_TotalesOrdenesPorProducto`) no sea confiable; reutilizar `Unidades_Medida`/`Producto_Unidad` de 010-remitos sin crear un catálogo de unidades nuevo.

**Scale/Scope**: 153 órdenes históricas a migrar, 820 renglones de insumo, 4.319 renglones de distribución, 40 lotes, 11 cultivos, 32 campañas, 21 contratistas. Alcance funcional: 7 historias de usuario (spec.md), todas P1 salvo dos P2 (órdenes sin cultivo, administración de catálogo de labores).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|---|---|
| I. SQL Server es el sistema de registro | ✅ Toda la lógica nueva lee/escribe `WC` vía el backend Python existente; no se usa Access ni `.accdb`. |
| II. Protección de datos reales | ✅ Fase de diseño y migración son de solo lectura hasta backup verificado y autorización explícita (igual que 010-remitos); los scripts de migración son idempotentes. |
| III. Procesos de negocio, no tablas crudas | ✅ Las pantallas siguen el proceso real: planificar orden → repartir por lote/dosis → retirar insumo → devolver sobrante → costo por Cultivo/Campaña, no un CRUD de `Ordenes`. |
| IV. Trazabilidad y significado financiero explícito | ✅ Cada costo (insumo, maquinaria, contratista) expone su origen (capa FIFO, orden, factura) y su fecha/moneda/TC, igual que Remitos. |
| V. Contrato SQL/API primero, con pruebas | ✅ Se define `data-model.md` y `contracts/` antes de UI; se reutilizan las funciones FIFO ya probadas en `test_stock_fifo.py`. |
| VI. Colaboración de especialistas | ✅ Ya ejecutada: sesión de 30 preguntas con los 5 agentes especialistas + 4 preguntas de clarificación adicionales, todas resueltas en `spec.md`. |
| VII. Simplicidad y reversibilidad | ✅ Reutiliza el costeo FIFO y las tablas de unidades existentes en vez de duplicarlas; nuevas tablas siguen el patrón de scripts idempotentes de 010-remitos. |
| VIII. Stack aprobado | ✅ Python/FastAPI + SQL Server + Next.js/TypeScript/Tailwind/TanStack Query, sin introducir otra tecnología. |

Sin violaciones. No aplica Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/011-ordenes-trabajo/
├── plan.md              # Este archivo
├── research.md           # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/            # Fase 1 (contratos de API)
└── tasks.md              # Fase 2 (/speckit-tasks, no generado por /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   ├── crear_tablas_ordenes.py        # Tablas nuevas en WC (idempotente, como crear_tablas_remitos.py)
│   ├── indices_ordenes.py             # Índices/PK en tablas heredadas sin tocar datos (como indices_remitos.py)
│   └── migrar_ordenes.py              # Migración de datos heredados (153 órdenes) + unificación de unidades y contratista
├── src/features/ordenes/
│   ├── __init__.py
│   ├── schemas.py          # Pydantic: OrdenIn, RenglonIn, DistribIn, DevolucionIn, MaquinariaIn, AnularIn
│   ├── repository.py       # Alta/edición/anulación de orden, consumo FIFO (usa remitos.stock_fifo), devoluciones
│   ├── distribucion.py     # Cálculo dosis/ha × superficie, validación de cierre exacto (FR-004)
│   ├── costeo.py           # Costo de insumo (FIFO), maquinaria propia (manual) y contratista (factura + TC BNA)
│   ├── resultado.py        # Conexión con vistas heredadas de costeo por Cultivo/Campaña (vw_ResultadoCultivo_Campaña, etc.)
│   ├── formulario_retiro.py # Numeración secuencial y export del Formulario de Retiro
│   ├── exportacion.py      # Export a Excel de listados y costo por Cultivo/Campaña
│   └── router.py           # Endpoints /api/ordenes
├── src/main.py              # Registrar ordenes_router
└── tests/
    ├── test_ordenes_api.py
    └── test_distribucion.py

frontend/src/
├── app/produccion/ordenes/
│   ├── page.tsx
│   ├── nuevo/page.tsx
│   ├── [idOrden]/page.tsx
│   ├── [idOrden]/editar/page.tsx
│   └── resultado-cultivo/page.tsx      # Historia 6: costo por Cultivo/Campaña
├── components/ordenes/
│   ├── OrdenForm.tsx                   # Cabecera + selección contratista/maquinaria propia
│   ├── DistribucionLotesPanel.tsx      # Selección de lotes, dosis/ha, cultivo/campaña por renglón
│   ├── OrdenesListado.tsx
│   ├── EstadosOrden.tsx                # Planificada / Ejecutada / Anulada
│   ├── DevolucionPanel.tsx
│   ├── FormularioRetiroView.tsx
│   ├── TipoLaborAdmin.tsx              # Historia 7: alta de tipos de labor
│   └── ResultadoCultivoListado.tsx
├── services/ordenesApi.ts
└── components/layout/NavHeader.tsx      # Agregar "Órdenes de Trabajo" al submenú Producción
```

**Structure Decision**: Se replica exactamente el patrón de módulo de `backend/src/features/remitos/` y `frontend/src/components/remitos/` (ya validado y en producción), agregando un módulo hermano `ordenes/` en backend y `ordenes/` en frontend, dentro del mismo submenú "Producción" del nav. `ordenes/costeo.py` importa (no duplica) las funciones FIFO de `remitos/stock_fifo.py` y `remitos/stock_datos.py`.

## Complexity Tracking

*Sin violaciones de la constitución; sección no aplica.*
