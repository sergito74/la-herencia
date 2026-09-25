# Implementation Plan: Cuentas corrientes de socios/directores y condominio

**Branch**: `021-cuentas-socios` | **Date**: 2026-09-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-cuentas-socios/spec.md`

## Summary

Cuando un gasto pagado por la empresa (típicamente una compra "particular" con tarjeta, ya neteada a $0 en su propio total) le corresponde en realidad a un socio, el sistema debe reflejar automáticamente esa deuda en una cuenta corriente propia de ese socio — sin que la empresa quede con un gasto o una deuda falsa. Catálogo cerrado de 4 socios (Sergio, Lucy, Cond LSC, Ceci). Cada asignación (y su reversión) queda en una tabla de auditoría dedicada, separada del propio movimiento (que es inmutable, se anula no se borra — mismo patrón que `AplicacionesPago`, 019). Incluye devoluciones manuales cuando el socio compensa a la empresa, y una pantalla de cuenta corriente por socio. Reutiliza la fórmula de "importe bruto de una compra particular" ya corregida en tarjetas (008/009), extraída a una función compartida.

## Technical Context

**Language/Version**: Python 3.11 (backend existente), TypeScript/Next.js (frontend existente)

**Primary Dependencies**: FastAPI, pyodbc (SQL Server), TanStack Query — todas ya en uso, sin agregar nada nuevo

**Storage**: SQL Server `WC` (producción post-corte) — 3 tablas nuevas: `Socios`, `MovimientosCuentaSocio`, `AuditoriaReflejoSocio`

**Testing**: pytest (backend), mismo criterio que 004/019/020: tests unitarios con monkeypatch para lógica/endpoints, validación manual contra datos reales de `WC` para el flujo completo (no se escribe en `WC` real desde tests automatizados)

**Target Platform**: Windows (mismo entorno que el resto del sistema)

**Project Type**: web application (backend + frontend existentes) — un módulo nuevo en cada lado

**Performance Goals**: mismo orden que 004 (lecturas de cuenta corriente por contacto) — no hay volumen de datos significativo (4 socios, movimientos manuales/esporádicos), sin requerimiento de performance especial

**Constraints**: no debe modificar el cálculo de saldo/cuenta corriente de proveedores (004) ni la conciliación de tarjetas (008/009) — solo lee de ahí (`Compras`, `Det_Compras`) para calcular el importe bruto; nunca escribe en `LaHerencia` (frozen, post-corte)

**Scale/Scope**: 3 tablas nuevas, ~5 endpoints de lectura/escritura, 1 pantalla de listado (4 socios) + 1 de detalle por socio, reutilización de un flujo de selección de compras particulares candidatas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. SQL Server es el sistema de registro**: todo el desarrollo (esquema, lectura, escritura) opera exclusivamente sobre `WC` (producción post-corte, Amendment 1.4.0) — cumple.
- **II. Protección de datos reales**: el script de esquema requiere backup verificado antes de correr (es un cambio de esquema, aunque aditivo/bajo riesgo); las escrituras normales de la feature (asignar, anular, devolución) son escritura de tarea normal, sin requerir confirmación por operación — mismo criterio que 019/020 — cumple.
- **III. Procesos de negocio, no tablas crudas**: la pantalla no es un CRUD de `MovimientosCuentaSocio` — sigue el flujo real (elegir compra particular candidata → asignar → ver reflejado en la cuenta del socio → eventualmente compensar) — cumple.
- **IV. Trazabilidad y significado financiero explícito**: cada movimiento distingue deuda/crédito (`Tipo`), origen real (`Origen`/`IdOrigen`), y cada acción queda registrada en `AuditoriaReflejoSocio` — cumple.
- **V. Contract-first, integración testeada**: contratos (`contracts/api.md`, `contracts/schema-script.md`) documentados antes de implementar; tests unitarios + validación manual contra `WC` real, mismo patrón que 004/019/020 — cumple, a detallar en tasks.
- **VI. Colaboración de especialistas**: el diseño central (catálogo cerrado, `MovimientosCuentaSocio`, `AuditoriaReflejoSocio` dedicada, reflejo automático reversible) ya fue decidido con el equipo de especialistas el 2026-09-24, recuperado y confirmado en esta sesión — cumple.
- **VII. Simplicidad y reversibilidad**: reutiliza el patrón de inmutabilidad de 019 y la fórmula de importe bruto de 008/009 (extraída a función compartida, no duplicada); cada movimiento es anulable individualmente, sin necesidad de un "deshacer" a nivel transacción completa — cumple.
- **VIII. Stack aprobado**: Python + SQL Server + Next.js/TypeScript/Tailwind/TanStack Query, sin introducir nada nuevo — cumple.

Sin violaciones; no aplica la sección de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/021-cuentas-socios/
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
│   └── crear_tablas_cuentas_socios.py       # nuevo: DDL idempotente, 3 tablas + catálogo fijo
├── src/features/
│   ├── tarjetas_resumenes/
│   │   └── conciliacion_documentos.py        # existente (008/009): se extrae de acá (o de repository.py)
│   │                                          # la función de importe bruto de "compra particular",
│   │                                          # para reutilizarla sin duplicar la consulta SQL
│   └── cuentas_socios/                       # módulo nuevo
│       ├── __init__.py
│       ├── repository.py     # Socios, MovimientosCuentaSocio, AuditoriaReflejoSocio, saldo, compras candidatas
│       ├── router.py         # endpoints de contracts/api.md
│       └── schemas.py
└── tests/
    ├── test_cuentas_socios_repository.py
    └── test_cuentas_socios_endpoints.py

frontend/
└── src/
    ├── services/
    │   └── cuentasSociosApi.ts
    ├── components/
    │   └── cuentas-socios/
    │       ├── SociosListado.tsx      # los 4 socios + saldo (análogo a SaldosListado.tsx, 004)
    │       └── CuentaSocio.tsx        # detalle: saldo + movimientos + asignar gasto + registrar devolución
    └── app/
        └── finanzas/
            └── cuentas-socios/
                ├── page.tsx                    # listado
                └── [idSocio]/page.tsx           # detalle
```

**Structure Decision**: mismo patrón de módulo por feature que `backend/src/features/*` (004/019/020). La única pieza compartida entre módulos es la función de "importe bruto de compra particular", que se extrae de `tarjetas_resumenes` a un lugar reusable (research.md §3) en vez de duplicarse — el resto del módulo (`cuentas_socios`) es autocontenido y no modifica ningún módulo existente.

## Complexity Tracking

*Sin violaciones de la Constitución — sección no aplica.*
