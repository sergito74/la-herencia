# Data Model: Módulo Ganadero (052)

Las tablas nuevas llevan el prefijo `Gan` (verificado que no choca con tablas ajenas). Todas tienen `CreadoPor`, `CreadoEn` y, cuando corresponde, `Anulado bit`. La etapa en que entra cada una se indica entre corchetes.

## Cambios a tablas existentes [E1]
- `Map_CultivoResultado` + `EsGanaderia bit NOT NULL DEFAULT 0`, en 1 para Avena, Pastura, Maíz diferido, Sorgo, Rye grass y Verdeos (FR-004).
- `[Tipo Hacienda]`, `[Venta Hacienda]` y `[Det_Ventas Hacienda]` no se modifican.

## GanCategoria [E1]
| Columna | Tipo | Nota |
|---|---|---|
| IdCategoria | int PK identity | |
| Nombre | nvarchar(60) | Vacas, Vacas 2.º servicio, Vaquillonas 1-2, Vaquillonas 2 dientes, Vaquillonas preñadas, Vacas preñadas, Vacas conserva, Terneras 15 meses, Terneros, Terneras, Novillitos, Novillos, Toritos, Toros |
| IdTipoHacienda | int NULL | equivalencia con `[Tipo Hacienda]` para las ventas |
| Sexo | char(1) | H/M |
| CoefEV | decimal(5,2) | vaca 1; toro 1,3; torito, novillo y novillito 0,7; ternero/a 0,6; vaquillona 0,8 |
| PesoTipicoKg | decimal(7,1) | para estimar kg (FR-009) y valuar (E2) |
| Orden | int | orden de evolución |
| IdCategoriaSiguiente | int NULL FK | cambio de categoría |
| EsReproductor | bit | capital en reproductores (FR-012) |
| Activo | bit | |

## GanCategoriaAlias [E1]
`Texto nvarchar(80) UNIQUE` → `IdCategoria`. Ejemplos: "Terneros / Terneras al pie", "Vaq. 1-2", "Terneras Miguel".

## GanMovimiento [E1]
| Columna | Tipo | Nota |
|---|---|---|
| IdMovimiento | int PK | |
| Fecha | date | |
| Tipo | nvarchar(20) CHECK | Nacimiento, Compra, Venta, Muerte, Consumo, CambioCategoria, PastajeEntrada, PastajeSalida, Traslado, AjusteRecuento |
| IdCategoria | int FK | |
| IdCategoriaDestino | int NULL | solo en CambioCategoria |
| Cabezas | int | con signo según el tipo; validación: la existencia no puede quedar negativa (aviso) |
| Kg | decimal(12,1) NULL | |
| KgEstimado | bit | |
| IdContactoDueno | int NULL | NULL = propia; tercero = contacto (San Justo 5671) |
| IdEstablecimiento | int FK Establecimientos | 1 La Herencia, 2 San Pedro |
| IdEstablecimientoDestino | int NULL | solo en Traslado |
| IdDetalleVenta | int NULL FK `[Det_Ventas Hacienda]` | UNIQUE si no es NULL: una venta, un movimiento |
| IdContratoPastaje | int NULL | |
| IdCompra | int NULL (IdDeuda) | compra de hacienda |
| Causa, CausaDiagnostico | nvarchar(40) NULL | solo en Muerte (FR-006) |
| Fuente | nvarchar(120) | "Venta 0003-00010318", "Recuento 06/04/2026", etc. |
| Motivo | nvarchar(300) NULL | obligatorio en AjusteRecuento |
| Anulado | bit | |

**Regla de existencia a una fecha F:**
- Se toma el recuento confirmado más cercano anterior o igual a F, por establecimiento y dueño, y se le suman los movimientos no anulados posteriores a ese recuento y hasta F.
- Las ventas generan su movimiento desde `ventas_hacienda/repository.py`, con cabezas por la regla R4.

## GanRecuento / GanRecuentoDetalle [E1]
- **GanRecuento:**
  - IdRecuento, Fecha, IdEstablecimiento;
  - Origen CHECK (Recuento, Acta, Cierre, Planilla);
  - Archivo nvarchar(400) NULL, Observaciones.
- **GanRecuentoDetalle:**
  - IdRecuento, IdCategoria, IdContactoDueno NULL, Cabezas;
  - KgPromedio NULL, PrecioCabeza NULL, Moneda NULL (la planilla trae precios).
  - UNIQUE (IdRecuento, IdCategoria, IdContactoDueno).

## GanRubroMapa [E1]
- **Columnas:**
  - RubroPlanilla nvarchar(60);
  - Grupo: Ventas, Comercializacion, Directos, Sanidad, Alimentacion;
  - Orden;
  - IdRubro NULL FK Rubros, IdDestino NULL FK DestinoCompras, IdCultivo NULL FK Cultivos.
- **Regla:** cada fracción de `vw_Gan_Costos` cae en un solo rubro de la planilla (el mapeo más específico gana); lo que no mapea va a "Otros", que es visible.

## GanForrajeRegla [E1]
`IdCultivo` PK, `Tratamiento` CHECK ('Consumo', 'Amortiza'), `Anios` (Pastura = 4).

## GanCalendarioCultivo [E1]
`IdCultivo`, `MesDesde`, `MesHasta`: meses fuera del pastoreo cuando no hay fechas reales (R3).

## GanSuperficieAjuste [E1]
`IdLote`, `Ejercicio`, `MesesGanaderos` override con `Motivo`. Es la excepción documentada; no se usa como regla.

## GanControlAceptado [E1]
La misma forma que `ControlRemitosAceptados`: Tipo, Clave (texto estable del caso), Motivo, Usuario, Fecha, Vigente.

## Vista vw_Gan_Costos [E1]
Columnas: Fecha, Ejercicio, Campania, IdCompra, IdDetalleCompra, IdLote NULL, IdCultivo NULL, IdRubro, IdDestino, Origen (050 / Tamiz / Centro2), Fraccion, ImportePesos, ImporteUSD_TC, ImporteUSD_Billete.
- Neto de IVA y de la parte particular.
- **Invariante (SC-008):** Σ de los centros = total de compras.

## Etapa 2 (modelo previsto, no se crea en E1)
- **GanValuacionCierre:** Ejercicio, IdCategoria, Cabezas, KgCab, PrecioKg, Fuente, PctGastosVenta, Valor, Confirmado.
- **GanPlanSanitario.**
- **GanAplicacionSanitaria:** FK a `Stock_Bajas` con IdCentro = 2.
- **GanTrabajoVeterinario:** FK a la compra.
- **GanObservado:** caravana/CUIG.
- **GanFrasco:** serie, nro SENASA, vencimiento, dosis.
