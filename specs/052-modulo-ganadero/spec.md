# Feature Specification: Módulo Ganadero (gestión y control de la hacienda)

**Feature Branch**: `052-modulo-ganadero` (se trabaja en main; push autorizado)
**Created**: 2026-11-25
**Status**: Lista para plan; método de costos revisado por 04/05/07/10 (25/11/2026)
**Input**: Sergio (24/11/2026): "armar el módulo ganadero que nos permita gerenciar y controlar la parte ganadera del negocio … acoplarlo a lo que ya está armado". Antecedentes: [propuesta-especialistas-20261124.md](propuesta-especialistas-20261124.md), con la propuesta de los agentes 05/06/07, las respuestas de Sergio y la historia encontrada en carpetas y mails.

## Clarifications

### Session 2026-11-24/25 (respuestas de Sergio)
- **Actividad:** hay hacienda propia. Se hace cría, recría e invernada según la situación económica y el forraje disponible. Se venden vientres (vaquillonas con garantía de preñez). La compra de hacienda es posible pero no habitual.
- **Venta por kg vivo o por cabeza:** depende de la categoría y del destino. En [Det_Ventas Hacienda] la `Unidad de medida` ya lo distingue; no hay columnas invertidas.
- **Ejercicio ganadero = ejercicio contable** (cierre 31/03, abril–marzo).
- **Valuación del stock:** a precio de mercado.
- **Forrajes:** los verdeos se consumen dentro de la campaña; las pasturas se amortizan en 4 años (falta que el Estudio lo confirme para el balance).
- **Seguimiento individual:** no hay. Solo planillas de preñez y de sangrado (con caravanas).
- **Veterinario:** Miguel Basterrechea (contacto 220).
- **Hacienda de terceros:** las 70 vaquillonas de Ganadera San Justo en pastaje (contrato 039). Figuran como "terneras Miguel" en la planilla de vacunas. La sanidad la paga el dueño.
- **Recuento actual:** Sergio no lo tiene a mano. Se arranca con las fuentes existentes (actas de vacunación, planilla de vacunas 10/2026, stock informado al Estudio).

### Discrepancia a resolver
El 039 imputa el pastaje a la campaña ganadera julio–junio, y la planilla histórica de Sergio también usa julio–junio. La nueva decisión es el ejercicio contable abril–marzo. **Propuesta:** el resultado se presenta por ejercicio contable y se puede ver además por campaña julio–junio, para comparar con la historia. Hay que confirmarlo con Sergio.

## Contexto (fuentes reales)
- **Planilla de gestión de Sergio:** `Documents/La Herencia/Ganaderia/Historico Negocio Ganadero (ver 2).xlsx`. Es el modelo de resultado ganadero en US$ desde 2015/16 hasta 2023/24, con los siguientes rubros:
  - ventas por categoría;
  - gastos de comercialización y flete de hacienda;
  - costos directos operativos;
  - sanidad e inseminación: productos veterinarios, inseminación, laboratorio, aranceles, honorarios, vacunas;
  - alimentación: silo, avena, pastura, maíz, maíz diferido, sorgo, alimento;
  - margen bruto, ha ganaderas y MB/ha;
  - capital de reproductores;
  - carga animal, EV y EV/ha.

  Trae además stock por categoría en cada fecha de vacunación, con su precio.
- **Stock oficial:** actas de vacunación de 2012 a 2026 (dos por año); stock al 31/03 que pide el Estudio Criado; planilla `Sanidad/Req Vacunas Oct 26.xlsx` (stock 10/2026).
- **Método de valuación de Sergio** (mail al Estudio del 10/08/2023):
  - vacas, vaquillonas y toritos: kg × precio por kg de Cañuelas o del mercado;
  - terneros y terneras: remates feria de Entre Surcos y Corrales, por rango de peso;
  - toros usados: 500 kg de novillo.
- **Sanidad:**
  - `Plan Sanitario Valorizado 2026.xlsx`: productos, dosis por categoría, plan mensual y proyección del rodeo;
  - listado de vacunas usadas, con serie, número SENASA y vencimiento;
  - planillas de caravanas de sangrado 2024–2026;
  - planillas de preñez y tactos;
  - facturas de Basterrechea: IATF, tacto, ecografía, sangrados, revisión de toros.
- **Historia:**
  - rodeo propio en pastaje en Tapalqué ("San Pedro") de 2019 a 2024, pagado a Duffau Arricau y luego a J. J. Kahn; el RENSPA de Tapalqué quedó en 0 en 03/2025;
  - RENSPA de La Herencia 1088545.
