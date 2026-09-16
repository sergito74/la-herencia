# Análisis de lógica de negocio — Sistema Access legado

**Fecha del relevamiento**: 2026-09-16
**Método**: automatización COM de solo lectura sobre Microsoft Access (`Access.Application`, `OpenCurrentDatabase(path, False)`, `SaveAsText` para exportar formularios/módulos/informes a texto plano). Nunca se ejecutó código VBA, nunca se guardó/compactó/reparó nada, nunca se abrió en modo exclusivo. Código fuente exportado disponible en el scratchpad de la sesión que lo generó (no versionado en este repo).

**Propósito de este documento**: es el insumo consolidado para decidir, vía `/speckit-specify` y `/speckit-clarify`, cómo ampliar o crear specs que incorporen la lógica de negocio real descubierta acá. No reemplaza ninguna spec — es research previo a especificar.

## 0. Qué son los dos archivos

| Archivo | Rol |
|---|---|
| `AdmLaHerenciaVer3.accdb` | Sistema administrativo/operativo completo: compras, ventas de granos, ventas/compra de hacienda, alquileres, remuneraciones, impuestos, tarjetas de crédito, y un módulo agrícola/productivo entero (costeo por cultivo). |
| `La Herencia - Cuentas.accdb` | Subconjunto especializado en tesorería/cuenta corriente/tarjetas. Tiene lógica duplicada de `AdmLaHerenciaVer3` (queries casi idénticas copiadas) y también se usó como herramienta de migración Access→SQL Server. |

Ambos usan tablas vinculadas (linked tables) al mismo SQL Server (`LaHerencia`), pero **toda la lógica de negocio real vive en consultas, formularios y VBA de Access**, no en el esquema SQL Server — de ahí la necesidad de este relevamiento.

---

## 1. Hallazgos que confirman y precisan specs ya escritas

### 1.1 Fórmula de saldo de cuenta corriente (`004-cuentas-corrientes`)

Confirmado en dos lugares (el cálculo manual legado en VBA de `FrmConsultaMovimientosCuentas`, y el `RecordSource` de `SbfrmMovCuenta` que ya usa la vista SQL nueva):

- El saldo es un **acumulado cronológico con signo**: `SaldoParcial = SaldoParcial - Deuda + Credito`.
- **Orden de acumulación**: `Fecha, Origen, IdOrigen` — no solo fecha. `Origen`/`IdOrigen` son el criterio de desempate cuando hay varios movimientos el mismo día.
- El **saldo actual** de un contacto es simplemente el `SaldoParcial` de la última fila de esa serie (`TOP 1 ORDER BY Fecha DESC, Origen DESC, IdOrigen DESC`), no una suma independiente.
- Ya existe `vw_MovimientosCuenta_Saldo` en SQL Server con columnas `Fecha, Documento, Nro Documento, Deuda, Credito, SaldoParcial, Origen, IdOrigen` — es la vista "moderna" que reemplaza el cálculo manual.

**Acción sobre la spec**: verificar en implementación que el `repository.py` de `004-cuentas-corrientes` ordene explícitamente por las 3 columnas, no solo por fecha (el diseño actual ya lo asume correctamente, pero no estaba confirmado contra el comportamiento real hasta ahora).

### 1.2 Mapeo completo del campo `Origen` (ya incorporado a `004-cuentas-corrientes` el 2026-09-16)

12 valores reales confirmados contra `INFORMATION_SCHEMA`/datos: `Compras`, `Banco Nacion`, `Galicia`, `Pagos efectivo`, `Cobros Valores Recibidos`, `Pagos Valores Recibidos`, `Alquileres`, `Impuestos`, `Remuneraciones`, `Ret. IVA Granos`, `Ret. Ventas Hacienda`, `Retenciones`. Ya se agregó el estado `"fuera_de_alcance"` para los 6 últimos. Este documento no repite ese trabajo — ya está en `specs/004-cuentas-corrientes/data-model.md`.

### 1.3 Ciclo de vida de "Valores Recibidos" (cheques de terceros) — `003-tesoreria`

Confirmado (campos `Fecha Emision`, `Fecha Endoso`, `Fecha Cobro`, `IdEmisor`, `IdReceptor`): el flujo real es **Emisión → Endoso (opcional, a un tercero) → Cobro**, con emisor y receptor como contactos distintos. Ya incorporado parcialmente en `data-model.md` de `003-tesoreria`; falta modelar el estado "endosado" explícitamente si se quiere representar el ciclo completo (hoy solo se distingue cobrado/no cobrado).

