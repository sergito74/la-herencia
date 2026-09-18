# Data Model: Ventas de Hacienda (alta) y Ventas de Granos (lectura + alta)

Todas las tablas de negocio ya existen en `WC`/`LaHerencia` (confirmadas por `INFORMATION_SCHEMA`/`sys.foreign_keys` reales, ver `research.md`). Este spec agrega únicamente las tablas de bloqueo de edición: `VentaHaciendaEditLocks`, `VentaGranosEditLocks` (mismo patrón que `CompraEditLocks` de 006).

## Venta de Hacienda (tabla `dbo.[Venta Hacienda]`)

| Campo (API) | Columna real | Tipo | Obligatorio en alta | Notas |
|---|---|---|---|---|
| idVenta | IdVenta (PK, identity) | int | — (generado) | |
| idConsignatario | IdConsignatario | int, nullable | Sí | Debe existir en `Contactos`, tipo ∈ {Comprador, Consignatario, Multiple} (research.md §2). |
| idEstablecimiento | IdEstableciemiento (**sic**, typo real de la columna) | int, NOT NULL | Sí | FK lógica a `Establecimientos.Id` (sin constraint declarada, validar en aplicación). |
| idTipoDocumento | IdTipoDocumento | int, nullable | Sí | FK lógica a `[Tipo Documento]` (catálogo real, no un enum fijo — ver research.md §1). |
| numeroDocumento | [Nro documento] | nvarchar(50), nullable | Sí | |
| fecha | Fecha | datetime, nullable | Sí | |
| porcComision | [Porc Comision] | real, nullable | No (default 0) | |
| visMunicipal | [Vis Municipal] | money, nullable | No (default 0) | |
| balanza | Balanza | money, nullable | No (default 0) | |
| gsVsNoGravados | [Gs Vs No Gravados] | money, nullable | No (default 0) | |
| alicuotaIVA | AlicuotaIVA | money, nullable | No (default 0) | Porcentaje. |
| retencionGanancias | [Retencion Ganancias] | money, nullable | No (default 0) | |
| retencionIVA | [Retencion IVA] | money, nullable | No (default 0) | |
| ingresosBrutos | [Ingresos Brutos] | money, nullable | No (default 0) | |
| leyDeSellos | [Ley de Sellos] | money, nullable | No (default 0) | |
| flete | Flete | money, nullable | No (default 0) | |
| gastosVarios | [Gastos Varios] | money, nullable | No (default 0) | |
| complemento | Complemento | money, nullable | No (default 0) | |
| documentoOriginal | [Documento Original] | nvarchar(MAX), nullable | No | Mismo patrón que Compras: enlace/ruta local servido por `GET /api/ventas-hacienda/documento-local`. |

Columna del esquema real no expuesta en v1: `IdOperacion`.

**Campos calculados** (fórmula real confirmada contra `Frm Venta Hacienda`, no reinventada):
- `subTotal` = Σ(línea.subtotalA) = Σ(línea.cantidad × línea.precioUnitarioA)
- `subtotalB` = Σ(línea.cantidad × línea.precioUnitarioB)
- `comision` = (subTotal + subtotalB) × porcComision / 100
- `iva` = (subTotal − visMunicipal − balanza − comision − gsVsNoGravados) × alicuotaIVA / 100
- `importe` = subTotal − visMunicipal − balanza − comision − gsVsNoGravados + iva − leyDeSellos − retencionGanancias − ingresosBrutos − gastosVarios
- `importeTotal` = importe + subtotalB

## Línea de Venta de Hacienda (tabla `dbo.[Det_Ventas Hacienda]`)

| Campo (API) | Columna real | Tipo | Obligatorio | Notas |
|---|---|---|---|---|
| idDetalleVenta | IdDetalleVenta (PK, identity) | int | — (generado) | |
| idVenta | IdVenta | int, nullable | Sí (FK real declarada) | `FK_DetVentasHacLB_VentaHacLB` — única FK real de todo este dominio. |
| idComprador | IdComprador | int, nullable | Sí | Debe existir en `Contactos`, tipo ∈ {Comprador, Multiple} (research.md §2) — **independiente del consignatario de cabecera** (FR-002). |
| idTipoProducto | IdTipoProducto | int, nullable | Sí | FK lógica a `[Tipo Hacienda]` (catálogo ya usado en spec 005, FR-009). |
| cantidad | Cantidad | real, nullable | Sí | Cantidad de cabezas. Sin validar > 0 (mismo criterio que Compras). |
| unidadMedida | [Unidad de medida] | nvarchar(255), nullable | No | |
| pesoTotal | [Peso Total] | real, nullable | No | |
| precioUnitarioA | [Precio unitario (A)] | money, nullable | Sí | |
| precioUnitarioB | [Precio unitario (B)] | money, nullable | No (default 0) | Se suma aparte al importe total, sin pasar por IVA/deducciones (ver fórmula de cabecera). |

