# Feature Specification: Remitos y control de stock de insumos

**Feature Branch**: `010-remitos`
**Created**: 2026-09-23
**Status**: Implementado (backend + frontend); revisado por los agentes especialistas (SQL, financiero, producción agrícola) y con las correcciones de esa revisión aplicadas.

**Input**: Módulo Remitos del sistema Access real (`Remitos` + `SbfrmRemitosDet`), migrado a la web app sobre `WC`, ampliado con el control completo de ingreso y egreso de insumos al stock: vínculo remito↔factura de Compras (por documento y renglón por renglón), unidades de medida normalizadas y bajas de stock sin orden de trabajo. Base para el próximo módulo (Órdenes de Trabajo) y para la imputación automática del costo de los insumos a Centro de Costos, Cultivo y Campaña.

## Clarifications

### Session 2026-09-23 (20 preguntas, con los agentes especialistas: SQL Server, gestión agro, producción agrícola, dirección financiera, UX del ERP, arquitectura de producto y administración)

- Un remito cumple dos funciones: entrada de mercadería (suma stock) y respaldo para controlar la factura del proveedor. Se migran las dos.
- Se carga **desde el remito**. Puede haber una factura en el sistema sin remito vinculado y un remito sin factura: depende de cómo el proveedor maneje facturación y entrega. Ninguno de los dos es un error.
- Un remito puede tener **varias facturas y una factura varios remitos** (N a N).
- **Requisito fundamental**: el vínculo **renglón por renglón** remito↔factura es obligatorio de soportar, porque sobre él se desarrollará la automatización del destino de las compras de insumos (Centro de Costos, Cultivo y Campaña). Las 736 conciliaciones existentes se conservan; el estado por remito es completo / parcial / con diferencia.
- El número de factura escrito a mano se reemplaza por el vínculo real a Compras (el texto queda derivado).
- Entran **todos los insumos**: agroquímicos, fertilizantes y semillas (el catálogo `vw_CnsU_Producto_link` ya los unifica: 9.516 productos).
- **Unidades**: lista cerrada, limpia y unificada, con equivalencias; la unidad la fija el producto.
- **Vencimiento opcional** (no siempre se dispone del dato). Sin lote.
- El remito **no lleva precio**: el costo sale de la factura vinculada.
- El remito **suma stock al guardarse** (sin estado borrador).
- Edición libre mientras no haya consumo ni factura; después solo anulación con motivo (sin borrado físico) y sin bajar la cantidad por debajo de lo ya consumido.
- Ajuste manual de inventario con motivo; se avisa antes de permitir stock negativo.
- Remito duplicado (mismo proveedor y número): se avisa y se pide confirmación, sin bloquear; se valida el formato `0000-00000000`. Los 11 duplicados históricos se conservan y se marcan para revisión.
- Se migra todo tal cual (215 remitos, 467 renglones, vínculos existentes); se descartan las tablas vacías de un intento anterior.
- Archivo del remito (foto o PDF): opcional, con el mismo campo de arrastrar y soltar del resumen de tarjeta.
- Listado por proveedor y fecha, con filtros por producto y estado, atajo "remitos sin factura" y exportación a Excel.
- **Nuevo (pedido explícito)**: opción para **dar de baja del stock** productos que salen sin haber sido usados en una orden de trabajo (deterioro, vencimiento, uso interno, etc.). No se vinculan a ningún cultivo ni campaña y **son un gasto para la empresa**.

### Session 2026-09-23 (respuestas a las preguntas abiertas)

