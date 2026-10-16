# Data Model: 037 — Descarga de peajes

Tablas nuevas en `WC`. Las crea `backend/scripts/crear_esquema_descarga_peajes_037.py` de forma idempotente, con respaldo verificado antes y la opción `--revertir`. Los nombres son nuevos y no reutilizan ninguna tabla existente.

## dbo.DescargaPeajes_Ejecuciones

| Campo | Tipo | Notas |
| --- | --- | --- |
| IdEjecucion | int IDENTITY PK | |
| Origen | varchar(10) NOT NULL | `manual` \| `semanal` |
| Usuario | varchar(60) NULL | usuario de la sesión si es manual |
| Inicio | datetime2 NOT NULL | default SYSDATETIME() |
| Fin | datetime2 NULL | |
| Estado | varchar(15) NOT NULL | `en_curso` → `completa` \| `con_errores` \| `incompleta` \| `salteada` |
| Mensaje | nvarchar(400) NULL | error general (ej. carpeta Dropbox no disponible) |

Transiciones: `en_curso` → `completa` si todos los portales terminan bien; → `con_errores` si al menos uno falla; → `incompleta` si la detecta la siguiente ejecución sin lock vivo (R3). `salteada` se crea directamente cuando no se obtiene el lock.

## dbo.DescargaPeajes_EjecucionPortales

| Campo | Tipo | Notas |
| --- | --- | --- |
| IdEjecucion | int FK → Ejecuciones | PK compuesta (IdEjecucion, Portal) |
| Portal | varchar(20) | `TelepeajePlus` \| `TelePASE` \| `CEAMSE` \| `AUBASA` |
| Estado | varchar(15) | `pendiente` → `en_curso` → `ok` \| `error` \| `sin_credenciales` |
| Nuevos | int default 0 | documentos bajados en esta ejecución |
| Existentes | int default 0 | ofrecidos por el portal y ya registrados |
| Cargados | int default 0 | compras creadas automáticamente |
| Pendientes | int default 0 | quedaron para carga manual |
| Error | nvarchar(400) NULL | mensaje legible, nunca credenciales |

## dbo.DescargaPeajes_Documentos

| Campo | Tipo | Notas |
| --- | --- | --- |
| IdDocumento | int IDENTITY PK | |
| Clave | varchar(120) NOT NULL UNIQUE | identificador en el portal (las mismas claves del manifiesto actual: `tp-resumen-<id>`, `tp-FA…pdf`, `ts-<conc>-<nro>`, `ceamse-<pv>-<nro>`, `aubasa-<pv>-<nro>`) |
| Portal | varchar(20) NOT NULL | |
| Proveedor | varchar(40) NOT NULL | nombre estándar del archivo (`AutopistasDelSol`, …); `desconocido` en los `historico` |
| IdContacto | int NULL | contacto de Compras según el mapeo; NULL si el concesionario es desconocido |
| FechaDocumento | date NULL | NULL solo en los `historico` importados del manifiesto (no se conoce la fecha) |
| NumeroDocumento | varchar(30) NULL | como se carga en `Compras.[Nro Documento]` |
| TotalImpreso | decimal(18,2) NULL | |
| Ruta | nvarchar(400) NULL | ruta completa del PDF; NULL en `historico` sin archivo identificado |
| IdEjecucion | int NULL FK | NULL para los importados del manifiesto |
| EstadoCarga | varchar(20) NOT NULL | `cargado_auto` \| `ya_cargado` \| `pendiente` \| `historico` |
| Motivo | nvarchar(300) NULL | por qué quedó pendiente (formato no reconocido, no cierra por $X, concesionario sin proveedor, número duplicado con otro total…) |
| IdCompra | int NULL | `Compras.IdDeuda` creada o encontrada |
| Creado | datetime2 NOT NULL default SYSDATETIME() | |

Reglas:
- `Clave` única: es lo que evita volver a bajar un documento (FR-006).
- Un documento `pendiente` cuenta para el contador mientras no exista una compra con `[Documento Original] = Ruta` o con `(IdContacto, [Nro Documento])` igual; al consultarlo se actualiza a `ya_cargado` con su `IdCompra` (R8).
- Una compra creada automáticamente es una fila común de `dbo.Compras`, `dbo.Det_Compras` y, si corresponde, `dbo.[Vencimiento Compras]`, creada por `compras.repository.create_compra`. No se agregan columnas a esas tablas.

## Mapeo de proveedores (en código, `portales.py`)

| Portal / concesionario | Proveedor (archivo) | IdContacto |
| --- | --- | --- |
| TelepeajePlus resumen | Telepeaje | 328 |
| TelepeajePlus CVSA* / TelePASE ACCESO RICCHERI | CorredoresViales | 436 |
| TelepeajePlus CORRESUR* | Corresur | 2657 |
| TelepeajePlus PENTAVIA | CV5 | 2658 |
| TelePASE ACCESO NORTE | AutopistasDelSol | 276 |
| TelePASE ACCESO OESTE | GrupoConcesionarioDelOeste | 306 |
| TelePASE AUTOPISTAS URBANAS | AUSA | 380 |
| TelePASE AU. BS AS - LA PLATA / oficina virtual AUBASA | AUBASA (la misma factura se baja una sola vez: se compara el número entre los dos portales) | 316 |
| TelePASE AU. ROSARIO - SANTA FE | AutopistaRosarioSantaFe | — (sin contacto: queda pendiente) |
| TelePASE AU. DEL MERCOSUR | AutopistaDelMercosur | — (sin contacto: queda pendiente) |
| CEAMSE | Ceamse | 314 |
| AUBASA | AUBASA | 316 |
