# Auditoría de aplicaciones de pago — 28/10/2026 (Claude)

**Estado: SOLO DIAGNÓSTICO. No se escribió nada en WC.** El plan de saneamiento de la sección 5 espera la aprobación de Sergio.

- Script (solo lectura, re-corrible): `auditoria_aplicaciones_20261028.py` (correr desde `backend/` con `.venv`, argumento: ruta del JSON de salida).
- Tabla completa por cuenta (391 cuentas): `auditoria-aplicaciones-20261028.csv`.
- Respaldo previo a los cambios de Codex de hoy: `WC_antes-de-saneamiento-cuentas-20261028_20261028_110154_577882.bak`.

## 1. Alcance

Todas las aplicaciones activas (`Anulada = 0`) de `dbo.AplicacionesPago` sobre `CompraDeuda`: 8.136 aplicaciones en 391 cuentas. Para pagos por BNA, Galicia y efectivo se compara la fecha del pago con la fecha del comprobante.

**Fuera del alcance de esta pasada:** aplicaciones sobre ventas (VentaHacienda/VentaGranos, unas 510), y pagos por tarjeta, retenciones y compensaciones (no tienen una fecha de pago directa en la tabla). Queda pendiente revisarlos.

## 2. Hallazgo principal: no es solo la corrida 020, el problema es el FIFO

| Origen | Activas |
|---|---|
| `sistema-conciliacion-020` (automatica-exacta / mejor-esfuerzo) | 643 (de 8.388; el resto ya estaba anulado) |
| `fifo-032` (todas las tandas: 035, 036, saneamientos de hoy) | ~9.000 en total, unas 6.900 sobre compras |
| manual | ~1.300 |

La corrida 020 que quedó activa está concentrada en pocas cuentas: **Cargill 198**, **Ricardo Criado 109**, **Coto 107**, Banco Nación 21, Easy 15, Nidera 14 y Naldo Lombardi 13. El resto son cuentas chicas con 1 a 8 aplicaciones, casi todas de importe exacto 1 a 1, que se ven bien.

**El problema masivo es el FIFO-032.** Cuando a una cuenta le falta una factura o le sobra un pago, el FIFO corre todos los pagos siguientes hacia facturas posteriores. Esto produce un **desfasaje en cascada**: pagos aplicados a facturas emitidas meses o años después, y un pago partido en 2 o 3 facturas cuando había una de importe idéntico en el mismo período.

**Esto le pasa incluso al saneamiento de hoy de Estudio Criado.** El tramo 2026 quedó bien, 1 a 1. Pero la tanda "Saneamiento FIFO 032 Estudio Criado" volvió a hacer FIFO sobre el histórico. Por ejemplo, el pago BNA del 23/07/2012 ($2.711) quedó aplicado a facturas de nov-2012, dic-2012 y ene-2013, y así en cadena hasta 2016. En esa cuenta hay **84 pagos con factura de importe idéntico ignorada ($2,55 M)** y 224 aplicaciones de pagos hechos más de 90 días antes de la factura.

**Impacto:**
- **Saldos totales:** no cambian, porque la suma de la cuenta es la misma.
- **Estado de cada factura (pagada o impaga):** queda mal.
- **Cash Flow:** el detalle de celda toma el rubro, el centro de costo y el comprobante del documento aplicado (`vinculos.cadenas`). Por eso muestra la factura equivocada. En proveedores con varios rubros (Coop. Agropecuaria, Agrovet, Bayá Casal) puede además cambiar el **rubro** del gasto.

### Totales globales

- **314 pagos** con una única factura contemporánea de importe idéntico (±60 días), aplicados a otra(s) factura(s): **$3,29 M** nominales. Se excluyeron los importes que se repiten, como cuotas fijas iguales.
- **1.144 aplicaciones** con el pago más de 90 días anterior a la factura. Puede ser un anticipo legítimo o un arrastre de FIFO.
- Clasificación: **46 rojas, 115 amarillas, 230 verdes.**

## 3. Criterios de semáforo

- **ROJA:** al menos uno de estos casos:
  - un pago con match unívoco ignorado;
  - un documento sobreaplicado (aplicado mayor que el total);
  - aplicaciones de la 020 con desfasaje de más de 180 días;
  - más de 2 aplicaciones con desfasaje de más de un año.
- **AMARILLA:** remanentes de la 020 sin desfasaje, o desfasajes aislados de más de 180 días, o cruces de orden. Hay que mirarlas, pero probablemente estén bien.
- **VERDE:** ninguna señal.

## 4. Cuentas rojas (por gravedad)

| Cuenta | Problema | Magnitud |
|---|---|---|
| 258 Cargill | 198 aplicaciones de la 020, 175 con desfasaje de más de 1 año, 135 de ellas con pagos 2025-26; 4 documentos sobreaplicados | $8,08 M de pagos 2025-26 aplicados a documentos viejos |
| 115 Estudio Criado | FIFO histórico 2012-2025 en cascada | 84 matches ignorados ($2,55 M); 224 anticipos aparentes ($0,87 M) |
| 210 Ricardo Criado | 109 aplicaciones de la 020 todavía activas (Codex anuló 19) | 36 con más de 1 año; 52 anticipos aparentes ($0,73 M) |
| 97 (contacto sin nombre "XXXXXXXXX") | 603 FIFO | 122 matches ignorados; 386 anticipos aparentes. Ver qué cuenta es antes de tocarla |
| 48 Jáuregui y Morales | 539 FIFO (tanda "FIFO Jauregui, auditoría 035") | 50 matches ignorados; 275 anticipos aparentes |
| 226 Bayá Casal | 11 documentos sobreaplicados; un pago 2025-26 de $10 M con desfasaje de más de 180 días | Cerrada el 20/10 con el método bimonetario: confirmar si es efecto del US$ |
| 465 Coto | 107 aplicaciones de la 020 | desfasajes menores |
| 23 Coop. Eléctrica | match ignorado en 2024-25 (pago de $98.460 de ene-2025, entre otros) | $0,20 M |
| 22 Coop. Agropecuaria, 217 FEDEA, 17 ASP, 303 Nidera, 444 Madelan, 273 Carrefour, 442 Gentos, 39 Ferias, 278 Yanquelen, 467 Pérez | documentos sobreaplicados (aplicado mayor que el total) | revisar uno por uno, son pocos |
| 30 EESS Saladillo, 71 Movistar | aplicaciones de $0,01 a $0,04 a facturas de hace un año | residuos de redondeo; limpiar |
| Resto (171 Sancor, 5 Agrovet, 89 Ojuez, 144 EDP, 72 Municipalidad, 16, 76, 43, 37, 449, 92, 233, 9, 112, 41, 108, 118, 213, 236, 382, 387, 42, 176, 263, 61, 282) | 1 a 6 matches ignorados o desfasajes de más de 1 año | bajo monto |