- **Valorización por FIFO** (primero entra, primero sale). Es un requisito fundamental del sistema.
- **Gasto de las bajas**: se imputa a **Pérdidas y bajas de insumos** o a **Mantenimiento**, según el destino que se le dio al insumo.
- **Automatización del destino** (imputación a Cultivo y Campaña): se desarrolla con el módulo de Órdenes de Trabajo; este módulo deja la base.
- El **vínculo por renglón es la fuente de verdad**; el de documento se completa a partir de él.
- **Unidad base por producto**: se propone según el uso histórico y el usuario la revisa.
- **Ajuste de inventario**: incluye faltantes y sobrantes (en general no hay ingreso de insumos sin remito).
- **Reglas de edición aprobadas**: vincular una factura nunca traba la edición; se congelan producto, unidad y cantidad (y fecha y proveedor del remito) de los renglones ya consumidos o vinculados; observaciones, archivo y N° de remito siguen editables; la cantidad de un renglón consumido puede subir pero no bajar de lo consumido; para corregir lo demás se anula el remito con motivo.

## Hallazgos de datos reales (WC, 2026-09-23)

- 215 remitos (2011-2026, 22 proveedores), 467 renglones (prom. 2,2, máx. 14). Unidades: LTS 320, KGS 128, PACKS 13, Bolsa 5, KG 1. Vencimiento en 117 de 467.
- Los 219 productos remitidos ya están en el catálogo unificado (Herbicida 102, Semilla 37, Insecticida 27, Coadyuvante 20, Fungicida 18, Fertilizante 15); no hay códigos repetidos entre los tres registros.
- **Vínculo por documento** (`Remitos_Facturas`): 199 filas, 192 remitos; 23 remitos sin factura; 7 remitos con varias facturas; 14 facturas con varios remitos.
- **Vínculo por renglón** (`tblRemitoCompra`): 736 filas sobre 213 de los 467 renglones (46%) y 118 remitos. En el 100% el producto del renglón de compra coincide con el del renglón de remito. 149 renglones de remito se reparten en varios renglones de compra y 76 renglones de compra en varios de remito. En 20 renglones lo vinculado difiere de lo remitido. Su columna `IdDeuda` vale 0 (la factura se obtiene por `Det_Compras.IdCompra`).
- **Los dos vínculos no están sincronizados**: los vínculos por renglón implican 303 pares remito–factura y solo 67 figuran en `Remitos_Facturas`.
- Stock actual (`vw_ExistenciaProductos`) = entradas por remitos − consumos de órdenes de trabajo (`Ordenes_Detalles.Total Aplicado`); 39 productos con existencia. No existe ninguna salida de stock fuera de las órdenes.
- Las compras ya traen `IdFormulado` por renglón (1.908 de 15.379) y cada renglón de compra lleva Centro de Costos, Destino, Rubro y Campaña; la distribución de una orden por lote/cultivo/campaña vive en `Ordenes_Detalles_Distrib`.

## Implementación y hallazgos (2026-09-23)

- **«SIN REMITO» es un número válido y repetible**: 43 de los 215 remitos se cargaron así (el proveedor entregó sin remito y se cargó igual para dar entrada al stock). Los duplicados verdaderos son 4 grupos con 12 remitos (no 57): se marcan «a revisar».
- **Vínculos**: la migración completó 236 vínculos por documento desde los de renglón (`Remitos_Facturas` pasó de 199 a 435 filas). Quedan 19 remitos sin factura.
- **Costo de un renglón** (`costeo.py`): en el 92% de los vínculos la cantidad de la factura coincide con la remitida (la columna «Unidad» de la factura casi siempre está vacía); entonces el costo es el precio unitario neto de la factura (× tipo de cambio de la factura si es en dólares); si no coincide se prorratea el subtotal. Renglón con varias facturas: promedio ponderado.
- **FIFO** (`stock_fifo.py`): sobre cantidades acumuladas, igual que la vista heredada. La cantidad calculada coincide exactamente con `vw_ExistenciaProductos` (40 productos, 0 diferencias). No se guarda ninguna asignación: se recalcula siempre desde los datos, así el costo provisorio se corrige solo al vincular la factura (no hace falta la tabla `Stock_Consumos_Capa` prevista).
- **Valor del stock a costo FIFO**: $ 642.860,15 en 40 productos; 33 con parte del stock sin costo (remitos recientes sin factura).
- **Producto asignado en Compras**: solo el 12% de los renglones de compra tiene `IdFormulado`. Al vincular un renglón sin producto se le asigna el del remito (queda como base para la imputación automática); el panel de vinculación sugiere por producto asignado o por coincidencia del nombre.
- **Fechas**: el driver devuelve las columnas `date` como texto y las `datetime` como fecha; se normalizan antes de ordenar.

