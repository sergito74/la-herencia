# Implementation Plan: Flujo de caja real

**Branch**: `018-flujo-caja-real` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/018-flujo-caja-real/spec.md`

## Summary

Pantalla nueva de solo lectura ("Finanzas → Flujo de caja real") que agrega los movimientos ya existentes de `Movimientos BNA` (ya separado en sus 3 cuentas reales, migración previa) y `Movimientos Galicia` en un flujo mensual/semanal de ingresos, egresos y neto, excluyendo del neto operativo los movimientos internos (transferencias entre cuentas propias, FIMA) mediante reglas de clasificación por concepto — sin escribir ni modificar ningún movimiento bancario.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript/Next.js 14 (frontend) — mismo stack que el resto del sistema.

**Primary Dependencies**: ninguna nueva. Reutiliza `src/db/connection.py` (`fetch_all`/`fetch_one`, solo lectura), el patrón de agregación ya usado en `tesoreria/repository.py`, y `CuentasBancarias`/`Movimientos BNA.IdCuentaBancaria` ya migrados (ver `backend/scripts/separar_cuentas_bna.py`).

**Storage**: SQL Server `WC`. No se crean tablas nuevas — el catálogo de "tipo de movimiento" (Operativo/Interno) se resuelve con reglas de clasificación en la consulta (por `Concepto`/`[Grupo de Conceptos]` de Galicia y patrones ya identificados de transferencia propia en BNA), no con una tabla de clasificación manual. Si en 019/020/021 hace falta persistir clasificaciones más finas (Socios/Cartera), se evalúa ahí — fuera de alcance de 018 (constitución VII, no anticipar estructura que esta feature no necesita).

**Testing**: `pytest` (unit de las reglas de clasificación interno/operativo con casos reales conocidos — ej. "Inversiones" de Galicia, transferencias BNA↔Galicia — y de la agregación mensual/semanal; contract tests del endpoint nuevo con `TestClient`, mismo patrón que 003/014).

**Target Platform**: Web local.

**Project Type**: Web application. Nuevo feature `backend/src/features/flujo_caja/` (o extensión de `tesoreria/` si el agregado resulta más simple ahí — a confirmar en research.md); una pantalla nueva en frontend.

**Performance Goals**: agregar ~9.400 movimientos BNA + los de Galicia por mes es aritmética simple sobre filas ya indexadas por fecha — sin requerimiento de performance especial más allá de lo que ya cumple Tesorería hoy.

**Constraints**: constitución I/II — solo lectura sobre `WC`, cero escritura de movimientos bancarios desde esta feature (FR-006). El flujo debe cuadrar exactamente contra los totales que ya muestra Tesorería para el mismo filtro (SC-002) — no puede introducir una fuente de verdad paralela.

**Scale/Scope**: 1 endpoint de lectura nuevo (agregación mensual/semanal + detalle), 1 pantalla nueva en Finanzas. Cajas en efectivo y cuentas de socios (019) quedan fuera de esta iteración.

## Constitution Check

- **I**: ✅ toda la información sale de SQL Server `WC` (`Movimientos BNA`, `Movimientos Galicia`, `CuentasBancarias`), sin fuente paralela.
- **II**: ✅ solo lectura (`fetch_all`/`fetch_one`); ningún dato real se modifica ni se inserta desde esta feature (FR-006).
- **III**: ✅ el objetivo es el proceso de negocio "entender el flujo de caja real", no una grilla cruda de la tabla — agrega, clasifica y explica (últimas fechas de carga, movimientos internos separados), no expone columnas sin significado.
- **IV**: ✅ cada total es trazable a los movimientos individuales que lo componen (FR-005); el signo y la moneda (ARS) son explícitos en cada celda (FR-007); un movimiento sin clasificación clara se muestra igual, nunca se oculta (FR-009).
- **V**: ✅ contrato de API definido antes de implementación (contracts/api-flujo-caja.md); tests de clasificación y agregación antes/junto con el código.
- **VI**: ✅ especificado con el coordinador funcional, el especialista financiero y el sql-server-engineer (ver research.md), validado con el dueño en conversación previa a esta spec.
- **VII (simplicidad)**: ✅ sin tabla nueva; reutiliza la separación de cuentas BNA ya migrada; reglas de clasificación en la consulta en vez de un motor de reglas configurable que esta feature no necesita todavía.
- **VIII**: ✅ sin nuevas dependencias de stack.

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/018-flujo-caja-real/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api-flujo-caja.md # Phase 1 output
└── tasks.md              # Phase 2 output (speckit-tasks, NOT created by speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   └── features/
│       └── flujo_caja/
│           ├── __init__.py
│           ├── clasificacion.py     # reglas: interno (transferencia propia / FIMA) vs operativo
│           ├── repository.py        # agregación mensual/semanal desde Movimientos BNA + Movimientos Galicia
│           ├── router.py            # GET /api/flujo-caja/resumen, /detalle
│           └── schemas.py
├── main.py                          # + flujo_caja_router
└── tests/
    ├── test_flujo_caja_clasificacion.py
    └── test_flujo_caja_endpoints.py

frontend/src/
├── app/finanzas/flujo-caja-real/
│   └── page.tsx                     # tabla mensual/semanal + bloque de movimientos internos + drill-down
├── components/flujo-caja/
│   └── TablaFlujoCaja.tsx
└── services/flujoCajaApi.ts
```

**Structure Decision**: nuevo feature `backend/src/features/flujo_caja/`, mismo criterio que los demás dominios (`src/features/*`). No se toca `tesoreria/` (se reutilizan sus tablas de origen por lectura, sin importar su código interno, para no acoplar un módulo de agregación a la paginación de Tesorería). Frontend sigue el árbol de navegación ya validado con el arquitecto de producto: `Finanzas → Flujo de caja real`.

## Complexity Tracking

*Sin violaciones.*