La lista completa, con las amarillas y las verdes, está en el CSV.

## 5. Plan propuesto (NO aplicado)

**REGLA DE ORO (Sergio, 28/10/2026):** las cuentas con resumen o cuenta corriente emitida por el proveedor (Cargill, Bayá Casal, FEDEA, etc.) se imputan exactamente como ese resumen: qué recibo cancela qué comprobante, retenciones y créditos. A esas cuentas no se les aplica ningún algoritmo. **Paso 0 obligatorio:** clasificar cada cuenta roja o amarilla según tenga o no resumen del proveedor (portal, mail, PDF).

**Principio, solo para cuentas SIN resumen del proveedor:** primero el match exacto contemporáneo, después el FIFO solo sobre el remanente, y nunca un FIFO que cruce un hueco documental (factura faltante o pago sin factura). Ese hueco se deja visible como saldo o anticipo pendiente, no se "absorbe" corriendo todo lo posterior.

1. **Nuevo algoritmo de reconciliación por cuenta.** Lo implementaría como parte del recálculo FIFO 032, con modo simulación:
   1. Pasada A: 1 a 1 por importe idéntico (±$0,01) dentro de ±60 días, eligiendo la factura más cercana en fecha.
   2. Pasada B: combinaciones de 2 o 3 facturas del mismo período que sumen el pago exacto.
   3. Pasada C: FIFO del remanente limitado a una ventana (por ejemplo 180 días). Lo que no entra queda como pago a cuenta o factura impaga, a la vista, para revisión.
   4. Resultado: una simulación por cuenta (antes y después, aplicaciones que cambian), para revisarla en pantalla antes de aplicarla, según la regla de revisión de cargas automáticas.
2. **Cargill (258).** Sin FIFO ni automatismos. Se anulan las 198 aplicaciones de la 020 y se reproducen las imputaciones del libro financiero del portal (API por trimestre, autorización de solo lectura del 20/10): recibos, LPG, retenciones y créditos, comprobante por comprobante, en US$ al TC del comprobante. Hay que verificar que el saldo siga cerrando en US$ −60.000,10.
3. **Ricardo Criado (210) y Coto (465).** Anular las aplicaciones remanentes de la 020 y re-aplicar con el algoritmo nuevo. En Ricardo Criado, revisar primero los débitos que eran de socios o DPPJ, igual que en el caso de los 19 que ya anuló Codex.
4. **Estudio Criado (115), Jáuregui y Morales (48), contacto 97 y el resto de las rojas con FIFO.** Re-correr el algoritmo nuevo sobre el histórico completo. En Estudio Criado conservar el tramo 2026 alineado hoy, 1 a 1.
5. **Documentos sobreaplicados (unas 40 facturas).** Lista individual; recortar la aplicación sobrante y dejarla como pago a cuenta.
6. **Residuos de $0,01 a $0,04** (EESS Saladillo, Movistar): anularlos y dejarlos como redondeo.
7. **Amarillas.** Remanentes de la 020 de 1 a 8 aplicaciones sin desfasaje: verlos en bloque y, si son 1 a 1 exactos, re-etiquetarlos como manuales y conservarlos.
8. **Cada tanda:** respaldo verificado antes, control de saldo por cuenta con `refrescar=True` (el saldo total no debe moverse) y registro en este archivo.
9. **Pendiente de alcance:** repetir la auditoría sobre ventas (hacienda y granos) y sobre aplicaciones de tarjeta, retenciones y compensaciones.

### 5bis. Revisión de las ventanas de tiempo (28/10, con el especialista financiero 07) — PROPUESTA VIGENTE

Las ventanas de ±60 y 180 días se **descartan como prohibición**. De las 662 aplicaciones manuales, el 12% está a más de 180 días del comprobante y el 21% son anticipos. Una ventana rompería 1 de cada 8 imputaciones bien hechas. Tampoco hay plazo legal: el CCyC (art. 900 y siguientes) dice que se imputa según lo que indique el recibo o el deudor, y si no indica nada, a la deuda más antigua.

Nuevo orden, solo para cuentas **sin** resumen del proveedor:

1. Referencia explícita (factura citada en el concepto, el recibo o la orden de pago).
2. Importe idéntico; entre varios candidatos se elige el más cercano en fecha, sin límite.
3. Combinación de 2 o 3 facturas que sumen exacto, prefiriendo las más cercanas.
4. FIFO del resto, que **se corta en cada hueco** (falta una factura o sobra un pago) y avisa, en vez de arrastrar el desfasaje.
5. Lo que quede, a la vista como pago a cuenta o factura impaga.

Lo que se aparte del patrón del proveedor, o pase de 180 días, **se imputa igual pero entra al listado de revisión**. La fecha ordena y advierte; no prohíbe.

## 6. Decisiones que necesito de Sergio

1. ¿Aprobás el principio de la sección 5 (exacto, luego combinación, luego FIFO acotado, y los huecos a la vista) como regla general que reemplaza el FIFO-032 puro?
2. ¿La ventana de ±60 días para el match exacto y de 180 días para el FIFO te parece bien?
3. ¿Arranco por Cargill (portal) o por el algoritmo general en simulación?

## 7. Detector de facturas faltantes (28/10, con el especialista 07) — PROPUESTA, sin implementar

