---

description: "Task list for Exportar Saldos de Cuentas Corrientes y Valores Propios a Excel"
---

# Tasks: Exportar Saldos de Cuentas Corrientes y Valores Propios a Excel

**Input**: Design documents from `/specs/014-informes-cuentas-valores/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/informes-api.md, quickstart.md

**Tests**: tests focalizados de la consulta agregada de saldos (US2, la única lógica nueva no trivial — las exportaciones en sí son composición de datos ya probados).

**Organization**: US1 y US3 son extensiones aditivas independientes sobre módulos ya probados (solo agregan un endpoint de export); US2 es la única con lógica nueva real (consulta agregada de saldos), así que se implementa primero.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

`backend/src/`, `frontend/src/` — mismo layout que 003/004/012.

---

## Phase 1: User Story 2 — Saldos de todos los proveedores (Priority: P1)

**Goal**: Listado agregado de saldos de todos los contactos con movimientos, consultable y exportable (spec.md Historia 2).

**Independent Test**: Comparar 5 contactos del listado contra su saldo individual de 004 — deben coincidir exactamente (SC-002).

- [X] [US2] Implementar `backend/src/features/cuentas_corrientes/repository.py::get_saldos_todos(orden) -> list[dict]`: `SELECT IdContacto, [Razon Social], SaldoParcial FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY IdContacto ORDER BY Fecha DESC, Origen DESC, IdOrigen DESC) AS rn FROM vw_MovimientosCuenta_Saldo) t WHERE rn = 1 ORDER BY ...` según `orden` (`razonSocial` | `saldo`) — incluye contactos con saldo $0 (FR-004, data-model.md)
- [X] [P] [US2] Test `backend/tests/test_cuentas_corrientes_saldos.py`: `get_saldos_todos` devuelve una fila por contacto (no una por movimiento), incluye saldo $0, ordena por ambos criterios — mock de `fetch_all`
- [X] [US2] Agregar `SaldoContacto`/`SaldosResponse` a `backend/src/features/cuentas_corrientes/schemas.py`
- [X] [US2] Agregar endpoint `GET /api/cuentas-corrientes/saldos` en `router.py` según `contracts/informes-api.md`
- [X] [US2] Implementar `backend/src/features/cuentas_corrientes/exportacion.py::saldos_xlsx(orden) -> bytes`: hoja "Saldos" (razón social, saldo), mismo patrón que `ordenes/exportacion.py` (research.md §2)
- [X] [US2] Agregar endpoint `GET /api/cuentas-corrientes/saldos/exportar` en `router.py`
- [X] [US2] Extender `frontend/src/services/cuentasCorrientesApi.ts` con `fetchSaldos(orden)`, `urlExportarSaldos(orden)`
- [X] [US2] Crear `frontend/src/app/finanzas/cuentas-corrientes/saldos/page.tsx`: tabla ordenable (razón social / saldo) + botón "Exportar a Excel"
- [X] [US2] Agregar link a `/finanzas/cuentas-corrientes/saldos` desde la navegación de Cuentas Corrientes existente

**Checkpoint**: listado de saldos de todos los proveedores funcional, verificado contra el saldo individual de 004.

---

## Phase 2: User Story 1 — Exportar la cuenta corriente de un proveedor (Priority: P1)

**Goal**: Exportar a Excel la cuenta corriente de un contacto puntual, respetando el filtro de fechas ya soportado (spec.md Historia 1).

**Independent Test**: Exportar un proveedor con movimientos reales y verificar que el Excel coincide con la pantalla, con y sin filtro de fechas.

- [X] [US1] Implementar `cuentas_corrientes/exportacion.py::cuenta_corriente_xlsx(id_contacto, fecha_desde, fecha_hasta) -> bytes`: hoja "Movimientos" (fecha, documento, número de documento, deuda, crédito, saldo acumulado) reusando `repository.get_movimientos` + fila de saldo final (`repository.get_saldo`)
- [X] [US1] Agregar endpoint `GET /api/cuentas-corrientes/{idContacto}/exportar` en `router.py` según `contracts/informes-api.md`
- [X] [US1] Extender `cuentasCorrientesApi.ts` con `urlExportarCuenta(idContacto, params)`
- [X] [US1] Agregar botón "Exportar a Excel" en `frontend/src/components/cuentas-corrientes/CuentaCorriente.tsx`, respetando el filtro de fechas ya aplicado en pantalla

**Checkpoint**: cuenta corriente de un proveedor exportable, con y sin filtro de fechas, incluido el caso sin movimientos.

---

## Phase 3: User Story 3 — Listado y exportación de Valores Propios (Priority: P2)

**Goal**: Exponer todos los campos reales de un cheque (incluido `comentarios`) y permitir su exportación (spec.md Historia 3).

**Independent Test**: Exportar el listado completo y verificar que incluye todos los campos, con el mismo total que la consulta existente de 003.

- [X] [US3] Agregar `comentarios` a `select_columns` de `"valores-propios"` en `tesoreria/repository.py::MEDIOS_CONFIG` (data-model.md)
- [X] [US3] Agregar `comentarios: str | None` a `ValorPropio` en `tesoreria/schemas.py` y al tipo equivalente en `frontend/src/services/tesoreriaApi.ts`
- [X] [US3] Implementar `tesoreria/exportacion.py::valores_propios_xlsx(fecha_desde, fecha_hasta) -> bytes`: hoja "Valores propios" con todos los campos (mismo patrón de `_hoja`/`_cerrar`/`_bytes`)
- [X] [US3] Agregar endpoint `GET /api/tesoreria/valores-propios/exportar` en `tesoreria/router.py` según `contracts/informes-api.md`
- [X] [US3] Extender `tesoreriaApi.ts` con `urlExportarValoresPropios(params)`
- [X] [P] [US3] Test en `backend/tests/test_tesoreria_cargas_endpoints.py` o archivo nuevo: `GET /valores-propios/exportar` devuelve un `.xlsx` válido (openpyxl) con las columnas esperadas
- [X] [US3] Agregar botón "Exportar a Excel" en `frontend/src/components/tesoreria/MovimientosPorMedio.tsx`, visible solo cuando `medio === "valores-propios"`

**Checkpoint**: valores propios exportable con todos sus campos reales.

---

## Phase 4: Polish

- [X] Aplicar formato numérico y monetario del sistema (miles `.`, decimales `,`, `$`) en `saldos/page.tsx` y en los 3 archivos `.xlsx` (formatos de columna en `_cerrar`)
- [X] Ejecutar los 4 escenarios de `quickstart.md` de punta a punta y confirmar SC-001 a SC-005

---

## Dependencies & Execution Order

- **US2 (Phase 1)**: sin dependencias — es la única con lógica nueva no trivial, se hace primero
- **US1 (Phase 2)**: depende de que `cuentas_corrientes/exportacion.py` exista como módulo — puede compartir archivo con US2 sin bloquearla (mismo módulo, funciones independientes)
- **US3 (Phase 3)**: independiente de US1/US2 — toca `tesoreria`, no `cuentas_corrientes`
- **Polish (Phase 4)**: depende de que las 3 historias estén completas

## Implementation Strategy

1. US2 primero — único cálculo nuevo, validarlo a fondo antes de construir el resto encima
2. US1 y US3 en paralelo — son extensiones aditivas independientes sobre módulos distintos
3. Polish — formato + verificación end-to-end