---

## 2. Hallazgos de alto impacto — no contemplados en ninguna spec

### 2.1 Compras en dólares con dos criterios de tipo de cambio

- `Compras` tiene campos `Tipo de Cambio` y `Ajusta Tipo Cambio` (booleano).
- Vista SQL ya existente: `vw_CnsU_ComprasDolares` (y variantes `vw_CnsComprasDolarBNA`/`vw_CnsComprasDolarTC`).
- Regla real (query `Cns_ComprasBaseImputacion` en Access): `TotalUSD_TCFactura` = convertido al tipo de cambio de la propia factura; `TotalUSD_BNA` = convertido al dólar BNA (`Dolar BNA.Comp_billete`) de la fecha de compra, **solo si** `Ajusta Tipo Cambio = False` en la cabecera de la compra (`IIf([Ajusta Tipo Cambio], 0, ...)`).
- **Gap**: `specs/002-compras` no modela moneda, tipo de cambio, ni el flag `Ajusta Tipo Cambio`. Si hay compras reales en USD, el módulo actual las mostraría con el total en pesos únicamente, sin la doble conversión que el negocio espera ver.

### 2.2 Remitos como control de entrega vs. facturación

- Tablas: `Remitos`, `Remitos_Detalles`, `Remitos_Facturas` (puente remito↔factura).
- Formulario `Remitos` con subformulario `SbfrmRemitosDet`: punto de entrada físico de insumos, antes/además de la factura de compra.
- **Matching remito↔factura es 100% dinámico** (`basRemitosFacturas.CalcConsumoRemito`, algoritmo greedy en 2 pasadas):
  1. Pasada 1: busca líneas de `Det_Compras` de las facturas ya vinculadas al remito (`Remitos_Facturas`) con el **mismo `IdFormulado`**, consume cantidad disponible.
  2. Pasada 2 (fallback): si queda cantidad sin cubrir, busca por **palabras clave** (tokens de 3+ caracteres de Marca+Tipo del producto) en la descripción de líneas de factura, incluso con `IdFormulado` distinto.
  - No existe una tabla que registre el vínculo línea a línea — se recalcula en runtime cada vez.
  - Estado resultante por línea: "Sin remitos" / "Completamente remitida" / "Parcialmente remitida" (`Cns_ComprasConRemitos_Saldo`).
- **Gap**: `specs/002-compras` no menciona remitos en absoluto. Si el negocio necesita ver "¿esta compra ya fue remitida?", falta por completo.

### 2.3 Cargos de cabecera de una compra

El total de una compra (`Frm Compras`) no es solo líneas + IVA: `= Subtotal Neto + IVA + Ingresos Brutos + Conceptos no gravados + Guias + Comisión + Financiación + Gastos...` (varios campos a nivel de cabecera, no de línea). `specs/002-compras/data-model.md` modela `conceptosNoGravados`/`ingresosBrutos` pero no `Guias`/`Comision`/`Financiacion`/`Gastos`.

### 2.4 5 tarjetas de crédito corporativas con datos 100% locales en Access

`Resumenes AgroNacion` (+`_Det`), `Resumenes Corporativa Nacion` (+`_Det`), `Resumenes Mastercard BNA` (+`_Det`), `Resumenes TGR` (+`_Det`), `Resumenes Visa Galicia` (+`_Det`) — miles de consumos reales, **sin confirmar si están migrados** a las tablas `Tarjetas`/`Tarjetas_Resumenes`/`Tarjetas_Resumenes_Lineas` que usa `specs/003-tesoreria`. Hay evidencia de que al menos "Visa Galicia" fue migrada al modelo unificado (`basCompararEstructuraVisa` compara estructuras), pero no está confirmado para las otras 4.

**Acción recomendada antes de especificar**: correr un `SELECT COUNT(*)` en SQL Server sobre `Tarjetas_Resumenes` filtrando por cada una de las 5 tarjetas, y comparar contra el conteo de filas locales en Access, para saber cuáles ya migraron.

### 2.5 Reglas de conciliación/distribución de tarjetas

