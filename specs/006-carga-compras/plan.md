# Implementation Plan: Carga de Compras (alta y edición)

**Branch**: `006-carga-compras` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-carga-compras/spec.md`

## Summary

Alta y edición de una Compra completa (cabecera `Compras` + líneas `Det_Compras` + fechas de vencimiento `[Vencimiento Compras]`) escrita exclusivamente contra `WC`, extendiendo el módulo de solo lectura ya existente (`specs/002-compras`) en vez de duplicarlo. Reutiliza `ContactoSelect` para el proveedor y reproduce las fórmulas reales de IVA/pesificado confirmadas por inspección read-only de los formularios Access (`Frm Compras`/`SbFrm Det_Compras`/`Sbfrm Vencimiento Compras`). Introduce dos piezas nuevas de infraestructura, ambas acotadas a `WC`: (1) un mecanismo de escritura transaccional multi-tabla (cabecera+líneas+vencimientos en una sola transacción, todo o nada) y (2) un bloqueo de edición exclusivo por compra (sin sistema de autenticación real todavía, se implementa con un token de sesión de navegador + expiración por inactividad).

## Technical Context

**Language/Version**: Python 3.13 (backend) + TypeScript 5.x / Next.js (frontend) — mismas versiones que `specs/002-005`

**Primary Dependencies**: FastAPI + Pydantic; pyodbc (DSN `SQL_LaHerencia`); Next.js, TanStack Query, Tailwind CSS. Sin dependencias nuevas.

**Storage**: SQL Server, base `WC` únicamente para escritura (lectura puede seguir sirviendo desde `WC` o `LaHerencia` indistintamente, igual que hoy) — `dbo.Compras`, `dbo.Det_Compras`, `dbo.[Vencimiento Compras]`, `dbo.Contactos`, `dbo.Rubros`, `dbo.[Centro de costos]`, `dbo.DestinoCompras`, `dbo.UnidadesMedida`, `dbo.Campañas` (catálogos ya usados por 002-compras/003-tesoreria, sin cambios de estructura). Tabla nueva en `WC`: `dbo.CompraEditLocks` (bloqueo de edición, ver research.md).

**Testing**: pytest + httpx (contract tests con fixtures, mismo patrón que `test_compras_*.py`); unit tests para el guard de transacción multi-tabla y el guard de bloqueo, análogos a `test_db_connection.py`.

**Target Platform**: Igual que el resto de la app — backend Python + frontend Next.js, uso interno del equipo administrativo.

**Project Type**: Web application (frontend + backend), extiende `specs/002-compras` en el mismo feature.

**Performance Goals**: Alta de una compra completa (cabecera + 1 línea) en menos de 3 minutos de interacción de usuario (SC-001); guardado (llamada a la API) en menos de 2s para una compra típica (≤20 líneas, ≤12 vencimientos).

**Constraints**: Toda escritura exclusivamente contra `WC` (regla de oro, FR-015); ninguna escritura automática/masiva sobre histórico (FR-016); bloqueo pesimista de edición por compra (FR-009a); sin validación de unicidad de documento a nivel de base (solo advertencia de aplicación, FR-014); sin exigir cantidad/precio > 0 (FR-004a).

**Scale/Scope**: Volumen bajo-medio, comparable a 002-compras (6436 compras históricas); alta nueva esperada en el orden de decenas por semana, no miles — no hay riesgo de escala para el diseño de bloqueo por fila.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Resultado |
|---|---|---|
| I. SQL Server es la fuente de verdad | Usa las tablas reales de `Compras`/`Det_Compras`/`Vencimiento Compras` ya confirmadas por inspección Access + `INFORMATION_SCHEMA`; agrega solo la tabla de bloqueo `CompraEditLocks`, necesaria para el requisito de concurrencia (FR-009a), no un almacén de datos paralelo al de negocio. | Pass |
| II. Protección de datos reales | Toda escritura pasa por `execute_write`/nueva `execute_write_transaction`, que se niegan a operar fuera de `WC` (`_assert_target_is_wc`); `LaHerencia` permanece de solo lectura. Se requiere backup verificado de `WC` antes de habilitar escritura en producción (ya existe desde la regla de oro, ver memory.md). | Pass |
| III. Procesos de negocio antes que tablas | El flujo de alta sigue el proceso real: seleccionar proveedor → cargar cabecera fiscal → cargar líneas con su clasificación de gestión → cargar vencimientos → guardar, replicando la secuencia del formulario Access real, no una grilla CRUD genérica. | Pass |
| IV. Trazabilidad y significado financiero explícito | Cabecera y líneas distinguen explícitamente subtotal, IVA, importe total, moneda, tipo de cambio y "pesificado"; vencimientos quedan trazables a su compra vía `IdCompra`. | Pass |
| V. Contrato primero, integración probada | Contrato de API definido en Fase 1 (`contracts/`) antes de tocar el frontend; contract tests para alta/edición/bloqueo antes de cerrar el módulo. | Pass |
| VI. Colaboración de especialistas | Reglas de cálculo (IVA 10.5% sobre gastos accesorios, bloque pesificado, defaults de clasificación) confirmadas por inspección real de los formularios Access con el especialista financiero como checkpoint, no inventadas. | Pass |
| VII. Simplicidad y reversibilidad | Extiende el feature `compras` existente (mismo directorio, no uno nuevo) reutilizando `db/connection.py`/`db/pagination.py`/`ContactoSelect`; el mecanismo de bloqueo es la pieza nueva mínima indispensable para cumplir FR-009a, no una capa de sesión/autenticación completa. | Pass |
| VIII. Stack aprobado | Mismo stack (FastAPI/SQL Server/Next.js/TypeScript/Tailwind/TanStack Query), sin dependencias nuevas. | Pass |

No hay violaciones que requieran justificación.

*Re-chequeo post-Fase 1 (2026-09-17): `data-model.md` y `contracts/compras-alta-api.md` confirman que `CompraEditLocks` es la única tabla nueva, acotada a `WC`, sin datos de negocio propios; `execute_write_transaction` reutiliza exactamente las mismas validaciones de `execute_write` (solo INSERT/UPDATE/DELETE, sin DDL, `_assert_target_is_wc`) aplicadas a cada sentencia de la transacción. Los 8 principios siguen en Pass.*

## Project Structure

### Documentation (this feature)

```text
specs/006-carga-compras/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── compras-alta-api.md
└── tasks.md          # generado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── db/
│   │   └── connection.py         # + execute_write_transaction (nueva función)
│   └── features/
│       └── compras/              # feature existente (002), se extiende, no se duplica
│           ├── schemas.py        # + CompraAltaRequest/CompraEditRequest/LineaInput/VencimientoInput/LockResponse
│           ├── repository.py     # + create_compra/update_compra/get_rubro_sugerido/validaciones referenciales
│           ├── repository_locks.py   # nuevo: adquirir/liberar/consultar bloqueo de edición
│           └── router.py         # + POST /api/compras, PUT /api/compras/{id}, POST/DELETE lock endpoints
└── tests/
    ├── test_db_connection.py     # + tests de execute_write_transaction
    └── contract/
        └── test_compras_alta_api.py   # nuevo

