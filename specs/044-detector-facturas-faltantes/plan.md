# Implementation Plan: Detector de facturas faltantes de proveedores

**Branch**: `044-detector-facturas-faltantes` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/044-detector-facturas-faltantes/spec.md`

## Summary

Módulo de solo lectura sobre la contabilidad de WC (Compras, pagos de la vista de cuentas, vínculos de las cinco vías, retenciones y remitos) que aprende el ciclo de facturación de cada proveedor, asigna sus comprobantes a períodos esperados por secuencia (no por mes calendario) y produce un tablero de facturas esperadas y un listado de alarmas "a verificar". Las únicas escrituras son tres tablas propias (perfil del proveedor, decisiones sobre alarmas, marcas de falta factura), sin tocar saldos. Se integra con la rutina 043 (resumen desde el día 5) y con el formulario de pagos (aviso no bloqueante).

## Technical Context

**Language/Version**: Python 3.13 (backend FastAPI), TypeScript / Next.js (frontend)

**Primary Dependencies**: FastAPI, pyodbc, Pydantic; Next.js, Tailwind CSS, TanStack Query

**Storage**: SQL Server `WC` (lectura de Compras, vw_MovimientosCuenta_Saldo, AplicacionesPago y demás vías vía `features/vinculos/fuente`, Retenciones, tblRemitoCompra/Remitos_Facturas); 3 tablas nuevas con DDL y respaldo verificado

**Testing**: pytest con datos simulados (motor de ciclos y estados puro), contrato API con TestClient, tsc/eslint y recorrido UI con API interceptada

**Target Platform**: aplicación web local (backend en 127.0.0.1, frontend Next.js)

**Project Type**: web application (backend + frontend)

**Performance Goals**: tablero completo < 3 s (SC-005); el cálculo carga en bloque y cachea por proceso con invalidación al guardar

**Constraints**: sin escrituras contables; alarmas siempre rotuladas "a verificar"; sin ids/códigos en pantalla; Ganadera San Justo excluida; sin consultas externas

**Scale/Scope**: ~600 contactos con compras, ~8.000 comprobantes, ~10.000 pagos

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I. WC sistema de registro | Lee y escribe solo WC; no usa Access ni LaHerencia. |
| II. Protección de datos | DDL de 3 tablas propias con respaldo verificado previo; ninguna escritura en tablas contables. |
| III. Procesos antes que tablas | Tablero por proceso (facturas del mes) y alarmas con origen y acceso a cuenta/carga. |
| IV. Trazabilidad | Cada estado/alarma muestra el comprobante o pago que lo origina, período, monto y fuente del cálculo. |
| V. Contrato primero | contracts/api.md y pruebas de contrato antes de la UI. |
| VI. Dominio | Reglas de la auditoría 036 §7 acordadas con Sergio; umbrales documentados en research.md. |
| VII. Simplicidad | Motor puro en un archivo, reutiliza `vinculos.fuente`; sin abstracciones nuevas. |
| VIII. Stack | Python + Next.js/TS + Tailwind + TanStack Query. |

Resultado: sin violaciones. Re-chequeo post-diseño: sin cambios.

## Project Structure

### Documentation (this feature)

```text
specs/044-detector-facturas-faltantes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── scripts/crear_esquema_detector_044.py      # DDL con respaldo
├── src/features/facturas_faltantes/
│   ├── motor.py        # ciclo, períodos, estados, alarmas (puro, sin SQL)
│   ├── repository.py   # lecturas en bloque y escrituras de las 3 tablas
│   ├── service.py      # arma tablero/alarmas, cache e invalidación
│   ├── schemas.py
│   └── router.py       # /api/facturas-faltantes/...
└── tests/
    ├── test_facturas_faltantes_motor_044.py
    └── test_facturas_faltantes_contrato_044.py

frontend/src/
├── app/finanzas/facturas-esperadas/page.tsx
├── components/facturas-faltantes/{TableroFacturasEsperadas,AlarmasFaltantes}.tsx
└── services/facturasFaltantesApi.ts
```

**Structure Decision**: módulo nuevo `facturas_faltantes` siguiendo el patrón de `features/<modulo>`; integra con `documentos_nuevos` (resumen 043) y `NavHeader` (entrada en Finanzas).

## Complexity Tracking

Sin desvíos que justificar.
