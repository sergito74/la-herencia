# Implementation Plan: Exportar Saldos de Cuentas Corrientes y Valores Propios a Excel

**Branch**: `014-informes-cuentas-valores` | **Date**: 2026-09-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-informes-cuentas-valores/spec.md`

## Summary

Cubre 2 de los 3 informes de Access con valor real detectados en la auditoría de 2026-09-22 (el tercero, Flujo de Fondos, se descartó por decisión del usuario): exportación de la cuenta corriente de un proveedor puntual, un listado agregado de saldos de todos los proveedores (nuevo, no existía ni en consulta), y exportación del listado de valores propios (cheques) con sus campos completos. Todo solo lectura contra `WC`, sin cambios de esquema.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript/Next.js 14 (frontend) — mismo stack que 003/004/012.

**Primary Dependencies**: FastAPI, `openpyxl` (ya usado en 010/011/012). Sin dependencias nuevas.

**Storage**: SQL Server, `WC`. Sin tablas ni columnas nuevas — reusa `vw_MovimientosCuenta_Base`/`Saldo` y `dbo.[Valores propios]`.

**Testing**: `pytest` (mock de `connection.py`) + `tsc --noEmit`.

**Target Platform**: Web local, mismo entorno.

**Project Type**: Web application, extiende `backend/src/features/cuentas_corrientes/` (nuevo módulo `exportacion.py`) y `backend/src/features/tesoreria/` (extiende `exportacion` — a crear, mismo patrón).

**Performance Goals**: exportar un listado de saldos con volumen actual (~cientos de contactos) en menos de 10 segundos (SC-002); sin requisito de alto volumen adicional.

**Constraints**: 100% solo lectura (constitución II) — ningún endpoint de esta spec usa `execute_write`/`execute_write_transaction`.

**Scale/Scope**: 3 endpoints nuevos (2 exports + 1 consulta agregada) + 1 extensión de schema existente (`comentarios`) + 2 módulos de exportación backend + botones de export en frontend ya existente (004, 003), sin pantallas nuevas.

## Constitution Check

- **I/II (solo lectura)**: ✅ ningún cambio de escritura — reusa vistas/tablas ya existentes, solo agrega `SELECT`s y exports.
- **III (proceso de negocio)**: ✅ completa procesos ya migrados (cuenta corriente, tesorería) con su capa de reporte, no expone tablas crudas nuevas.
- **IV (trazabilidad)**: ✅ el listado de saldos usa la misma fuente y el mismo orden ya validado (`get_saldo`), sin inventar un cálculo paralelo.
- **V (contract-first)**: ✅ contrato en `contracts/informes-api.md`; tests de la consulta agregada de saldos antes/junto con el código.
- **VII (simplicidad)**: ✅ reusa el patrón de exportación ya usado 3 veces (010/011/012) en vez de crear una abstracción compartida nueva; no se toca Flujo de Fondos (evita una decisión de diseño no resuelta).
- **VIII (stack aprobado)**: ✅ sin cambios de stack.

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/014-informes-cuentas-valores/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── informes-api.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── src/features/cuentas_corrientes/
│   ├── repository.py          # extendido: get_saldos_todos, mantiene get_saldo intacto
│   ├── exportacion.py         # nuevo: cuenta_corriente_xlsx, saldos_xlsx
│   ├── router.py              # extendido: GET /saldos, GET /{id}/exportar, GET /saldos/exportar
│   └── schemas.py             # extendido: SaldoContacto, SaldosResponse
└── tests/
    └── test_cuentas_corrientes_saldos_exportacion.py   # nuevo

backend/src/features/tesoreria/
├── repository.py          # extendido: comentarios en select_columns de valores-propios
├── exportacion.py         # nuevo: valores_propios_xlsx
├── router.py               # extendido: GET /valores-propios/exportar
└── schemas.py               # extendido: comentarios en ValorPropio

frontend/
├── src/components/cuentas-corrientes/
│   └── CuentaCorriente.tsx    # extendido: botón "Exportar a Excel"
├── src/app/finanzas/cuentas-corrientes/
│   └── saldos/page.tsx        # nuevo: listado de saldos, ordenable, con botón exportar
├── src/components/tesoreria/
│   └── MovimientosPorMedio.tsx  # extendido: botón exportar cuando medio === "valores-propios"
└── src/services/
    ├── cuentasCorrientesApi.ts  # extendido: fetchSaldos, urlExportarCuenta, urlExportarSaldos
    └── tesoreriaApi.ts          # extendido: urlExportarValoresPropios
```

**Structure Decision**: extiende los dos features existentes (`cuentas_corrientes`, `tesoreria`) en vez de crear un feature "informes" nuevo — cada export vive junto a su dominio, mismo patrón que 010/011/012 no crearon un módulo de reporting compartido.

## Complexity Tracking

*Sin violaciones — sección no aplica.*
