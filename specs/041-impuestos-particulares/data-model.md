# Data Model — 041 Impuestos particulares

## dbo.ImpuestosParticulares
| Campo | Regla |
|---|---|
| IdCarga int IDENTITY PK | |
| IdImpuesto int NOT NULL | dbo.Impuestos |
| IdSocio int NOT NULL | 1 Sergio, 2 Lucy, 3 Condominio LSC, 4 Ceci |
| Importe decimal(18,2) NOT NULL | > 0; Σ vigentes por impuesto ≤ Impuestos.Importe |
| Motivo nvarchar(255) NOT NULL | |
| Partida nvarchar(60) NULL | inmobiliaria, patente o tasa |
| IdMovimientoSocio int NOT NULL | Debe en MovimientosCuentaSocio (Origen 'ImpuestoParticular', IdOrigen = IdCarga) |
| Estado varchar(10) NOT NULL | 'vigente' / 'anulada' |
| MotivoAnulacion, CreadoPor, CreadoEn, AnuladoPor, AnuladoEn | auditoría |

## dbo.ImpuestosParticularesDevoluciones
IdCarga, IdMovimientoSocio (Haber del mismo socio), Importe, Usuario, Fecha. PK (IdCarga, IdMovimientoSocio).

## dbo.PartidasTitulares
Partida (PK), IdSocio, IdCargaOrigen, Fecha, Usuario.

## Derivados
- Impuesto: `aCargoDeSocios` = Σ cargas vigentes; `parteEmpresa` = Importe − aCargoDeSocios.
- Carga: `devuelto` = Σ devoluciones; estado devuelto / parcial / pendiente.