## Revisión de especialistas y correcciones (2026-09-22)

Tres revisiones read-only sobre datos reales de WC (SQL Server, dirección financiera, producción agrícola). Aplicado:

- **Notas de crédito y débito vinculadas a un renglón** (financiera): 92 renglones tenían factura y NC/ND vinculadas a la vez, mezcladas en un solo promedio de costo (las NC siempre con precio negativo, las ND casi siempre positivo). Se corrigió `costeo.py`: cuenta separada por moneda — una NC/ND en **pesos** solo corrige el promedio de los vínculos en **pesos** de ese renglón; una en **dólares** solo corrige el promedio en **dólares** (con su propio tipo de cambio). Nunca se mezclan entre monedas; el costo final del renglón combina las cuentas por moneda ya convertidas a pesos, ponderadas por cantidad.
- **Toneladas de fertilizantes**: se agregó la unidad `TN` con conversión física universal fija a `KGS` (1 TN = 1000 KGS, no requiere equivalencia por producto) en `stock_datos.py`; el stock de fertilizantes queda siempre expresado en kilos aunque el remito venga en toneladas.
- **Integridad y concurrencia** (SQL): `Remitos_Detalles` y `tblRemitoCompra` no tenían PK ni índice único, lo que permitía duplicar un vínculo renglón↔factura si dos altas llegaban a la vez. Se agregó PK sobre ambas identity, índice único `(IdDetalleRemito, IdDetalleCompra)` en `tblRemitoCompra` e índices de soporte en las columnas más consultadas (`scripts/indices_remitos.py`, idempotente, sin tocar columnas ni datos heredados).
- **Precisión de cantidades**: `Cantidad` es `real` (float32) en varias tablas heredadas; se redondean las cantidades a 4 decimales al leerlas (`stock_datos._f`) para que las comparaciones de FIFO y de vínculos no queden a merced del error de precisión del tipo original.
- **`Det_Compras.IdFormulado` huérfano al desvincular**: si `vincular_renglones` le había asignado el producto a un renglón de factura que no tenía ninguno, `desvincular_renglon` ahora lo revierte a `NULL` cuando ese era el único vínculo que lo sostenía.
- **Unidad base mal inferida en 4 productos** (3 en LTS, 1 en KGS remitados solo en PACK/BOLSA sin equivalencia cargada): no se fuerza una corrección automática porque no hay dato real de conversión; ya están cubiertos por el flujo existente de confirmación manual (`UnidadesProductos`, badge «Falta equivalencia» en existencias) — se confirman cuando se cargue la equivalencia real del envase.
- **Sin corregir, solo documentado** (dato heredado de Access, se deja intacto): 3 `Remitos_Facturas` huérfanos (`IdDeuda` sin fila en `Compras`), 76 vínculos por renglón con proveedor distinto al del remito, y 3 `Remitos_Detalles` con cantidad negativa. No se tocan porque alterar datos heredados de Access está fuera de alcance de este módulo y podría romper trazabilidad histórica.

## User Scenarios & Testing