- **Datos (desde 2020):**
  - 44 proveedores tienen 12 meses o más con factura; 14 facturan casi todos los meses (80% o más) y suman 31 meses-hueco.
  - Estudio Criado: 4 huecos en 2012-2026. Sancor: 12.
  - Coop. Eléctrica es bimestral: contar por mes daría 93 falsos faltantes.
  - Movistar: contar por mes no detecta el faltante conocido de jun-2025, porque otro comprobante tapa ese mes. Hay que controlar **período facturado**, no mes calendario.
- **Recurrentes:** el ciclo se aprende de la distancia típica entre las últimas 12 a 24 facturas (30, 60 o 90 días, ±25%), con la opción de fijarlo a mano por proveedor. Factura esperada = última fecha + ciclo + margen (15 o 25 días). Monto esperado = el último, ajustado por tendencia; un salto de más de 30% es un aviso de cambio de monto. La señal más fuerte es un pago sin comprobante del período. Si no factura en 3 ciclos, se pregunta una vez si se dio de baja.
- **No recurrentes (señales):**
  - pago sin factura compatible;
  - pago a cuenta o saldo a favor de más de 90 días;
  - retención SICORE sin factura;
  - remito sin facturar a los 60 días;
  - cruce con Mis Comprobantes de ARCA, solo con autorización explícita de Sergio cada vez.
- **Prevención:**
  - aviso al cargar un pago sin factura (anticipo o factura por cargar);
  - tablero "Facturas esperadas este mes" (llegó / pendiente / atrasada);
  - aviso de cierre de mes el día 5, integrado con la rutina 043.
- **Integración con el FIFO que se corta en huecos:** el hueco se muestra como "Falta factura de X mes, aprox. $Y".
  - **Observación de Claude:** NO crear facturas provisorias en `Compras`. Cambiarían saldos, deuda y Cash Flow con un documento inexistente.
  - **Alternativa:** registrar el hueco como marca de pendiente, vinculada al pago, fuera de las tablas contables. El pago queda "a cuenta, falta factura" hasta que se carga la real.

## 8. PREMISA de Sergio (28/10): no romper saldos

**Solo se corrigen imputaciones.** El saldo de cada cuenta conciliada debe quedar igual al centavo antes y después de cada tanda. No se crean facturas provisorias, ajustes, ND/NC ni reasignaciones de contacto como parte de este saneamiento.

## 9. Simulación del detector de faltantes (28/10, solo lectura)

Script: `detector_faltantes_20261028.py`. Facturas desde 2020; proveedores con 12 meses o más facturados y ciclo de 1 a 3 meses.

> **ATENCIÓN:** esta tabla son alarmas automáticas SIN VERIFICAR, no faltantes confirmados. El caso de Estudio Criado resultó falso (ver 9bis), y el detector por mes calendario no es confiable. La verificación válida es el cruce contra los PDFs de la sección 10.

**Alarmas sin verificar** (cobertura de 80% o más; "con pago" = hubo un pago al proveedor en ese período):

| Proveedor | Meses sin factura |
|---|---|
| ~~Estudio Criado~~ | ~~11/2024 y 12/2024~~: FALSO. Las facturas estaban cargadas con fecha errónea; corregido el 28/10 |
| Sancor | 12/2020, 01/2021 y 03/2023, con pago |
| Duffau Arricau | 05/2023, con pago |
| Banco Nación | 07/2026, con pago |
| Banco Galicia | 08/2021 a 04/2022 (6 meses) |
| TCS Comunicaciones | 2020-2022 (9 meses) |
| Telepeaje | 7 meses sueltos sin pago (¿pagados con tarjeta?) |
| Autopistas del Sol | 05 y 06/2020, sin pago (probable pandemia, legítimo) |

**Sin huecos:** Movistar, Coop. Eléctrica (bimestral, bien detectada), Starlink, Fideicomiso La Esperanza, Pérez.

**Ojo con Movistar:** tiene un faltante conocido (jun-2025) que el control por mes no detecta, porque otro comprobante cae en ese mes. Hay que agregar el control por período facturado o por cantidad de comprobantes por año.

**Ruido a filtrar:**
- Cuentas de cobertura baja con compras sueltas: YPF Nordelta, AUSA, Coop. Agropecuaria, Lartirigoyen, Vanina Silva, Angus, SENASA, Bayá Casal (tiene resumen del proveedor) y el contacto 97.
- Proveedores que dejaron de facturar: Fideicomiso Alcalá (2021), Direct TV (2024), La Esperanza Agropecuaria (2024, reemplazada por el Fideicomiso). Se pregunta una vez si se dieron de baja; no se marcan como atrasados.

### 9bis. Verificación de Estudio Criado contra los PDFs (28/10) — el detector dio FALSO POSITIVO

Carpeta: `Dropbox/Giamigli de Bolivar SA/Compras/04 2024 - 03 2025`. Las 12 facturas de abr-2024 a mar-2025 están cargadas en WC; **no falta ninguna**. Lo que hay son **2 fechas mal cargadas**:

- 00003-00000676: el PDF dice 12/11/2024 y WC tiene **12/10/2024**.
- 00003-00000693: el PDF dice 17/01/2025 y WC tiene **07/01/2025**.

En dic-2024 el estudio no emitió factura: la 689, del 07/01/2025, sigue a la de noviembre. El detector por mes calendario interpretó esto como "nov y dic sin factura".

Corregir las fechas no mueve el saldo, pero queda **pendiente de autorización de Sergio**.

**Lección:** ningún hallazgo del detector se presenta como faltante sin antes cruzarlo con la carpeta de comprobantes.

## 10. Cruce completo PDFs de Compras contra WC (28/10, Claude) — APLICADO lo verificado

Script: `cruce_pdf_compras_20261028.py`, re-corrible. Lee los 4.249 PDFs de `Dropbox/Giamigli de Bolivar SA/Compras`, extrae número y fecha de emisión de cada uno y busca el número en `Compras`.

**Criterio para corregir:** número completo igual, mismo emisor, importe coincidente y fecha de emisión explícita en el PDF. Antes de cada tanda, respaldo verificado; después, control de que el saldo de cada cuenta quede igual al centavo (en todas las tandas quedó igual).