**Campos calculados**: `subtotalA` = cantidad × precioUnitarioA; `subtotalB` = cantidad × precioUnitarioB; `importe` = subtotalA + subtotalB (mismo nombre que ya usa el contrato de lectura existente, `LineaVentaHacienda.importe` en `backend/src/features/ventas_hacienda/schemas.py` — no introducir un segundo nombre para el mismo concepto entre el camino de lectura y el de escritura).

## Vencimiento de Venta (tabla `dbo.[Vencimientos Ventas]`, compartida entre Hacienda y Granos)

| Campo (API) | Columna real | Tipo | Obligatorio | Notas |
|---|---|---|---|---|
| idVencimientoVenta | IdVencimientoVenta (PK, identity) | int | — (generado) | |
| idVenta | IdVenta | int, nullable | Sí | Sin FK declarada — validar en aplicación (research.md §1). |
| fecha | Fecha | datetime, nullable | Sí | |
| importe | Importe | money, nullable | Sí | A diferencia de Compras (solo fecha), acá el vencimiento tiene su propio importe (FR-004). |

## Venta de Granos (tabla `dbo.[Venta Granos]`)

| Campo (API) | Columna real | Tipo | Obligatorio en alta | Notas |
|---|---|---|---|---|
| idVenta | IdVenta (PK, identity) | int | — (generado) | |
| idConsignatario | IdConsignatario | int, nullable | Sí | Debe existir en `Contactos`; histórico usa 100% tipo Multiple, se admite también Comprador/Consignatario (research.md §3). |
| idTipoDocumento | IdTipoDocumento | int, nullable | Sí | FK lógica a `[Tipo Documento]` (mismo catálogo que Hacienda). |
| numeroDocumento | [Nro Documento] | nvarchar(255), nullable | Sí | |
| fecha | Fecha | datetime, nullable | Sí | |
| precioUnitario | [Precio unitario] | money, nullable | Sí | Único (a diferencia de Hacienda, que tiene A/B). |
| tipoCambio | [Tipo Cambio] | money, nullable | No | Presente en el esquema real; moneda no está explícitamente modelada como enum — asumir Pesos si no se informa (igual criterio que "sin tipo de cambio = Pesos" de Compras). |
| gradoOperacion | [Grado Operacion] | nvarchar(5), nullable | No | Campo de significado ambiguo — se captura tal cual (decisión Q2, research.md §4). |
| idProducto | IdProducto | int, nullable | Sí | FK lógica a `Granos.IdGrano` (join real confirmado con muestra, research.md §3). |
| tipoDeGrano | [Tipo de Grano] | nvarchar(255), nullable | No | Texto libre, redundante con el catálogo `Granos.[Tipo de Cultivo]` — capturar tal cual sin forzar consistencia. |
| campania | Campaña | nvarchar(10), nullable | No | **Texto libre, no FK** — valores reales inconsistentes ('2011', '2010/2011'); input de texto, no combo cerrado (research.md §3, decisión ya anticipada en Assumptions del spec). |
| flete | Flete | money, nullable | No (default 0) | Entra en la fórmula de `precioKg`. |
| nroDeposito | [Nro Deposito] | nvarchar(255), nullable | No | |
| gradoMercaderia | [Grado Mercaderia] | nvarchar(5), nullable | No | Campo de significado ambiguo — se captura tal cual (decisión Q2). |
| factor | Factor | real, nullable | No (default 100) | Entra en la fórmula de `precioKg`. |
| contProteico | [Cont Proteico] | real, nullable | No | |
| cantidadEntregada | [Cantidad entregada] | real, nullable | Sí | Campo separado de `cantidadVendida` (decisión Q2) — no fusionar. |
| cantidadVendida | [Cantidad vendida] | real, nullable | Sí | Entra en la fórmula del subtotal. |
| alicuotaIVA | AlicuotaIVA | real, nullable | No (default 0) | Porcentaje. |
| retencionIVA | [Retencion IVA] | money, nullable | No (default 0) | |
| retIG | [Ret IG] | money, nullable | No (default 0) | Retención Ganancias. |
| percepciones | Percepciones | money, nullable | No (default 0) | |
| otraRetenciones | [Otra Retenciones] | money, nullable | No (default 0) | |
| sellado | [Sellado (0,375%)] | money, nullable | No (default 0) | |
| derechoRegistro | [Derecho de Registro (0,125%)] | money, nullable | No (default 0) | |
| honorariosCamara | [Honorarios Camara] | money, nullable | No (default 0) | |
| aCuentaCalidad | [A cuenta de Calidad] | money, nullable | No (default 0) | |
| iibb | [IIBB (1%)] | money, nullable | No (default 0) | |
| documentoOriginal | [Documento Original] | nvarchar(MAX), nullable | No | Mismo patrón que Compras/Hacienda. |

