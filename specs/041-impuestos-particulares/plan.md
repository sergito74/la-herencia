# Implementation Plan: Impuestos particulares

**Branch**: `main` (spec 041) | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

## Summary
Cargar un impuesto (total o parte) a la cuenta de un socio o del Condominio, con Debe valuado y enlazado; excluir esa parte de los costos de Giamigli en el flujo de caja y la revisión de cuentas; estado de devolución; padrón de partidas armado con las marcas; migración del caso 3206. Ver [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md).

## Technical Context
**Language/Version**: Python 3.13 (FastAPI), TypeScript/Next.js
**Storage**: SQL Server WC — tablas nuevas `ImpuestosParticulares`, `ImpuestosParticularesDevoluciones`, `PartidasTitulares`; sin cambios en `Impuestos`
**Testing**: pytest con pyodbc bloqueado; tsc y eslint
**Constraints**: magnitudes positivas en la cuenta de socio (el Tipo da el signo); respaldo antes de DDL y de la migración del 3206; solo WC
**Scale**: decenas de cargas

## Constitution Check
I SQL Server sistema de registro ✔ · II respaldo y solo WC ✔ · III proceso impuesto → carga → devolución ✔ · IV trazabilidad (carga enlazada, auditoría, anulación no destructiva) ✔ · V contrato antes de UI ✔ · VI especialistas 07 y administración consultados ✔ · VII cambio aditivo y reversible ✔ · VIII stack aprobado ✔. **Gate: PASS** (pre y post diseño).

## Project Structure
```text
backend/scripts/migrar_impuestos_particulares_041.py   # DDL + migración del 3206 (inspección / --aplicar)
backend/src/features/impuestos/particular.py           # cargas, devoluciones, padrón, validaciones
backend/src/features/impuestos/router.py, schemas.py, repository.py   # endpoints, lista, baja bloqueada
backend/src/features/flujo_caja/atribucion.py           # rubro «Cuenta de socios» por la parte cargada
backend/src/features/revision_cuentas/datos.py          # «cargado a socio»
backend/src/features/cuentas_socios/repository.py       # origen ImpuestoParticular con enlace en el listado
backend/tests/test_impuestos_particulares_041.py
frontend/src/components/impuestos/ImpuestoParticularPanel.tsx   # sección «A cargo de socio» en la ficha
frontend/src/components/impuestos/ImpuestosListado.tsx           # etiqueta, estado, filtro
frontend/src/services/impuestosApi.ts
```

## Complexity Tracking
Sin violaciones.
