# Data Model — 041 Impuestos particulares

Refinado25/10/2026. Tres tablas nuevas; no alterar dbo.Impuestos ni ampliar MovimientosCuentaSocio.Origen (varchar(20) verificado). Todas las referencias usan identificadores reales; toda escritura exclusiva deWC.

## dbo.ImpuestosParticulares

| Campo | Regla |
|---|---|
| IdCarga int IDENTITY PK | Identidad de cada carga; no usar IdImpuesto como IdOrigen del Debe |
| IdImpuesto int NOT NULL | FK dbo.Impuestos; no cascada de borrado |
| IdSocio int NOT NULL | FK Socios:1 Sergio,2 Lucy,3 Condominio LSC,4 Ceci |
| Importe decimal(18,2) NOT NULL | >0; suma vigente por impuesto no supera Importe de boleta, bajo bloqueo de la boleta |
| Motivo nvarchar(255) NOT NULL | Texto recortado, no vacío |
| Partida nvarchar(60) NULL | Referencia completa normalizada: trim, espacios colapsados y mayúsculas; preservar ceros y puntuación |
| TitularOscar bit NOT NULL DEFAULT0 | Solo con Partida informada; si true,IdSocio=3; no entidadOscar separada |
| IdMovimientoSocio int NOT NULL | FK al Debe; Origen='ImpuestoParticular',IdOrigen=IdCarga, magnitudes positivas |
| Estado varchar(10) NOT NULL | vigente / anulada |
| ClaveIdempotencia uniqueidentifier NOT NULL | UNIQUE dentro de tabla; clave de creación, no se libera al anular |
| HuellaSolicitud char(64) NOT NULL | SHA256 del cuerpo canónico y usuario autenticado; decimal normalizado y campos efectivos de intención, no cotización variable |
| CreadoPor nvarchar(60) NOT NULL, CreadoEn datetime2 NOT NULL | Usuario de sesión y fechaUTC servidor |
| MotivoAnulacion nvarchar(255) NULL, AnuladoPor nvarchar(60) NULL, AnuladoEn datetime2 NULL | Obligatorios al anular; motivo no vacío |

Secuencia dentro de una transacción: crear Debe aún sin origen ligado, insertar carga con su IdMovimientoSocio y obtener IdCarga, completar Origen/IdOrigen del Debe y confirmar. Ningún estado intermedio se confirma; el fallo revierte todo. No se modifica el índice único existente de Debe vigentes por origen.

## dbo.ImpuestosParticularesDevoluciones

| Campo | Regla |
|---|---|
| IdVinculo int IDENTITY PK | Identidad de cada vínculo histórico |
| IdCarga int NOT NULL | FK a carga |
| IdMovimientoSocio int NOT NULL | FK a Haber vigente TipoDevolucion del mismo socio |
| Importe decimal(18,2) NOT NULL | >0; importe nominal asignado, no necesariamente todo el Haber |
| Estado varchar(10) NOT NULL | vigente / anulada |
| ClaveIdempotencia uniqueidentifier NOT NULL, HuellaSolicitud char(64) NOT NULL | UNIQUE de clave dentro de tabla; misma semántica que carga; cuerpo distingue vínculo existente de Haber nuevo |
| Usuario nvarchar(60) NOT NULL, Fecha datetime2 NOT NULL | Creación auditada, horaUTC servidor |
| MotivoAnulacion nvarchar(255) NULL, AnuladoPor nvarchar(60) NULL, AnuladoEn datetime2 NULL | Obligatorios al anular |

Índice único filtrado(IdCarga,IdMovimientoSocio)WHERE Estado='vigente'; reemplaza la PK compuesta inicial para permitir anulación y posterior revinculación sin borrar historial. IdVinculo nuevo y clave nueva en una acción nueva. No modificar en sitio el importe de un vínculo: anularlo y crear otro.