### Historia 1 — Cargar y consultar remitos (P1)
Un administrativo carga un remito recibido (fecha, proveedor, N° de remito, renglones con producto, cantidad, unidad y vencimiento opcional, observaciones, establecimiento destino, archivo opcional) y lo consulta luego por proveedor y fecha, con filtros por producto y estado.
1. Guardar suma la cantidad al stock de cada producto.
2. El N° de remito con formato inválido o repetido para el proveedor advierte y pide confirmación.
3. Renglón sin vencimiento se guarda sin problema.
4. Editar: libre mientras el remito no tenga consumo ni factura; después solo observaciones y archivo, o anular con motivo.
5. Anular quita su entrada del stock; no se puede anular ni bajar una cantidad si dejaría el consumo ya realizado sin cobertura.

### Historia 2 — Vincular remitos y facturas, renglón por renglón (P1)
Desde un remito (y también desde una factura) el usuario vincula documentos y, dentro de ellos, renglones: qué renglón de remito cubre qué renglón de factura y con qué cantidad. Puede haber varios en ambos sentidos.
1. Panel de facturas del mismo proveedor, tildable (como en Compras); sugerencia automática de renglones por producto y cantidad.
2. Vincular un renglón crea o mantiene el vínculo por documento correspondiente (una sola fuente de verdad).
3. Estado por remito: **sin vincular / parcial / completo / con diferencia** (cantidad remitida vs facturada, con las diferencias a la vista).
4. Bandejas: "Remitos sin factura" (con antigüedad) y "Facturas de insumos sin remito".
5. De cada renglón vinculado se obtiene el **costo unitario** (precio de la factura, en pesos con el tipo de cambio de la factura), sin que el remito lleve precio.

### Historia 3 — Unidades de medida normalizadas (P1)
Una lista cerrada de unidades (base litros / kilos / unidades) con presentaciones y sus equivalencias (bidón, bolsa, pack). Cada producto tiene una unidad base; el remito puede cargarse en una presentación y el stock se lleva en la unidad base. Se unifica `KG`→`KGS` y se propone la unidad base de cada producto según su uso histórico, para que el usuario la revise.

### Historia 4 — Bajas de stock sin orden de trabajo (P1, pedido explícito)
El usuario registra una salida de stock de productos que no se usaron en una orden: fecha, motivo (deterioro, vencimiento, uso interno, otro con detalle), productos y cantidades, observaciones.
1. Descuenta del stock; avisa si el stock quedaría negativo.
2. **No se vincula a cultivo ni campaña**; se valoriza por **FIFO** al costo de las facturas vinculadas y queda registrada como **gasto de la empresa**.
   Cada baja se imputa a un **Rubro** y un **Centro de Costos** (obligatorios): deterioro, vencimiento u otro motivo → rubro **«Pérdidas y bajas de insumos»** (hoy no existe en el catálogo `Rubros`: se crea, clasificación Gastos); uso interno o mantenimiento → uno de los rubros de **Mantenimiento** existentes (Maquinarias, Instalaciones, Construcciones) y el centro de costos que corresponda (Agricultura, Ganadería, Adm. General, Maquinaria o SIP).
3. Se puede anular con motivo (restituye el stock).
4. Consulta y exportación por período, motivo y producto.

### Historia 5 — Ajustes de inventario (P2)
Ajuste manual con motivo cuando el stock físico no coincide con el del sistema, en ambos sentidos: **faltante** (sale del stock, por FIFO) o **sobrante** (entra al stock como una nueva capa; su costo es el de la última capa conocida del producto o uno ingresado a mano). Nunca deja stock negativo sin aviso explícito.

### Historia 6 — Existencias (P2)
Consulta de existencia por producto (base para las órdenes de trabajo), con detalle de entradas, consumos, bajas y ajustes, y exportación a Excel.

## Requirements