frontend/
├── src/
│   ├── components/
│   │   └── compras/
│   │       ├── ComprasListado.tsx     # existente, sin cambios de contrato
│   │       ├── CompraForm.tsx         # nuevo: alta/edición de cabecera+líneas+vencimientos
│   │       ├── DetalleLineaForm.tsx   # nuevo: fila editable de línea con sugerencia de rubro
│   │       └── VencimientosEditor.tsx # nuevo: lista editable de fechas de vencimiento
│   ├── services/
│   │   └── comprasApi.ts              # + crearCompra/actualizarCompra/adquirirBloqueo/liberarBloqueo/fetchRubroSugerido
│   └── app/
│       └── compras/
│           ├── nueva/page.tsx         # nuevo
│           └── [idCompra]/editar/page.tsx  # nuevo
```

**Structure Decision**: Se extiende el feature `compras` ya existente (backend `backend/src/features/compras/`, frontend `frontend/src/components/compras/` + `frontend/src/app/compras/`) en vez de crear un feature `compras_alta` separado — cabecera, líneas y vencimientos son las mismas tablas que ya lee 002-compras, y duplicar el feature dividiría innecesariamente la lógica de un mismo dominio (principio VII).

## Complexity Tracking

*No hay violaciones de la Constitution Check que requieran justificación.*
