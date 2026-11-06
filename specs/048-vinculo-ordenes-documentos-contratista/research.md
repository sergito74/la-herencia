# Research: 048 vínculo órdenes ↔ documentos del contratista

Hallazgos verificados en WC el 06/11/2026.

## R1. Qué es un "documento de labor"

- **Decision**: es un documento de un contacto con órdenes de trabajo que tiene al menos un renglón de los rubros Fumigación, Siembra, Cosecha, Fertilización, Disqueado o Embolsado Grano.
- **Rationale**: Yanquelen también vende hacienda, semilla y urea y factura trabajos de la maquinaria de Giamigli. Con este filtro quedan 91 facturas de labor; sin él, el primer listado incluyó "Vacas preñadas".
- **Alternatives**: filtrar por unidad "hectáreas" (falla: hay renglones sin unidad o con "HAS"/"HECTAREA" mezclados) o por texto del concepto (frágil).

## R2. Regla de propuesta

- **Decision**: para cada factura de labor, proponer las órdenes ejecutadas del mismo contratista con fecha mayor que la de la factura de labor anterior del mismo contratista y menor o igual que la de la factura, dentro de un máximo de 90 días, que no estén ya vinculadas a otra factura. Se rotula la diferencia de hectáreas: "coincide" (<1%), "cerca" (<10%), "no coincide", "otra unidad" o "sin orden".
- **Rationale**: en la simulación del 06/11, 39 de 94 facturas coincidieron dentro del 10%. La regla solo ordena y rotula: nada se confirma solo (D1).
- **Alternatives**: emparejar por importe (no hay importe en la orden) o por número de orden en el comprobante (los contratistas no lo informan).

## R3. Propuestas: calcular al vuelo y guardar solo decisiones

- **Decision**: las propuestas no se guardan. Se guardan los vínculos confirmados (`OrdenesContratistaFacturas`, ampliada con usuario y fecha) y los descartes (`OrdenesContratistaDescartes`). Un descarte se invalida solo si cambian las órdenes candidatas (se guarda su conjunto).
- **Rationale**: menos estado y sin propuestas viejas desincronizadas (Constitución VII).

## R4. Reparto e imputación

- **Decision**: confirmar = guardar el vínculo + `motor.evaluar_contratista(idCompra)` + `guardar_corrida` + `aprobar_corrida` con el usuario, todo en el mismo pedido. Desvincular = nueva corrida (sin órdenes → se retira; si quedan otras órdenes, se recalcula y aprueba).
- **Neto a repartir**: suma de los renglones cuyo rubro no es insumo ni otro negocio (excluidos: Semillas, Fertilizantes, Agroquímicos, Hacienda, Trabajos Maq. Propia, Gastos Comercializacion). En dólares, al TC del comprobante. La última fracción absorbe el redondeo para cerrar al centavo.
- **NC/ND**: si tienen documento relacionado (`CompraDocumentosRelacionados`) con una factura vinculada, se imputan con la misma proporción y su signo. Hoy las 6 NC de contratistas no tienen relación: aparecen en la revisión con la acción "Relacionar con factura" (se agrega a `CompraDocumentosRelacionados`). Una NC/ND nunca se vincula directo a una orden (FR-005).
- **Rationale**: el motor 017 ya reparte por superficie, maneja las órdenes sin cultivo (centro de costo) y guarda trazabilidad. La confirmación del usuario equivale a la aprobación de 017.

## R5. Resultado por cultivo sin doble conteo

- **Decision**: `costos_heredados` excluye, de las compras con corrida de contratista aprobada vigente, todos los renglones repartidos (labor más flete, viáticos y gasoil: todo lo que no está en los rubros fuera del reparto). `costos_contratista` pasa a sumar las fracciones aprobadas vigentes de `ImputacionPropuestas` (Origen = 'Contratista') del cultivo y campaña. Solo los renglones de los rubros fuera del reparto (insumos, otros negocios) siguen por la vista heredada. Así el conjunto excluido es exactamente el repartido (análisis 06/11, F1).
- **Rationale**: FR-006 y FR-007. Los documentos no vinculados siguen igual que hoy.
- **Old table**: `Ordenes_Trabajo_Contratista_Factura` (0 filas) deja de leerse en `costos.py` y `resultado.py`; se elimina en una tarea posterior, con backup.

## R6. Facturas nuevas sin orden (FR-008b)

- **Decision**: la fecha de puesta en marcha se guarda en una constante con la fecha del deploy. Una factura de labor posterior, sin vínculo ni descarte, cuenta como pendiente: aparece en la revisión del contratista y en el listado de revisión de la rutina 043 ("Factura de contratista sin orden de trabajo"). No bloquea la carga de la compra.
- **Rationale**: bloquear la carga impediría registrar la deuda (no romper saldos); el aviso cumple "no puede quedar sin orden".

## R7. Permisos

- **Decision**: los endpoints de escritura quedan bajo el middleware de autenticación existente (016), que rechaza a los usuarios de solo lectura; en la UI, los botones van dentro de `<SoloLectura>`.
