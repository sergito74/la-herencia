# Implementation Plan: Ventas de Hacienda (alta) y Ventas de Granos (lectura + alta)

**Branch**: `007-ventas-hacienda-granos` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-ventas-hacienda-granos/spec.md`

## Summary

Dos features de escritura nuevas, extendiendo la infraestructura probada de `006-carga-compras`: (1) alta/edición/eliminación de **Ventas de Hacienda** (extiende el módulo de solo lectura de `005-egresos-y-ventas-menores`, cabecera `Venta Hacienda` + detalle `Det_Ventas Hacienda` con comprador independiente por línea + vencimientos con importe propio `Vencimientos Ventas`); (2) **Ventas de Granos** desde cero (lectura + alta/edición/eliminación, cabecera única `Venta Granos` sin tabla de líneas, con subformularios de ajustes/deducciones). Ambas escriben exclusivamente contra `WC`. Reutiliza al máximo lo ya construido en 006: `execute_write_transaction`, patrón de bloqueo de edición (TTL corto + "forzar"), `ContactoSelect` con filtro por tipo real, documentos relacionados con búsqueda acotada, listados vacíos por defecto con filtros/orden/página en la URL, y CORS con `PUT`/`DELETE` ya corregido.

## Technical Context

**Language/Version**: Python 3.13 (backend) + TypeScript 5.x / Next.js (frontend) — mismas versiones que `specs/002-006`

**Primary Dependencies**: FastAPI + Pydantic; pyodbc (DSN `SQL_LaHerencia`); Next.js, TanStack Query, Tailwind CSS. Sin dependencias nuevas.

**Storage**: SQL Server, base `WC` únicamente para escritura — `dbo.[Venta Hacienda]`, `dbo.[Det_Ventas Hacienda]`, `dbo.[Vencimientos Ventas]`, `dbo.[Tipo Hacienda]`, `dbo.Establecimientos`, `dbo.[Tipo Documento]`, `dbo.Contactos` (todas ya existentes, sin cambios de estructura); `dbo.[Venta Granos]`, `dbo.[Venta Granos_Ajustes]`, `dbo.[Venta Granos_Deducciones]`, `dbo.[Venta Granos_ConceptosDeducciones]`, `dbo.Granos` (ya existentes, nunca antes usadas por la app). Tablas nuevas en `WC`: `dbo.VentaHaciendaEditLocks`, `dbo.VentaGranosEditLocks`, `dbo.VentaDocumentosRelacionados` (mismo patrón que `CompraEditLocks`/`CompraDocumentosRelacionados` de 006).

**Testing**: pytest + httpx (contract tests con fixtures, mismo patrón que `test_compras_*.py`, duplicado por dominio: `test_ventas_hacienda_*.py`, `test_ventas_granos_*.py`).

**Target Platform**: Igual que el resto de la app — backend Python + frontend Next.js, uso interno del equipo administrativo.

**Project Type**: Web application (frontend + backend). Extiende `specs/005-egresos-y-ventas-menores` (feature `ventas_hacienda`, agrega escritura) y crea un feature nuevo `ventas_granos` (nunca existió, ni lectura ni escritura).

**Performance Goals**: Alta de una venta de hacienda completa (cabecera + 1 línea) en menos de 2 minutos de interacción de usuario (SC-001); guardado (llamada a la API) en menos de 2s para una venta típica.

**Constraints**: Toda escritura exclusivamente contra `WC` (FR-008, FR-013); advertencia no bloqueante ante documento duplicado, nunca bloqueo duro (FR-009a, FR-012a — decisión Q3, distinto del bloqueo duro de Compras); bloqueo pesimista de edición con TTL de 5 minutos y opción de "forzar" (FR-006, lección de 006); `Campaña` de Granos es texto libre, no combo cerrado (research.md §3); columnas de significado ambiguo de Granos se capturan tal cual, sin fusionar ni descartar (FR-012, decisión Q2).

**Scale/Scope**: Volumen bajo-medio. Hacienda ya tiene precedente (005 leyó el histórico completo); Granos nunca fue leído — el volumen real se confirma en el Escenario 6/9 del quickstart antes de asumir paginación agresiva.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Resultado |
|---|---|---|
| I. SQL Server es la fuente de verdad | Usa las tablas reales de `Venta Hacienda`/`Det_Ventas Hacienda`/`Vencimientos Ventas`/`Venta Granos` y sus subformularios, todas confirmadas por `INFORMATION_SCHEMA`/`sys.foreign_keys` reales (research.md); agrega solo tablas de infraestructura de bloqueo/vínculo, no un almacén paralelo de datos de negocio. | Pass |
| II. Protección de datos reales | Toda escritura pasa por `execute_write_transaction` (ya existente, `_assert_target_is_wc`); `LaHerencia` permanece de solo lectura. No se ejecutó ningún INSERT/UPDATE/DELETE/DDL durante la investigación de esta fase (solo SELECT contra `INFORMATION_SCHEMA`/`sys.foreign_keys`/muestras). | Pass |
| III. Procesos de negocio antes que tablas | El flujo de alta sigue el proceso real: seleccionar consignatario → cargar cabecera fiscal → cargar líneas con comprador propio (Hacienda) o ajustes/deducciones (Granos) → cargar vencimientos → guardar, replicando la secuencia de los formularios Access reales inspeccionados (`Frm Venta Hacienda`, `Frm Venta Granos`), no una grilla CRUD genérica. | Pass |
| IV. Trazabilidad y significado financiero explícito | Cabecera y detalle distinguen explícitamente subtotal, IVA, retenciones, deducciones, importe neto; vencimientos quedan trazables a su venta vía `IdVenta`. Las columnas de significado ambiguo de Granos (`Grado Operacion`/`Grado Mercaderia`) se documentan explícitamente como no confirmadas, en vez de presentarlas como certeza. | Pass |
| V. Contrato primero, integración probada | Contrato de API definido en Fase 1 (`contracts/ventas-api.md`) antes de tocar el frontend; contract tests para alta/edición/eliminación/bloqueo antes de cerrar cada dominio. | Pass |
| VI. Colaboración de especialistas | Alcance y reglas de negocio confirmados por consulta a los 10 agentes especialistas del proyecto en `/speckit-specify` (proceso, producción agrícola, sanidad ganadera, dirección financiera, arquitectura de producto, nomenclatura, ingeniería SQL/frontend/Python, administración de cuentas) más inspección read-only real de Access. | Pass |
| VII. Simplicidad y reversibilidad | Extiende el feature `ventas_hacienda` existente (005) en vez de duplicarlo; `ventas_granos` es nuevo porque el dominio nunca existió, no por preferencia de diseño. Reutiliza `execute_write_transaction`/`ContactoSelect`/patrón de locks de 006 sin reinventar mecanismos. Se evaluó y descartó una tabla de locks genérica multi-entidad por ahora (research.md §5) — más simple mantener el patrón ya probado replicado, que refactorizar 006 al mismo tiempo. | Pass |
| VIII. Stack aprobado | Mismo stack (FastAPI/SQL Server/Next.js/TypeScript/Tailwind/TanStack Query), sin dependencias nuevas. | Pass |

No hay violaciones que requieran justificación.

*Re-chequeo post-Fase 1 (2026-09-17): `data-model.md` confirma que las únicas tablas nuevas son de infraestructura (`VentaHaciendaEditLocks`, `VentaGranosEditLocks`, `VentaDocumentosRelacionados`), sin datos de negocio propios. `contracts/ventas-api.md` reutiliza exactamente el mismo patrón de headers/status codes que `compras-alta-api.md` (006). Los 8 principios siguen en Pass.*

## Project Structure

### Documentation (this feature)

```text
specs/007-ventas-hacienda-granos/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ventas-api.md
└── tasks.md          # generado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── db/
│   │   └── connection.py              # sin cambios — execute_write_transaction ya existe (006)
│   └── features/
│       ├── ventas_hacienda/           # feature existente (005), se extiende con escritura
│       │   ├── schemas.py             # + VentaHaciendaAltaRequest/EditRequest/LineaInput/VencimientoInput/LockResponse
│       │   ├── repository.py          # + create_venta/update_venta/delete_venta/validaciones referenciales
│       │   ├── repository_locks.py    # nuevo: mismo patrón que compras/repository_locks.py
│       │   └── router.py              # + POST/PUT/DELETE /api/ventas-hacienda, lock endpoints, documento-local
│       └── ventas_granos/             # feature nuevo — nunca existió ni lectura ni escritura
│           ├── schemas.py             # VentaGranosResponse/AltaRequest/EditRequest/AjusteInput/DeduccionInput/LockResponse
│           ├── repository.py          # search_ventas/get_detalle/create_venta/update_venta/delete_venta
│           ├── repository_locks.py    # mismo patrón que ventas_hacienda/repository_locks.py
│           └── router.py              # GET/POST/PUT/DELETE /api/ventas-granos, lock endpoints
└── tests/
    └── contract/
        ├── test_ventas_hacienda_alta_api.py   # nuevo
        ├── test_ventas_hacienda_list.py       # existente (005), sin cambios de contrato de lectura
        └── test_ventas_granos_api.py          # nuevo (lectura + escritura, dominio nunca testeado)