### Correcciones aplicadas (solo fecha o número; ningún saldo cambió)

| IdDeuda | Proveedor | Comprobante | Antes | Después |
|---|---|---|---|---|
| 2143514888 | Estudio Criado | 00003-00000676 | 12/10/2024 | 12/11/2024 |
| 2143514942 | Estudio Criado | 00003-00000693 | 07/01/2025 | 17/01/2025 |
| 2143512811 | Movistar | 2467-00201453 | 16/06/2020 | 14/06/2020 |
| 2143514395 | Ceamse | 00113-03471745 | 10/12/2023 | 17/01/2024 |
| 2143514451 | AUBASA | 0050-01048275 | 15/01/2018 | 24/01/2018 |
| 2143513484 | Zurra | 00003-00000094 | 06/01/2022 | 05/01/2022 |
| 2143514968 | El Miralejo | 00002-00000197 | 07/02/2025 | 13/02/2025 |
| 2143515081 | Servicios Turísticos de Rutas | 00009-00089058 | 05/05/2025 | 15/05/2025 |
| 2143511739 | Fideicomiso Alcalá | 0002-00000124 | 04/06/2018 | 01/06/2018 |
| 2143512485 | Estudio Criado | 00003-00000141 | 20/01/2020 | 13/01/2020 |
| 2143512644 | TCS Comunicaciones | 00004-00000393 | 09/03/2020 | 02/03/2020 |
| 2143513035 | Cargill | 5850-00000379 | 31/12/2020 | 30/12/2020 |
| 2143514287 | Estudio Criado | 00003-00000573 | 11/10/2023 | 09/10/2023 |
| 2143514559 | Corredores Viales | 0104-06017336 | 13/06/2024 | 14/06/2024 |
| 2143514759 | Zurra | 00003-00000181 | 12/08/2024 | 02/08/2024 |
| 2143515349 | Estudio Criado | 00003-00000801 | 14/01/2026 | 09/01/2026 |
| 2143515394 | Corredores Viales | 0104-12473258 | 13/02/2026 | 14/02/2026 |
| 2143517416 | Corredores Viales | 0104-13411466 | 28/04/2026 | 29/04/2026 |
| 2143518509 | Banco Nación | 00005-00007811 | 14/08/2026 | 10/08/2026 |
| 2143512209 | Santiago Peveri | nro 00002-00000090 | — | **00002-00000091** (número corregido) |

Respaldos:

- `WC_antes-fechas-criado-676-693_20261028_123025_153146.bak`
- `WC_antes-fechas-compras-cruce-pdf_20261028_123433_692290.bak`
- `WC_antes-fechas-compras-cruce-pdf-2_20261028_124605_759274.bak`
- `WC_antes-nro-peveri-091_20261028_124639_318638.bak`

### Comprobantes en la carpeta que NO están en WC — NO cargados (moverían saldo; decide Sergio)

- Sancor: **NC 00035-00006907 ($1.895,78) y NC 00030-00003040 ($813,44) del 28/07/2026**. Anulan las facturas 00035-00002077 y 00030-00003814, que sí están cargadas, así que la cuenta tiene hoy $2.709,22 de deuda de más.
- Sancor: factura 00038-00229895, 16/10/2026, $47.247,23. Reciente, quizá pendiente de la rutina 043.
- Coop. Agropecuaria: factura 00039-00034238, 21/07/2025.
- Agroveterinaria Central: factura 0003-00012227, 11/09/2025, $39.256,20.
- Bulonera Central: factura 0001-00070062, 16/01/2025.
- Ochoa Erika Agustina (no existe como contacto): factura 00001-00000094, 28/12/2022, $45.000.
- Pablo Car: factura 00005-00000936, 05/08/2021.
- María Alejandra D'Agostino: factura 00002-00001174, 28/08/2019, $3.200. Ojo: el contacto está duplicado (212 y 395).
- Lartirigoyen: NC 0149-00001775 (mar-2023).

**Sin confirmar** (el lector pudo haber tomado otro número del PDF; hay que mirarlos a ojo):

- Lartirigoyen F 0149-00008983 (en WC está la 8984 del mismo día)
- IT Brokers 0002-00247772 (en WC está la 0005-00058564 del mismo día)
- Extragas 0002-00769151 (en WC está la 00002-00773667 del mismo día)
- Grupo Concesionario del Oeste 0629-05950537, $1.155,52, 16/03/2025
- Telepeaje: 12 estados de cuenta 2017-2023

**Descartados:** remitos de Ernesto Hernández y de Cargill (no son facturas). Unos 420 "desvíos" eran números iguales de otros emisores.

**Límite del cruce:** no detecta facturas que faltan en la base cuando su PDF tampoco está en la carpeta. Para eso queda el cruce con Mis Comprobantes de ARCA (requiere autorización de Sergio) y el detector de recurrentes.

### 10bis. Ernesto Hernández (contacto 560): verificado a ojo y contra la caja chica del campo (28/10) — RESUELTO

Sergio indicó que no son remitos para descartar, sino gastos reales en negro, y que la verdad está en la caja chica. Son facturas C manuscritas con talonario de CAI vencido. El texto del PDF no sirve: el número que se lee es el de la imprenta. Revisé a ojo los **19 PDFs**, incluidos 6 con el nombre invertido ("HernandezErnesto", "AdanHernandez"), contra WC y contra `MovimientosCajaEfectivo` (Caja = 'CampoChica').

- **El proveedor repitió números en papel:**
  - Hay dos facturas **0011-00000126**: 30/08/2024 y 05/10/2024, cada una de 2 garrafas por $22.000.
  - Hay dos facturas **0011-00000198**: 15/08/2025, 1 garrafa por $16.500; y 01/11/2025, 2 garrafas por $33.000.
  - Los números de WC son correctos; **no se renombra nada**. Se corrigen dos afirmaciones anteriores de este informe, que estaban equivocadas: que 4 facturas "no tenían PDF" y la propuesta de rotular esos comprobantes "sin número".
