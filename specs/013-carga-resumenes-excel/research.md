# Research: Confirmar la carga de resúmenes bancarios (BNA/Galicia) desde Excel (013)

## 1. Tablas reales destino (confirmado contra `WC`, 2026-09-22)

- `dbo.[Movimientos BNA]`: `IdMovimientoBNA` (PK identity), `Reg_Concatenado`, `Fecha / Hora Mov#`, `Nro# Comprobante`, `Concepto`, `Importe`, `Nro# Mov#`, `IdContacto`, `Contacto`. `Nro# Mov#` es un número de secuencia del banco (visto en filas reales: 11899807-11899809) que **no viaja en el Excel de 003** (`excel_import.py` solo expone `Fecha, Comprobante, Concepto, Importe, Saldo`) — no sirve como clave de deduplicación para filas nuevas, ni se completa al insertar desde esta spec (queda `NULL`, igual que `Reg_Concatenado`, ambos campos de origen manual histórico).
- `dbo.[Movimientos Galicia]`: `IdMovimiento` (PK identity), `Fecha`, `Descripción`, `Origen` (campo del banco, no relacionado con "origen de importación"), `Débitos`, `Créditos`, `Grupo de Conceptos`, `Concepto`, `Número de Terminal`, `Observaciones Cliente`, `Número de Comprobante`, `LeyendasAdicionales1-4`, `Tipo de Movimiento`, `Saldo`, `IdContacto`, `Contacto`, `Centro de Costos`/`Rubro`/`Destino` (ignorados, FR-011), `F22`, `F23`, `OrdenMovimiento`.
- Filas reales existentes ya conviven con `IdContacto`/`Contacto` en `NULL` (confirmado: movimientos de impuestos/gravámenes bancarios) — insertar así (Clarifications Q1) no rompe ninguna regla ni vista existente.
- Ninguna de las dos tablas tiene una columna de lote/origen de importación — se confirma la Decisión Q3 (tablas nuevas).

## 2. Detección de duplicados (Decisión Q2, confirmada con el usuario)

**Decision**: clave de comparación = `Fecha` + `Importe` (BNA) / `Débitos`-`Créditos` (Galicia) + `Concepto`/`Descripción` normalizado (mayúsculas, `TRIM`, espacios colapsados a uno) + `Número de Comprobante` si el archivo lo trae (Galicia) o `Comprobante` (BNA). Se compara contra los movimientos ya persistidos del mismo banco en el rango de fechas del archivo subido (no toda la tabla, para no escanear miles de filas en cada carga).

**Rationale**: ningún campo persistido hoy es un identificador estable que también viaje en el Excel (`Nro# Mov#`/`Reg_Concatenado` son post-hoc). La combinación fecha+importe+concepto normalizado es el mismo criterio que usaría un humano revisando el resumen, y el `Número de Comprobante`/`Comprobante` (cuando existe) reduce falsos positivos en días con varios movimientos similares (ej. varios débitos del mismo impuesto en fechas distintas del mes).

**Alternatives considered**: hash MD5 de la fila completa (rechazado: cualquier diferencia de formato entre exports del mismo banco en fechas distintas rompería la comparación sin razón real); usar solo fecha+importe (rechazado: dos movimientos legítimos del mismo importe el mismo día — ej. dos gravámenes iguales — se pisarían entre sí, perdiendo uno real).

## 3. Trazabilidad de la carga (Decisión Q3, confirmada)

**Decision**: dos tablas nuevas en `WC`, mismo patrón que `Tarjetas_Resumenes_Lineas_Estado` (009) — infraestructura de esta app, no existen en `LaHerencia`:

- `dbo.CargasResumenBancario`: `IdCarga` (PK identity), `Banco` (`BNA`|`Galicia`), `NombreArchivo`, `FechaHoraCarga` (datetime2, default `SYSUTCDATETIME()`), `CantidadInsertados`, `CantidadOmitidosDuplicado`, `CantidadOmitidosIncompletos`.
- `dbo.CargasResumenBancario_Movimientos`: `IdCarga` (FK), `Banco`, `IdMovimiento` (el `IdMovimientoBNA`/`IdMovimiento` real insertado), PK compuesta `(Banco, IdMovimiento)` — permite `JOIN` directo desde un movimiento hacia su carga de origen (FR-008), y una `UNIQUE` natural evita que el mismo movimiento quede vinculado a dos cargas.

Script de creación idempotente (mismo patrón que `backend/scripts/crear_tabla_estado_lineas.py` de 009): `backend/scripts/crear_tablas_carga_resumenes.py`, con `IF OBJECT_ID(...) IS NULL CREATE TABLE ...`.

## 4. Concurrencia (FR-005)

**Decision**: la detección de duplicados + el `INSERT` de los movimientos nuevos + el `INSERT` del registro de `CargasResumenBancario`/`_Movimientos` se ejecutan dentro de una única transacción SQL Server (`execute_write_transaction`, ya usado en compras/tarjetas) con nivel de aislamiento `SERIALIZABLE` acotado al rango de fechas del archivo (`SELECT ... WITH (UPDLOCK, SERIALIZABLE) WHERE Fecha BETWEEN ? AND ?` antes del `INSERT`), evitando escanear/bloquear toda la tabla.

**Rationale**: mismo mecanismo ya disponible en `connection.py` (`execute_write_transaction`), sin introducir un nuevo mecanismo de locking (constitución VII, simplicidad). El rango acotado por fecha limita el bloqueo a la ventana real del archivo (semanas, no toda la tabla histórica).

**Alternatives considered**: `sp_getapplock` con un nombre de lock por banco (rechazado por ahora: agrega una primitiva nueva sin necesidad — el volumen real es bajo, una persona sube resúmenes mensuales, no hay evidencia de cargas concurrentes reales del mismo banco; documentado como mejora futura si aparece el caso).

## 5. Reuso de 003

- `excel_import.py::validar_y_previsualizar` se reusa sin cambios para el primer paso (ya está probado). Esta spec agrega una función nueva `confirmar_carga(filename, contenido, banco)` en el mismo módulo (o uno nuevo `importar.py` del feature `tesoreria`) que reprocesa el archivo (FR-002), aplica la deduplicación (§2) y persiste (§3) dentro de la transacción (§4).
- El componente `CargaExcel.tsx` (003) se extiende con un paso de confirmación (mostrar "N nuevos / M omitidos" antes de un botón "Confirmar carga"), reenviando el mismo archivo (no una copia cacheada) al nuevo endpoint.
