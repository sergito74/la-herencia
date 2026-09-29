# Implementation Plan: Reasignación de contacto en movimientos de cuenta corriente

**Branch**: `022-reasignacion-contacto` | **Date**: 2026-09-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/022-reasignacion-contacto/spec.md`

## Summary

Permitir corregir, desde la propia cuenta corriente de un proveedor, un movimiento cuyo contacto quedó mal asignado (caso real: una transferencia bancaria de $159.720 asignada a "Carbajo, Juan Manuel" cuando el texto decía "Encode S.A."), con confirmación explícita y trazabilidad completa (US1/MVP); una función de detección que sugiere candidatos sobre movimientos bancarios comparando el texto de la descripción contra nombres de otros contactos, descartando ruido de términos genéricos (US2); y una consulta de historial de reasignaciones (US3).

Enfoque técnico: una tabla nueva `ReasignacionesContacto` (insert-only, mismo patrón que `MovimientosCuentaSocio`/`AplicacionesPago` — nunca UPDATE/DELETE, la fila más reciente por `(Origen, IdOrigen)` es la vigente) actúa como capa de *override* que se aplica en la vista que alimenta la cuenta corriente (`vw_MovimientosCuenta_Base`), sin tocar las tablas de origen (`Movimientos Galicia`, `Movimientos BNA`, `Tarjetas_Resumenes_Lineas_Compras`/`Compras`). Esto resuelve FR-014 (no tocar la Compra vinculada) de forma uniforme para todos los orígenes soportados, y además deja un historial completo (FR-013) sin necesitar una columna "vigente" mutable. La detección (US2) es una consulta de solo lectura sobre `Movimientos Galicia`/`Movimientos BNA` con una tabla chica `CandidatosDescartados` (insert-only) para recordar qué sugerencias fueron descartadas como falso positivo.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5 (frontend Next.js)

**Primary Dependencies**: FastAPI, pyodbc (backend); Next.js, TanStack Query, Tailwind CSS (frontend) — mismo stack que 004/019/020/021 (Constitución, Principio VIII)

**Storage**: SQL Server `WC` (producción post-corte, Constitución Amendment 1.4.0)

**Testing**: pytest con monkeypatch sobre `repository` (mismo criterio que 019/020/021); validación manual contra `WC` real con backup previo para el flujo completo

**Target Platform**: Web interno (mismo entorno que el resto de la aplicación)

**Project Type**: Web application (backend + frontend), Option 2 de la estructura estándar del repo

**Performance Goals**: N/A — operación manual, baja frecuencia (corrección puntual, no un proceso masivo)

**Constraints**: La detección (US2) es de solo lectura y bajo demanda; nunca debe escribir por sí sola (FR-009). El override nunca debe modificar `Compras.IdContacto` ni las tablas bancarias de origen (FR-014).

**Scale/Scope**: Alcance inicial: movimientos bancarios (`Movimientos Galicia`, `Movimientos BNA`) y vínculos de tarjeta (`Tarjetas_Resumenes_Lineas_Compras`) — los dos orígenes con casos reales conocidos (Assumptions de spec.md). Volumen: ~3.300 movimientos de Galicia, cientos de BNA, ~1.400 vínculos de tarjeta — consultas puntuales, no procesamiento masivo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (SQL Server es el sistema de registro)**: cumple — toda lectura/escritura es sobre `WC`; no se toca `LaHerencia`.
- **Principio II (protección de datos reales)**: cumple — se toma backup verificado antes de crear el esquema nuevo (`ReasignacionesContacto`, `CandidatosDescartados`) y antes de cualquier reasignación real de validación, mismo criterio que 020/021.
- **Principio III (procesos de negocio, no tablas crudas)**: cumple — la reasignación se expone como una acción en el contexto de la cuenta corriente del proveedor, no como edición directa de una tabla.
- **Principio IV (trazabilidad y significado financiero explícito)**: cumple — es el requisito central de la feature (FR-004/FR-005/FR-013).
- **Principio V (contrato primero, integración probada)**: se sigue el mismo patrón: contrato en `contracts/api.md` antes de UI, tests con monkeypatch + validación real acotada.
- **Principio VI (colaboración de especialistas)**: no aplica un dominio agro específico nuevo; es una corrección transversal de cuentas corrientes ya cubierta por 004/020.
- **Principio VII (simplicidad, reversibilidad)**: el diseño de *override* insert-only evita tocar las tablas de origen (reversible: basta con no considerar la última fila) y reutiliza el patrón ya validado en 019/021 en vez de introducir uno nuevo.
- **Principio VIII (stack aprobado)**: Python/FastAPI + Next.js/TypeScript/Tailwind/TanStack Query — sin excepciones.

Sin violaciones. No se requiere `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/022-reasignacion-contacto/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── api.md
└── tasks.md              # Phase 2 output ($speckit-tasks — not created here)
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   └── crear_tablas_reasignacion_contacto.py   # DDL: ReasignacionesContacto, CandidatosDescartados
│   └── aplicar_override_reasignacion_en_vista.py  # ALTER VIEW: aplica el override en vw_MovimientosCuenta_Base
├── src/
│   └── features/
│       └── reasignacion_contacto/
│           ├── __init__.py
│           ├── repository.py   # reasignar, listar_historial, detectar_candidatos, descartar_candidato
│           ├── router.py       # /api/reasignacion-contacto/*
│           └── schemas.py
└── tests/
    ├── test_reasignacion_contacto_repository.py
    └── test_reasignacion_contacto_endpoints.py

frontend/
├── src/
│   ├── services/
│   │   └── reasignacionContactoApi.ts
│   ├── components/
│   │   ├── cuentas-corrientes/
│   │   │   └── ReasignarMovimientoButton.tsx   # botón en contexto (US1), integrado en CuentaCorriente.tsx
│   │   └── reasignacion-contacto/
│   │       └── CandidatosReasignacion.tsx      # pantalla de detección (US2)
│   └── app/
│       └── finanzas/
│           └── reasignacion-contacto/
│               └── page.tsx                    # US2 (detección) + US3 (historial)
```

**Structure Decision**: Web application estándar del repo (backend FastAPI + frontend Next.js), mismo layout que 004/019/020/021. El botón de reasignación (US1) se integra en el componente ya existente `CuentaCorriente.tsx` en vez de crear una pantalla nueva, siguiendo el requisito de "corregir en contexto" de la spec. La detección (US2) y el historial (US3) comparten una pantalla nueva bajo Finanzas.

## Complexity Tracking

*Sin violaciones — sección no aplica.*
