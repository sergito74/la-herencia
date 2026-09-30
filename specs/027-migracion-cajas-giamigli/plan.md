# Implementation Plan: Migración histórica de Cajas Giamigli

**Branch**: `027-migracion-cajas-giamigli` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/027-migracion-cajas-giamigli/spec.md`

## Summary

Migrar a `WC` el historial completo (2011-2026, ~7.000 filas) de "Cajas Giamigli.xlsx": las 4 cuentas de socios/directores (Sergio, Lucy, Cond LSC, Ceci — extendiendo el módulo 021 existente con saldos en pesos, USD y Kg de carne, sin convertir entre monedas) y 2 cajas de efectivo nuevas para el sistema (Giamigli SA y caja chica del campo, solo lectura en esta iteración). La migración corre vía scripts one-off idempotentes (mismo patrón que `cargar_boletas_uatre_faltantes.py`), deduplicando contra lo ya cargado a mano en esta sesión (El Luchador, GMRA SA, Coto, DER S.A.) y contra `Pagos efectivo` para la caja de Giamigli SA, con una cola de "casos a revisar" para filas que no se puedan interpretar con confianza. El motor de revalorización diaria de la planilla ("Deuda Actualizada" vía Índice Novillo/Dólar BNA) queda fuera de alcance (spec Clarifications).

## Technical Context

**Language/Version**: Python 3.11 (backend existente), TypeScript/Next.js (frontend existente)

**Primary Dependencies**: FastAPI, pyodbc (SQL Server), TanStack Query — ya en uso; `openpyxl` para leer `Cajas Giamigli.xlsx` (ya usado ad-hoc en esta sesión para explorar el archivo, se formaliza acá como dependencia real del script de migración)

**Storage**: SQL Server `WC` — extiende `MovimientosCuentaSocio` (021) con columnas de USD/Kg de carne; agrega 2 tablas nuevas: `MovimientosCajaEfectivo` (genérica para las 2 cajas nuevas) y `MigracionCajasGiamigliRevision` (cola de casos a revisar)

**Testing**: pytest (backend) — tests unitarios con monkeypatch para repositorios/endpoints nuevos y para las reglas de deduplicación/parseo, mismo criterio que 004/019/020/021; verificación manual del resultado de la migración contra los saldos reales de la planilla (no se re-corre la migración completa en tests automatizados, solo su lógica de parseo/dedup con fixtures)

**Target Platform**: Windows (mismo entorno que el resto del sistema)

**Project Type**: web application (backend + frontend existentes) — extiende un módulo existente (021) y agrega uno nuevo de solo lectura (cajas de efectivo), más scripts de migración one-off

**Performance Goals**: sin requerimiento de performance especial — migración es un proceso batch de una sola vez (~7.000 filas), no una ruta de usuario; las lecturas nuevas (saldo/movimientos de una caja o de un socio) son del mismo orden que 004/021 (una cuenta a la vez, paginada)

**Constraints**: no debe modificar `Compras`, `Det_Compras`, `Tarjetas_Resumenes_Lineas_Compras`, `Pagos efectivo` ni ningún dato ya cargado de proveedores/documentos (spec FR-010) — la migración solo agrega filas nuevas en `MovimientosCuentaSocio`, `MovimientosCajaEfectivo` y `MigracionCajasGiamigliRevision`; nunca escribe en `LaHerencia`; el archivo `Parametros financieros.xlsx` (Índice Novillo/Dólar BNA) NO se lee ni se importa en esta iteración (fuera de alcance, spec Clarifications)

**Scale/Scope**: ~4.270 (Lucy) + ~477 (Sergio) + ~271 (Cond LSC) + ~2 (Ceci) filas de socios; ~1.841 (Caja Efectivo Pesos/Giamigli SA) + ~95 (Caja chica campo) filas de cajas; 1 ALTER de tabla existente + 2 tablas nuevas; 3 scripts de migración one-off + 1 módulo de lectura nuevo (`cajas_efectivo`) + 1 endpoint de solo lectura para la cola de revisión + extensión de 1 módulo existente (`cuentas_socios`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. SQL Server es el sistema de registro**: toda la migración y las lecturas nuevas operan exclusivamente sobre `WC`; el archivo Excel es solo la fuente de datos de entrada, no queda como dependencia del sistema en producción — cumple.
- **II. Protección de datos reales**: el `ALTER TABLE` sobre `MovimientosCuentaSocio` y las 2 tablas nuevas requieren backup verificado antes de correr (cambio de esquema); los scripts de migración son idempotentes (verifican antes de insertar) para poder re-correrse sin duplicar tras una falla parcial — cumple, a detallar en tasks.
- **III. Procesos de negocio, no tablas crudas**: las pantallas nuevas/extendidas (cuenta de socio con 3 saldos, cuenta de caja de efectivo) siguen el mismo patrón de cuenta corriente ya validado en 004/021 (selección → saldo → historial → origen) — cumple.
- **IV. Trazabilidad y significado financiero explícito**: cada movimiento migrado conserva su fecha, proveedor/detalle y forma de pago originales de la planilla (en `Motivo`/`Medio`); los casos dudosos quedan trazados en `MigracionCajasGiamigliRevision` con el motivo, no se pierden en silencio — cumple.
- **V. Contract-first, integración testeada**: contratos (`contracts/api.md`, `contracts/schema-script.md`) documentados antes de implementar; tests unitarios de parseo/dedup con fixtures (sin depender del Excel real ni de `WC` real) — cumple, a detallar en tasks.
- **VI. Colaboración de especialistas**: el modelo de datos (3 saldos separados sin conversión, motor de revalorización fuera de alcance, regla de deduplicación) se decidió en vivo con el usuario durante `/speckit-clarify` (2026-09-30) a partir del análisis real de las fórmulas de la planilla — cumple.
- **VII. Simplicidad y reversibilidad**: reutiliza el patrón de tabla `MovimientosCuentaSocio` existente (extendida, no reemplazada) y el patrón de módulo de solo lectura de cuentas corrientes (004); los scripts de migración son aditivos y no destructivos (nunca hacen `UPDATE`/`DELETE` sobre datos existentes de otros módulos) — cumple.
- **VIII. Stack aprobado**: Python + SQL Server + Next.js/TypeScript/Tailwind/TanStack Query; `openpyxl` es una librería de lectura de datos (no reemplaza ni compite con el stack aprobado) — cumple.

Sin violaciones; no aplica Complexity Tracking.

**Re-chequeo post-diseño (Phase 1)**: el `ALTER TABLE` aditivo sobre `MovimientosCuentaSocio` y las 2 tablas nuevas (`data-model.md`) no introducen ninguna dependencia nueva, no tocan datos de otros módulos, y siguen el mismo patrón de scripts idempotentes ya usado en el proyecto — ninguna de las decisiones de diseño (Phase 0/1) abre una violación nueva de la Constitución.

## Project Structure

### Documentation (this feature)

```text
specs/027-migracion-cajas-giamigli/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md
│   └── schema-script.md
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   ├── crear_tablas_cajas_efectivo.py            # DDL: ALTER MovimientosCuentaSocio + 2 tablas nuevas
│   └── migracion_cajas_giamigli/                 # paquete de migración one-off
│       ├── __init__.py
│       ├── lector_excel.py                       # abre Cajas Giamigli.xlsx, normaliza filas de cada hoja,
│       │                                          # detecta filas vacías/incompletas → casos a revisar
│       ├── dedup.py                               # regla de coincidencia fecha+proveedor+importe (spec Clarifications)
│       ├── migrar_socios.py                       # hojas Cuenta Sergio/Lucy/Cond LSC/Ceci → MovimientosCuentaSocio
│       ├── migrar_caja_giamigli_sa.py             # hoja Caja Efectivo Pesos → MovimientosCajaEfectivo
│       │                                          # + dedup contra Pagos efectivo (FR-008)
│       └── migrar_caja_chica_campo.py             # hoja Caja chica campo → MovimientosCajaEfectivo
├── src/features/
│   ├── cuentas_socios/                            # existente (021), extendido
│   │   ├── repository.py                          # + importeUSD/importeKgCarne, saldo en 3 monedas
│   │   ├── router.py                               # sin cambios de rutas, solo de payload
│   │   └── schemas.py                              # + campos USD/Kg carne
│   ├── cajas_efectivo/                             # módulo nuevo, 100% solo lectura
│   │   ├── __init__.py
│   │   ├── repository.py                           # listar_movimientos(caja), calcular_saldo(caja)
│   │   ├── router.py                               # GET /api/cajas-efectivo/{caja}/movimientos, /saldo
│   │   └── schemas.py
│   └── migracion_cajas_giamigli/                   # módulo nuevo, solo lectura de la cola de revisión
│       ├── __init__.py
│       ├── repository.py                           # listar_casos_a_revisar()
│       ├── router.py                               # GET /api/migracion-cajas-giamigli/revision
│       └── schemas.py
└── tests/
    ├── test_migracion_cajas_giamigli_lector.py     # parseo/normalización de filas (fixtures, sin Excel real)
    ├── test_migracion_cajas_giamigli_dedup.py       # regla de coincidencia fecha+proveedor+importe
    ├── test_cuentas_socios_repository.py            # existente, + casos de USD/Kg carne
    ├── test_cajas_efectivo_repository.py
    ├── test_cajas_efectivo_router.py
    └── test_migracion_cajas_giamigli_router.py

