# Research: Aplicación de pagos y cobros

## 1. Importe total de un documento

**Decision**: 
- Compras: reusar `dbo.vw_Cns_Total_Compra.GranTotal` (vista ya existente, confirmado por su definición real en `WC`: `TotalDetalleCompra + IB + conceptos no gravados + guías/comisión/financiación/gastos varios con IVA + ley de sellos + res. 4169/96`) — es el mismo total que ya usa `vw_MovimientosCuenta_Base` para el saldo de proveedores.
- Venta Hacienda: reusar `ventas_hacienda.repository.calcular_totales(lineas, cabecera)["importeTotal"]` — ya es la fórmula confirmada contra el formulario Access real (ver docstring de esa función), y ya se reutiliza en `flujo_caja/atribucion.py` para el matching exacto actual.
- Venta Granos: columna `[Importe Neto a percibir]` de `dbo.[Venta Granos]`, ya calculada en el dato de origen.

**Rationale**: ninguna fórmula se reinventa. Constitución VII: no duplicar cálculos que ya existen y están validados contra el sistema real.

## 2. ¿Vista SQL nueva para Ventas, o cálculo en Python?

**Decision**: cálculo en Python (`aplicaciones_pago/documentos.py`), reusando las mismas funciones que ya usa `flujo_caja/atribucion.py` (`get_venta_cabecera`, `get_lineas_venta`, `calcular_totales`) — no se crea una vista SQL nueva tipo `vw_MovimientosCuenta_Base` para Ventas.

**Rationale**: la fórmula de Venta Hacienda (comisión, IVA, retenciones) ya vive en Python y reimplementarla en SQL duplicaría lógica que se puede desincronizar. El volumen real es chico (~12 ventas hacienda/año, confirmado en relevamientos previos de 018) — no hay necesidad de una vista optimizada para consultas masivas.

**Alternatives considered**: vista SQL espejo de `vw_MovimientosCuenta_Base` para Ventas — rechazada por duplicar la fórmula de `calcular_totales` en dos lenguajes distintos, con riesgo real de que diverjan (ej. si se corrige la fórmula en un lado y no en el otro).

## 3. Sugerencia FIFO

**Decision**: dado un movimiento con contacto e importe, se listan los documentos pendientes de ese contacto ordenados por fecha ascendente (el más viejo primero), y se les va asignando importe hasta cubrir el total del movimiento — la última factura de la sugerencia puede quedar con aplicación parcial si el importe no alcanza para cubrirla entera. Todo editable por el usuario antes de confirmar (FR-003/FR-004).

**Rationale**: confirmado por el dueño (respuesta a la pregunta 2 del `financial-direction-specialist`).

## 4. Tolerancia de redondeo

**Decision**: **$1 (un peso)** como valor de partida para considerar "cubierto" un documento cuyo saldo pendiente es menor o igual a esa tolerancia, y para el mismo margen al validar que un documento/movimiento no quede sobre-aplicado.

**Rationale**: el dueño pidió "usos y costumbres" sin dar un número exacto (Assumptions de spec.md). $1 es conservador (no esconde diferencias reales de varios pesos) y cubre el caso típico de redondeo de centavos por tipo de cambio ya observado en otras partes de este mismo diseño (ej. la validación de saldo de la migración BNA, que cerró exacto al centavo). Queda como constante nombrada (`TOLERANCIA_REDONDEO_APLICACION`), fácil de ajustar si en la práctica resulta muy chica o muy grande.

## 5. Validación de contacto cruzado

**Decision**: si el contacto del movimiento bancario difiere del contacto del documento aplicado, la aplicación se permite igual (confirmado por el dueño, pregunta 4) — se guarda tal cual, y se puede mostrar como información en la pantalla de detalle (no es un requisito bloqueante de esta fase, ver FR-006).

**Rationale**: caso real conocido (consignatarios que centralizan cobros/pagos de varios contactos) — bloquear esto rompería un flujo de trabajo real del dueño.

## 6. Catálogo de orígenes de movimiento aplicables

**Decision**: reusar el mismo catálogo `MEDIOS`/`MEDIOS_CONFIG` de `tesoreria/repository.py` (bna, galicia, efectivo, valores-propios, valores-recibidos, tarjetas) como `OrigenMovimiento` — no se inventa un catálogo paralelo.

**Rationale**: consistencia con lo que ya existe; cualquier medio de pago real del sistema debe poder aplicarse, no solo BNA/Galicia.

## 7. Relación con `flujo_caja/atribucion.py`

**Decision**: se extiende `atribuir_egreso`/`atribuir_ingreso` para que, ANTES de intentar el matching exacto actual, consulten si el movimiento tiene aplicaciones vigentes en `AplicacionesPago`; si las tiene, el Rubro/Centro de Costos sale de ahí (ponderado por `ImporteAplicado` si se repartió entre documentos de distinto rubro). El matching exacto queda como fallback solo para movimientos sin aplicación — y la respuesta debe distinguir tres casos (FR-010): aplicado / posterior al corte sin aplicar / histórico sin aplicar (antes de 2015-09-01), en vez de una única etiqueta genérica.

**Rationale**: pedido explícito del dueño y ya confirmado por el `financial-direction-specialist` en el turno de diseño previo.
