# Research: Exportar Saldos de Cuentas Corrientes y Valores Propios (014)

## 1. Fuente real de datos (confirmado contra `WC`, 2026-09-22)

- Cuenta corriente por contacto: `dbo.vw_MovimientosCuenta_Base` (movimientos) y `dbo.vw_MovimientosCuenta_Saldo` (con `SaldoParcial` acumulado) — ya usadas por `cuentas_corrientes/repository.py` (004). Sin cambios de esquema necesarios.
- Saldo de todos los contactos a la vez: no existe hoy ninguna consulta agregada — `get_saldo(id_contacto)` (`repository.py:56`) trae uno por vez con `SELECT TOP 1 ... WHERE IdContacto = ? ORDER BY Fecha DESC, Origen DESC, IdOrigen DESC`. La misma lógica se puede expresar para todos los contactos con `ROW_NUMBER() OVER (PARTITION BY IdContacto ORDER BY Fecha DESC, Origen DESC, IdOrigen DESC)` sobre `vw_MovimientosCuenta_Saldo`, filtrando `rn = 1` — evita repetir la consulta contacto por contacto (FR-002).
- Valores propios: `dbo.[Valores propios]` (1142 filas, última carga real 2026-04-16 según los datos de `WC`) — mismas columnas que ya expone `tesoreria/repository.py` (`MEDIOS_CONFIG["valores-propios"]`), sin cambios de esquema. `Cobrado` tiene valores reales `'S'` (1133), `'A'` (9); `'N'`/vacío soportado por el campo aunque hoy no tiene filas.

## 2. Patrón de exportación a reusar

`backend/src/features/ordenes/exportacion.py` define el patrón ya validado en 010/011/012: `Workbook` de `openpyxl`, helper `_hoja(wb, titulo, columnas)` para encabezado con estilo, `_cerrar(ws, formatos)` para aplicar formato numérico/fecha por columna y activar autofiltro, `_bytes(wb)` para serializar. El router expone `GET .../exportar` devolviendo `Response` con `media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"` y `Content-Disposition: attachment`.

**Decision**: replicar el mismo patrón en dos módulos nuevos de exportación — `cuentas_corrientes/exportacion.py` (US1: resumen de cuenta, US2: saldos) y extender `tesoreria` con la exportación de valores propios (US3), en vez de crear un módulo de exportación compartido/genérico. **Rationale**: cada módulo ya sigue este patrón de forma independiente (010/011/012), no hay abstracción compartida hoy y crear una prematuramente violaría la constitución (Principio VII, simplicidad) sin un tercer caso real que la justifique.

## 3. Alcance descartado (decisiones del usuario, 2026-09-22)

- **Flujo de Fondos (Rubro x mes)**: descartado explícitamente — la fuente de Rubro por movimiento es ambigua entre bancos (Galicia grabó Centro de Costos/Rubro directamente en `Movimientos Galicia`, pero 003 ya decidió no usar esas columnas como fuente de verdad; BNA no tiene esas columnas en absoluto). El usuario pidió rediseñar este informe en una spec futura, no forzar una decisión de diseño apurada acá.
- **Informes de Compras duplicados** ("Compras por proveedor" vs "Inf documentos_Fecha", mismo dato con otro orden): fuera de esta spec — si se prioriza, es una extensión menor de `compras/router.py` (agregar `GET /exportar`), no necesita spec propia pero tampoco se resuelve acá para mantener 014 acotada a Cuentas Corrientes + Valores Propios.

## 4. Listado de Valores Propios como pantalla nueva

003-tesorería ya expone `GET /api/tesoreria/valores-propios/movimientos` con paginación, pero el frontend de tesorería no tiene una vista dedicada de detalle/exportación por medio — es una tabla genérica reusada entre todos los medios. Para US3 (exportar Valores Propios) no hace falta una pantalla nueva de consulta: se agrega un botón de exportación a la vista ya existente de tesorería para el medio `valores-propios`, reusando los mismos filtros de fecha ya soportados por `MovimientosParams`.