- **Lo que ya existe en el sistema:**
  - Ventas de hacienda (007): 146 ventas desde 2011.
  - Pastaje (039).
  - Compras con centro de costos 2 "Ganadería", con destinos forrajeros (Verdeo, Avena, Pastura, Rye Grass, Maíz diferido, Sorgo).
  - Imputación automática (049/050).
  - Stock de insumos con FIFO (remitos).
  - Órdenes de trabajo por lote y campaña.
  - Resultado de cultivos.
  - Flujo de caja.
  - Avisos de documentos nuevos.

## User Scenarios & Testing *(mandatory)*

### User Story 1: Resultado ganadero por ejercicio (Priority: P1)
Sergio abre *Producción → Ganadería → Resultado* y ve, por ejercicio, el mismo cuadro que su planilla histórica, armado solo con datos del sistema. El cuadro tiene:
- ventas por categoría (precio A + Complemento B);
- comercialización y fletes;
- pastaje cobrado;
- costos directos, sanidad e inseminación, y alimentación;
- diferencia de inventario valuada;
- margen bruto, MB/ha, kg producidos y carga EV/ha.

Lo puede ver en pesos o en US$ (al TC del comprobante) y comparar entre ejercicios.

**Por qué P1:** reemplaza la planilla que Sergio mantiene a mano y usa datos que ya están cargados.

**Prueba independiente:** con los ejercicios 2016/17 a 2023/24, cada rubro debe coincidir con la planilla histórica o explicar la diferencia en una lista, sin ajustes escondidos.

**Escenarios de aceptación:**
1. **Dado** un ejercicio con ventas y compras imputadas a Ganadería, **cuando** se abre el resultado, **entonces** cada rubro muestra su total y se puede abrir hasta el comprobante.
2. **Dado** un ejercicio sin stock inicial o final cargado, **entonces** el cuadro muestra el resultado sin variación de inventario y avisa "falta el stock al cierre".
3. **Dado** que una compra de un cultivo forrajero se imputó a Agricultura y a Ganadería a la vez, **entonces** el control de doble conteo la muestra.

### User Story 2: Stock de hacienda por categoría y sus movimientos (Priority: P1)
Sergio registra el stock por categoría en una fecha: un recuento, un acta de vacunación o el cierre al 31/03. Cada movimiento actualiza la existencia por categoría y por dueño (propia o de terceros en pastaje):
- **Por carga de documento:** las ventas, que ya existen, descuentan solas.
- **Por registro manual:** nacimientos (o señalada y destete), compras, muertes, consumo propio y cambios de categoría.

**Prueba independiente:** con el stock del acta de vacunación de abril/2026 más los movimientos, la existencia teórica de octubre/2026 se compara con la planilla de vacunas 10/2026 y se muestra la diferencia.

**Escenarios de aceptación:**
1. **Dado** un stock inicial y una venta de 20 terneros, **entonces** la existencia de terneros baja en 20 con el vínculo a la venta.
2. **Dado** un recuento que no coincide con la existencia teórica, **entonces** se muestra la diferencia por categoría. Se ajusta con motivo y usuario, nunca en silencio.
3. **Dado** un movimiento que deja una existencia negativa, **entonces** se rechaza o se avisa.
4. Las 70 vaquillonas de San Justo figuran como **hacienda de terceros**: no se valúan ni suman al stock propio, pero cuentan para la carga animal.

### User Story 3: Valuación a mercado al cierre (Priority: P2)
Al cierre del ejercicio (31/03) el sistema propone el valor neto de realización del stock por categoría con la regla de Sergio (FR-008):
- **Peso por categoría:** viene de la configuración.
- **Precio por kg:** de la fuente de mercado, cargado a mano o leído de una fuente pública.
- **Toros:** su equivalente en kg de novillo.

Sergio revisa y confirma. El valor confirmado alimenta la diferencia de inventario del resultado y el informe para el Estudio.

**Escenario:** con los datos del 31/03/2023 (260 vacas × 480 kg × $290, etc.) el sistema reproduce los valores del mail al Estudio.

### User Story 4: Sanidad y calendario (Priority: P2)
Plan sanitario anual por categoría (producto, dosis, mes), tomado del Plan Sanitario Valorizado.

**Cálculo a partir del stock:**
- **Requerimiento de dosis** contra el stock de vacunas y la compra necesaria. Reemplaza la planilla "Req Vacunas".
- **Costo sanitario presupuestado** por ejercicio.

**Registro de aplicaciones:**
- Cada aplicación (fecha, categoría, cabezas, producto, serie, vencimiento) descuenta el stock de insumos de Compras.
- Las aplicaciones a hacienda de terceros no generan costo propio.

