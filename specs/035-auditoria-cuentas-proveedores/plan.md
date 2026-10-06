# Implementation Plan: Auditoría de cuentas corrientes de proveedores

**Branch**: `035-auditoria-cuentas-proveedores` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/035-auditoria-cuentas-proveedores/spec.md`

## Summary

Se arma una verificación metódica de las cuentas de proveedores y clientes en cuatro piezas: (1) un **control de solo lectura** que compara el saldo de cada cuenta de `WC` contra la referencia del Access al 25/09/2026, explica la diferencia por causa y agrupa las excepciones; (2) una **regla de plazo** (24 meses, ajustable) que marca los pagos aplicados a facturas demasiado viejas, medida entre la fecha de la factura y la **fecha real del movimiento de pago**; (3) el **FIFO completo** reutilizando el motor de la feature 032 (simular, revisar, aplicar con respaldo, revertir), sin cambiar saldos; (4) **correcciones por regla** sobre un grupo de excepciones, con las cuentas tildadas una a una, respaldo verificado y reversión. Todo se apoya en lo existente: la vista `vw_MovimientosCuenta_Base`, `AplicacionesPago` (con baja lógica), `SaldosReferenciaAccess`, `CuentasARevisar` y el módulo `recalculo_fifo`. Medición previa en `WC` (06/10/2026): 10.110 aplicaciones vigentes; las 2.194 que superan 24 meses entre factura y fecha del movimiento (Banco Nación 1.477 por $5,5 M; Galicia 717 por $33,4 M) están en unos 110 contactos, todas de origen `automatica-exacta`.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript con Next.js 14 (frontend)

**Primary Dependencies**: FastAPI, pyodbc, pydantic, openpyxl; TanStack Query, Tailwind CSS

**Storage**: SQL Server `WC` (tablas nuevas: `AuditoriaParametros`, `AuditoriaCorrecciones`, `AuditoriaCorreccionesCuentas`; se reutilizan `AplicacionesPago`, `SaldosReferenciaAccess`, `CuentasARevisar`, `RecalculoFifo*`, `ReasignacionesContacto`, `AjustesCuentaCorriente`)

**Testing**: pytest (funciones puras con fixtures, pruebas de contrato con httpx, lecturas de solo lectura sobre `WC`), `npx tsc --noEmit`, recorrido de navegador con Playwright

**Target Platform**: aplicación web local de escritorio (launcher), Windows

**Project Type**: aplicación web (backend + frontend)

**Performance Goals**: el control completo de las cuentas en menos de 10 segundos; la simulación FIFO de todos los contactos en menos de 2 minutos

**Constraints**: solo se escribe en `WC`, nunca en `LaHerencia`; respaldo verificado antes de cada aplicación; todo reversible; umbral de $300 solo en pesos (nunca en dólares); el control no escribe; textos en español simple

**Scale/Scope**: unos 500 contactos con saldo de referencia (513), unas 10.000 aplicaciones de pago, FIFO aplicado a 7 contactos y unos 485 por recalcular, 8 cuentas hoy en `CuentasARevisar`

## Constitution Check

| Principio | Cumple | Cómo |
|---|---|---|
| I. SQL Server es el sistema de registro | Sí | Todo vive en `WC`; el Access solo aporta la referencia ya cargada |
| II. Protección de datos reales | Sí | Respaldo verificado antes de cada aplicación; nada se escribe en `LaHerencia`; el control es de solo lectura |
| III. Procesos antes que tablas | Sí | Una pantalla de auditoría por causa → grupo → cuenta → pago/factura |
| IV. Trazabilidad y significado financiero | Sí | Cada hallazgo muestra pago, factura, fechas, días, importe y causa; cada corrección guarda quién, cuándo, qué y cómo revertir |
| V. Contrato primero y probado | Sí | Contrato en `contracts/`; pruebas de contrato antes de la interfaz |
| VI. Colaboración con especialistas | Sí | Revisión del especialista financiero de reglas y resultados (tarea de cierre) |
| VII. Simplicidad y reversibilidad | Sí | Se reutiliza el motor FIFO y la baja lógica de `AplicacionesPago`; sin motor nuevo; correcciones reversibles |
| VIII. Stack aprobado | Sí | Python, SQL Server, Next.js, TypeScript, Tailwind, TanStack Query |

Resultado: sin violaciones; no se requiere tabla de complejidad. Se vuelve a evaluar tras el diseño: sin cambios.

## Project Structure

### Documentation (this feature)

```text
specs/035-auditoria-cuentas-proveedores/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── auditoria-cuentas-api.md
└── tasks.md             # lo crea /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── src/features/auditoria_cuentas/
│   ├── __init__.py
│   ├── schemas.py          # respuestas del control, grupos, correcciones
│   ├── clasificacion.py    # funciones puras: causa de cada cuenta y hallazgos de plazo / doble descuento
│   ├── datos.py            # carga de solo lectura (saldos, referencia, aplicaciones, tarjetas)
│   ├── correcciones.py     # reglas de corrección: simular, aplicar con respaldo, revertir
│   ├── exportacion.py      # Excel
│   └── router.py           # /api/auditoria-cuentas
├── scripts/
│   └── crear_esquema_auditoria_035.py   # tablas nuevas, con respaldo y modo --verificar
└── tests/
    ├── test_auditoria_clasificacion.py
    ├── test_auditoria_correcciones.py
    └── contract/test_auditoria_cuentas_api.py

frontend/
├── src/app/finanzas/auditoria-cuentas/page.tsx
├── src/components/auditoria-cuentas/   # ResumenCausas, GrupoExcepciones, DialogoCorreccion, ParametrosAuditoria
├── src/services/auditoriaCuentasApi.ts
└── tests/auditoria-cuentas.e2e.cjs
```

**Structure Decision**: aplicación web existente (backend + frontend). Módulo nuevo `auditoria_cuentas` al lado de `tarjetas_cuenta` y `recalculo_fifo`; el FIFO se opera con el módulo `recalculo_fifo` ya existente (sus endpoints y su pantalla), sin duplicarlo.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
