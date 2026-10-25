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
**Integridad**: orígenes ImpuestoParticular/DevImpParticular compatibles con varchar(20); UUID+huella persistidos por carga/vínculo; control de edición/baja de impuesto y de movimientos vinculados; capacidad nominal de Haber bloqueada transaccionalmente.
**Devoluciones/padrón**: vínculos históricos con identidad, estado y anulación propia; estado nominal en pesos separado de saldo valuado; padrón derivado vigente/ambiguo/sin_cargas, con partida auxiliar ingresada por usuario y sin columnas nuevas en Impuestos.

## Constitution Check
I SQL Server sistema de registro ✔ · II respaldo y solo WC ✔ · III proceso impuesto → carga → devolución ✔ · IV trazabilidad (carga enlazada, auditoría, anulación no destructiva) ✔ · V contrato antes de UI ✔ · VI especialistas 07 y administración consultados ✔ · VII cambio aditivo y reversible ✔ · VIII stack aprobado ✔. **Gate: PASS** (pre y post diseño).

## Project Structure
```text
backend/scripts/migrar_impuestos_particulares_041.py   # DDL + migración del 3206 (inspección / --aplicar)
backend/src/features/impuestos/particular.py           # cargas, devoluciones, padrón, validaciones
backend/src/features/impuestos/router.py, schemas.py, repository.py   # endpoints, lista, baja bloqueada
backend/src/features/flujo_caja/atribucion.py           # rubro «Cuenta de socios» por la parte cargada
backend/src/features/revision_cuentas/datos.py          # «cargado a socio»
backend/src/features/cuentas_socios/repository.py       # origen enlazado y protección de movimientos ligados
backend/src/features/cuentas_socios/router.py           # 409 consistente al bloquear edición/anulación
backend/src/features/cajas_efectivo/service.py           # impedir anulación indirecta de movimientos vinculados
backend/src/features/cajas_efectivo/operaciones.py       # comprobación compartida bajo transacción si el flujo la requiere
backend/tests/test_impuestos_particulares_041.py
frontend/src/components/impuestos/ImpuestoParticularPanel.tsx   # sección «A cargo de socio» en la ficha
frontend/src/components/impuestos/ImpuestosListado.tsx           # etiqueta, estado, filtro
frontend/src/components/impuestos/ImpuestoForm.tsx              # consulta auxiliar de partida sin alterar boleta
frontend/src/services/impuestosApi.ts
```

## Complexity Tracking
Sin violaciones.


## Orden de entrega y controles refinados

1. Verificar esquema e identificadores contra research; crear las tres tablas sin cambiar Impuestos ni Origen de socios.
2. Implementar cargas idempotentes y protección de ediciones; devoluciones con importe asignado, control de capacidad y desvinculación; anulación coordinada y recálculo del padrón.
3. Integrar las protecciones en las entradas de socios/caja capaces de cambiar esos movimientos; verificar rollback y concurrencia con fixtures sin SQL real.
4. Migrar el 3206 con respaldo y clave estable, manteniendo fechas históricas y saldo en todas las unidades; validar UI, roles y avisos sin transacciones reales de prueba.

La resolución documental de I1, C1, C2, U1, I2, U2, U3 y U4 está registrada en validacion.md. T002 verifica las reglas ya resueltas en contrato/modelo; no delega decisiones funcionales a la implementación.