**Trabajos del veterinario** (IATF, tacto, ecografía, sangrado, revisión de toros): se cargan con su resultado agregado (preñadas/vacías, positivos) y se vinculan a la factura de Basterrechea.

**Avisos:** vacunas vencidas o por vencer, y vacunación de la campaña oficial (marzo/abril y octubre/noviembre) próxima o atrasada.

### User Story 5: Controles automáticos (Priority: P2)
El sistema corre los controles solo (al cargar y a pedido) y los muestra en la pantalla de controles, con la marca "revisado y aceptado" en los datos.

**Controles de ventas:**
- venta sin cabezas o sin kg;
- kg por cabeza fuera de rango para la categoría;
- consignatario que no cierra en cero;
- Complemento sin precio B.

**Otros controles:**
- **Stock:** existencia teórica contra el último recuento o acta.
- **Pastaje:** lo facturado contra cabezas × días.
- **Sanidad:** dosis compradas contra aplicadas.
- **Imputación:** compra de Ganadería sin imputar, o imputada dos veces.

### User Story 6: Indicadores de cría (Priority: P3)
Desde las planillas de tacto, preñez y destete: % preñez, % destete, kg destetados por vaca y por ha, y reposición. Se carga el resultado agregado por servicio (no por animal).

### Edge Cases
- **Venta por cabeza sin kg:** el kg se estima por el peso típico de la categoría, marcado como estimado.
- **Venta con renglones negativos:** son correcciones de la liquidación; se suman al neto de la venta.
- **Categorías:** hay que mapear las de las actas y planillas (Vaquillonas 2 dientes, Terneras 15 meses, Toritos, Vacas 2º servicio) al catálogo del sistema.
- **Varios campos:** La Herencia y Tapalqué/San Pedro en la historia. El stock y el resultado se pueden separar por establecimiento.
- **Hacienda en pastaje afuera:** hacienda propia en un campo ajeno. Su costo de pastaje es gasto propio.
- **Hacienda de terceros:** pastaje en La Herencia.
- **Cambio de categoría por edad:** ternera → vaquillona → vaca. Se registra en fechas de manejo (destete, servicio), no automáticamente por calendario.

## Requirements *(mandatory)*

> Revisado el 25/11/2026 por los agentes 01/03/04 (datos y backend), 02/08/09/12 (pantallas), 05 (producción), 06 (sanidad), 07 y administración de cuentas (finanzas), 10 (forense) y 11 (seguros). Lo verificado contra código o base lo indica cada requisito.

### Functional Requirements

**Navegación y pantallas**
- **FR-001:** Ganadería tiene **menú propio de primer nivel**, como ya prevé el estándar de encabezados de la 051. Rutas:
  - `/ganaderia/resultado`
  - `/ganaderia/stock`, con `recuento` y `valuacion`
  - `/ganaderia/sanidad`, con `aplicar`, `plan` y `trabajos`
  - `/ganaderia/controles`
  - `/ganaderia/configuracion`

  El menú incluye además enlaces a Ventas de hacienda, Pastaje y el flujo de caja filtrado por ganadería. Cada pantalla sigue el estándar de 2 filas de la 051 (PageHeader + Segmentos; TiraIndicadores ≤ 3) y usa los helpers de `lib/format.ts` y `NumberInput`/`MoneyInput`.
- **FR-015:** La pantalla no muestra nada interno.
  - **Estados vacíos:** ejercicio sin stock, sin valuación o sin ha ganaderas muestra "—", nunca una división por cero.
  - **"Próximamente" en la 1.ª entrega:** indicadores de cría y transferencia interna a precio de mercado.
  - **Sin prompts del navegador:** los motivos se piden en un panel lateral.
- **FR-017:** Las cargas de recuento y de aplicación sanitaria funcionan en el celular, para cargar desde el campo. Hay un rol "veterinario" que solo puede cargar en Sanidad.

**Resultado**
- **FR-002:** Resultado por **ejercicio contable abril–marzo**, que es la vista por defecto. Tiene una vista alternativa "campaña julio–junio" para comparar con la planilla histórica; esa vista va rotulada "sin variación de inventario", porque el stock valuado solo existe al 31/03.
  - **Moneda:** $ o US$.
  - **Ventas:** se abren en A (contable), B (Complemento) y total. El informe para el Estudio usa solo A.
  - **Detalle:** cada celda se abre hasta los comprobantes.
  - **Reparto por fecha:** el ejercicio abril–marzo no coincide con las campañas, así que los costos se reparten por fecha de consumo de la orden o, si no la hay, por fecha de la factura.
