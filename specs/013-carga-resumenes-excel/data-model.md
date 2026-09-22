# Data Model: Confirmar la carga de resúmenes bancarios (BNA/Galicia) desde Excel (013)

## Entidades existentes (sin cambio de esquema)

### Movimiento BNA — `dbo.[Movimientos BNA]`
Reusada de 003. Esta spec solo agrega filas vía `INSERT`:

| Columna | Origen al insertar desde Excel |
|---|---|
| `IdMovimientoBNA` | autogenerado (identity) |
| `Reg_Concatenado` | `NULL` (campo de carga manual histórica, no se reconstruye) |
| `Fecha / Hora Mov#` | `fecha` del preview |
| `Nro# Comprobante` | `comprobante` del preview (si es numérico; si no, `NULL`) |
| `Concepto` | `concepto` del preview |
| `Importe` | `importe` del preview |
| `Nro# Mov#` | `NULL` (no viaja en el Excel, ver research.md §1) |
| `IdContacto` / `Contacto` | `NULL` (Clarifications Q1) |

### Movimiento Galicia — `dbo.[Movimientos Galicia]`
Reusada de 003. Columnas insertadas desde Excel: `Fecha`, `Descripción` (desde `descripcion`), `Débitos`, `Créditos`, `Número de Comprobante` (desde `numeroComprobante`), `Saldo`. El resto (`Origen`, `Grupo de Conceptos`, `Número de Terminal`, `Observaciones Cliente`, `LeyendasAdicionales1-4`, `Tipo de Movimiento`, `Centro de Costos`, `Rubro`, `Destino`, `F22`, `F23`, `OrdenMovimiento`, `IdContacto`, `Contacto`) queda `NULL` — no vienen en la vista previa de 003 y no se inventan.

## Entidades nuevas (infraestructura de esta app, en `WC`)

### CargaResumenBancario — `dbo.CargasResumenBancario`

| Columna | Tipo | Notas |
|---|---|---|
| `IdCarga` | int identity PK | |
| `Banco` | varchar(20) | `'BNA'` \| `'Galicia'` |
| `NombreArchivo` | nvarchar(260) | nombre del archivo subido |
| `FechaHoraCarga` | datetime2 | default `SYSUTCDATETIME()` |
| `CantidadInsertados` | int | |
| `CantidadOmitidosDuplicado` | int | |
| `CantidadOmitidosIncompletos` | int | filas descartadas por fecha/importe faltante (Edge Cases) |

### VínculoMovimientoCarga — `dbo.CargasResumenBancario_Movimientos`

| Columna | Tipo | Notas |
|---|---|---|
| `IdCarga` | int FK → `CargasResumenBancario.IdCarga` | |
| `Banco` | varchar(20) | redundante con `IdCarga.Banco`, evita un `JOIN` extra al filtrar por banco |
| `IdMovimiento` | int | `IdMovimientoBNA` o `IdMovimiento` real, según `Banco` |

PK compuesta `(Banco, IdMovimiento)` — un movimiento pertenece a una sola carga.

## Reglas de validación

- Una fila del archivo sin `fecha` o sin `importe`/`débitos`+`créditos` válidos no se inserta y cuenta en `CantidadOmitidosIncompletos` (Edge Cases de spec.md).
- La comparación de duplicados (research.md §2) corre por fila, contra los movimientos del mismo banco con `Fecha` dentro de `[MIN(fecha archivo), MAX(fecha archivo)]`.
- `CantidadInsertados + CantidadOmitidosDuplicado + CantidadOmitidosIncompletos` MUST igualar la cantidad de filas de datos del archivo (excluyendo encabezado/metadata).