- **La B 0001-00013882 del 09/05/2026 está bien:** la caja confirma esa fecha.
- **Faltaba cargar la 198 del 15/08/2025, por $16.500.** Estaba en la caja chica (movimiento 1218, sin contacto), pero no en la cuenta 560. **Se aplicó así:**
  - compra IdDeuda **2143524146**, con su renglón "Garrafa 10 Kg.", mismo rubro y centro de costo que las demás;
  - pago efectivo **2702** (CampoChica, 15/08/2025, $16.500);
  - movimiento de caja 1218 vinculado al contacto 560;
  - aplicación manual del pago a la factura.
  - Respaldo previo: `WC_antes-carga-hernandez-198-20250815_20261028_131816_732224.bak`. El saldo de la 560 estaba en 0 y quedó en 0.
- **Regla:** los comprobantes de Ernesto Hernández son gastos reales y la caja chica del campo es la fuente de verdad de sus compras de garrafas.

### 10ter. Fundamentos de los comprobantes no cargados (28/10), para que decida Sergio

Para cada comprobante se buscó el pago en BNA, Galicia, pagos efectivo, caja chica y caja Giamigli, y en líneas de tarjeta (±40/60 días, mismo importe, y por palabra clave).

| Comprobante | Qué es | ¿Pago de la empresa? | Efecto de cargarlo |
|---|---|---|---|
| Sancor NC 00035-00006907 $1.895,78 y NC 00030-00003040 $813,44 (28/07/2026) | Anulan las facturas 00035-00002077 y 00030-00003814 (pólizas cuyo tomador es Irma Miranda) | Las facturas están cargadas; la cuenta Sancor da −$694 | Saldo a favor de unos $2.015, salvo que aparezca reintegro o compensación |
| Agroveterinaria Central F 0003-00012227 (11/09/2025), **$47.500 total** (neto $39.256,20) | Alimento para gato, Excellent 7,5 kg, contado efectivo | Sí: caja GiamigliSA 11/09/2025 "Comida Gatos" −$47.500, sin contacto | Factura más vínculo del pago de caja; saldo queda en 0 |
| Coop. Agropecuaria tique F-A 00039-00034238 (21/07/2025) $37.403 | Cadena de moto, pagada en efectivo en el mostrador | No encontrado en ninguna caja ni banco | Sin pago: deuda de $37.403 en una cuenta hoy en 0 |
| Bulonera Central Pacheco F 00001-00070062 (16/01/2025), neto $28.662,10 | Bulones, contado, Gral. Pacheco | No encontrado | Ídem |
| Ochoa Erika F-C 00001-00000094 (28/12/2022) $45.000 | Instalación de aire acondicionado, El Talar; facturada a Giamigli como consumidor final | No encontrado; no existe el contacto | Ídem |
| Pablo Car (González Pablo Marcelo) F-B 00005-00000936 (05/08/2021) $34.848 | Batería C500, Ituzaingó; consumidor final | No encontrado; no existe el contacto | Ídem |
| D'Agostino F-A 00002-00001174 (28/08/2019) $3.200 | Escribana: certificación de firmas (acta 121 L-102), Gral. Pacheco | No encontrado. El contacto está duplicado (212 y 395) | Ídem |
| Lartirigoyen NC 0149-00001775 (registro 28/03/2023) US$28,74 | Curasemillas Nova 5 L; origen 0149-00012454 | WC tiene 3 facturas iguales de US$28,74 (10/03 y 14/03 ×2) y la cuenta da ≈0 | Saldo a favor de US$28,74, salvo que una de las 3 facturas esté duplicada |

### 10quater. Decisiones de Sergio sobre los no cargados (28/10) — APLICADO

Respaldo previo: `WC_antes-carga-pendientes-20261028_20261028_134717_528403.bak`. Los dos primeros intentos se revirtieron enteros (texto de más de 50 caracteres; ficha de revisión duplicada). El respaldo corresponde al estado anterior.

| # | Decisión de Sergio | Aplicado | Saldo |
|---|---|---|---|
| 2 | Agroveterinaria Central: gasto de la empresa (confirmado) | Compra 2143524154 F-A 0003-00012227 $47.500 (Insumos Generales) + pago efectivo 2707 desde caja GiamigliSA, vinculado al movimiento de caja 1101 "Comida Gatos" + aplicación | 434: 0 → 0 |
| 3 | Coop. Agropecuaria: cadena de **motosierra**, pagó Marcelo Sierra en efectivo y se le repuso | Compra 2143524155 F-A 00039-00034238 $37.403 (Mant. Maquinarias; percepción DGR $153,92) + pago efectivo 2708 por $37.403, vinculado al movimiento 1100 de caja GiamigliSA del 11/09/2025 "Cadena Motosierra" −$37.500. Los $97 de diferencia son el redondeo de la reposición a Sierra. | 22: −0,02 → −0,02 |
| 4 | Bulonera: gasto particular de Sergio, pagado por él al contado | Contacto nuevo **5676** Bulonera Central Pacheco S.R.L. (CUIT 30715502204). Compra 2143524156 con renglón "Bulones" $28.662,10 + IVA y renglón "Compra particular Sergio" por el mismo importe en negativo; total 0 | 0 |
| 5 | Ochoa: gasto particular de Lucy | Contacto nuevo **5677** Ochoa Erika Agustina (CUIT 27401286174). Compra 2143524157 con renglón "Instalación aire acondicionado" $45.000 y renglón "Compra particular Lucy" en negativo; total 0 | 0 |
| 7 | Unificar D'Agostino | La 395 se unificó en la **212**: se pasaron sus compras, pagos efectivo y movimientos, la 212 recibió el CUIT 27256615032, y se borraron la ficha de revisión y el contacto 395. Los registros de auditoría y recálculo FIFO conservan el número 395 como historial | 212+395 = −0,01 → −0,01 |

**Pago de la escribana ($3.200, 28/08/2019): no encontrado.** Se buscó en bancos, cajas, cajas particulares L/S, tarjetas y en la planilla "Informacion DDJJ 2019 Particulares.xlsx". No hay extractos personales de los socios de 2019; las carpetas arrancan en 2021. Sus dos facturas anteriores se pagaron en efectivo desde caja. La factura queda sin cargar hasta que Sergio decida.