- **FR-003:** **Fuente de costos = la imputación vigente de 050, fracción por fracción** (`VIGENTE_050`, `resultado_cultivo/costos.py`). Se reusa, no se copia. Cuentan como Ganadería:
  - las fracciones marcadas como ganadería, o imputadas a un cultivo forrajero;
  - los tamices con destino Ganadería;
  - los renglones con centro de costos Ganadería que quedan fuera del alcance de 050, con las mismas exclusiones que usa el resultado de cultivos.

  Reglas del cálculo:
  - **Nunca se usa el centro o el destino de Det_Compras como fuente**, porque daría doble conteo. Verificado: hay 317 renglones con centro Ganadería imputados a cultivos agrícolas y 59 con centro y destino contradictorios.
  - Se toma el neto sin IVA, sin la parte particular (`factor_particular`), y los renglones en US$ al TC del comprobante.
  - **La compra de hacienda no es costo:** entra al stock y se resta en los kg producidos.
  - Los rubros de la planilla se mapean a rubro, destino o cultivo de compra con una tabla de configuración.
- **FR-004:** **Hoy el Resultado de cultivos SÍ suma los forrajes** como costo agrícola (verificado: 2023/24 maíz diferido US$ 9.221 y sorgo US$ 12.391). Con este módulo:
  - **Cultivos ganaderos** (Sergio, 25/11/2026): **Sorgo, Maíz diferido, Avena y Pastura**, más Rye grass y Verdeos. **Dejan de figurar** en el Resultado de cultivos y pasan a Ganadería.
  - **Maíz picado para silo:** las ha de maíz que se pican como forraje (Datos Cosecha, superficie ensilada) son ganaderas.
    - **Cálculo:** es el que ya existe (`resultado_cultivo/resultado.py` `_costo_silo`, Sergio 20/11/2026): implantación por ha × ha picadas + confección de silo. Hoy ese monto se resta del maíz.
    - **Destino:** pasa a sumarse en Ganadería → Alimentación, rubro "Maíz silo", por el mismo importe. El resto del maíz sigue siendo agrícola.
    - **Lote:** el lote picado cuenta como ganadero en las ha efectivas desde el picado. Se marcan en `Map_CultivoResultado` con una columna nueva.
  - **Prueba obligatoria:** el costo agrícola baja exactamente lo que sube el ganadero.
  - Los verdeos, el maíz diferido y el sorgo van al ejercicio de consumo.
  - La implantación de pastura se amortiza en 4 años (parámetro), por lote, como en la solapa "Amort Pasturas" de la planilla. Es un rubro propio.
- **FR-005:** Grano o silo propio consumido por la hacienda (los kg con destino Silo de Datos Cosecha):
  - **Etapa 1:** se valúa a costo de producción. Lo que se descuenta del cultivo entra igual a Ganadería.
  - **Etapa posterior:** transferencia interna a precio de mercado, con eliminación en el consolidado.
  - **Decidido por Sergio (25/11/2026): a costo de producción**, porque ese forraje no se puede comercializar fácilmente. La transferencia a precio de mercado queda descartada para el forraje.
- **FR-012:** Indicadores:
  - **Kg producidos** = vendidos + stock final − stock inicial − comprados.
  - **EV:** promedio de los recuentos del ejercicio × coeficiente, como la planilla. Coeficientes iniciales: vaca 1; toro 1,3; torito, novillo y novillito 0,7; ternero/a 0,6; vaquillona 0,8.
  - **EV/ha, MB/ha y rentabilidad:** la rentabilidad es MB / capital en reproductores.
  - **% preñez y destete:** cuando haya datos de servicio.
  - **Por establecimiento:** La Herencia y San Pedro (Tapalqué) por separado.
- **FR-013:** **Ha ganaderas efectivas**, con el método de Sergio (Superficie Campo.xlsx, solapas "Sup Ganadera 2011/2012"): cada lote del campo cuenta por los **meses del ejercicio en que está en uso ganadero**, sobre 12. Σ superficie × meses ganaderos / 12. Respuesta de Sergio del 25/11/2026: los lotes ganaderos están en el plano y en el plan.
  - **Fuentes:** el **Plan agrícola del sistema** (`PlanAgricola`: lote, cultivo y campaña, que ya incluye Avena, Pastura, Maíz diferido y Sorgo) y las órdenes de trabajo.
  - **Lote con cultivo agrícola:** queda fuera desde la siembra hasta la cosecha (fechas de la orden de siembra y de Datos Cosecha; si faltan, el calendario típico del cultivo, configurable). El resto del año (rastrojo) es ganadero.
  - **Lote con forraje, pastura perenne (vida de 4 años desde la implantación), campo natural o bajo sin plan:** ganadero los 12 meses.
  - **Superficie:** la de `Lotes`, que coincide con el plano.
  - Así se reemplaza el "415 − agrícolas" que la planilla histórica cargaba a mano.
