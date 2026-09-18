# Implementation Plan: Tarjetas de Crédito

**Branch**: `008-tarjetas` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/008-tarjetas/spec.md`

## Summary

Feature nueva desde cero (nunca existió, ni lectura ni escritura): catálogo de tarjetas (solo lectura), resúmenes de tarjeta con líneas de consumo (lectura + alta/edición/eliminación con bloqueo exclusivo), compras en cuotas con generación automática de cronograma, y cuenta corriente por tarjeta. La investigación previa (tres especialistas, `research.md`) encontró que el esquema real difiere de lo asumido en el borrador inicial en dos puntos estructurales, ya resueltos con el usuario y reflejados en `spec.md`: (1) la compra en cuotas (`dbo.[Tarjetas de Credito]`) nunca tuvo columna `IdTarjeta` — no se vincula a una tarjeta del catálogo; (2) la cuenta corriente de una tarjeta se construye únicamente a partir del total de sus resúmenes, no de las cuotas de compras en cuotas, para evitar contar la misma deuda dos veces (mismo problema que las tablas de conciliación de Access, con 0 filas, nunca resolvieron). Reutiliza al máximo la infraestructura probada en 006/007: `execute_write_transaction`, patrón de bloqueo de edición (TTL + "forzar"), listados vacíos por defecto con filtros en la URL, advertencia no bloqueante ante duplicado.

## Technical Context

**Language/Version**: Python 3.13 (backend) + TypeScript 5.x / Next.js (frontend) — mismas versiones que 002-007.

**Primary Dependencies**: FastAPI + Pydantic; pyodbc (DSN `SQL_LaHerencia`); Next.js, TanStack Query, Tailwind CSS. Sin dependencias nuevas.

**Storage**: SQL Server, base `WC` únicamente para escritura — `dbo.Tarjetas`, `dbo.Tarjetas_Resumenes`, `dbo.Tarjetas_Resumenes_Lineas`, `dbo.[Tarjetas de Credito]`, `dbo.[Cuotas Tarjetas de Credito]` (todas ya existentes, sin cambios de estructura — ninguna ALTER, ver Constitution Check). Tablas nuevas en `WC`: `dbo.TarjetaResumenEditLocks`, `dbo.TarjetaCuotasEditLocks` (mismo patrón que `CompraEditLocks` de 006).

**Testing**: pytest + httpx (contract tests con fixtures, mismo patrón que `test_ventas_hacienda_*.py`/`test_ventas_granos_*.py`, duplicado por dominio: `test_tarjetas_api.py`, `test_tarjetas_resumenes_api.py`, `test_tarjetas_cuotas_api.py`).

**Target Platform**: Igual que el resto de la app — backend Python + frontend Next.js, uso interno del equipo administrativo.

**Project Type**: Web application (frontend + backend). Feature completamente nueva: `tarjetas` (catálogo + cuenta corriente), `tarjetas_resumenes`, `tarjetas_cuotas` — ningún dominio existía antes en la app web.

**Performance Goals**: Encontrar y abrir cualquiera de los 293 resúmenes reales por tarjeta y fecha en menos de 30s (SC-001); cargar una compra en cuotas y ver el cronograma generado en menos de 1 minuto (SC-004).

**Constraints**: Toda escritura exclusivamente contra `WC` (FR-015); advertencia no bloqueante ante resumen duplicado (mismo código+tarjeta), nunca bloqueo duro (FR-012, mismo criterio que FR-009a/012a de 007); bloqueo pesimista de edición con TTL y opción de "forzar" (FR-013); sin conciliación automática línea↔cuota ni distribución de línea entre contactos (FR-014, 0 filas reales en esas tablas); ninguna ALTER/DDL sobre el esquema real — la ausencia de `IdTarjeta` en `[Tarjetas de Credito]` se resuelve por diseño (compra en cuotas sin tarjeta), no modificando el esquema.

**Scale/Scope**: Volumen medio-bajo, ya cuantificado por research real: 5 tarjetas, 293 resúmenes, 1694 líneas de consumo, 18 compras en cuotas, 183 cuotas. No requiere paginación agresiva ni índices nuevos.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Resultado |
|---|---|---|
| I. SQL Server es la fuente de verdad | Usa las tablas reales `Tarjetas`/`Tarjetas_Resumenes`/`Tarjetas_Resumenes_Lineas`/`[Tarjetas de Credito]`/`[Cuotas Tarjetas de Credito]`, todas confirmadas por `INFORMATION_SCHEMA`/`sys.foreign_keys` reales (research.md) por tres especialistas de forma independiente. Solo agrega tablas de infraestructura de bloqueo, sin almacén paralelo de datos de negocio. | Pass |
| II. Protección de datos reales | Toda escritura pasa por `execute_write`/`execute_write_transaction` (`_assert_target_is_wc`, sin cambios). Ningún INSERT/UPDATE/DELETE/DDL se ejecutó durante la investigación — solo SELECT contra `INFORMATION_SCHEMA`/`sys.foreign_keys`/`OBJECT_DEFINITION`/datos reales. Se evaluó explícitamente un `ALTER TABLE` para agregar `IdTarjeta` a `[Tarjetas de Credito]` y se descartó junto con el usuario — decisión de producto, no técnica, para no modificar el esquema real sin necesidad probada. | Pass |
| III. Procesos de negocio antes que tablas | El flujo sigue el proceso real: catálogo → resumen (cabecera fiscal + líneas de consumo) → cuenta corriente por tarjeta con navegación al resumen de origen → compra en cuotas con cronograma automático y marcado de cobro por cuota, replicando la secuencia de los formularios Access reales (`Tarjetas_Resumenes`, `Cuotas Tarjetas de Credito`), no una grilla CRUD genérica. | Pass |
| IV. Trazabilidad y significado financiero explícito | Cabecera de resumen distingue explícitamente cada cargo/impuesto con su signo real (sin `ABS()`); `totalCalculado` documenta exactamente qué suma (data-model.md); saldo de cuenta corriente trazable a `IdResumen`; decisión de "solo resúmenes" documentada explícitamente como forma de evitar doble conteo, en vez de ocultarlo. | Pass |
| V. Contrato primero, integración probada | Contrato de API definido en Fase 1 (`contracts/tarjetas-api.md`) antes de tocar el frontend; contract tests para catálogo/resúmenes/cuotas/lock antes de cerrar cada dominio; validación manual contra `WC` real planificada en `quickstart.md` (mismo criterio que T086/T087 de 006/007). | Pass |
| VI. Colaboración de especialistas | Contrato de datos, fórmulas financieras y navegación confirmados por consulta explícita a `sql-server-engineer`, `financial-direction-specialist` y `administracion-cuentas` contra `WC` real antes de escribir este plan — no se asumió nada del borrador inicial de la spec sin verificar, y dos discrepancias estructurales encontradas por los tres de forma independiente (`IdTarjeta` faltante, ausencia de rama "Tarjetas" en la vista de cuentas corrientes) se resolvieron con el usuario antes de continuar. | Pass |
| VII. Simplicidad y reversibilidad | No se toca `vw_MovimientosCuenta_Base` (vista compartida de 004) — se construye una fuente propia por `IdTarjeta`, evitando riesgo sobre otro módulo ya en producción. No se agrega columna nueva al esquema real (se prefirió ajustar el alcance de FR-004/006 antes que un ALTER). Reutiliza el patrón de locks/transacciones de 006/007 sin reinventar mecanismos. | Pass |
| VIII. Stack aprobado | Mismo stack (FastAPI/SQL Server/Next.js/TypeScript/Tailwind/TanStack Query), sin dependencias nuevas. | Pass |

No hay violaciones que requieran justificación.

*Re-chequeo post-Fase 1 (2026-09-18): `data-model.md` confirma que las únicas tablas nuevas son de infraestructura (`TarjetaResumenEditLocks`, `TarjetaCuotasEditLocks`), sin datos de negocio propios ni ALTER sobre tablas existentes. `contracts/tarjetas-api.md` reutiliza el mismo patrón de headers/status codes que `ventas-api.md` (007). Los 8 principios siguen en Pass.*

## Project Structure

### Documentation (this feature)

```text
specs/008-tarjetas/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── tarjetas-api.md
└── tasks.md          # generado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── src/
│   └── features/
│       ├── tarjetas/                      # catálogo (solo lectura) + cuenta corriente por tarjeta
│       │   ├── schemas.py                 # TarjetaResponse, MovimientoTarjetaResponse
│       │   ├── repository.py              # get_tarjetas, get_movimientos (query propia, no vw_MovimientosCuenta_Base)
│       │   └── router.py                  # GET /api/tarjetas, GET /api/tarjetas/{id}/movimientos
│       ├── tarjetas_resumenes/            # feature nuevo
│       │   ├── schemas.py                 # ResumenResponse/AltaRequest/EditRequest/LineaInput/LockResponse
│       │   ├── repository.py              # search_resumenes/get_detalle/create/update/delete
│       │   ├── repository_locks.py        # mismo patrón que ventas_hacienda/repository_locks.py
│       │   └── router.py                  # GET/POST/PUT/DELETE /api/tarjetas-resumenes, lock endpoints
│       └── tarjetas_cuotas/               # feature nuevo
│           ├── schemas.py                 # CompraCuotasResponse/AltaRequest/EditRequest/CuotaResponse/LockResponse
│           ├── repository.py              # search/get_detalle/create (genera cronograma)/update/delete/marcar_cobrada
│           ├── repository_locks.py        # mismo patrón
│           ├── calculo_cuotas.py          # generador de cronograma (data-model.md, cuota fija + ajuste redondeo)
│           └── router.py                  # GET/POST/PUT/DELETE /api/tarjetas-cuotas, PATCH cuotas/{id}, lock endpoints
└── tests/
    └── contract/
        ├── test_tarjetas_api.py            # nuevo (catálogo + cuenta corriente)
        ├── test_tarjetas_resumenes_api.py  # nuevo
        └── test_tarjetas_cuotas_api.py     # nuevo

