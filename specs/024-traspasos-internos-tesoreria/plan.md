# Implementation Plan: Traspasos internos de Tesorería

**Branch**: `024-traspasos-internos-tesoreria` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/024-traspasos-internos-tesoreria/spec.md`

## Summary

Permitir, desde los listados de Tesorería (mismos 6 medios que 023), vincular un movimiento con OTRO movimiento de Tesorería (de cualquier medio, incluido el mismo) que representa el mismo traspaso de dinero entre cuentas propias — sin generar ningún efecto contable. Técnicamente: una tabla nueva insert-only (`TraspasosInternosTesoreria`, eventos `Vincular`/`Deshacer`), una función central `esta_resuelto(medio, idMovimiento)` que unifica los 5 estados posibles de un movimiento (compartida con 023 para el gate simétrico de no-doble-resolución), y una sugerencia automática de contraparte por fecha/importe — verificada contra el caso real conocido (ML↔Galicia, mismo día, mismo importe exacto).

## Technical Context

**Language/Version**: Python 3.13 (backend, FastAPI), TypeScript/Next.js (frontend) — mismo stack que 023.

**Primary Dependencies**: FastAPI, pyodbc, TanStack Query, Tailwind — sin dependencias nuevas.

**Storage**: SQL Server, base `WC` (producción). Requiere: 1 tabla nueva (`TraspasosInternosTesoreria`). A diferencia de 023, **no requiere `ALTER VIEW`** — este módulo nunca toca `vw_MovimientosCuenta_Base` porque, por diseño (FR-004), no genera ningún efecto en cuentas corrientes.

**Testing**: pytest (contract + repository), `tsc --noEmit` — mismo patrón que 023.

**Target Platform**: Web app interna, mismo backend/frontend que el resto del sistema.

**Project Type**: Web application (backend FastAPI + frontend Next.js ya existentes).

**Performance Goals**: Sin metas distintas al resto del sistema — uso interno, bajo volumen (ver Scale/Scope).

**Constraints**: No debe agregar una conexión directa del navegador a SQL Server. No debe escribir en `LaHerencia`. El cambio de esquema (tabla nueva) requiere backup verificado antes de aplicarse (Constitución Principio II, `WC` es producción).

**Scale/Scope**: Volumen real verificado (`WC`, 2026-09-28): de los 75 movimientos de Mercado Libre sin contacto, 24 siguen el patrón "Ingreso de dinero Cuenta Banco de Galicia" — candidatos directos para este módulo. El caso real verificado (ML `IdMovimiento=25` ↔ Galicia `IdMovimiento=2151`) tiene importe y fecha idénticos, confirmando que la heurística de sugerencia (research.md §3) es viable con una ventana ajustada. 6 medios cubiertos (mismos que 023, sin Tarjetas).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (SQL Server es el sistema de registro)**: Cumple. Toda escritura nueva va contra `WC`.
- **Principio II (Protección de datos reales)**: `TraspasosInternosTesoreria` es una tabla nueva — cambio de esquema no trivial. GATE: requiere backup verificado de `WC` antes de aplicarse, igual que 023 (puede reusarse un backup del mismo día si sigue siendo representativo, o tomar uno nuevo si pasó tiempo/hubo escrituras intermedias — a confirmar con el usuario antes de ejecutar el DDL).
- **Principio III (Procesos de negocio, no tablas crudas)**: Cumple — la acción se ofrece inline desde los listados de Tesorería ya existentes, mismo flujo que 023.
- **Principio IV (Trazabilidad y significado financiero explícito)**: Cumple — cada evento queda con ambos movimientos, usuario y fecha; el estado del movimiento (`traspaso_interno`) es explícito y distinguible de los otros 4.
- **Principio V (Contrato primero, integración probada)**: Contrato definido en `contracts/` antes de tocar frontend; tests de contrato/repository análogos a 023.
- **Principio VI (Colaboración de especialistas)**: El diseño de la ventana de sugerencia se ajustó tras verificar contra el caso real (research.md §3) — no se asumió un criterio sin comprobar contra datos reales.
- **Principio VII (Simplicidad, reversible)**: Reusa el patrón insert-only ya validado (021/022/023) en vez de inventar uno nuevo; reusa `conciliacion_tesoreria.calcular_estado` en vez de duplicar su lógica; no requiere `ALTER VIEW` (menor superficie de cambio que 023).
- **Principio VIII (Stack aprobado)**: Cumple, sin nuevas dependencias.

No hay violaciones que requieran `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/024-traspasos-internos-tesoreria/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── traspasos-internos-api.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── src/features/
│   ├── traspasos_internos_tesoreria/   # NUEVO — mismo patrón que conciliacion_tesoreria/
│   │   ├── __init__.py
│   │   ├── repository.py               # vincular/deshacer, esta_resuelto (compartida con tesoreria/router.py)
│   │   ├── schemas.py
│   │   └── router.py
│   ├── conciliacion_tesoreria/
│   │   └── repository.py               # existente — su POST ahora también consulta esta_resuelto (FR-007)
│   └── tesoreria/
│       └── router.py                   # existente — estadoConciliacion pasa a usar esta_resuelto (5 estados)
├── scripts/
│   └── crear_tabla_traspasos_internos_tesoreria.py   # DDL de la tabla nueva (one-off, re-corrible)
└── tests/
    ├── contract/
    │   └── test_traspasos_internos_tesoreria_api.py
    └── test_traspasos_internos_tesoreria_repository.py

frontend/
├── src/
│   ├── components/tesoreria/
│   │   ├── MovimientosPorMedio.tsx     # existente — badge/acción de traspaso interno
│   │   └── VincularTraspasoInterno.tsx # NUEVO — panel de búsqueda/confirmación
│   └── services/
│       └── traspasosInternosTesoreriaApi.ts   # NUEVO
```

**Structure Decision**: mismo patrón de 023 — módulo backend nuevo dedicado (no se mezcla con `tesoreria/` ni con `conciliacion_tesoreria/`, porque tiene su propia tabla y sus propias reglas), sin pantalla frontend aparte (se ofrece inline desde los listados ya existentes, Principio III). La única pieza compartida entre 023 y 024 es la función `esta_resuelto` — vive en `conciliacion_tesoreria/repository.py` (ya tiene `calcular_estado`) o se extrae a un módulo común si `tasks.md` lo justifica al implementar (decisión de detalle, no de arquitectura).

## Complexity Tracking

Sin violaciones de la Constitución que requieran justificación.
