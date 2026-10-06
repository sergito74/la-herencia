# Implementation Plan: Cuentas de tarjetas y de Mercado Pago

**Branch**: `034-cuenta-corriente-tarjetas` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/034-cuenta-corriente-tarjetas/spec.md`

## Summary

Cada entidad de tarjeta pasa a tener en la cuenta corriente compartida (`vw_MovimientosCuenta_Base`) su **pata deuda**: cada consumo en su fecha de consumo y los cargos propios de cada resumen en la fecha de cierre, además de los pagos bancarios que ya recibía como crédito. Los saldos de proveedores no cambian, salvo el pago real de UATRE hecho con fondos de la billetera de Mercado Pago (+$17.185,82). Mercado Pago recibe las reglas de un banco (movimientos con contacto acreditan, "conducto" se atribuye al banco de origen) sin pantalla nueva. Se agregan un **control de integridad** (anomalías y posibles duplicaciones) y **cruces con visto bueno** (devolución↔débito de tarjeta y devolución de billetera↔consumo), ambos semi automáticos. La UI extiende las pantallas de 008 (cuenta de la tarjeta) y suma una pantalla de control; no hay pantalla nueva para Mercado Pago.

Enfoque técnico: un script idempotente con backup verificado crea dos tablas pequeñas y amplía la vista con cuatro ramas nuevas (sin tocar las existentes); un módulo backend nuevo (`tarjetas_cuenta`) expone lectura, control y cruces; el frontend reutiliza los componentes de tarjetas y el patrón de integridad de 031.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript con Next.js 14 (frontend)

**Primary Dependencies**: FastAPI, pyodbc, openpyxl (exportación); React, TanStack Query, Tailwind CSS

**Storage**: SQL Server, base `WC` (producción). Dos tablas nuevas y cuatro ramas nuevas en la vista compartida; `LaHerencia` y los archivos Access no se tocan

**Testing**: pytest (contratos con `httpx.AsyncClient`, fixtures puros para el cálculo y el control, pruebas de solo lectura sobre `WC` para las invariantes); `tsc --noEmit` y script e2e con Playwright para el frontend

**Target Platform**: Windows con SQL Server local; navegador de escritorio

**Project Type**: Aplicación web (backend + frontend), patrón de módulos por funcionalidad ya existente

**Performance Goals**: cuenta completa de la tarjeta con más historia (AgroNacion: 113 resúmenes, 149 pagos, unas 1.800 líneas de consumo) en menos de 3 segundos (SC-005)

**Constraints**: los saldos de contactos que no son tarjetas no cambian (salvo UATRE, FR-005); el flujo de caja real no cambia (FR-017); backup verificado antes de cambios de estructura o escrituras masivas; el módulo `flujo_caja` no consulta las ramas nuevas

**Scale/Scope**: 5 tarjetas, ~1.800 líneas de consumo vigentes, 318 resúmenes, 343 pagos de resumen; 1 contacto (UATRE) con efecto en saldos; 9 endpoints nuevos y 2 pantallas (extensión de la cuenta de la tarjeta y panel de control)

## Constitution Check

*GATE: debe pasar antes de la investigación (Fase 0) y revisarse tras el diseño (Fase 1).*

| Principio | Evaluación |
|---|---|
| I. SQL Server es el sistema de registro | Cumple: todo se lee y escribe en `WC`; no se escribe en `LaHerencia` ni en Access. |
| II. Protección de datos reales | Cumple: backup verificado antes de crear tablas, ampliar la vista y reasignar movimientos; la vista previa se guarda para poder revertir; las pruebas usan fixtures y las de `WC` son de solo lectura. |
| III. Procesos antes que tablas | Cumple: la pantalla guía de "cuánto debo a cada tarjeta" al detalle y al origen; el control y los cruces son procesos, no tablas. |
| IV. Trazabilidad y significado financiero | Cumple: cada fila indica origen, documento o movimiento, deuda, crédito y saldo; los cruces registran usuario, fecha y sugerencia. |
| V. Contrato primero, probado | Cumple: contratos en `contracts/` y pruebas de contrato antes de la UI. |
| VI. Colaboración con especialistas | A cumplir: consultar al especialista financiero (`.github/agents`) en el punto de control antes de implementar (supuestos de fecha de deuda, conducto y apertura); registrado en las tareas. |
| VII. Simplicidad y cambio reversible | Cumple: se reutilizan la vista, 008 y el patrón de 031; dos tablas mínimas; sin pantalla de Mercado Pago; la vista se puede restaurar con el script de reversión. |
| VIII. Stack aprobado | Cumple: Python/FastAPI, SQL Server, Next.js/TypeScript, Tailwind, TanStack Query. |

Resultado: sin violaciones. Revalidado tras el diseño (Fase 1): sin cambios.

## Project Structure

### Documentation (this feature)

```text
specs/034-cuenta-corriente-tarjetas/
├── plan.md              # Este archivo
├── research.md          # Decisiones y alternativas
├── data-model.md        # Tablas nuevas, ramas de la vista y entidades derivadas
├── quickstart.md        # Guía de validación de extremo a extremo
├── contracts/
│   └── tarjetas-cuenta-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Lo genera /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── scripts/
│   ├── vista_tarjeta_cuenta_corriente.py      # tablas + ramas de la vista, idempotente, con backup y reversión
│   └── preparar_tarjetas_cuenta_034.py        # reasignaciones de saldo inicial y verificación antes/después
├── src/features/
│   ├── tarjetas_cuenta/                       # módulo nuevo
│   │   ├── repository.py                      # cuenta por tarjeta, resumen de las cinco, cuotas a vencer
│   │   ├── control.py                         # función pura: hallazgos (a)-(j)
│   │   ├── cruces.py                          # sugerencias y alta/baja de cruces
│   │   ├── exportacion.py                     # xlsx de la cuenta y del control
│   │   ├── router.py
│   │   └── schemas.py
│   ├── tarjetas/repository.py                 # get_id_contacto_tarjeta pasa a leer la tabla explícita
│   ├── cuentas_corrientes/origen_resolver.py  # resuelve los orígenes nuevos de la vista
│   └── tesoreria/                             # marca de "conducto" en los movimientos de Mercado Libre
└── tests/
    ├── contract/test_tarjetas_cuenta_api.py
    ├── test_tarjetas_cuenta_control.py
    ├── test_tarjetas_cuenta_cruces.py
    └── test_vista_cuenta_tarjetas.py          # invariantes de solo lectura contra WC

frontend/
└── src/
    ├── app/finanzas/tarjetas/
    │   ├── page.tsx                           # resumen de las cinco tarjetas con saldo
    │   ├── [idTarjeta]/cuenta-corriente/      # se extiende: consumos, cargos, pagos, cuotas a vencer
    │   └── control/page.tsx                   # panel de control y cruces
    ├── components/tarjetas-cuenta/            # tabla de la cuenta, panel de control, diálogo de cruce
    └── services/tarjetasCuentaApi.ts
```

**Structure Decision**: aplicación web con módulo backend nuevo por funcionalidad (como 031 y 032) y extensión de la ruta de cuenta corriente de tarjetas de 008. Todo el cálculo contable vive en la vista compartida para que la lista general de cuentas corrientes y sus totales reflejen a las tarjetas sin código adicional; el módulo nuevo agrega lectura específica por tarjeta, control y cruces.

## Complexity Tracking

Sin violaciones de la constitución que justificar. Dos tablas nuevas (`TarjetasContacto`, `TarjetasCruces`) son el mínimo para cumplir FR-006 y FR-022 sin alterar tablas heredadas.