frontend/
├── src/
│   ├── components/
│   │   ├── tarjetas/
│   │   │   ├── TarjetasListado.tsx             # nuevo (catálogo, Historia 4)
│   │   │   └── TarjetaCuentaCorriente.tsx      # nuevo (Historia 2, patrón visual de cuentas-corrientes/ sin reusar el componente)
│   │   ├── tarjetas-resumenes/
│   │   │   ├── ResumenesListado.tsx            # nuevo
│   │   │   └── ResumenForm.tsx                 # nuevo: cabecera + grilla de líneas
│   │   └── tarjetas-cuotas/
│   │       ├── ComprasCuotasListado.tsx        # nuevo
│   │       └── CompraCuotasForm.tsx            # nuevo: cabecera + cronograma generado (solo lectura tras guardar, toggle cobrado por cuota)
│   ├── services/
│   │   ├── tarjetasApi.ts                      # nuevo
│   │   ├── tarjetasResumenesApi.ts              # nuevo
│   │   └── tarjetasCuotasApi.ts                 # nuevo
│   ├── components/layout/
│   │   └── NavHeader.tsx                       # "Tarjetas" nuevo dentro de "Finanzas" (research.md §7)
│   └── app/
│       └── finanzas/
│           └── tarjetas/
│               ├── page.tsx                            # catálogo (Historia 4)
│               ├── [idTarjeta]/cuenta-corriente/page.tsx  # Historia 2
│               ├── resumenes/
│               │   ├── page.tsx                          # listado (Historia 1)
│               │   ├── nuevo/page.tsx
│               │   └── [idResumen]/{page.tsx, editar/page.tsx}
│               └── compras-en-cuotas/
│                   ├── page.tsx                          # listado (Historia 3)
│                   ├── nueva/page.tsx
│                   └── [idPagoTarjeta]/editar/page.tsx
```

**Structure Decision**: Tres features backend independientes (`tarjetas`, `tarjetas_resumenes`, `tarjetas_cuotas`) en vez de uno solo, porque son tres dominios de datos sin relación estructural entre sí en el esquema real (confirmado en research.md: la compra en cuotas no tiene FK a `Tarjetas`, y la cuenta corriente no depende de `tarjetas_cuotas` en absoluto por la decisión de "solo resúmenes"). Frontend agrupado bajo `/finanzas/tarjetas/` porque para el usuario sí es un único módulo de navegación (research.md §7), aunque el backend los separe. No se reutiliza el componente de cuenta corriente de 004 (`cuentas-corrientes/page.tsx`) — la fuente de datos se agrega por `IdTarjeta`, no por `IdContacto`, sería forzar una vista ficticia sobre un modelo de datos que no calza (research.md §7).

## Complexity Tracking

*No hay violaciones de la Constitution Check que requieran justificación.*
