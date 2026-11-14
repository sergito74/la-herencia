# Data model — 049 + 050

Las tablas nuevas están en `dbo` de WC. Las crea `backend/scripts/crear_tablas_tamiz_050.py`, que es idempotente y se corre con backup previo.

## Tablas nuevas

### PartesEstructuraCosto
Contiene las 9 partes: Semilla, Fertilizantes, Agroquímicos, Labores, Cosecha, Fletes, Seguro agrícola, Asesoramiento/análisis y Comercialización.

| Columna | Tipo | Nota |
|---|---|---|
| IdParte | int PK | |
| Nombre | nvarchar(50) | único |
| Orden | int | orden de presentación |

### PartesEstructuraCultivoInactivas
Guarda las partes que un cultivo no usa. Por defecto están todas activas.

| Columna | Tipo |
|---|---|
| IdCultivo | int (PK compuesta) |
| IdParte | int (PK compuesta) |

### TamizRubroDestino
Tabla fija cargada desde [tabla-rubros-destino.md](tabla-rubros-destino.md). La mantiene Claude a pedido de Sergio.

| Columna | Tipo | Nota |
|---|---|---|
| IdRubro | int PK | FK Rubros |
| Destino | varchar(20) | `CultivoStock`, `Cultivo`, `Depende`, `Ganaderia`, `Financiero`, `Estructura`, `NoImputa` |
| IdParte | int NULL | obligatorio si el destino es `CultivoStock` o `Cultivo` |
| ReglaDepende | varchar(30) NULL | `AnalisisLaboratorio`, `Combustible`, `Financiamiento`, `SegunUsoOrden` |

**Regla**: un rubro sin fila en la tabla → el renglón va a revisión con el motivo `rubroSinRegla`.

### TamizReglaProducto
Se arma con lo que aprende el sistema: las correcciones de Sergio que él aceptó guardar.

| Columna | Tipo | Nota |
|---|---|---|
| IdRegla | int identity PK | |
| TextoNormalizado | nvarchar(200) NULL | para asignar producto desde la descripción |
| IdFormulado | int NULL | producto que se asigna |
| Destino / IdParte | NULL | si la regla fija un destino para ese producto |
| Usuario, FechaAlta | | |

### ImputacionConfig
Guarda una sola fila: `IdDeudaCorte`, `FechaActivacion` y `Activo` (bit). Mientras `Activo = 0`, el tamiz solo calcula y el resultado no cambia (fase de informe de impacto).

### ImputacionAlcance

| Columna | Tipo | Nota |
|---|---|---|
| IdDetalleCompra | int PK | |
| Motivo | varchar(20) | `Nuevo`, `StockSinImputar` |
| FechaAlta | datetime | |

### TamizRenglones
Guarda la clasificación vigente de cada renglón en alcance. Cada vez que se recalcula se escribe una fila nueva, y las anteriores quedan como historial.

| Columna | Tipo | Nota |
|---|---|---|
| IdTamiz | int identity PK | |
| IdDetalleCompra | int | |
| Destino, IdParte | | resultado |
| IdCultivo, IdCampania | int NULL | cuando el destino es de una sola vez |
| OrigenDecision | varchar(15) | `Manual`, `Orden`, `Producto`, `Rubro`, `Revision` |
| Estado | varchar(15) | `Aprobada`, `Pendiente` |
| Motivo | nvarchar(200) NULL | texto llano para la pantalla |
| FechaCalculo | datetime | |
| Vigente | bit | una sola vigente por renglón |
| Usuario | NULL | quien aprobó o corrigió |

### VinculoRemitoPendiente
Lista los remitos sin vincular y los vínculos dudosos que se muestran en "Para revisar".

| Columna | Tipo |
|---|---|
| IdVinculoPend | int identity PK |
| IdDetalleRemito | int |
| CandidatosJson | nvarchar(max) |
| Motivo | nvarchar(200) |
| FechaCalculo | datetime |
| Resuelto | bit |

## Tablas existentes que se usan

- **`ImputacionPropuestas`**: corridas por `IdDetalleCompra` y `Origen`. Se agrega el `Origen = 'Directo'` para los renglones de una sola vez, y la columna `IdParte int NULL`.
- **`tblRemitoCompra`**: el vínculo remito↔factura. El vínculo automático escribe acá.
- **`Det_Compras`**: rubro, imputación manual e `IdFormulado`. Solo se escribe `IdFormulado`, y solo en renglones en alcance.
- **`Ordenes_Trabajo*`**: consumo, cultivo/campaña y centro.
- **`OrdenesContratistaSinOrden`**: 048, sin cambios.

## Estados

```text
Renglón en alcance:
  tamizado → (Destino CultivoStock) → en stock 100% → usos parciales… → consumido
           → (Destino Cultivo/Ganadería/Estructura/Financiero) → imputado de una vez
           → (dudoso) → Pendiente en revisión → Aprobada (por Sergio)
Corrida: Pendiente → Aprobada; un recálculo crea una corrida nueva y la anterior queda en el historial.
```

## Reglas que el sistema tiene que cumplir siempre

- En cada renglón en alcance, la suma de las fracciones de la corrida vigente es igual al total del renglón, al centavo.
- La suma de `CantidadRemitida` de un renglón de factura nunca supera su cantidad.
- Un renglón fuera de alcance nunca recibe corridas `Directo` ni capas virtuales.