- `Tarjetas_TipoLinea.Distribuible` (booleano): determina si una línea de gasto de tarjeta se puede prorratear entre contactos/documentos (`Tarjetas_Lineas_Distrib`). Si el tipo de línea no es distribuible, el subformulario de distribución queda deshabilitado (no oculto).
- Validación real (`sfTarjetasDistrib.Form_BeforeInsert`): no se puede crear una fila de distribución si la línea padre no tiene `IdTipoLinea` asignado.
- Consultas de control ya existentes en Access (`CnsCtrl_Tarjetas_ErroresCierreResumen`, `CnsCtrl_Tarjetas_ErroresDistribucionCompras`): comparan total declarado del resumen vs. suma de líneas, e importe de línea vs. suma de su distribución, con tolerancia `Round(...,2)`.
- **Gap**: `specs/003-tesoreria` modela tarjeta/resumen/línea pero no la capa de distribución ni el flag `Distribuible`.

### 2.6 Impuesto de sellos condicional por banco (tarjetas)

`Frm Resumenes TarjCredito`: el cálculo de impuesto de sellos depende del banco emisor, hardcodeado (`IIf([IdTarjetaBanco]=372, ...)`). Es una regla de negocio real pero frágil (hardcodeo de un ID específico) — señalar como deuda técnica a resolver conscientemente al migrar, no replicar el hardcode sin más.

---

## 3. Módulo completo fuera de las 3 specs: costeo/resultado por cultivo

No es un anexo de compras — es un **ERP de producción agrícola separado**, con vistas SQL ya construidas:

- `vw_ResultadoCultivo_Campaña`, `vw_ResultadosCultivo_CostosAgrupados/Base/Deducciones/Seguros/Ventas`, `vw_InsumosOrden`, `vw_LotesPorOrden`, `vw_ProductosConStock`, `vw_TotSuperficiePorCultivoCampania`, `vw_DistribDetalle_Edit`.
- Formularios: `FrmOrdenTrabajo` (aplicación de insumos a lotes por orden de trabajo), `FrmAsignarInsumoACultivos` (distribución de insumo comprado entre cultivos/lotes por dosis/ha), `FrmKardexInsumo` (kardex de stock con saldo corrido), `FrmCostos`/`FrmResultados` (costeo y rentabilidad por cultivo-campaña: margen bruto, MB/ha, rentabilidad, renta anual), `FrmCultivosSegurosCobros` (cobros de seguros agrícolas por siniestro).
- Lógica no obvia relevada en detalle (ver sección 4) — reparto proporcional iterativo, kardex por distribución de OT, matching remito-factura, redondeo de dosis a envase.

**No se está recomendando abordar este módulo ahora** — se documenta para que la decisión de incluirlo como "módulo 5" (o no) sea consciente, no un descubrimiento tardío.

---

## 4. Detalle de lógica no obvia del módulo de insumos/costeo (para cuando se aborde)

Relevante solo si en el futuro se especifica el módulo de cultivos/insumos. Resumen ejecutivo, sin repetir el detalle línea por línea (disponible en el scratchpad original si hace falta):

1. **No hay FIFO real de costeo**: el kardex (`basKardexTmp`) calcula saldo de *cantidad* (ingresos por remito − egresos por `Ordenes_Detalles_Distrib`), en orden cronológico, pero no asigna costo por lote de ingreso. Si se necesita costeo FIFO real, es lógica a diseñar de cero.
2. **Imputación de Órdenes de Trabajo** (`basImputacionOT.AutoImputarServicio_Linea_Proporcional`): reparto proporcional **iterativo con saturación** (tipo water-filling, hasta 10 rondas) del importe de una línea de compra de servicio entre las OT candidatas del mismo contratista/labor, según saldo pendiente de cada OT — no es un prorrateo simple de una pasada.
3. **Varios stored procedures viven directo en SQL Server**, no en VBA: `sp_Lotes_AfterToggle` (borra en cascada la distribución de un lote al destildarlo), `sp_Distrib_Proporcional_PorDetalle` (distribución proporcional entre lotes con redondeo), `sp_Orden_AgregarInsumo`. Hay que extraerlos de SQL Server directamente si se aborda este módulo.
4. **"Total Aplicado" y el stock mostrado en UI son campos derivados**, recalculados por suma de `Ordenes_Detalles_Distrib.CantidadAsignada` — no son fuente de verdad materializada de forma confiable.
5. **Redondeo de dosis a envase** (`basRedondeoInsumos.SugerirCantidad`): tolerancia de ajuste ±10%, aviso a partir de 5%, preferencia configurable de redondeo hacia arriba — parámetros por línea de orden (`EnvasePreferido`, `PasoMinimo`), no globales.
6. **Imputación automática de Centro de Costos en compras** (`basMapeoCentroCostos`): autocompleta por keyword desde `Map_Keyword_CentroCostos`; si no hay match, pregunta al usuario, crea el mapeo, y **actualiza retroactivamente compras históricas** con esa keyword sin centro de costos. Contradice el supuesto de "imputación 100% manual" de `002-compras` — relevante incluso sin tocar el módulo de cultivos, porque afecta directamente el dato que `002-compras` consume.
7. **Clasificación automática de conceptos de compra a rubro**: diccionario `Tmp_Descr_Rubro*` (~5000 entradas) + módulos `basClasifCompras`/`basClasifPreview`. Mismo punto que el anterior: la imputación de rubro tampoco es puramente manual hoy.