frontend/
└── src/
    ├── services/
    │   ├── cuentasSociosApi.ts                     # existente, + campos USD/Kg carne
    │   └── cajasEfectivoApi.ts                     # nuevo
    ├── components/
    │   ├── cuentas-socios/
    │   │   └── CuentaSocio.tsx                     # existente, + columnas/saldos USD y Kg carne
    │   └── cajas-efectivo/
    │       └── CajaEfectivo.tsx                     # nuevo, análogo a CuentaCorriente.tsx (004) pero de solo lectura
    └── app/
        └── finanzas/
            └── cajas-efectivo/
                └── [caja]/page.tsx                  # nuevo: 'giamigli-sa' | 'campo-chica'
```

**Structure Decision**: mismo patrón de módulo por feature que `backend/src/features/*` (004/020/021). Las 2 cajas nuevas comparten un único módulo (`cajas_efectivo`) parametrizado por `caja` en vez de dos módulos casi idénticos, porque su estructura de datos y su único caso de uso (consulta de solo lectura) son idénticos — evita duplicar repository/router/schemas para una diferencia que es solo de datos, no de comportamiento. La migración en sí vive en `backend/scripts/` (no en `src/features/`) porque es una operación one-off sobre datos históricos cerrados (spec Assumptions), no un flujo que la aplicación vuelva a ejecutar — mismo criterio que `cargar_boletas_uatre_faltantes.py`.

## Complexity Tracking

*Sin violaciones de la Constitución — sección no aplica.*