**Pablo Car (pendiente de confirmación).** La cuenta de Mercado Libre está cargada recién desde feb-2024. En jul-sep 2021 no hay cargos de Mercado Libre por $34.848 en bancos ni tarjetas de la empresa, así que la compra se pagó por fuera de la empresa, probablemente con la cuenta o la tarjeta personal de un socio. Propuesta: cargarla como gasto de Giamigli (el PDF dice "Batería C500"), con "pago por socio", como se hace en Sancor. Falta saber qué socio la pagó.

**Sancor: análisis de las dos cuentas.**

- **Cuenta A, tomador Giamigli:** póliza 1730/166 Vida Colectivo (1152211; desde ago-2026, 1302295). Unos $347 por mes, por débito de Galicia.
- **Cuenta B, tomador Irma Miranda (asociado 4288366):** póliza 600/21 Accidentes Personales (de $37.000 a $47.000 por mes) y, desde jul-2026, las pólizas 2500/29 y 1730/8. Las pagan los socios: Sergio en ene-feb y Lucy desde marzo.
- **Qué pasó en julio:** el 22/07 Sancor emitió un cupón para las pólizas viejas (13484620, 2310558 y 1289680; vigencia 02/08 a 02/09). El 28/07 las reemitió con números nuevos (13500137, 2315661 y 1294497), con las facturas 00019-10654, 00035-2077 y 00030-3814. Las NC 00035-6907 y 00030-3040 anulan los endosos 129 y 125 de las pólizas viejas 2500 y 1730/8 para ese mismo período.
- **El pago:** Lucy pagó el 03/08 **$42.563,59 = exactamente las 3 facturas nuevas**. Las facturas que anulan las NC (las de las pólizas viejas) no están en WC ni en la carpeta.
- **Conclusión:** **las NC no se cargan solas** (crearían un saldo a favor que no existe). O no se carga nada, o se cargan el par factura vieja más NC (efecto neto 0) cuando se pueda verificar con ARCA.
- El −$694 de saldo coincide con dos facturas de $347 (sep y oct) cuyo débito en Galicia todavía no está cargado. Es probable, pero no está verificado.

**ARCA:** Sergio autorizó entrar en solo lectura (28/10). Según el relevamiento de la spec 042, la clave fiscal no tiene habilitado "Mis Comprobantes". Para el cruce, Sergio tiene que habilitar ese servicio para Giamigli en el Administrador de Relaciones. No se intentó habilitarlo.

## 11. Cruce con ARCA, Mis Comprobantes Recibidos (28/10)

**Acceso:** Sergio autorizó (con doble chequeo) entrar con la clave fiscal de **Lucy (27-04862094-4)**, que **sí** tiene "Mis Comprobantes" representando a Giamigli (la de Sergio no lo tiene). Solo lectura: se consultaron y descargaron los CSV de recibidos 2017-2026 (2.994 comprobantes). Quedó constancia en la auditoría de la bóveda (portal 15).

Scripts: `cruce_arca_mis_comprobantes_20261028.py` y `cruce_arca_faltantes_20261028.py`. Detalle de lo no cargado: `arca-no-cargados-20261028.csv`.

**Resultado:**

- 2.558 coinciden en número, emisor, fecha e importe.
- 168 coinciden tras desempatar números repetidos.
- 47 están cargados con otro número; mismo emisor, ±10 días, mismo importe.
- 13 quedan ambiguos.
- **77 no están en WC.**

**Aplicado:** **26 fechas de emisión corregidas según ARCA** en facturas en pesos (AUBASA, Ricardo Criado, FEDEA, Lartirigoyen, Movistar, Pet Supplies, EESS Saladillo, Coto, Coop. Eléctrica, Garantizar). Saldo de las 10 cuentas igual. Respaldo: `WC_antes-fechas-segun-arca_20261028_141826_139565.bak`. Se excluyó la Bayá Casal 20-196397, en US$: en las cuentas en dólares, cambiar la fecha cambia el TC y movería el saldo.

**No son errores:** las diferencias de importe son compras particulares cargadas con total 0 o parcial (Wagen, Allianz, Coto) y facturas en US$ que ARCA informa en pesos (Sunanco, Gentos, Nidera, Bayá Casal, Yanquelen).

**Contactos con CUIT mal cargado** (el comprobante cruza bien): Astecna, Carpintería Arioni, Katat, Electricidad Lavalle.

**No cargados en WC: para decidir con Sergio** (no se cargó nada; moverían saldos)

- **Montos grandes o sensibles:**
  - Allianz: NC en US$ de ago-2026 (9-3396, 9-3397, 9-3615) y documentos relacionados.
  - **Estudio Criado: NC 0003-00000009 por −$387.907 (15/02/2024)**, emitida con el CUIT de Nicolás Criado.
  - Wallace Hnos.: NC 4-1355, −$428.183 (10/07/2025).
  - Wagen: F 38-4643, $410.568 (27/01/2025).
  - EESS Saladillo (OPESSA): 3 facturas, $162.535.
  - Asoc. Cooperadora Laboratorio: F-C 4-122, $159.000 (10/08/2026).
  - Calderón: 2 facturas, $88.572.
  - Syngenta: ND 303-21626 $64.593 y NC 303-9275 −$24.172.
- **Pares factura + NC que suman 0:** Pérez Claudio ($1.872.584), Sainte Cluque, Coto (×2), Aguer, Soc. Rural Tapalqué, Agrovial, Fideicomiso Alcalá 2-199, Angus.
- **Menores:** Lartirigoyen (2 ND en pesos más la NC 149-1775 en US$), Folgado (NC en US$), Silva Rossi, Izaguirre, Gutiérrez Néstor, GMRA, Sedafe, Simplex, Lavalle, Palaversich, Peret, Masivos, Manso, Unipase, Buira, Saavedra, Crevena, D'Agostino, entre otros.
- **Excluidos:** recibos (tipos 4 y 15: Ricardo Criado, Cordero). ARCA no incluye los comprobantes manuales, como los de Ernesto Hernández.
- **Sancor:** ARCA **no** muestra facturas de las pólizas viejas (endosos 129 y 125). Confirma que las NC del 28/07 no deben cargarse solas.

