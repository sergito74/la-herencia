# Implementation Plan: Integridad de vínculos entre pagos y documentos

**Branch**: `031-integridad-vinculos` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/031-integridad-vinculos/spec.md`

## Summary

Hoy cinco tablas guardan vínculos pago → documento, y cada pantalla lee solo algunas. El plan crea un módulo `features/vinculos/` que las unifica con reglas de cadena:

- el débito de un resumen hereda los consumos imputados;
- el débito de un cheque hereda los documentos del cheque;
- las aplicaciones directas redundantes no suman.

El flujo 030, el saldo por factura y un control de integridad leen de ese módulo.

La causa raíz de las aplicaciones erróneas es el FIFO de `sugerencia.sugerir`: no controla fechas, compara us$ contra $ y no ve los pagos con tarjeta ni con cheque. Se corrige en el código y en los datos. Los datos se corrigen con lotes revisables (agrupados por motivo y certeza), con backup verificado, anulación sin borrar, reemplazos propuestos y reversión. Al guardar un vínculo nuevo, un exceso de más del 2% se bloquea.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript / Next.js (frontend)

**Primary Dependencies**: FastAPI, pyodbc, pytest. React con los componentes existentes (SideDrawer, tablas de 029).

**Storage**: SQL Server, base `WC`. Dos tablas nuevas (`CorreccionVinculosLote`, `CorreccionVinculosItem`). Las escrituras en `AplicacionesPago` solo anulan o insertan.

**Testing**: pytest con funciones puras más contract tests con monkeypatch (patrón 030). Validación final sobre WC real.

**Target Platform**: escritorio Windows, un único usuario.

**Project Type**: aplicación web (backend + frontend).

**Performance Goals**: control completo en menos de 10 s (SC-005). El flujo 030 no debe empeorar más de 2 s.

**Constraints**:

- Nunca escribir en LaHerencia.
- Backup verificado antes de crear las tablas y antes de aplicar cada lote.
- Las aplicaciones manuales no se tocan.

**Scale/Scope**: ≈ 8,4 k aplicaciones, 1,6 k imputaciones de tarjeta, 229 pagos de resumen, 1,1 k cheques, ≈ 2 k ítems de corrección.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. SQL Server es el sistema de registro**: toda la lectura y escritura se hace contra `WC`. Cumple.
- **II. Protección de datos reales**: se toma un backup `COPY_ONLY, CHECKSUM` + `RESTORE VERIFYONLY` antes de crear las tablas y antes de aplicar cada lote. No se borra nada: se anula, y cada lote se puede revertir. Cumple.
- **III. Procesos de negocio**: se modela la cadena real de pago (factura ← consumo o cheque ← débito bancario), tal como la describió Sergio. Cumple.
- **IV. Trazabilidad y significado financiero**:
  - Cada vínculo conserva su vía y su registro de origen.
  - Las anulaciones llevan motivo, usuario y fecha.
  - Pesificar crea una aplicación nueva y conserva la original.
  - Cumple.
- **V. Contract-first**: el contrato está en [contracts/api.md](contracts/api.md), con tests de las reglas puras antes de las escrituras. Cumple.
- **VI. Especialistas**: las reglas de precedencia, el margen de 60 días y la tolerancia del 2% las decidió Sergio. Antes de aplicar el primer lote real, se hará una revisión con la persona del agente contable (`.github/agents`). Cumple.
- **VII. Simplicidad y cambio reversible**: se reusa el patrón de lotes de 029 y el esquema existente de `AplicacionesPago`, sin vistas SQL nuevas. Cumple.
- **VIII. Stack aprobado**: sin agregados. Cumple.

Sin violaciones. Re-chequeo post diseño: sin cambios.

## Project Structure

### Documentation (this feature)

```text
specs/031-integridad-vinculos/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
└── tasks.md          # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   └── crear_tablas_031.py              # backup verificado + CREATE TABLE
├── src/features/vinculos/               # NUEVO
│   ├── fuente.py         # carga en bloque de las 5 vías → Vinculo[]
│   ├── cadenas.py        # resumen→consumos, cheque↔débito, exclusión de redundantes
│   ├── control.py        # hallazgos de integridad
│   ├── correccion.py     # propuesta: anular / pesificar / reemplazo, certeza y grupos
│   ├── lotes.py          # persistencia, backup, aplicar, revertir
│   ├── validacion.py     # verificar_exceso (FR-012)
│   ├── router.py / schemas.py
├── src/features/aplicaciones_pago/
│   ├── sugerencia.py     # FIFO con margen de fecha y pesificación
│   ├── documentos.py     # saldo pendiente desde la fuente unificada
│   └── repository.py     # verificar_exceso al crear
├── src/features/tarjetas_resumenes/repository.py   # verificar_exceso al imputar
├── src/features/conciliacion_tesoreria/repository.py
├── src/features/flujo_caja/repository.py           # partes desde la fuente unificada
└── tests/
    ├── test_vinculos_fuente_cadenas.py
    ├── test_vinculos_control_correccion.py
    ├── test_vinculos_lotes.py
    └── contract/test_integridad_vinculos_api.py

frontend/src/
├── app/finanzas/integridad-vinculos/page.tsx
├── components/integridad/ControlIntegridad.tsx
├── components/integridad/RevisionLote.tsx
└── services/integridadVinculosApi.ts
```

**Structure Decision**: aplicación web existente. El módulo nuevo va en `features/vinculos/` y los consumidores actuales se modifican en su lugar.

## Orden de entrega

1. Fuente unificada + control, solo lectura. Se obtiene la línea de base sin riesgo.
2. Flujo 030 y saldo por factura leyendo la fuente, junto con la corrección del FIFO.
3. Tablas de lote + propuesta + revisión en la UI.
4. Aplicar y revertir con backup, revisión del especialista y primer lote real con Sergio.
5. Bloqueo al guardar en las pantallas de vinculación.

## Complexity Tracking

Sin violaciones.
