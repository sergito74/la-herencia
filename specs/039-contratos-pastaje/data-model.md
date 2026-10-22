# Data Model — 039 Contratos de pastaje

Todas las tablas nuevas en WC, esquema `dbo`, aditivas. Importes `decimal(18,2)`, kg `decimal(18,4)`, índice `decimal(18,3)`. Auditoría estándar en cada tabla: `CreadoPor`, `CreadoEn`, `ModificadoPor`, `ModificadoEn`, `Version` (rowversion o int para concurrencia optimista).

## IndiceINMAG
| Campo | Tipo | Regla |
|---|---|---|
| Fecha | date PK | una fila por fecha con remate |
| Indice | decimal(18,3) | > 0; días sin índice no se guardan |
| CabIngresadas | int | entero (miles con '.') |
| Origen | varchar(10) | `auto` / `manual` |
| Fuente | varchar(200) | URL o nota |
| ObtenidoEn | datetime2 | |
| Nota | nvarchar(400) | obligatoria si `manual` o corrección |
Correcciones: se guarda historial en `IndiceINMAG_Historial` (Fecha, IndiceAnterior, IndiceNuevo, Motivo, Usuario, Momento).

## ContratosPastaje
| Campo | Regla |
|---|---|
| IdContratoPastaje PK | |
| IdContactoCliente | FK Contactos; tipo cliente |
| IdEmpresaContacto | 386 Giamigli de Bolivar (fijo) |
| IdEstablecimiento | FK Establecimientos (1) |
| FechaInicio, FechaFin NULL | FechaFin ≥ FechaInicio |
| Modalidad | `mes_vencido` (único valor por ahora) |
| CondicionVenta | `contado` |
| AlicuotaIva | 21.00 |
| CarpetaDocumentos | ruta destino de PDFs |
| ArchivoContrato NULL | adjunto opcional |
| ClausulaInfraestructura, ClausulaSanidad, ClausulaMortandad, OtrasClausulas | texto |
| Estado | `vigente` / `finalizado` / `anulado` |

## PastajeTarifas
IdTarifa, IdContratoPastaje, IdTipoHacienda (FK [Tipo Hacienda]), TipoTarifa (`kg_novillo` / `fijo_ars` / `fijo_usd`), Valor (kg/cab/mes o precio/cab/mes), VigenteDesde. Única por (contrato, categoría, VigenteDesde). El cálculo usa la tarifa vigente de cada día.

## PastajeBitacora
IdMovimiento, IdContratoPastaje, Fecha, Tipo (`ingreso`, `egreso`, `muerte`, `faltante`, `nacimiento`, `destete`, `recuento`), IdTipoHacienda, Cabezas (>0), NumeroDTe NULL, Observacion, Estado (`vigente`/`anulado`), MotivoAnulacion.
- Efecto en cabezas cobrables: ingreso +; egreso/muerte/faltante − (desde el día del evento, que no se cobra); nacimiento → cabezas no cobrables de cría; destete → pasa cabezas de cría a la categoría indicada (cobran desde esa fecha); recuento: sin efecto, guarda `CabezasSistema` y diferencia para alertar.
- Validación: no dejar cabezas negativas por categoría en ninguna fecha.

## PastajeLiquidaciones
IdLiquidacion, IdContratoPastaje, Periodo (primer día del mes), Tipo (`mensual` / `ajuste`), IdLiquidacionOriginal NULL (ajuste), Estado (`borrador` / `confirmada` / `anulada`), PrecioPromedio, KgTotal, Neto, Iva, Total, Moneda, ArchivoPdf, ConfirmadaPor/En.
Única: una `mensual` no anulada por (contrato, período).
- **PastajeLiquidacionTramos**: IdLiquidacion, IdTipoHacienda, Desde, Hasta, Cabezas, Dias, KgCabMes, Kg, Importe.
- **PastajeLiquidacionIndices**: IdLiquidacion, Fecha, Indice (copia fijada de los valores usados).
Transiciones: borrador → confirmada (fija, genera PDF) → anulada (solo sin comprobante vigente). Borrador se recalcula libremente.

## PastajeComprobantes
IdComprobante, IdContratoPastaje, IdLiquidacion NULL, Tipo (`factura` / `nota_debito` / `nota_credito`), Letra, PuntoVenta, Numero, Fecha, VtoPago, Cae, VtoCae, CuitCliente, PeriodoDesde, PeriodoHasta, Detalle, Neto, Iva, Total, IdComprobanteAsociado NULL (ND/NC → factura), IdCampaña, IdEstablecimiento, ArchivoPdf, Estado (`vigente`/`anulado`).
Única: (Tipo, Letra, PuntoVenta, Numero). Una factura vigente por liquidación mensual.
- Entra a `vw_MovimientosCuenta_Base` como Origen `'Pastaje'`: factura/ND al debe del cliente, NC al haber.
- Cobros: `AplicacionesPago` con `TipoDocumento='Pastaje'`, `IdDocumentoAplicado=IdComprobante`.

## Derivados (no persistidos)
- **Devengado del mes**: cálculo en vivo con bitácora e índices actuales.
- **Diferencia**: devengado recalculado − liquidación confirmada (alerta si ≠ 0).
- **Estado del mes**: en curso / sin liquidar / liquidado sin factura / facturado / cobrado parcial / cobrado / con diferencia.
