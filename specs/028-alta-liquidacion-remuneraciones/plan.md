# Implementation Plan: Alta de liquidación de remuneraciones

**Branch**: `028-alta-liquidacion-remuneraciones` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/028-alta-liquidacion-remuneraciones/spec.md`

## Summary

Primera escritura del módulo Remuneraciones (hoy 100% GET-only): una pantalla para cargar una liquidación mensual nueva — elegir empleado (Contacto tipo Empleado), completar los ~15 conceptos monetarios (siempre en positivo, como en el recibo real) y opcionalmente adjuntar el PDF del recibo escaneado. El backend calcula el importe neto restando los conceptos de descuento (misma fórmula que ya usa `vw_MovimientosCuenta_Base`) y de paso corrige el bug ya existente del listado (`_IMPORTE_SQL`, que hoy suma todo sin restar). El PDF se guarda en la carpeta real de recibos con un nombre de archivo estandarizado y su ruta relativa se escribe en `dbo.Remuneraciones.Recibo` — la misma columna que ya lee el listado y el matching por archivo agregados en la sesión anterior (backlog post-025). Advierte pero no bloquea duplicados de empleado+período.

## Technical Context

**Language/Version**: Python 3.11 (backend existente), TypeScript/Next.js (frontend existente)

**Primary Dependencies**: FastAPI (incl. `UploadFile`, mismo patrón que `tesoreria/router.py::validar_excel`), pyodbc (SQL Server), TanStack Query — todas ya en uso, sin agregar nada nuevo

**Storage**: SQL Server `WC` (producción post-corte) — sin tablas nuevas: escribe en `dbo.Remuneraciones` (tabla existente, hoy solo leída) y en el filesystem local (carpeta real de recibos, ya usada en solo lectura desde la sesión anterior)

**Testing**: pytest (backend) — validación de fórmulas puras (neto, nombre de archivo) con unit tests; validación del flujo completo contra `WC` real con dry-run manual (mismo criterio que 021/025/027), nunca desde tests automatizados

**Target Platform**: Windows (mismo entorno que el resto del sistema)

**Project Type**: web application (backend + frontend existentes) — extensión de un módulo existente (`remuneraciones`), sin módulos nuevos

**Performance Goals**: sin requerimiento especial — alta manual y esporádica (una liquidación por empleado por mes, ~5 empleados activos), mismo orden que el resto de los módulos de alta de este sistema

**Constraints**: NO debe modificar el comportamiento de los endpoints de lectura ya existentes salvo la corrección explícita de FR-015 (fórmula de importe neto); nunca escribe en `LaHerencia`; el nombre de archivo nuevo debe seguir siendo encontrado por `buscar_archivo_recibo` (matching CamelCase ya implementado) aun si no se llega a escribir la columna `Recibo` por algún motivo — redundancia intencional, no unifica ambos mecanismos en uno

**Scale/Scope**: 1 tabla existente (sin DDL), 3 endpoints nuevos (alta de liquidación, adjuntar/reemplazar recibo sobre una liquidación existente, chequeo de duplicado), 1 formulario nuevo integrado a la pantalla de Remuneraciones ya existente

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. SQL Server es el sistema de registro**: toda la escritura ocurre exclusivamente contra `WC` (producción post-corte) — cumple.
- **II. Protección de datos reales**: no hay cambio de esquema (la tabla y la columna `Recibo` ya existen) — la escritura de alta es una escritura de tarea normal, sin requerir backup por operación, mismo criterio que 021/025/027; solo si algún ajuste de esquema resultara necesario en el camino (no previsto) se pediría backup verificado antes — cumple.
- **III. Procesos de negocio, no tablas crudas**: la pantalla no es un INSERT crudo de `Remuneraciones` — sigue el flujo real (elegir empleado → completar conceptos del recibo real → ver el neto calculado → opcionalmente adjuntar el PDF → queda visible en el mismo listado y cuenta corriente del empleado) — cumple.
- **IV. Trazabilidad y significado financiero explícito**: distingue explícitamente haberes de descuentos (FR-014), corrige el cálculo para que el "importe" mostrado sea un neto con sentido financiero real, y el PDF queda trazable por `IdSalario` — cumple.
- **V. Contract-first, integración testeada**: contratos documentados en `contracts/api.md` antes de implementar; tests unitarios de la fórmula de neto y del nombrado de archivo; validación manual contra `WC` real (dry-run) antes de dar por cerrada la feature — a detallar en tasks.
- **VI. Colaboración de especialistas**: decisión de signos de conceptos y alcance resuelta con el usuario en `/speckit-clarify` (sesión 2026-09-30) — cumple.
- **VII. Simplicidad y reversibilidad**: no agrega tablas nuevas, reusa columnas y convenciones ya existentes (`Recibo`, carpeta de recibos, `ContactoSelect`, `UploadFile`); la corrección de FR-015 es un cambio acotado a una expresión SQL, no un rediseño — cumple.
- **VIII. Stack aprobado**: Python + SQL Server + Next.js/TypeScript/Tailwind/TanStack Query, sin introducir nada nuevo — cumple.

Sin violaciones; no aplica la sección de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/028-alta-liquidacion-remuneraciones/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)

```text
backend/
└── src/features/remuneraciones/     # módulo existente, se extiende (no se crea)
    ├── repository.py    # + calcular_neto(), + crear_liquidacion(), + adjuntar_recibo(),
    │                     #   + existe_liquidacion_periodo(); corrige _IMPORTE_SQL (FR-015)
    ├── router.py         # + POST "" (alta), + POST "/{id_salario}/recibo" (adjuntar/reemplazar PDF)
    └── schemas.py        # + NuevaLiquidacionRequest, + validación de conceptos

backend/tests/
├── test_remuneraciones_alta.py       # nuevo: fórmula de neto, duplicados, nombrado de archivo
└── test_remuneraciones_recibo.py     # existente: sin cambios de comportamiento

frontend/
└── src/
    ├── services/remuneracionesApi.ts       # + crearLiquidacion(), + subirRecibo()
    └── components/remuneraciones/
        ├── RemuneracionesListado.tsx        # existente: botón "Nueva liquidación" (SoloLectura)
        └── NuevaLiquidacionForm.tsx          # nuevo: formulario de alta + adjuntar PDF
```

**Structure Decision**: extensión pura del módulo `remuneraciones` ya existente en ambos lados (backend/frontend) — no se crea ningún módulo ni tabla nueva. El único archivo tocado fuera de `remuneraciones/` es el botón de entrada en `RemuneracionesListado.tsx` (ya existente, agregado en la sesión anterior).

## Complexity Tracking

*Sin violaciones de la Constitución — sección no aplica.*
