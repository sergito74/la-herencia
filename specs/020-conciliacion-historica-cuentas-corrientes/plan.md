# Implementation Plan: Conciliación histórica de cuentas corrientes de proveedores y ventas

**Branch**: `020-conciliacion-historica-cuentas-corrientes` | **Date**: 2026-09-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/020-conciliacion-historica-cuentas-corrientes/spec.md`

## Summary

Aplicar retroactivamente los movimientos de tesorería históricos (2015 hasta el corte 2025-09-01) contra sus compras/ventas usando la lógica FIFO ya construida en 019, marcando explícitamente los casos de "mejor esfuerzo" (coincidencia aproximada) y dejando en un listado de excepciones los que no tienen ningún documento candidato. Se agrega un script one-off (`--apply`/dry-run, mismo patrón que `migrar_ordenes.py`) para generar las aplicaciones, dos columnas nuevas en `AplicacionesPago` (`Origen`, `NotaConciliacion`) para distinguirlas de las manuales, endpoints de solo lectura para revisar el resultado por contacto, y una comparación de saldo contra una tabla de referencia cargada desde una exportación puntual de Access (`SaldosReferenciaAccess`). No se toca el cálculo de saldo de 004 ni la atribución de 018/019.

## Technical Context

**Language/Version**: Python 3.11 (backend existente), TypeScript/Next.js (frontend existente)

**Primary Dependencies**: FastAPI (backend, ya en uso), pyodbc (SQL Server), TanStack Query (frontend)

**Storage**: SQL Server `WC` — extiende `AplicacionesPago` (019), agrega `SaldosReferenciaAccess`

**Testing**: pytest (backend), contra datos reales de `WC` igual que 019/004 (`test_conciliacion_historico_*.py`)

**Target Platform**: Windows (mismo entorno de desarrollo/servidor que el resto del sistema)

**Project Type**: web application (backend + frontend existentes, esta feature agrega un módulo backend + un script CLI + una pantalla de revisión simple en frontend)

**Performance Goals**: el script procesa el histórico completo (miles de movimientos) en una corrida batch; no es un endpoint interactivo, no aplica un objetivo de latencia por request salvo los endpoints de lectura (`GET`, deben responder en el orden de los que ya expone 004/019)

**Constraints**: no debe modificar `LaHerencia` (protegida); no debe alterar el cálculo de saldo/atribución existente de 004/018/019; debe ser re-ejecutable sin duplicar aplicaciones

**Scale/Scope**: todos los contactos con movimientos de tesorería en 2015-2026 (alcance confirmado con el usuario); 3 endpoints de lectura nuevos, 1 script CLI, 1 script de carga de referencia, 2 columnas + 1 tabla nueva

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. SQL Server es el sistema de registro**: el script y los endpoints operan exclusivamente sobre `WC`; `SaldosReferenciaAccess` es una tabla nueva en `WC`, no una conexión a los `.accdb` — cumple.
- **II. Protección de datos reales**: el script corre en dry-run por defecto y requiere `--apply` explícito; se documenta en el propio contrato (`contracts/cli-script.md`) que el operador debe verificar backup de `WC` antes de `--apply` — cumple, mismo patrón que `migrar_ordenes.py`.
- **III. Procesos de negocio, no tablas crudas**: la pantalla de revisión (US2) y la de verificación de saldo (US3) presentan un flujo de auditoría completo (resumen por contacto → detalle → corrección vía mecanismo existente), no un CRUD de la tabla — cumple.
- **IV. Trazabilidad y significado financiero explícito**: cada aplicación automática queda marcada con su `Origen` y, si es mejor esfuerzo, con el detalle de la diferencia en `NotaConciliacion`; nunca se oculta que una aplicación no es exacta — cumple.
- **V. Contract-first, integración testeada**: contratos documentados en `contracts/` antes de implementar; se agregan tests pytest contra `WC` (dry-run y `--apply` sobre datos de prueba acotados) — cumple, a detallar en tasks.
- **VI. Colaboración de especialistas**: las decisiones de tolerancia (2%) y de alcance (todos los contactos, mejor esfuerzo) ya se acordaron explícitamente con el usuario antes de este plan — cumple.
- **VII. Simplicidad y reversibilidad**: se reutiliza `sugerencia.sugerir`/`documentos.documentos_pendientes` de 019 sin reescribirlos; cada aplicación automática es anulable individualmente con el mecanismo ya existente, sin necesidad de un "rollback de script" — cumple.
- **VIII. Stack aprobado**: Python + SQL Server + Next.js/TypeScript/Tailwind/TanStack Query, sin introducir nada nuevo — cumple.

Sin violaciones; no aplica la sección de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   ├── conciliar_historico_cuentas_corrientes.py   # nuevo: dry-run/--apply
│   └── cargar_saldos_referencia_access.py          # nuevo: carga CSV -> SaldosReferenciaAccess
├── src/features/
│   ├── aplicaciones_pago/                          # existente (019), reutilizada sin cambios de contrato
│   │   ├── sugerencia.py
│   │   ├── documentos.py
│   │   └── repository.py
│   ├── cuentas_corrientes/                         # existente (004), reutilizada sin cambios
│   │   └── repository.py
│   └── conciliacion_historico/                     # nuevo módulo
│       ├── __init__.py
│       ├── repository.py     # resumen por contacto, detalle, comparación de saldo
│       ├── router.py         # GET /api/conciliacion-historico/*
│       └── schemas.py
└── tests/
    ├── test_conciliacion_historico_script.py       # dry-run, --apply, idempotencia
    └── test_conciliacion_historico_endpoints.py    # resumen/detalle/saldos

frontend/
└── src/
    └── (pantalla de revisión bajo el área de finanzas/cuentas corrientes existente;
        ruta y componente exactos a definir en tasks, reutilizando el layout de 004/019)
```

**Structure Decision**: se sigue la estructura de módulo por feature ya usada en `backend/src/features/*` (patrón de 004/019), con un módulo nuevo `conciliacion_historico` que solo lee/agrega sobre `AplicacionesPago` y agrega `SaldosReferenciaAccess`, sin modificar los módulos existentes. El proceso de aplicación en sí vive como script en `backend/scripts/`, no como endpoint, siguiendo el precedente de `migrar_ordenes.py`/`migrar_remitos.py`.

## Complexity Tracking

*Sin violaciones de la Constitución — sección no aplica.*