- **FR-016:** **Un solo dólar para todos los centros de costos** (Sergio, 25/11/2026: "unificar el valor del dólar para dolarizar homogéneamente todos los costos").
  - **Regla, la que ya usa el Resultado de cultivos** (`resultado_cultivo/costos.py`, `_USD_SQL`):
    - comprobante en US$ → su propio TC;
    - comprobante en pesos → BNA comprador divisa (`[Dolar BNA].Comp_Divisa`) de la fecha del comprobante;
    - comprobante con "Ajusta TC" → 0 US$, porque es ajuste de cambio.
  - **Alcance:** la misma regla vale para Agricultura, Ganadería y Administración, y para ventas, consumos y transferencias internas. Se centraliza en una función o vista común del backend que usan todos los módulos de resultado; no se copia la fórmula en cada uno.
  - **Planilla histórica:** usaba el dólar billete promedio del día. La comparación SC-001 se hace con la regla unificada, y la diferencia por TC se muestra aparte, sin cambiar la regla para que coincida.

**Stock y valuación**
- **FR-006:** Existencia por eventos, en cabezas y kg (con marca "kg estimado"), por **categoría, dueño (Propia / De terceros con su nombre) y campo**.
  - **Movimientos:** stock inicial, nacimiento, compra, venta, muerte, consumo, cambio de categoría (también masivo al destete o al servicio), entrada y salida de pastaje, ajuste por recuento con motivo.
  - **Ventas:** generan su movimiento solas al guardarse.
  - **Muerte:** lleva causa (natural o enfermedad, accidente, rayo, intoxicación, falta de agua o infraestructura, abigeato, desconocida) en dos campos, "registrada" y "diagnóstico veterinario". También quién la constató, la evidencia y una marca de siniestro (denunciado, indemnizado o rechazado, con importe).
  - **Muerte de hacienda de terceros por causa no natural:** avisa de posible responsabilidad según el contrato.
  - **Categorías propias del módulo**, con vínculo opcional a `[Tipo Hacienda]`, que no se modifica. Se agregan toritos, novillitos, vaquillonas 1-2 y 2 dientes, terneras 15 meses, vacas 2.º servicio, y una tabla de alias para los nombres de las actas y planillas.
- **FR-007:** Stock histórico importado con un script re-corrible, con fuente y revisión antes de aplicar:
  - solapa "Stock Hacienda": 23 recuentos de 2016 a 2023, La Herencia y San Pedro;
  - stocks al 31/03 informados al Estudio;
  - actas de vacunación;
  - planilla de vacunas 10/2026.

  Las fechas de recuento no son fechas de cierre: el stock a cada corte se calcula con los movimientos, y si faltan movimientos queda "estimado".
- **FR-008:** **Valuación al cierre = valor neto de realización** (RT 22 / NUA): kg × precio de la fuente − % de gastos de venta.
  - **Fuentes de precio:** Cañuelas por kg para vacas, vaquillonas y toritos; remates feria ESyC para terneros; toro usado = 500 kg de novillo.
  - **% de gastos de venta:** **se calcula de las ventas reales del ejercicio** (Sergio, 25/11/2026). Son comisión, garantía, gastos administrativos, derecho de piso, visaciones, sellos, SENASA y flete sobre el importe bruto, por categoría si hay datos y, si no, total.
  - **Apertura de la diferencia de inventario:** resultado **por producción** (kg producidos × precio de cierre) y **por tenencia** (cambio de precio sobre el stock inicial).
  - **Confirmación:** Sergio confirma la valuación y queda bloqueada. Si cambian las cabezas, se avisa para reconfirmar.
  - **Moneda:** se guarda en pesos al 31/03; en US$, al BNA del 31/03.
- **FR-009:** Venta de hacienda con cabezas y kg siempre.
  - **Regla general por `Unidad de medida`:**
    - **Kilos:** Cantidad son kg y Peso Total son cabezas.
    - **Unidades/Cabezas:** Cantidad son cabezas y Peso Total son kg.
    - **Pesos:** es un gasto o ajuste, sin cabezas.
  - **Faltantes:** se completan con el peso típico, marcados como estimados y con lista para revisar.
  - **Pares anulación/refactura** (ej. 00002-00005483 / 5484): se tratan como un solo par.