- **FR-001** El stock de un producto = entradas (remitos no anulados) − consumos de órdenes de trabajo − bajas ± ajustes, siempre en la unidad base. Se calcula con consultas propias; las vistas heredadas no se modifican.
- **FR-001a (FIFO)** El stock se lleva por capas: cada renglón de remito (y cada sobrante de ajuste) es una capa con su cantidad y su costo unitario en pesos, ordenadas por fecha del remito y luego por número. Toda salida (consumo de una orden de trabajo, baja o faltante de ajuste) consume primero las capas más antiguas. El costo de una salida es la suma de lo consumido de cada capa a su costo.
- **FR-001b (costo pendiente)** El costo de una capa sale de la factura vinculada al renglón (ponderado por cantidad si hay varias). Si el remito todavía no tiene factura, la capa queda con **costo pendiente**: las salidas que la consumen se muestran como provisorias y se **recalculan solas** cuando se vincula la factura. Nada se valoriza «a cero» en silencio.
- **FR-002** Toda escritura va exclusivamente contra `WC`.
- **FR-003** El remito no tiene precio; el costo unitario de un renglón se deriva de los renglones de factura vinculados (ponderado por cantidad si hay varios).
- **FR-004** Un vínculo por renglón implica el vínculo por documento; ambos se mantienen sincronizados.
- **FR-005** La cantidad vinculada de un renglón de remito no puede superar su cantidad remitida (se advierte), ni la de un renglón de factura su cantidad facturada.
- **FR-006** No hay borrado físico de remitos ni de bajas: solo anulación con motivo.
- **FR-007** Ninguna operación deja el stock negativo sin aviso y confirmación explícitos.
- **FR-008** Unidades: lista cerrada con equivalencias; unidad base por producto.
- **FR-009** Formato numérico y monetario del sistema (miles `.`, decimales `,`, `$` / `us$`).
- **FR-010** Archivo del remito opcional (ruta local, arrastrar y soltar o selector de Windows).
- **FR-011** Exportación a Excel de remitos, existencias y bajas con los filtros aplicados.

## Datos (propuesta)

Tablas nuevas en `WC` (script idempotente, como `Tarjetas_Resumenes_Lineas_Estado`); las tablas heredadas no se alteran:

- `Remitos_Extra` — IdRemito, IdEstablecimiento, Observaciones, Archivo, Anulado, MotivoAnulacion, ConDuplicadoRevisar.
- `Unidades_Medida` — Codigo, Nombre, Magnitud (volumen / masa / unidad), FactorABase; `Producto_Unidad` — IdProducto, UnidadBase.
- `Stock_Bajas` (cabecera: fecha, motivo, detalle, IdRubro, IdCentro, anulada) y `Stock_Bajas_Detalle` (IdProducto, cantidad, importe del gasto por FIFO, marca de costo pendiente).
- `Stock_Consumos_Capa` — asignación FIFO de cada salida a las capas (remito/renglón) de las que salió, para poder recalcular cuando cambia el costo de una capa.
- `Stock_Ajustes` — fecha, IdProducto, cantidad (±), motivo, detalle.
- El vínculo por renglón sigue en `tblRemitoCompra` (IdDetalleRemito, IdDetalleCompra, CantidadRemitida) y el de documento en `Remitos_Facturas`.

## Migración

Se conserva todo: 215 remitos, 467 renglones, 199 vínculos por documento y 736 por renglón. Se agregan los vínculos por documento que faltan a partir de los de renglón (236 pares); `KG`→`KGS`; los 11 duplicados se marcan para revisión; los 23 remitos sin factura quedan como "pendiente de factura"; se ignoran `IdContacto` (redundante), `Remitos_LOCAL_BACKUP` y las tablas vacías `remito`, `remito_item`, `stock_insumo`, `conciliacion_factura_remito`.

## Fuera de alcance de este módulo

- La **imputación automática del costo a Cultivo y Campaña** (requiere las órdenes de trabajo que consumen el stock). Este módulo deja resuelta su base: producto, cantidad, vínculo renglón-factura y costo unitario.
- Órdenes de Trabajo, lotes, contratistas (módulo siguiente).
- Alertas de vencimientos próximos, lote, kardex valorizado FIFO.
- Auditoría de quién/cuándo.