### Pablo Car — APLICADO

El pago apareció en la **caja de ahorro en pesos de Sergio en ICBC: 29/04/2021, "CPA. MERCADOPAGO PABLOCAR", $34.848**. Se cargó así:

- contacto nuevo **5678** González Pablo Marcelo (Pablocar);
- compra 2143524158, F-B 00005-00000936 (Batería C500, Mantenimiento Maquinarias);
- asiento a favor de Sergio en su cuenta de socio (**3241**, "Devolución"), vinculado como pago por socio.

Saldo del proveedor: 0. Respaldo: `WC_antes-pablocar-pago-socio_20261028_141401_420177.bak`.

### 11bis. Análisis uno por uno de los no cargados más grandes (28/10) — sin aplicar

1. **Estudio Criado, NC 0003-00000009 (−$387.907, 15/02/2024).** El 09/02 el estudio emitió la F-C 612 ($387.907), cargada en WC y pagada por Galicia el 08/02. El 15/02 emitió la **616 por el mismo importe** y la anuló el mismo día con esta NC. Es una factura duplicada que el propio estudio anuló; efecto neto 0. No falta nada.
2. **Allianz, ND y NC en US$ de jul/ago-2026.** El 31/07 Allianz emitió 3 ND en US$ (9-3096, 9-3097 y 9-3604), las anuló con NC en US$ el 19/08 y las reemitió en **pesos** el 20/08 (9-4689, 9-4690 y 9-4528: $8.071,64, $51.752,26 y $38.623,50). WC ya tiene esos importes en pesos, cargados con el número del cupón (25008/206435, 25008/206436 y 26008/210976, del 23/07). No falta nada. Corrección posible (no mueve el saldo): pasar esas compras al número fiscal y a la fecha 20/08.
3. **Wallace Hnos., NC 4-1355 (−$428.182,96, 10/07/2025).** Ya está en WC como liquidación de **Venta Hacienda 00004-00001355** en la cuenta 600, que da saldo 0. No falta nada.
4. **Wagen, F 38-4643 ($410.568, 27/01/2025; neto $339.312,40).** No está en WC ni en la carpeta, y no se encontró pago. Las otras facturas de Wagen (camioneta 38-4588/4589 y servicios 53-6954/8120) sí están. Pendiente: qué es y quién la pagó.
5. **EESS Saladillo / OPESSA, 3 facturas ($48.644,96, $9.888 y $104.002,09).** **Están cargadas en YPF Debenedetti (282)**, pagadas con tarjeta (compras por la app de YPF), pero con números mal tipeados: 07500-00000329 en lugar de 7300-31829; 07296-00034628 en lugar de 7298-34628; 07296-00046997 en lugar de 7296-48997. El emisor real es OPESSA (CUIT 30-67877449-5 = contacto 30). Corrección posible: arreglar los números; mover el par factura+pago a la cuenta 30 no cambia ningún saldo.
6. **Calderón Fernando, F 6-6390 ($85.547, 23/09/2025).** La transferencia de Galicia del 23/09/2025 por $85.547 ("Calderón Fernando 24182374640") se **reasignó a la Municipalidad** el 07/10, por decisión de Sergio, contra una factura "SIN COPIA" de guías por $85.547 creada para esa fecha (IdDeuda 2143523855). **ARCA muestra que Calderón facturó exactamente $85.547 ese día.** Para revisar con Sergio. Si el pago era de Calderón: volver la transferencia a Calderón, cargar su factura y anular la "SIN COPIA" de la Municipalidad. Ninguno de los dos saldos cambia.
7. **Asoc. Cooperadora Laboratorio, F-C 4-122 ($159.000, 10/08/2026).** No está en WC ni en la carpeta, y no se encontró pago. Puede ser una deuda real impaga. Pendiente.
8. **Syngenta Agro (mismo CUIT que el contacto 398), ND 303-21626 ($64.593,27, 15/05/2023) y NC 303-9275 (−$24.172,24, 09/01/2024).** No están en WC; la cuenta 398 no tiene movimientos desde 2021 y da saldo 0. Netas suman +$40.421 de deuda. Pendiente; relacionado con la retención de $7.583,62 que figura en memoria.
9. **Pares factura + NC que suman 0** (Pérez Claudio $1.872.584, Sainte Cluque, Coto ×2, Aguer, Soc. Rural Tapalqué, Agrovial, Fideicomiso Alcalá 2-199, Angus): son comprobantes emitidos y anulados; no afectan nada. Propuesta: no cargarlos.

### 11ter. Decisiones de Sergio sobre 11bis (28/10) — aplicadas
Respaldos: `WC_antes-arca-allianz-ypf-calderon_20261028_155428_098922.bak` y `WC_antes-wagen-4643-particular_20261028_155734_988685.bak`. Saldos de 515, 282, 497, 72 y 636 iguales antes y después.

- **Allianz (515):** 2143521545 → 00009-00004689, 2143518508 → 00009-00004690 y 2143521546 → 00009-00004528, las tres con fecha 20/08/2026 (número fiscal según ARCA).
- **YPF / OPESSA (282):** se quedan en el mismo contacto. Números corregidos: 2143514540 → 07300-00031829, 2143514790 → 07298-00034628 y 2143517425 → 07296-00048997.
- **Calderón (497):**
  - se eliminó la factura "SIN COPIA" 2143523855 de la Municipalidad y se anuló su aplicación 21650;
  - se cargó la F A 00006-00006390 del 23/09/2025 (2143524159, flete, neto $70.700 + IVA 21%; sin PDF, datos de ARCA);
  - la transferencia Galicia 2800 volvió a Calderón (reasignación 3270) con su aplicación manual.