**Sanidad**
- **FR-010:** Sanidad:
  - **Plan por categoría y mes:** viene del Plan Sanitario Valorizado y lo valida el veterinario; el sistema no recomienda tratamientos. Las fechas de campaña oficial son un parámetro por año, cargado del acta, no fijo.
  - **Aplicación:** fecha + campo + categorías con cabezas + producto + **serie/frasco con vencimiento y nro. SENASA**. Descuenta dosis del stock de insumos **generando una baja de stock con centro Ganadería**: es el mecanismo FIFO existente, no hay uno paralelo.
  - **Producto vencido:** bloquea, salvo que se dé un motivo.
  - **Carencia:** período de retiro por producto. Avisa al vender una categoría en retiro.
  - **Hacienda de terceros:** **no consume stock propio.** Queda una nota "vacunado por el dueño" y el estado sanitario al ingreso. Si se usó una dosis propia, es un recupero a facturar.
  - **Trabajos veterinarios** (IATF, tacto, ecografía, sangrado, revisión de toros): se cargan con su resultado agregado y la factura vinculada, eligiéndola de una lista tildable de facturas de Basterrechea.
  - **Animales observados:** lista por caravana/CUIG (no es ficha): positivos de sangrado y de paratuberculosis, con motivo, fecha, resultado y destino.
  - **Brucelosis:** se controla por cohorte de terneras de la campaña.
  - **Requerimiento de dosis de la próxima campaña** = stock × plan − dosis vigentes en stock. El presupuesto sanitario completo queda para después.
  - **Actas de vacunación:** se cargan como respaldo, con cabezas por categoría.

**Controles**
- **FR-011:** Los controles corren solos (por evento y periódicos) y con un botón. Las excepciones se guardan con la marca "revisado y aceptado" (componente común extraído de ControlCierre). Controles:
  - **Ventas:**
    - sin cabezas o sin kg;
    - kg por cabeza fuera de rango;
    - renglones idénticos en un mismo documento, solo como **aviso a verificar con el PDF de la liquidación** (fuente de verdad). Ej. 0003-00010318: son 2 vacas distintas de 440 kg, no hay duplicado;
    - negativos sin su documento par.
  - **Consignatario:** saldo distinto de 0 a 30 días de la venta; venta sin cobro; Complemento sin cobro en caja.
  - **Stock:**
    - existencia negativa;
    - teórica vs último recuento o acta;
    - cabezas vacunadas en la campaña vs stock (±%);
    - mortandad mensual sobre el umbral;
    - muerte de terceros sin causa.
  - **Pastaje:**
    - facturado vs cabezas × días (promedio con 3 decimales);
    - meses sin liquidar;
    - antigüedad del saldo.
  - **Sanidad:**
    - dosis compradas vs aplicadas + stock;
    - frasco abierto sin cierre;
    - producto vencido;
    - vacunas por vencer.
  - **Imputación:**
    - suma de las fracciones = renglón;
    - suma de los centros = total de compras;
    - centro y destino contradictorios;
    - compra de Ganadería sin imputar.
  - **Seguros:** fuera del MVP (Sergio no contrata seguros ganaderos, 25/11/2026).

**Revisión de método de costos (25/11/2026: administrador agropecuario 04, agrónomo 05, financiero 07, contable 10)**
- **FR-020: Estructura del resultado** (estándar CREA/INTA/Márgenes Agropecuarios):
  - **Ingreso neto** = ventas netas de comercialización − compras de hacienda ± diferencia de inventario. Se muestra en la **etapa 1**, con una valuación simple a mercado (cabezas × kg típico × precio de cierre), rotulada "estimada" hasta que Sergio la confirme en la etapa 2.
  - **Margen bruto** = ingreso neto + pastaje − costos directos (sanidad, inseminación, alimentación y forrajes, personal atribuible).
  - **Estructura (administración, honorarios, movilidad, impuestos, mantenimiento de mejoras):** **va debajo, sin repartir**. La etapa 1 la muestra total junto con el resultado operativo consolidado; el reparto por ha efectivas o por % del MB queda para después. En la planilla estos rubros estaban dentro de los directos: el mapa de rubros los reclasifica, y una columna "como planilla" mantiene la comparación de SC-001.
  - **Margen de caja:** en la vista por campaña (sin inventario) el margen se llama "margen de caja", no margen bruto.
- **FR-012 (corregida):**
  - **Kg producidos** = vendidos + consumo propio + stock final − stock inicial − comprados ± traspasos. Las muertes no suman.
  - **Costo directo por kg producido y por ha.** Los kg y EV de la hacienda de terceros (pastaje) **no entran** en los kg producidos propios; sí en la carga EV/ha. Los coeficientes EV son simplificados por categoría y van rotulados así.
