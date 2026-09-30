---

description: "Task list for Flujo de caja por Rubro (030)"
---

# Tasks: Flujo de caja por Rubro

**Input**: Design documents from `/specs/030-flujo-caja-por-rubro/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: se incluyen tests unitarios de las funciones puras (reparto, internos, conversión USD, agregación) y contract tests del router, mismo criterio que 018/019. La validación de totales contra `WC` real es manual (quickstart.md).

**Organization**: por historia de usuario (spec.md): US1 tabla ARS (P1, MVP), US2 granularidad + USD (P2), US3 detalle de celda (P2), US4 exportar (P3).

## Phase 1: Setup

- [X] T001 Verificar que ningún componente del frontend consume `GET /api/flujo-caja/por-rubro` ni `saldoInicial` (grep en `frontend/src`) antes de cambiar el contrato; registrar el resultado en `specs/030-flujo-caja-por-rubro/research.md` §3.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: la unidad de cálculo pasa de "movimiento con un rubro" a "parte de movimiento" (data-model.md). Todas las historias dependen de esto.

- [X] T002 En `backend/src/features/flujo_caja/atribucion.py`, cambiar `atribuir_desde_aplicaciones` para que devuelva una lista de partes `{rubro, centroCosto, importe, documentoAplicado}` en vez de un único ganador. Reglas (research.md §1):
  - cada aplicación aporta su `ImporteAplicado`;
  - una compra con líneas de varios rubros se reparte en proporción al importe de cada línea;
  - el remanente sin aplicar es una parte "Pendiente de aplicar", o "Histórico sin aplicar" si el movimiento es anterior al 01-09-2015;
  - si lo aplicado supera al movimiento, se escala al importe del movimiento;
  - «la suma de las partes es igual al importe del movimiento (tolerancia 0,01; la última parte absorbe el redondeo)».
- [X] T003 En `backend/src/features/flujo_caja/atribucion.py`, cargar todas las aplicaciones vigentes del rango en una sola consulta (dict por `(origen, idMovimiento)`) y usarla en `atribuir_desde_aplicaciones`, en lugar de una consulta por movimiento (research.md §6).
- [X] T004 [P] En `backend/src/features/flujo_caja/clasificacion.py`, agregar `tipo_interno(banco, importe, concepto, grupo_conceptos)`:
  - Galicia "Inversiones" con importe < 0 → "Colocación FIMA";
  - Galicia "Inversiones" con importe > 0 → "Rescate FIMA";
  - BNA titular propio → "Traspaso entre bancos";
  - cualquier otro movimiento → `None`.
  - Sin cambiar `es_interno`.
  - Agregar `emparejar_traspasos(movimientos)`: por cada "Traspaso entre bancos" de BNA, buscar en Galicia un movimiento de signo opuesto, «mismo importe dentro de los 3 días», todavía no emparejado, y marcarlo también como "Traspaso entre bancos". Los que no encuentran pareja quedan con `sinContraparte=True`.
- [X] T005 [P] Crear `backend/src/features/flujo_caja/cotizacion.py` con `cargar_serie(desde, hasta)`:
  - lee `dbo.[Dolar BNA].Vend_Divisa` por `Fecha` en el rango ampliado 7 días hacia atrás;
  - agrega `cotizacion_del_dia(serie, fecha) -> (valor, fechaCotizacion) | None`, que toma la fecha o la última anterior «dentro de los 7 días»;
  - si no hay ninguna en ese plazo, devuelve `None`.
- [X] T006 En `backend/src/features/flujo_caja/repository.py`, implementar `partes_de_movimientos(movimientos)`: cada movimiento produce sus partes (T002) o una sola parte de sección `internos` (T004), con los campos de data-model.md: `seccion`, `rubro`, `centroCosto` («si falta, "Sin centro de costos"»), `importeArs` con signo, `documentoAplicado`, `cuenta`, `concepto`, `contacto`. Adaptar `atribuir_movimientos` para producir partes sin cambiar el fallback existente (Ley 25.413, recaudación ARBA, matching exacto, Pendiente/Histórico).
- [X] T007 [P] Tests en `backend/tests/test_flujo_caja_rubro_partes.py`:
  - reparto por importe aplicado entre 2 rubros;
  - remanente a Pendiente, y a Histórico si es anterior a 2015-09-01;
  - compra con líneas de 2 rubros;
  - suma de partes igual al movimiento;
  - `tipo_interno` para los 3 casos y para un movimiento operativo;
  - `emparejar_traspasos`: pareja encontrada a 2 días; sin pareja a 4 días (queda sin contraparte); dos candidatos iguales (se empareja el más cercano, uno solo);
  - `cotizacion_del_dia` con día exacto, fallback de 3 días y ausencia de cotización en 8 días.

**Checkpoint**: partes correctas y testeadas; la respuesta del endpoint todavía no cambió.

---

## Phase 3: User Story 1 - Ver el flujo de caja real por rubro y período (Priority: P1) 🎯 MVP

**Goal**: tabla en pesos con saldo inicial por cuenta, ingresos por rubro, egresos por centro de costo con subtotal, internos en filas propias y saldo final.

**Independent Test**: quickstart.md Escenarios 1 y 2. Los saldos finales coinciden con los extractos, y la suma de todas las celdas es igual a la de los movimientos del rango.

- [X] T008 [US1] En `backend/src/features/flujo_caja/repository.py`, reescribir `agregar_por_rubro(partes, granularidad)` sobre partes:
  - ingresos por rubro;
  - egresos por centro de costo con subtotal;
  - sección `internos` con las filas "Colocación FIMA", "Rescate FIMA" y "Traspaso entre bancos", «siempre presentes aunque estén en cero»;
  - `traspasosSinContraparte` con los traspasos sin pareja (contracts/api.md);
  - `netoOperativoPorPeriodo` y `saldoFinalPorPeriodo`: saldo inicial acumulado + neto operativo + internos.
  - Los períodos sin movimientos igual generan columna, con 0.
- [X] T009 [US1] En `backend/src/features/flujo_caja/repository.py`, cambiar `saldo_inicial_al` para que devuelva `{cuentas: [...], total}`:
  - Nación: todas las cuentas BNA;
  - Galicia CC;
  - Galicia Fondo FIMA = −Σ de los movimientos Galicia "Inversiones" antes de la fecha, con `aclaracion` "Capital neto colocado, sin rendimiento" (research.md §3).
- [X] T010 [US1] Actualizar `backend/src/features/flujo_caja/schemas.py` y `router.py` (`GET /por-rubro`) al contrato de `contracts/api.md`: `saldoInicial` como objeto, `internos`, `netoOperativoPorPeriodo`, `saldoFinalPorPeriodo`, `moneda` (en esta fase solo `ARS`) y `sinTipoCambio` vacío.
- [X] T011 [P] [US1] Contract tests en `backend/tests/contract/test_flujo_caja_por_rubro_api.py`: estructura de la respuesta, Pendiente/Histórico visibles, internos fuera de los totales operativos, y saldo final = saldo inicial + neto + internos. Actualizar los tests existentes de `/por-rubro` que asumían `saldoInicial` numérico.
- [X] T012 [P] [US1] En `frontend/src/services/flujoCajaApi.ts`, agregar los tipos del contrato y `fetchPorRubro({fechaDesde, fechaHasta, granularidad, moneda})`.
- [X] T013 [US1] Crear `frontend/src/components/flujo-caja/FlujoCajaRubro.tsx`:
  - filtros de rango de fechas (default: últimos 12 meses);
  - tabla con el orden saldo inicial por cuenta + total → Ingresos → Egresos por centro de costo (con fila de subtotal) → Neto operativo → Movimientos entre cuentas propias → Saldo final;
  - filas "Pendiente de aplicar" e "Histórico sin aplicar" con fondo distinguible;
  - `formatMoneda` y negativos con signo y en rojo;
  - scroll horizontal con la primera columna fija;
  - la aclaración del FIMA visible;
  - si hay `traspasosSinContraparte`, un aviso con la lista.
- [X] T014 [US1] Crear `frontend/src/app/finanzas/flujo-caja-rubro/page.tsx` y agregar "Flujo de caja por rubro" en Finanzas (`frontend/src/components/layout/NavHeader.tsx` y el home), junto a "Flujo de caja real".

**Checkpoint**: MVP usable en pesos, mensual.

---

## Phase 4: User Story 2 - Cambiar granularidad y moneda (Priority: P2)

**Goal**: semana, mes, trimestre y año, y USD convertido por movimiento con la cotización del día.

**Independent Test**: quickstart.md Escenarios 3 y 6.

- [X] T015 [US2] En `backend/src/features/flujo_caja/repository.py`, agregar `convertir_partes_a_usd(partes, serie)`:
  - cada parte se convierte con `cotizacion_del_dia` de su fecha, guardando `cotizacion`, `fechaCotizacion` e `importeUsd`;
  - las partes sin cotización se excluyen de la suma en USD y se acumulan en `sinTipoCambio` por celda, con cantidad e importe ARS;
  - en `router.py`, aceptar `moneda=USD` en `GET /por-rubro` y aplicar la conversión antes de agregar.
  - `saldoInicial` en USD se convierte con la cotización del día de inicio del rango, y cada `saldoFinalPorPeriodo` con la del último día del período; si falta, el saldo va `null` y se informa en `saldosSinTipoCambio` (contracts/api.md).
- [X] T016 [P] [US2] Tests en `backend/tests/test_flujo_caja_rubro_partes.py` y en el contract test: el total del rango es idéntico en las 4 granularidades; en USD, una parte con cotización se convierte y una sin cotización aparece en `sinTipoCambio` y no suma.
- [X] T017 [US2] En `FlujoCajaRubro.tsx`, agregar el selector de granularidad (Semana / Mes / Trimestre / Año, default Mes) y el de moneda (ARS / USD). En USD:
  - `formatMoneda(v, "Dolares")`;
  - las celdas con partes sin cotización llevan un ícono de aviso y un tooltip con cantidad e importe ARS no convertido;
  - un banner indica la última fecha de la serie de dólar disponible cuando el rango la excede.

**Checkpoint**: vista multi-granularidad en ARS y USD.

---

## Phase 5: User Story 3 - Ver qué movimientos componen un rubro (Priority: P2)

**Goal**: el clic en una celda abre los movimientos que la componen, y su suma es igual a la celda.

**Independent Test**: quickstart.md Escenario 5.

- [X] T018 [US3] En `backend/src/features/flujo_caja/repository.py` y `router.py`, agregar `GET /api/flujo-caja/por-rubro/detalle` (contracts/api.md). Filtra las partes (mismo cálculo que `por-rubro`, en la moneda pedida) por `periodo`, `seccion`, `rubro` y `centroCosto`, y devuelve `{total, items}` con `total` exactamente igual a la celda. Responde 422 si el `periodo` no corresponde a la granularidad.
- [X] T019 [P] [US3] Contract test en `backend/tests/contract/test_flujo_caja_por_rubro_api.py`: para cada celda con importe de un escenario simulado, el `total` del detalle es igual al valor de `por-rubro` (FR-006).
- [X] T020 [US3] Crear `frontend/src/components/flujo-caja/DetalleCeldaRubro.tsx`: panel lateral con fecha, cuenta, concepto, contacto, importe de la parte, importe del movimiento, documento aplicado (o "sin aplicar") y, en USD, cotización y fecha de cotización. Para las partes "Pendiente de aplicar", agregar un acceso al flujo existente de aplicación de pagos de 019. Conectar el clic de celda en `FlujoCajaRubro.tsx`.

**Checkpoint**: cada número es trazable hasta sus movimientos.

---

## Phase 6: User Story 4 - Exportar a Excel (Priority: P3)

**Goal**: el `.xlsx` reproduce la vista actual.

**Independent Test**: quickstart.md Escenario 7.

- [X] T021 [US4] Crear `backend/src/features/flujo_caja/exportacion.py` (mismo patrón que `cuentas_corrientes/exportacion.py`):
  - encabezado con rango, granularidad, moneda y fecha de generación;
  - las mismas filas y subtotales que la pantalla;
  - importes numéricos con formato de moneda;
  - en USD, una hoja "Sin tipo de cambio".
  - Agregar `GET /api/flujo-caja/por-rubro/exportar` en `router.py`, reusando `_xlsx_response` o un equivalente.
- [X] T022 [P] [US4] Test en `backend/tests/test_flujo_caja_rubro_partes.py`: abrir el xlsx generado con openpyxl y verificar que las celdas de importe son numéricas y que las filas coinciden con la respuesta de `por-rubro`.
- [X] T023 [US4] Botón "Exportar a Excel" en `FlujoCajaRubro.tsx`, apuntando a `urlExportarPorRubro(...)` en `frontend/src/services/flujoCajaApi.ts` con los parámetros actuales de la vista.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T024 Correr `backend/.venv/Scripts/python.exe -m pytest -q` completo sin regresiones, en particular los tests de 018 y 019 que usan `atribuir_desde_aplicaciones` y `saldo_inicial_al`.
- [X] T025 [P] Correr `npx tsc --noEmit` y `npx eslint` sobre los archivos de frontend tocados.
- [X] T026 Validar contra `WC` real los escenarios 1 a 7 de `quickstart.md` y registrar los resultados en `specs/030-flujo-caja-por-rubro/quickstart.md`, incluyendo la comparación del saldo final de Nación y Galicia CC con los extractos (SC-001) y el tiempo de consulta más exportación de 12 meses mensuales, que debe ser menor a 1 minuto (SC-004).
- [ ] T027 Verificar en el navegador (Escenario 8): cambio de granularidad y moneda, panel de detalle, exportación, y negativos en rojo.

---

## Dependencies & Execution Order

- **Setup (T001)** → **Foundational (T002–T007)** → historias.
- **US1 (T008–T014)** depende de Foundational y es el MVP.
- **US2 (T015–T017)** depende de US1 (extiende el mismo endpoint y la misma pantalla).
- **US3 (T018–T020)** depende de Foundational y de la pantalla de US1. En backend es independiente de US2; en USD usa la conversión de T015 si ya existe.
- **US4 (T021–T023)** depende de US1 (y de US2 para exportar en USD).
- **Polish** al final.

### Parallel Opportunities

- T004, T005 y T007 en paralelo (archivos distintos).
- T011 y T012 en paralelo con T008–T010.
- T016, T019 y T022 (tests) en paralelo con su implementación.

## Implementation Strategy

### MVP First

1. Foundational (partes + reparto + internos).
2. US1: tabla en pesos, mensual, con saldos por cuenta.
3. **Validar** los Escenarios 1 y 2 contra `WC`.

### Incremental Delivery

US1 → US2 (granularidad/USD) → US3 (detalle) → US4 (Excel). Cada paso se puede entregar solo.
