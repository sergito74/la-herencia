# Data Model: Detector de facturas faltantes

Lecturas (sin cambios): `Compras` + `vw_Compras_ImporteDocumento`, `vw_MovimientosCuenta_Saldo` (pagos y saldo), vías de vínculos de `features/vinculos/fuente`, `Retenciones`, `tblRemitoCompra`/`Remitos_Facturas`, `Contactos`.

## Tablas nuevas (WC, DDL con respaldo)

### dbo.FacturasFaltantesPerfil
| Columna | Tipo | Regla |
|---|---|---|
| IdContacto | int PK | contacto proveedor |
| CicloDias | int NULL | 30/60/90 fijado a mano; NULL = aprendido |
| SinCiclo | bit | 1 = no esperar facturas periódicas |
| MargenDias | int NULL | NULL = 15 (mensual) / 25 |
| DadoDeBaja | bit | respuesta a la pregunta de baja |
| PreguntaBajaFecha | datetime2 NULL | cuándo se preguntó (una sola vez) |
| Usuario, FechaModificacion | | auditoría |

### dbo.FacturasFaltantesAlarmas (decisiones)
| Columna | Tipo | Regla |
|---|---|---|
| IdDecision | int identity PK | |
| Clave | nvarchar(120) UNIQUE | firma estable de la señal (tipo + origen + período) |
| IdContacto | int | |
| Decision | nvarchar(20) | 'descartada' |
| Motivo | nvarchar(255) | obligatorio |
| Usuario, Fecha | | |

### dbo.FacturasFaltantesMarcas
| Columna | Tipo | Regla |
|---|---|---|
| IdMarca | int identity PK | |
| IdContacto | int | |
| OrigenPago | nvarchar(30) | medio (galicia, bna, efectivo, tarjetas, …) |
| IdPago | int | movimiento del medio |
| PeriodoDesde, PeriodoHasta | date NULL | |
| ImporteAprox | money NULL | |
| Estado | nvarchar(10) | 'abierta' / 'cerrada' |
| IdDeudaCierre | int NULL | comprobante que la cerró |
| Usuario, FechaAlta, FechaCierre | | |

Único filtrado: una marca abierta por (OrigenPago, IdPago).

## Transiciones
- Período: pendiente → llegó | atrasada → llegó; atrasada → ¿baja? (3 ciclos) → dado de baja.
- Alarma: abierta → descartada (motivo) | → marca de falta factura.
- Marca: abierta → cerrada (al detectar factura compatible: mismo proveedor, ±60 días, importe aproximado ±30% o sin importe).
