# Módulo Ganadero: propuesta unificada de los especialistas (24/11/2026)

Esta propuesta junta lo que diseñaron los agentes 06 (sanidad y manejo), 05 (producción) y 07 (dirección financiera). Los tres relevaron WC en modo solo lectura y no se escribió nada.

## Qué existe hoy
- **Ventas de hacienda:** 146 ventas (01/2011 a 07/2026) y 248 renglones, con consignatario, Complemento (B), guías y retenciones. Hay 9 categorías en `[Tipo Hacienda]`.
- **Pastaje (039):** 1 contrato (INMAG) y 3 liquidaciones en 2026, por $3,18M neto.
- **Compras con centro de costos 2 "Ganadería":** entre $3,1M (2022) y $19,4M (2024) por año. Los rubros principales son siembra de verdeos, inseminación, silo, vacunas, disqueado, veterinario y flete.
- **Destinos forrajeros ya en el centro 2:** Verdeo, Avena, Pastura, Rye Grass, Maíz diferido y Sorgo.
- **Agricultura:** 39 lotes que suman 630 ha (el lote hace de potrero). Avena, Pastura y Maíz diferido ya aparecen en órdenes. Hay 57 labores de maquinaria propia sobre avena y pastura.
- **Lo que no existe:** existencias de hacienda, movimientos (nacimientos, compras, muertes), DTe, pesadas, sanidad y reproducción.

## Alarma de datos (sin verificar contra comprobantes)
En las ventas, `Cantidad` parece guardar kg y `Peso Total` cabezas. Las cabezas por año no son confiables y hay una cantidad negativa en 2024. Antes de calcular kg producidos hay que sanearlo con una regla general, cruzándolo con las liquidaciones.

## Diseño
1. **Rodeos y categorías:** el rodeo tiene dueño (Giamigli o tercero de pastaje). El catálogo de categorías se mapea a `[Tipo Hacienda]`. El estado reproductivo va como atributo, no como categoría.
2. **Existencias por eventos**, a partir de un stock inicial a una fecha de corte:
   - suman: nacimientos, compras y entradas por pastaje;
   - restan: ventas, muertes y consumo;
   - ajustan: cambios de categoría.
   - Se llevan en cabezas, y en kg cuando hay pesada. Se cuadran contra recuentos físicos o la vacunación SENASA.
3. **Movimientos con DTe**, vinculados a la venta, a la liquidación del consignatario y a la factura.
4. **Sanidad:** calendario oficial (aftosa, brucelosis) y propio (clostridiales, reproductivas, antiparasitarios, revisión de toros). Cada tratamiento registra producto, lote, dosis y carencia. El producto sale del mismo stock FIFO de insumos que viene de Compras.
5. **Pesadas y mortandad:** la mortandad registra la causa y si hubo diagnóstico veterinario.
6. **Integración con agricultura, sin contar dos veces:**
   - cada renglón de compra se imputa a un solo centro;
   - los verdeos y el maíz diferido se imputan a Ganadería por su destino;
   - la pastura se amortiza en su vida útil;
   - el grano o silo propio consumido es una **transferencia interna** a precio de oportunidad, que se genera sola desde las órdenes y los recuentos;
   - el Resultado de cultivos excluye el centro 2.
7. **Resultado ganadero por ejercicio:** ventas (A + Complemento) + pastaje − costos directos − transferencias recibidas ± diferencia de inventario valuado.
   - Se muestra por actividad, por cabeza, por kg producido (vendidos + stock final − stock inicial − comprados) y por ha ganadera.
   - Indicadores: kg/ha, EV/ha, eficiencia de stock y, si hay cría, preñez y destete.
8. **Flujo de fondos ganadero:** vista filtrada dentro del flujo de caja existente. Presupuesto vs real, después.

## Controles (automáticos, por evento y con botón)
- **Existencia teórica vs recuento.** Se marca toda existencia negativa.
- **Ventas, DTe y consignatarios:** cabezas de la venta = cabezas del DTe = cabezas liquidadas. El consignatario tiene que cerrar en cero. Se marcan los kg/cab fuera de rango.
- **Pastaje:** lo facturado contra cabezas × días del período. Se marcan los meses sin liquidación.
- **Sanidad:** venta con un tratamiento en carencia (bloquea, pero se puede pasar con motivo); vacunas vencidas o próximas; dosis compradas vs aplicadas; mortandad sobre el umbral.

## Etapas
- **MVP 1 (con datos que ya existen):**
  - saneamiento de cabezas/kg en ventas;
  - tablero de resultado ganadero (ventas + pastaje − centro 2, con ratios por kg y por ha);
  - control de ventas, consignatario y cobro;
  - control de pastaje;
  - flujo ganadero.
- **MVP 2:** rodeos, stock inicial, existencias por eventos, DTe, sanidad con salida de stock y carencia, mortandad y pesadas.
- **Después:** transferencias internas de granos, valuación de stock y margen por actividad; reproducción e índices; ficha por animal (caravana o RFID); presupuesto vs real; SIGSA (solo lectura y con autorización).

## Preguntas para Sergio (unificadas)
Ver la respuesta en el chat del 24/11/2026.

## Respuestas de Sergio (24/11/2026) y verificaciones
1. Hay hacienda propia: cría, recría e invernada según la economía y el forraje disponible. Se venden vientres (19 vaquillonas con garantía de preñez).
2. Hay un recuento de hacienda, pero Sergio todavía no lo tiene a mano (queda pendiente).
3. Se vende por kg vivo o por cabeza según la categoría y el destino. **Verificado en WC: las columnas NO están invertidas** (la alarma de los agentes era falsa). Con `Unidad de medida` = Kilos, `Cantidad` son kg y `Peso Total` cabezas. Con Unidades/Cabezas, `Cantidad` son cabezas y `Peso Total` kg (cuando hay dato). Vacas y vaquillonas preñadas van siempre por cabeza. Los negativos son correcciones. Normalizar: "toros" y "Cabezas" pasan a Unidades.
4. El ejercicio ganadero coincide con el contable.
5. El stock de hacienda se valúa a precio de mercado (en la RT 22 es valor razonable menos gastos de venta; la NUA RT 54 la reemplaza).
6. Los verdeos se agotan dentro de la campaña. Las pasturas se amortizan en 4 años; falta verificarlo con el Estudio, porque la norma no fija la vida útil.
7. El veterinario es Miguel Basterrechea (contacto 220), con facturas desde 2015 hasta hoy: IATF, tactos y ecografías, sangrados (brucelosis, paratuberculosis), revisión de toros, selección de vaquillonas de compra. Algunos honorarios se cobran en kg de carne.
8. Los 70 animales en pastaje son vaquillonas de **Ganadera San Justo** (contrato 1, desde 25/09/2026). INMAG es solo el índice de precio. La sanidad la paga el dueño, ya lo dice la cláusula del contrato. Las compras de hacienda existen, pero son raras.