Capacidad bajo bloqueo de carga y Haber: `pendienteCarga = ImporteCarga − SUM(vínculos vigentes)`; `disponibleHaber = ImporteHaber − SUM(vínculos vigentes de ese Haber en todas las cargas)`. Solo cuentan cargas vigentes y Haber no anulado. Rechazar por exceso, socio distinto, tipo incorrecto o movimiento anulado. Un Haber nuevo se crea y vincula por el mismo importe en la misma transacción, con Origen='DevImpParticular',IdOrigen=IdCarga; a_fecha en la fecha del Haber, siempre magnitudes positivas. No representa un cobro nuevo de tesorería.

## dbo.PartidasTitulares

| Campo | Regla |
|---|---|
| Partida nvarchar(60) PK | Mismo criterio de normalización que carga |
| IdSocio int NULL | Solo informado cuando hay un único titular vigente |
| IdCargaOrigen int NULL | Una carga vigente del titular único; tomar el menor IdCarga vigente para resultado determinista |
| Estado varchar(12) NOT NULL | vigente / ambigua / sin_cargas |
| TitularOscar bit NOT NULL | Derivado de cualquier carga vigente con esa declaración |
| Fecha datetime2 NOT NULL, Usuario nvarchar(60) NOT NULL | Último recálculo auditado |

Materialización derivada, no editable independientemente:0 socios distintos en cargas vigentes → sin_cargas sin propuesta;1 → vigente;2 o más → ambigua,IdSocio/IdCargaOrigenNULL. Candidatos se consultan de las cargas, no se duplica su lista en la tabla. Si hay declaraciónOscar vigente, rechazar una carga nueva de esa partida a socio distinto de3; no sobrescribir titular para esconder el conflicto. Anular la última carga de la partida no borra el registro: pasa a sin_cargas.

No se agrega asociación partida/impuesto fuera de las cargas. El formulario consulta el padrón con una partida ingresada; al abrir una boleta se pueden recuperar partidas de sus cargas existentes, pero no inferirla cuando no hay ninguna.

## Integridad y operaciones coordinadas

- Bloquear edición de Fecha/Importe/IdOrganismo/IdTipoImpuesto y baja de una boleta mientras tenga cargas vigentes. El mismo bloqueo de la boleta serializa edición/baja y creación.
- Bloquear cambios directos de un Debe ligado a carga vigente y de cualquier Haber con vínculos vigentes, también desde anulación/corrección de su operación de origen. Devolver409 con referencias. Desvincular primero; no bypass por rutas alternativas ni operaciones de caja.
- Anular carga = anular Debe y todos sus vínculos vigentes, conservar todos los Haber y recalcular padrón en una transacción. No crear compensación automática. Anular un vínculo solo libera capacidad nominal, sin tocar Haber ni su cotización.
- Mantener orden de bloqueo determinista entre boleta/cargas, movimientos y partida en todas las rutas; concurrencia nunca supera total, reutiliza capacidad ni confirma una fila huérfana.
- Anulaciones repetidas devuelven estado actual sin nuevas escrituras ni duplicar auditoría. Las claves de creación no caducan ni se reutilizan en entidades anuladas.

## Derivados y unidades

- Impuesto:`aCargoDeSocios = Σ cargas vigentes`;`parteEmpresa = Importe − aCargoDeSocios`.
- Carga:`devueltoNominal = Σ vínculos vigentes`;`pendienteNominal = Importe − devueltoNominal`; pendiente si0 devuelto,parcial si0<devuelto<Importe,devuelto siigual. Nunca saldo negativo ni sobredevolución.
- En lista de varias cargas:devuelto solo si todas las vigentes lo están;pendiente si ninguna tiene devolución;parcial en los demás casos;sin cargas → estadoDevolucionNULL.
- Estado «devuelto» significa devolución nominal en pesos. No recalcular cotizaciones ni forzar saldo de la cuenta enUSD/kg a cero: cada movimiento conserva su fecha/valuación histórica. UI informa la diferencia entre estado nominal y saldo actualizado.
- Cambios del padrón y anulación conservan trazabilidad en tablas y auditoría existente del sistema. No se alteran boletas,pagos,cuenta del organismo ni mutuoscerrados para hacer coincidir saldos.