Columna del esquema real no expuesta en v1: `IdOperacion`. `[Importe Neto a percibir]` no se lista como input — es 100% campo calculado (ver abajo), no se persiste como valor tipeado por el usuario aunque la columna real permita guardarlo; el backend siempre lo recalcula al guardar.

**Campos calculados** (fórmula real confirmada contra `Frm Venta Granos`, en este orden):
- `precioKg` = (precioUnitario × factor / 100 − flete) / 1000
- `subTotal` = (cantidadVendida × precioKg) + Σ(ajuste.importe)
- `iva` = subTotal × alicuotaIVA / 100
- `importeConIVA` = subTotal + iva
- `totalOperacion` = importeConIVA
- `totalRetenciones` = retIG + retencionIVA
- `totalDeducciones` = Σ((deduccion.baseCalculo × deduccion.porc / 100) + (deduccion.baseCalculo × deduccion.porc / 100 × deduccion.alicuota / 100))
- `importeNetoAPercibir` = totalOperacion − (totalRetenciones + percepciones + otraRetenciones + totalDeducciones)

## Ajuste de Venta de Granos (tabla `dbo.[Venta Granos_Ajustes]`)

| Campo (API) | Columna real | Tipo | Obligatorio | Notas |
|---|---|---|---|---|
| idAjuste | IdAjuste (PK, identity) | int | — (generado) | |
| idVenta | IdVenta | int, nullable | Sí (FK real declarada) | |
| concepto | Concepto | nvarchar(50), nullable | Sí | Texto libre. |
| importe | Importe | money, nullable | Sí | Suma al subtotal (research.md, fórmula §5 arriba). |
| alicuotaIVA | AlicuotaIVA | real, nullable | No (default 0) | Informativo — el IVA de la venta se calcula sobre el subtotal ya incluidos los ajustes, no ajuste por ajuste. |

## Deducción de Venta de Granos (tabla `dbo.[Venta Granos_Deducciones]`)

| Campo (API) | Columna real | Tipo | Obligatorio | Notas |
|---|---|---|---|---|
| idDeduccion | IdDeduccion (PK, identity) | int | — (generado) | |
| idVenta | IdVenta | int, nullable | Sí (FK real declarada) | |
| idConcepto | IdConcepto | int, nullable | Sí (FK real declarada) | FK a `[Venta Granos_ConceptosDeducciones]`. |
| detalle | Detalle | nvarchar(50), nullable | No | Texto libre adicional al concepto. |
| porc | Porc | real, nullable | Sí | Porcentaje sobre `baseCalculo`. |
| baseCalculo | [Base Calculo] | money, nullable | Sí | |
| alicuota | Alicuota | real, nullable | No (default 0) | Alícuota de IVA de esta deducción puntual. |

## Documento relacionado (reuso del patrón de Compras)

Mismo mecanismo que `CompraDocumentosRelacionados` (006), aplicado a ventas: tabla nueva `VentaDocumentosRelacionados` (`IdVenta`, `IdVentaRelacionada`, `TipoVenta` — para distinguir Hacienda/Granos, dado que comparten el espacio de `IdVenta` como PK autoincremental mutuamente independiente entre ambas tablas).

## Locks de edición (tablas nuevas, mismo patrón que `CompraEditLocks`)

- `dbo.VentaHaciendaEditLocks` (`IdVenta`, `LockToken`, `LockedAt`, `ExpiresAt`)
- `dbo.VentaGranosEditLocks` (`IdVenta`, `LockToken`, `LockedAt`, `ExpiresAt`)

TTL: 5 minutos (no 15 — lección aprendida en 006, ver research.md §5).