frontend/
├── src/
│   ├── components/
│   │   ├── ventas-hacienda/
│   │   │   ├── VentasHaciendaListado.tsx      # existente (005), + botón "+ Nueva venta de hacienda"
│   │   │   ├── VentaHaciendaForm.tsx          # nuevo: alta/edición, línea con ContactoSelect embebido (comprador)
│   │   │   └── (reusa DocumentosRelacionadosPanel de compras/, generalizado o duplicado según research)
│   │   └── ventas-granos/
│   │       ├── VentasGranosListado.tsx        # nuevo
│   │       └── VentaGranosForm.tsx            # nuevo: cabecera + ajustes + deducciones (sin grilla de líneas)
│   ├── services/
│   │   ├── ventasHaciendaApi.ts                # + crearVenta/actualizarVenta/eliminarVenta/lock
│   │   └── ventasGranosApi.ts                  # nuevo
│   ├── lib/
│   │   └── documentoLocal.ts                   # reuso tal cual, sin duplicar (contracts/ventas-api.md, sección Transversal)
│   ├── components/layout/
│   │   └── NavHeader.tsx                       # "Ventas" pasa a tener submenu Hacienda/Granos (research.md §8)
│   └── app/
│       └── ventas/
│           ├── hacienda/
│           │   ├── page.tsx                    # existente, + botón alta
│           │   ├── nueva/page.tsx               # nuevo
│           │   └── [idVenta]/editar/page.tsx    # nuevo
│           └── granos/
│               ├── page.tsx                    # nuevo
│               ├── nueva/page.tsx               # nuevo
│               └── [idVenta]/editar/page.tsx    # nuevo
```

**Structure Decision**: Se extiende el feature `ventas_hacienda` ya existente (backend `backend/src/features/ventas_hacienda/`, frontend `frontend/src/components/ventas-hacienda/` + `frontend/src/app/ventas/hacienda/`) para el dominio conocido, y se crea `ventas_granos` como feature nuevo porque el dominio nunca existió en el sistema — no es una decisión de arquitectura, es un hecho: no hay nada que extender. Ambos features son independientes entre sí (no comparten repository/router), pero comparten el mismo patrón de infraestructura (locks, transacciones, documentos relacionados) copiado de `compras/` — evaluado en research.md §5 y descartado unificarlos en un mecanismo genérico por ahora (principio VII: la duplicación acotada de un patrón ya probado es más simple que una abstracción nueva a mitad de dos features).

## Complexity Tracking

*No hay violaciones de la Constitution Check que requieran justificación.*