- **FR-004 (agregados):**
  - **Período de consumo:** cada cultivo forrajero tiene un desfase campaña → ejercicio de consumo, en `GanForrajeRegla`. Ej.: Avena 2026 → ejercicio abr-26/mar-27; Maíz diferido 2025/26 → abr-26/mar-27.
  - **Pastura:**
    - empieza a amortizar en el primer pastoreo (mientras se implanta es sementera en proceso);
    - vida útil por lote, 4 años por defecto;
    - **baja anticipada:** si aparece un cultivo agrícola en el lote dentro de la vida útil, la cuota pendiente se carga en ese ejercicio como "baja de pastura", y el lote deja de contar como pastura en las ha efectivas.
  - **Cosecha de un cultivo ganadero** (Sergio, 25/11/2026: "puede haberse cosechado para destinarlo a forraje de la hacienda"):
    - **Costo:** sorgo, maíz diferido, avena y pastura **siempre son ganaderos**, aunque tengan cosecha. Su costo queda entero en Ganadería.
    - **Cosecha:** se mira su destino (`Datos Cosecha.IdDestino`).
    - **Destino propio** (silo, consumo de la hacienda, semilla para resiembra ganadera): entra como reserva o forraje, sin ingreso.
    - **Si se vende** (liquidación de granos o semilla vendida): esa venta es un **ingreso de Ganadería** ("venta de forraje o grano"). No pasa el cultivo a Agricultura.
    - **Sin aviso de "doble propósito":** el único control es "cosecha de un cultivo ganadero sin destino registrado".
  - **Rastrojos:** costo 0; solo cuentan los meses (FR-013).
- **FR-005 (corregida):** el forraje, silo o grano propio consumido va **a costo de producción**, sin margen en el centro que lo produce (se elimina la "etapa posterior a mercado"). El grano seco que se podía vender muestra al costado, solo como información, el "MB a precio de mercado", sin asiento.
- **FR-008 (agregado):** el resultado por tenencia se calcula **en US$** (stock inicial kg × Δ precio US$/kg), para no confundir devaluación con tenencia. El informe para el Estudio va en pesos.
- **FR-021: Reservas forrajeras como inventario, en la etapa 1** (Sergio, 25/11/2026: "el silo puede guardarse más de un año").
  - **Confección:** cada confección de silo (o rollo) crea una **reserva** con kg (o t), fecha, lote y costo. El costo es el de `_costo_silo`: implantación/ha × ha picadas + confección.
  - **Consumo:** se registra por fecha y kg (carga simple, con el panel lateral). Su costo pasa al ejercicio del consumo, a costo promedio de la reserva.
  - **Saldo al 31/03:** es inventario a costo; no es costo del ejercicio.
  - **Si no hay consumo registrado:** no se inventa un consumo. La reserva queda en stock y el control "reserva sin consumo registrado" avisa.
  - **Maíz diferido:** se consume en general en el período siguiente; se maneja con el desfase de FR-004, no como reserva.
  - **Verdeos en pie al 31/03:** sementera en proceso a costo. Se resuelve con el desfase de FR-004.
- **FR-022: Personal permanente:** el sueldo y las cargas del encargado del campo (Sierra, único permanente del campo) se reparten **70% Ganadería (directo), 20% Estructura, 10% Agricultura** (Sergio, 25/11/2026). El % es configurable por ejercicio. Irma no es personal del campo.
- **FR-023: Conciliación resultado ↔ flujo (etapa 2):** resultado + partidas sin caja (variación de stock, amortización, forraje propio) ± Δ de créditos y deudas = flujo neto ganadero.
- **Después (fuera de la etapa 1):**
  - amortización de toros y mejoras ganaderas;
  - interés al capital hacienda y renta de la tierra (parámetros), para llegar al **resultado económico**;
  - rentabilidad = resultado operativo / activo total;
  - apertura por actividad (cría / recría / invernada) con transferencia del ternero a mercado, solo para la hacienda;
  - EV por peso.

**Finanzas**
- **FR-014:** El flujo de fondos ganadero es una vista filtrada del flujo de caja. Se agrega el filtro de centro de costos a `/por-rubro` y a la exportación. Los cobros salen de los vencimientos y del cobro real, no de la fecha de la factura. Hay que declararle al usuario que el reparto de pagos por centro es aproximado, porque se hace por proximidad de facturas.
- **FR-018:** **Pastaje a cobrar:** la liquidación confirmada genera el crédito en la cuenta corriente del cliente, con su vencimiento. Solo se usan los comprobantes y cobros propios: no se baja nada de San Justo.
- **FR-019:** **Seguros:** registro de pólizas ganaderas (aseguradora, cobertura, suma por cabeza, franquicia, vigencia). La prima es costo ganadero; la indemnización es un ingreso vinculado a la muerte. Hoy no hay ninguna póliza ganadera (verificado en WC); solo un seguro de transporte del fletero en 2018.