- **Wagen (636), F 0038-00004643 ($410.568, 27/01/2025):**
  - según el mail de Wagen del 24/01/2025 es el sellado del 1% del alta del 0km ($363.808) más el grabado de autopartes ($46.760);
  - Sergio indicó que es un gasto suyo: compra particular de Sergio, total 0 (2143524160);
  - no hay ningún pago de la empresa por ese importe.
- **Cooperadora Laboratorio F-C 4-122:** la factura no llegó. No se carga.
- **Pares factura + NC:** se dejan como están.
- **Syngenta ND 303-21626 y NC 303-9275:** revisado, sin aplicar. Ver el detalle abajo.

**Syngenta, detalle:**
- El punto de venta 303 es el de las notas de Syngenta para la línea Nidera. La compra de semillas F 301-32216 (US$10.702,47, 17/04/2023) está en la cuenta **Nidera (303)**, no en Syngenta (398).
- En esa cuenta hay una **ND interna NDI303-230419 de $19.679,56** que cerró la diferencia entre la factura y lo pagado:
  - pagado: tarjeta $2.288.211 + retención $33.571,30;
  - es decir, un ajuste propio para dejar la cuenta en cero.
- En 2022 se hizo lo mismo: una NC interna NCI303-220701 y la nota AJ 21, junto a la ND real 303-15276.
- La hipótesis de Sergio (notas que no llegaron, compensadas con ajustes propios) se confirma en el mecanismo, pero **los importes no coinciden**:
  - las dos notas de ARCA netean $40.421,03;
  - el ajuste interno fue de $19.679,56.
- Si las reales reemplazaran al ajuste, Nidera quedaría debiendo $20.741,47.
- No están en los mails ni en la carpeta. Hace falta el PDF de ambas, pedido a Syngenta o a SUNANCO.

**Syngenta: CERRADO por decisión de Sergio (28/10). Se deja como está; no cargar la ND 303-21626 ni la NC 303-9275 ni tocar el ajuste interno NDI303-230419.**

## 12. Decisión (29/10/2026): principio APROBADO con las condiciones del especialista 07

Sergio lo aprobó con una condición: que lo avalara el especialista financiero (07). El 07 lo avaló **con condiciones**, y estas pasan a formar parte de la regla:

- **Hueco:** el FIFO se corta en dos casos. (1) Un pago que no cubre ninguna factura abierta anterior o de hasta 1 ciclo después: queda como anticipo. (2) Una factura que sigue impaga cuando ya hay pagos de un período más nuevo aplicados: queda como impaga o como factura faltante. En los proveedores recurrentes, también es hueco el período esperado sin comprobante que marca el detector 044. En cada corte el FIFO arranca de nuevo, sin arrastrar.
- **Empates en importe idéntico:** gana la menor distancia de fecha. Después, la factura anterior al pago. Después, el número de comprobante más bajo. Si el mismo importe se repite 3 veces o más en ±1 ciclo, se aplica FIFO dentro del grupo. Todo empate va marcado "a revisar".
- **Combinaciones:** solo entre facturas abiertas, a menos de 1 año del pago, con tope de cantidad. Si hay más de una combinación exacta, va a revisión.
- **US$:** se concilia en la moneda del documento; si hay cruce entre $ y US$, al TC del comprobante. En este saneamiento no se crean ND ni NC: las diferencias van a revisión. El saldo se controla en las dos monedas.
- **No se tocan** las aplicaciones manuales ni el tramo de Estudio Criado 2026. Solo se rehacen las de 020 y FIFO-032.
- **Piloto:** primero Estudio Criado (115) y Jáuregui (48), comparados a mano. Si el saldo con `refrescar=True` difiere, la tanda se bloquea. La cuenta 97 no se toca hasta saber qué cuenta es. En cada tanda se registra el antes y el después, y se muestra si cambia el rubro o el centro de costo en el Cash Flow.

Cargill (258) no usa el algoritmo: se copia del portal (Sergio 29/10).

## 13. Cargill (258) aplicado el 29/10/2026

Script: `backend/scripts/aplicacion_cargill_avisos_036.py`. Fuente: los 97 avisos de pago del portal, bajados en solo lectura a `backups/cargill-aplicaciones-20261029/` y parseados con `cargill_avisos_parsear_036.py`.

- Se anularon las 198 aplicaciones de la 020 y se grabaron **286 aplicaciones (`manual`), por $78,5 M**:
  - **Desde 2021:** 148, copiadas aviso por aviso. Cada aviso dice qué cancela cada LPG, NC, recibo o cobro con tarjeta.
  - **Antes de 2021, sin avisos:** 138 (11 por importe idéntico y 127 por FIFO de hasta un ciclo). Ningún comprobante queda cancelado antes de una fecha en que Cargill lo informó pendiente en sus 36 estados de cuenta.
- **Saldo antes = después:** $ −83.816.747,07 y US$ −60.000. Respaldo `WC_aplicacion-cargill-avisos-036_20261029_092136_360424.bak`.
- **Sin cubrir:**
  - ND 7050-76972 y 7050-77233: impagas, es correcto.
  - 7 redondeos de $0,02 a $113: Cargill los cancela con su ajuste de redondeo y en el sistema no hay un documento equivalente.
  - Para mirar: 7028-62758 ($14.426,73), 7028-73987 ($4.706,41), 5850-10872 ($100.757,26) y 5850-00000146 ($2.008.244,26). Esta última parece el anticipo financiero de sep-2024, y Cargill la da por $2.008.818.

**Corrección (misma fecha, 2ª corrida):** ahora cada documento recibe del aviso exactamente el importe que Cargill cancela, y primero se aparean los importes idénticos (líneas de tarjeta). Los débitos neteados en un desembolso de anticipo (V4) se cancelan cuando Cargill cancela ese anticipo (AH): la ND 5850-146 en dic-2024 y la factura 5850-10872 en may-2026. Resultado: **287 aplicaciones**, saldo sin cambios. Solo quedan sin cubrir los redondeos ($0,01 a $113,05) y las ND 7050-76972/77233, que están impagas. Respaldo `WC_aplicacion-cargill-avisos-036_20261029_093004_691927.bak`.