---

## 5. Notas operativas para la migración (transversales)

- **`IdContacto` en movimientos bancarios se normalizó a `0`, no `NULL`**, para "sin contacto" al migrar Access→SQL (`basMigracionBancosSQL`). Decidir si el sistema nuevo mantiene ese criterio o lo cambia a `NULL` explícito — impacta a `003-tesoreria` y `004-cuentas-corrientes`.
- **Normalización de nombres de columna durante la migración**: ej. `[Leyendas Adicionales1]` (con espacio, en Access) → `LeyendasAdicionales1` (sin espacio, en SQL Server). Señal de que puede haber más columnas con nombres "limpiados" al migrar — no asumir que el nombre en Access es igual al de SQL Server sin verificar.
- **Convención de nombres de backups locales**: sufijos `_LOCAL_OLD` (backup post-migración de una tabla) y `zz_..._LOCAL_BACKUP`/`zz_...` (auditoría o backup manual). Útil para reconocer qué tablas son historial, no dato vivo.
- **La entidad "Pago" es genérica y reutilizada** en 5+ módulos (compras, ventas, remuneraciones, impuestos, alquileres, tarjetas) vía el subformulario "Pagos"/"Valores propios". Si en el futuro se habilita escritura, conviene modelarla como entidad polimórfica única, no una por módulo.
- **Decimales con coma regional**: las migraciones VBA reemplazaban `,` por `.` al pasar valores a SQL Server (`SqlNumero`) — posible fuente de bugs de formato si se reimportan datos desde Excel/Access sin la misma normalización (relevante para la carga de resúmenes Excel de `003-tesoreria`).
- Ya se hizo un trabajo previo de auditoría de objetos vivos/muertos en Access, guardado en tablas `zz_AuditoriaObjetos`/`zz_ConsultasARevisar`/`zz_BusquedaForms` dentro de `AdmLaHerenciaVer3.accdb` — son datos (no código), consultables directamente si hace falta saber qué objetos ya fueron clasificados como obsoletos.

---

## 6. Resumen priorizado — qué specs tocar y cómo

| # | Hallazgo | Spec afectada | Tipo de cambio |
|---|---|---|---|
| 1 | Compras en USD (2 tipos de cambio, flag `Ajusta Tipo Cambio`) | `002-compras` | Ampliar spec existente |
| 2 | Remitos (control de entrega vs. facturación) | `002-compras` | Ampliar spec existente |
| 3 | Cargos de cabecera (Guías/Comisión/Financiación/Gastos) | `002-compras` | Ampliar spec existente |
| 4 | Imputación automática/retroactiva de rubro y centro de costos | `002-compras` | Ampliar spec existente (afecta la premisa de "imputación manual") |
| 5 | 5 tarjetas corporativas — confirmar migración a SQL | `003-tesoreria` | Verificar dato real antes de especificar |
| 6 | Flag `Distribuible` + distribución de gastos de tarjeta | `003-tesoreria` | Ampliar spec existente |
| 7 | Estado "endosado" en Valores Recibidos | `003-tesoreria` | Ampliar spec existente (menor) |
| 8 | Orden `Fecha, Origen, IdOrigen` en saldo | `004-cuentas-corrientes` | Verificar en implementación (spec ya correcta) |
| 9 | Módulo de costeo/resultado por cultivo | Ninguna | Spec nueva (módulo 5), si es prioridad del usuario |
| 10 | Entidad "Pago" genérica | Ninguna todavía | Consideración de diseño para cuando se habilite escritura |

Este documento queda como input de referencia para las próximas rondas de `/speckit-specify`/`/speckit-clarify` sobre `002-compras` y `003-tesoreria`, y para decidir si se abre `005-costeo-cultivos` (o el nombre que se defina) como módulo nuevo.