### Key Entities (prefijo `Gan`, verificado que no choca con tablas ajenas)
- **GanCategoria** (EV, peso típico, sexo, orden y categoría siguiente, FK opcional a `[Tipo Hacienda]`) y **GanCategoriaAlias**.
- **GanMovimiento:** tipo, categoría, cabezas, kg, kg estimado, dueño, establecimiento (`Establecimientos`: 1 La Herencia, 2 San Pedro). FK a renglón de venta, contrato de pastaje o compra. Lleva fuente, motivo, usuario y anulado.
- **GanRecuento / GanRecuentoDetalle:** el origen es recuento, acta o cierre.
- **GanValuacionCierre**.
- **GanRubroMapa** (rubro de la planilla → rubro, destino o cultivo) y **GanForrajeRegla** (consumo o amortización, años).
- **GanPlanSanitario**, **GanAplicacionSanitaria** (FK a `Stock_Bajas`), **GanTrabajoVeterinario** (FK a la compra), **GanObservado**.
- **GanPoliza**.
- **GanControlAceptado** (como ControlRemitosAceptados).
- Vista **vw_Gan_Costos** (FR-003).
- Backend en `backend/src/features/ganaderia/`. El movimiento de venta se crea desde `ventas_hacienda/repository.py`.

## Success Criteria *(mandatory)*
- **SC-001a:** Ventas, sanidad e inseminación, gastos generales y comercialización de 2016/17 a 2023/24 (vista julio–junio) reproducen la planilla en pesos, y en US$ salvo la diferencia de TC, que se muestra aparte (la planilla usaba dólar billete y el sistema usa la regla unificada de FR-016). El forense verificó 2018/19 y 2022/23.
  - Las diferencias de 2022/23 (productos veterinarios, aranceles, flete, pastaje) se listan con su comprobante.
- **SC-001b:** Los forrajes se concilian contra las solapas "Cultivos y forrajes" y "Amort Pasturas", que son valores cargados a mano. Las diferencias quedan en una lista, sin ajustar nada.
  - En la solapa principal las filas Avena, Pastura, Maíz y Maíz silo parecen tener el nombre corrido (detectado por el forense). **Se resuelve sin preguntar** (Sergio, 25/11/2026): se compara por valor contra las solapas fuente ("Cultivos y forrajes", "Amort Pasturas"), no por el rótulo de la fila.
- **SC-002:** Sergio deja de mantener a mano la planilla de resultado y la de requerimiento de vacunas.
- **SC-003:** La existencia teórica de 10/2026 coincide con la planilla de vacunas 10/2026, o la diferencia se explica por categoría.
- **SC-004:** El stock valuado al 31/03 para el Estudio sale del sistema, con fuente de precios y solo lo contable.
- **SC-005:** Pasar los forrajes a Ganadería no cambia el costo total (agricultura + ganadería + administración), y los saldos de las cuentas no cambian.
- **SC-006:** Los consignatarios cierran en $0 al cierre, o tienen excepción aprobada.
- **SC-007:** El pastaje facturado es igual al calculado, al centavo, en cada período.
- **SC-008:** La suma de los centros de costos es igual al total de compras del ejercicio.

## Respuestas de Sergio a las preguntas abiertas (25/11/2026)
1. Ha ganaderas → salen del plano y del plan (ver FR-013).
2. Grano o silo propio consumido → a costo de producción (FR-005).
3. % de gastos de venta → se calcula de las ventas reales del ejercicio (FR-008).
4. Filas con nombre corrido → se resuelve comparando por valor (SC-001b).
5. Seguros ganaderos (RC, mortandad, abigeato) → **no**. FR-019 queda solo como registro, si algún día hay una póliza; los controles de seguros salen del MVP.
6. Venta 0003-00010318 → verificada con el PDF de la liquidación (Dropbox/Ventas/04 2022 - 03 2023/20220909_JYMDeLaSerna 002.pdf): 2 vacas de 440 kg a $220, remate 491, Frigolar, faena. Es correcta, no se toca. RENSPA La Herencia 01.013.0.00531/01.

## Assumptions
- Las 70 "terneras Miguel" son la hacienda de San Justo (respuesta de Sergio del 25/11/2026). No se baja información de San Justo; solo se usa el contrato de pastaje ya cargado.
- Las cifras de la planilla histórica están en US$; el criterio de conversión hay que inferirlo de la planilla y confirmarlo.
- No hay ficha por animal en el MVP. La caravana solo aparece en sangrados y tactos, como adjunto o lista.
- No hay conexión con SIGSA/SENASA sin autorización explícita (regla de oro de cuentas externas).
- No hay póliza ganadera vigente (verificado en WC); ver FR-019.
