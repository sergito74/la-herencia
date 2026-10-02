# Implementation Plan: Recálculo FIFO de cuentas corrientes

**Branch**: `032-recalculo-fifo-cuentas` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/032-recalculo-fifo-cuentas/spec.md`

## Summary

Se reemplazan los lotes de corrección de 031 por un motor FIFO determinista por contacto. El motor arma dos colas por contacto:

- **Débitos:** cuotas de vencimiento de facturas y notas de débito, liquidaciones de granos y de hacienda, y saldo inicial estimado.
- **Créditos:** pagos y cobros con su fecha real de erogación, retenciones, notas de crédito, compensaciones cruzadas y anticipos.

Las cadenas reales de tarjeta y cheque, y las elecciones explícitas de factura, se fijan primero. El resto se reparte por vencimiento.

Cada corrida es una **ejecución**: primero simulación, que guarda el resultado sin tocar `AplicacionesPago`. Después Sergio aplica por etapas de contactos, con respaldo verificado y reversión en un paso.

Después del saneamiento, el mismo motor corre por contacto cuando entra un movimiento identificado, y aplica solo si los controles pasan. Se suman el saldo por tramos de vencimiento y el aviso de vencimientos de los lunes.

El flujo por rubro (030) ya lee la fuente unificada de 031, así que hereda los vínculos nuevos sin cambios de modelo.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript / Next.js 14 (frontend)

**Primary Dependencies**: FastAPI, pyodbc, TanStack Query, Tailwind CSS

**Storage**: SQL Server `WC`. Se crean tablas nuevas `RecalculoFifo*`. `AplicacionesPago` se reutiliza con `Origen='fifo-032'`.

**Testing**: pytest con funciones puras del motor y casos sintéticos, más lectura real contra `WC` en modo simulación.

**Target Platform**: PC local, con el lanzador de `launcher/`.

**Project Type**: Aplicación web (backend + frontend).

**Performance Goals**: Simulación de todos los contactos en menos de 5 minutos (SC-007). Recálculo de un contacto en menos de 2 s.

**Constraints**:

- Solo `WC`.
- Respaldo verificado antes de aplicar.
- Idempotente.
- Solo Sergio aplica.

**Scale/Scope**:

- 6.440 compras y 5.304 cuotas.
- 362 liquidaciones de venta.
- Unas 8.400 aplicaciones vigentes.
- Alrededor de 400 contactos con movimientos.

## Constitution Check

| Principio | Cumplimiento |
| --- | --- |
| I. SQL Server sistema de registro | Lee y escribe solo `WC`. `LaHerencia` no se toca. |
| II. Protección de datos | `vinculos/backup.py` hace un respaldo verificado antes de cada aplicación. La simulación no escribe en `AplicacionesPago`. |
| III. Procesos de negocio | Las pantallas siguen el flujo simulación, excepciones por contacto, detalle y aplicación. |
| IV. Trazabilidad | Cada aplicación guarda ejecución, origen, regla, tipo de cambio usado y marcas. |
| V. Contrato primero | Contratos en `contracts/api.md`. El motor es una función pura con tests antes de la interfaz. |
| VI. Especialistas | Revisión del especialista financiero (07) en checkpoints: motor y primera etapa. |
| VII. Simple y reversible | Reutiliza la fuente de 031 y `AplicacionesPago`. La reversión restaura las aplicaciones anteriores. |
| VIII. Stack aprobado | Python, FastAPI, Next.js, TypeScript, Tailwind y TanStack Query. |

**Resultado**: pasa, sin excepciones.

## Project Structure

### Documentation (this feature)

```text
specs/032-recalculo-fifo-cuentas/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
backend/
├── scripts/crear_esquema_recalculo_fifo.py      # DDL idempotente + respaldo previo
└── src/features/recalculo_fifo/
    ├── entrada.py      # arma débitos/créditos por contacto (usa vinculos.fuente/cadenas)
    ├── motor.py        # FIFO puro: fijos → compensación cruzada → reparto por vencimiento
    ├── controles.py    # FR-010/011/034/037 → excepciones por contacto
    ├── cambio.py       # TC BNA vendedor día anterior + ajustes "Ajusta tipo de cambio"
    ├── duplicados.py   # FR-019/035 (CUIT, luego similitud de nombre)
    ├── ejecuciones.py  # simular / aplicar / revertir (persistencia + backup)
    ├── saldos.py       # saldo vencido y por tramos (FR-022), aviso lunes (FR-030/038)
    └── router.py
backend/tests/recalculo_fifo/   # casos sintéticos del motor y controles

frontend/src/
├── app/finanzas/recalculo-fifo/page.tsx
├── components/recalculo-fifo/   # ListaContactos, DetalleContacto, BarraEjecucion
├── components/cuentas-corrientes/SaldoPorVencimiento.tsx
└── components/layout/AvisoVencimientos.tsx      # modal de lunes al entrar
```

**Structure Decision**: es una aplicación web con un nuevo módulo de backend junto a `vinculos/`, del que reutiliza la lectura. Al aplicar, `vinculos/correccion.py` y los lotes de 031 quedan desactivados (FR-016).

## Fases de entrega

1. **Motor y simulación** (US1): entrada, motor, controles y la pantalla de simulación con los 9 contactos de la primera etapa.
2. **Aplicar y revertir** (US2): ejecuciones, respaldo e idempotencia. Se aplican primero los 9 contactos y después el resto por etapas.
3. **Mixtas, saldo inicial y duplicados** (US3): se puede empezar en paralelo con la fase 1, porque Cargill está en la primera etapa.
4. **Operatoria continua** (US5): aplicación por contacto al identificar un movimiento, saldo por tramos y aviso de los lunes.
5. **Rubro** (US4): verificar SC-008 sobre el flujo de 030.

## Riesgos

- **Serie `[Dolar BNA]` al día.** Se mantiene con `backend/scripts/actualizar_dolar_bna.py` desde Errepar. Un pago posterior a la última fecha cargada usa el TC implícito marcado. Ver research R2.
- **`Valores Recibidos` tiene solo 17 filas.** Los e-cheqs de acopiadores probablemente estén como movimientos bancarios y no como valores. Ver research R6.
- **Las notas de crédito y débito de proveedor nuevas tienen 0 filas.** Las históricas están en `Compras` con su tipo de comprobante. Ver research R5.

## Complexity Tracking

Sin violaciones de la Constitución que justificar.
