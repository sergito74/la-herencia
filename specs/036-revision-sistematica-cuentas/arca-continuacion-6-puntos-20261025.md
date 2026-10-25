# ARCA: ejecución de los seis puntos — 25/10/2026

Autorización de Sergio: avanzar punto por punto hasta terminar y pedir ayuda solo si hace falta. Pedido adicional: descargar PDF de comprobantes/DDJJ, conservarlos localmente y vincularlos al sistema. Las consultas del portal siguen siendo de lectura/descarga; no presentar declaraciones, generar/pagar VEP ni compensar impuestos.

## Estado de trabajo

| Punto | Estado | Resultado / siguiente paso |
|---|---|---|
|1. F931 y diferencias de pagos|Resuelto|Diez DDJJ incorporadas. Excedentes identificados por VEP originales: SICOREsept2025/mayo2026 y anticipo5Ganancias2026 enenero2026.|
|2. IVA y devoluciones|En curso|Nueve reintegros oficiales RE-Granos aplicados a26certificados; SIRE216 sin resultados; percepciones en revisión.|
|3. Ganancias / anticipos / SICORE|En curso|Estados SCT 2025/2026 descargados; pendiente definir criterio de registración de obligaciones/créditos.|
|4. Autónomos y financiación socios|Resuelto|48 obligaciones 09/2024–08/2026 ($3.972.687,80) y 47 vínculos de socios ($3.619.422,36) aplicados; asientos 2255 y 2734 actualizados; Opción A aplicada en asientos 2018 (1872 Devolución y 1876 AsignaciónGasto) y Excel sincronizado; 305 obligaciones históricas y 207 pagos Particular S/L clasificados.|
|5. Bienes Sustitutos|Aplicado (2022–2026 conciliado a $0,00)|Incorporadas 15 obligaciones de planes U657364 y W143471 al corte ($1.427.555,70) con PDF vinculados y clasificados 32 débitos Galicia históricos ($914.443,36). Resta clasificar 27 pagos pre-2022 ($126.956,19).|
|6. Conciliación final al corte|Pendiente|Solo después del contraste por concepto; no cierre por ajuste global.|

## Punto1: aplicado

Las DDJJ del servicio Declaración en Línea confirman que junio2025 es **1.115.100,17** y agosto2025 **794.275,52**, ambos iguales al banco. Julio2025 es738.792,95. Quedan resueltas las discrepancias con los avisos anteriores; el aviso de agosto incluía un importe adicional que no pertenece al F931 oficial.

Se incorporaron diez obligaciones por **$9.442.305,95**: mayo–septiembre2025 y enero–mayo2026. Cada registro toma fecha de generación de la DDJJ, período y númeroVEP oficial; no se agregaron pagos. Diciembre2025 ya estaba y se conserva su obligación de1.311.952,66.

Se descargaron **22 PDF oficiales** (11 acuses +11 VEP pagados) y se conservaron11 impresionesPDF del formularioHTML oficial para los mismos períodos, claramente identificadas como copias del portal. Los originales descargados no se editaron. Se crearon **44 vínculos** a documentos: tres por obligación y un VEP por débito bancario. Los archivos permanentes están en `Documents/La Herencia/Administracion y gestion/Impuestos y Sociedades/ARCA/Giamigli/Cargas Sociales/<año>/`; fuentes y manifiestos en `backups/arca-continuacion-20261025/`.

Nuevo metadato `ArcaDocumentos`: tipo, período, número, ruta, SHA256 y carácter original/copia. La cuentaARCA muestra enlaces aPDF; el endpoint sirve únicamente archivos registrados deARCA dentro de esa raíz, con huella comprobada. Falta terminar comprobaciónUI de esta ampliación antes de declararla validada.

Once débitos existentes clasificados/repartidos: parte F931 a Cargas sociales, excedentes a Por identificar. Excedentes todavía sin concepto: septiembre2025 **18.515,27**; diciembre2025 **236.381,79**; mayo2026 **477.895,73**. No se inventó su imputación ni se modificó el importe del banco.

Saldo mayor119: **+5.739.479,4089 → −3.702.826,5411**, por las diez obligaciones faltantes. Cantidad1809→1819. No es deuda fiscal confirmada. Otras cuentas, cajas y socios conservados por invariantes de transacción; Excel no cambia porque no se tocaron socios.

Scripts: `afip_f931_pendientes_portal_036.py` (inspección/aplicación y repetición sin escrituras); `crear_subcuentas_arca_036.py` ampliado para metadatos documentales. Respaldo verificado de aplicación `WC_arca-f931-portal-036_20261025_172503_217464.bak`; esquema documental `WC_arca-subcuentas-036_20261025_172209_222323.bak`. El primer intento por incompatibilidad de enlace de fechas del driverSQL fue revertido íntegramente por la transacción; corregida conversión, aplicado y comprobada repetición sin nuevas escrituras.

23 pruebas focalizadas aprobadas, incluida raíz de archivos/huella. Resta TypeScript/lint y recorrido de enlacesPDF con esta ampliación.

### Identificación definitiva de los pagos y documentos adicionales

El buscador general de VEP pagados de Giamigli, usuarioTODOS,24meses y fechas01/01/2025–30/09/2026, devuelve59VEP. Se descargaron **los59PDF oficiales**, conservados con huella y copia local permanente en `ARCA/Giamigli/VEP/<año>/`. Hay21SICOSS,31SICORE/retencionesGanancias y7pagosGanancias (uno consolidado, no descomponer sin consultar sus subVEP).

Los59VEP se agrupan de forma única en **54débitos Galicia**, con igual CUIT, fecha de pago y suma exacta. No queda VEP del universo consultado sin vínculo bancario ni agrupación ambigua. Se aplicaron54clasificaciones y los enlacesPDF sin cambiar saldos ni ningún movimiento original. Script `clasificar_veps_arca_036.py`; extracción verificable `extraer_veps_arca_036.py`; respaldo verificado `WC_arca-59-veps-036_20261025_173314_682249.bak`.

| Banco | Diferencia / pago | VEP y concepto oficial |
|---|---:|---|
|2825|18.515,27|1526355915 — SICORE217, período09/2025|
|2991|236.381,79|1567666953 — GananciasSociedades10, concepto191, ejercicio2026, anticipo5|
|3269|477.895,73|1636407910 — SICORE217, período05/2026|
|2695|514.042,31|1489309726 — RetencionesGanancias07/2025|
|3282|666.208,36|1640408587 — RetencionesGanancias06/2026|

Los primeros tres débitos contienen más de un VEP. El F931 no se aumenta para absorber otro impuesto. La registración de obligacionesGanancias/SICORE se sigue enpunto3, después de completarIVA. El punto1 queda resuelto en su alcance (DDJJ, pago y diferencias identificadas).

## Punto2: devoluciones contrastadas y aplicadas

Servicio Pago Devoluciones: selección expresa CUITGiamigli;17pagos desde2022 a2026, reportePDF oficial completo descargado. Los nueve abonos propuestos están presentes y sus detalles oficiales dicen **RE-Granos** por los importes exactos. ARCA informa fecha de orden/pago anterior a la acreditación del banco; ambas se conservan, no se cambia el banco.

Se descargaron nuevePDF de detalle de pago y se verificaron visualmente junto al formularioF931. Se aplicó devolución a26certificados, antes0, por **13.179.515,62**, sin otro cobro. Documentos vinculados al banco y a cada certificado. Auditoría/script `aplicar_devoluciones_iva_arca_036.py`; respaldo `WC_arca-iva-devoluciones-036_20261025_173954_248155.bak`; repetición sin escrituras. Saldo119 **−3.702.826,5411 → +9.476.689,0789**; otros contactos/cajas/socios intactos.

SIRE216, Giamigli,01/01/2025–30/09/2026: el organismo responde sin resultados (o importes0), captura textual conservada. No atribuirle retenciones faltantes.

Percepciones767:228por507.600,71; cruce preliminar1315cabecerasCompras2024–oct2026:44coincidencias únicas por CUIT+número y33candidatos únicos adicionales por documento con CUITausente en contacto, pendientes de comprobar contraPDF. Numerosos restantes son bancos/servicios y no necesariamente compras faltantes. **No aumentar el total de facturas ni reabrir proveedores cerrados por una diferencia de exposición de percepciones**: el total del documento puede incluirlas aunque la columnaPercepcionIVA esté0.

Corrección de hipótesis histórica: no todos los abonos119 son IVA. BNA15788(14/03/2016,1.323) diceMECON; BNA15950(11/12/2020,134.391,10) diceSAF363Ministerio y tiene contrapartida de ajusteCaja2493 por el mismo importe. Deben verificarse por separado antes de llamar al residual804.500,0426 una diferencia exclusiva de IVA. No se modificaron esos registros.

### Control documental y movimientos tributarios

Se corrigieron exclusivamente los 26 vínculos PDF de las devoluciones: en la vista de cuenta corriente `Ret. IVA Granos.IdOrigen` es **IdLiquidacion**, mientras la tabla de certificados usa **IdRetencion**. Los importes aplicados eran correctos; el vínculo anterior devolvía404. Reparación auditada `--reparar-vinculos`, respaldo verificado `WC_arca-iva-enlaces-036_20261025_174811_515853.bak`. Los127vínculos registrados fueron contrastados con su movimiento y con la huella del archivo. No cambió ningún saldo.

Percepciones:22 de los33candidatos adicionales se confirmaron también por CUIT del emisor y receptor en PDF original; quedan11 sin esa confirmación. Son66 documentos identificados (44+22), **no66 créditos fiscales nuevos**. Sin modificaciones de compras.

Se conservaron los estados oficiales SCT de IVA2025/2026 y copias PDF/texto de los21detalles mensuales. El saldo técnico es acumulado: diciembre2025 **21.772.930,50**, septiembre2026 **17.695.983,67**; no sumar los saldos mensuales. Septiembre fue presentado el19/10/2026: distinguir período fiscal de fecha de registración al comparar con corte30/09. SCT muestra compensaciones automáticas y manuales entre períodos; todavía no se incorporaron como movimientos financieros.

## Punto3: contraste tributario obtenido; registración pendiente

Estados SCT de Ganancias2025/2026 y SICORE2025/2026 descargados enPDF, detalles conservados como copias del portal. Ganancias2025: impuesto determinado **7.316.860,39**, presentado08/08/2025, cancelado con créditos/anticipos/compensación. Ganancias2026: determinado **1.353.097,06**, presentado13/08/2026; saldo libre disponibilidad **3.715.623,22** y otros créditos **1.007.737,91** al consultar. No equivalen al saldo del mayor119. Nueve anticipos2026 generados de442.267,59 cada uno; cancelación combina banco, IVA y créditos/débitos. El VEP consolidado1612758340 incluye capital349.151,41 e interés320,06, total349.471,47. No registrar nuevamente los anticipos como gasto además del impuesto anual.

SICORE217: capital cancelado en períodos revisados; intereses residuales oficiales **471,21 (07/2025), 54,58 (10/2025), 610,69 (06/2026)**. Septiembre2026 fue presentado06/10 y completado con9.056,60 el08/10, además del pago26.202,18 de septiembre: separar el hecho posterior al corte. No cargar retenciones practicadas a proveedores como gasto propio; el tipo20 está excluido del móduloImpuestos. Falta resolver exposición fiscal sin duplicar fuentes comerciales y descargar las DDJJ/acuses originales que estén disponibles.

## Punto 4: resuelto en `WC` y planilla Excel sincronizada (Opción A aplicada para 2018)

Con la confirmación de Sergio sobre las preguntas **Q1 y Q2**, y la elección expresa de la **Opción A** para los asientos de 2018 (Pregunta 3):

1. **Ajuste de los dos asientos de socios contra CCMA oficial y sincronización de `Cajas Giamigli.xlsx`:**
   - **Sergio `IdMovimiento = 2255` (`05/10/2026`, `"ARCA — Autonomos Sergio 4 2026"`):** actualizado de `$136.628,92` (`45.0921 USD`, `16.761 kg`) a **`$160.290,79`** (`52.9013 USD`, `19.664 kg`), coincidiendo con el pago en CCMA del `05/10/2026` (`$153.985,59` capital + `$6.305,20` interés resarcitorio).
   - **Lucy `IdMovimiento = 2734` (`07/04/2026`, `"ARCA — Autonomos 03 2026"`):** actualizado de `$59.916,00` (`21.5525 USD`, `7.132 kg`) a **`$56.016,36`** (`20.1498 USD`, `6.667 kg`), coincidiendo con la obligación y el pago oficial en CCMA del `07/04/2026`.
2. **Aplicación de la Opción A en los asientos de 2018 (`IdMovimiento = 1872` y `1876`) en `WC` (`corregir_1872_1876_036.py`, regla `socio-sergio-autonomos-1872-1876-036`, respaldo `WC_socio_sergio_1872_1876_036_20261025_205635_147753.bak`):**
   - **`1872` (`07/05/2018`, `$2.842,12`, `Pago ICBC`):** pasó de `AsignacionGasto` (Debe) a **`Devolucion` (Haber)** con motivo `"Autonomos 04 2018"`, reflejando fielmente el pago personal realizado por Sergio desde su cuenta bancaria.
   - **`1876` (`29/05/2018`, `$2.842,12`, `Efectivo`):** pasó de `Devolucion` (Haber) a **`AsignacionGasto` (Debe)** con motivo `"Pago — Reintegro efectivo Autonomos 04 2018"`, reflejando el reintegro en efectivo que la caja de la empresa (`Caja Efectivo Pesos` fila 1217, `IdPagoEfectivo = 1432`) le entregó a Sergio en mano.
   - Sincronización completa de la planilla `Cajas Giamigli.xlsx` realizada con `preparar_planilla_socios_036.py`, `editar_planilla_socios_036.mjs apply` y `publicar_planilla_socios_036.py --publicar` (`sha256Final = d6293dc0dcc3f3bc78cc42181fc31ba5ecc12a251962ebed6f557fb7b200fa9e`), revaluando Sergio con `+15.6358 USD` y `+3.974 kg` de carne a favor por la restitución de la secuencia temporal correcta.
2. **Incorporación de las 48 obligaciones mensuales de Autónomos (`09/2024 – 08/2026`) al corte `30/09/2026`:**
   - Insertadas en `dbo.Impuestos` (`IdOrganismo = 119`, `IdTipoImpuesto = 5`): **24 de Sergio** por **`$2.796.545,05`** (`IdImpuesto = 1326..1349`) y **24 de Lucy** por **`$1.176.142,75`** (`IdImpuesto = 1350..1373`), total **`$3.972.687,80`**.
   - Copias PDF de los estados CCMA copiadas a `Documents/La Herencia/Administracion y gestion/Impuestos y Sociedades/ARCA/Giamigli/Autonomos/` (`CCMA-Sergio-202409-202609-copia.pdf` y `CCMA-Lucy-202409-202609-copia.pdf`) y vinculadas en `dbo.ArcaDocumentos` tanto a las 48 obligaciones como a los pagos por socio.
3. **Vinculación de los pagos de socios existentes (`09/2024 – 08/2026`) y clasificación histórica:**
   - Vinculados en `dbo.PagosSocioProveedor` (`IdContacto = 119`, `Criterio = 'ccma-036'`) **47 pagos por socio** existentes por **`$3.619.422,36`** (`22` de Sergio por `$2.488.573,87`, `18` de Lucy por `$822.178,61` y `7` de Lucy pagados desde la cuenta de Sergio por `$308.669,88`, que sumados a `IdMovimiento = 2160` por `$40.300,62` ya vinculado completan los 48 pagos del período por `$3.659.722,98`).
   - Los 8 pagos de Autónomos de Lucy abonados por Sergio (`2160, 2166, 2180, 2196, 2205, 2214, 2228, 2236`) quedaron clasificados en `autonomos-lucy`.
   - Clasificadas las **305 obligaciones históricas** de Autónomos (`152` en `autonomos-sergio` + `153` en `autonomos-lucy`, quedando únicamente los dos renglones de intereses menores `IdImpuesto = 373` por `$5,00` e `IdImpuesto = 930` por `$5,75` en `autonomos-pendientes`) y los **207 pagos en efectivo** de `Particular S` y `Particular L` en `autonomos-sergio`, `autonomos-lucy` y `cargas-sociales`.

### Detalle completo de 2018 para la decisión Q3 de Sergio (`IdMovimiento = 1872`, `1876` y `1885`)

Al cruzar fila por fila las hojas `Cuenta Sergio`, `Cuenta Lucy` y `Caja Efectivo Pesos` de `Cajas Giamigli.xlsx` contra `dbo.MovimientosCuentaSocio`, `dbo.Impuestos` y `dbo.vw_PagosEfectivoVigentes` entre mayo y julio de 2018, surge el siguiente mecanismo contable:

1. **Qué ocurría entre mayo y julio de 2018 (`períodos 04/2018 a 06/2018`):**
   - Sergio pagaba sus Autónomos desde su cuenta personal (`ICBC`) y Lucy desde la suya (`Supervielle`), generando un **Haber (`Devolucion`)** a favor del socio en su hoja (`Cuenta Sergio` / `Cuenta Lucy`).
   - Días después en el mismo mes, la **caja de efectivo de la empresa (`Caja Efectivo Pesos` en Excel = `Caja: La Herencia` en `Pagos efectivo` de Access)** les **reintegraba en billetes** ese mismo importe, anotando la salida en `Caja Efectivo Pesos` (y en `Pagos efectivo` hacia `AFIP`) y cargando un **Debe (`AsignacionGasto`)** por igual monto en la cuenta del socio (dejando el efecto neto en `$0,00` en la cuenta del socio).
   - A partir del período `07/2018` (agosto 2018), la caja `La Herencia` dejó de reintegrarles en efectivo: los pagos pasaron a registrarse en `Caja = 'Particular S'` / `'Particular L'` y en las cuentas de los socios quedó únicamente el **Haber (`Devolucion`)** mensual sin reintegro.

2. **Período `04/2018` (`IdImpuesto = 506` Sergio `$2.842,12` / `IdImpuesto = 505` Lucy `$1.199,02`):**
   - **En Lucy (`Cuenta Lucy` filas 6 y 7):**
     - Fila 6 (`07/05/2018`, `AFIP`, `Autonomos 04 2018`, `Supervielle`): **Haber `$1.199,02`** (`IdMovimiento = 2279`, `Devolucion`).
     - Fila 7 (`29/05/2018`, `Pago`, `Efectivo`): **Debe `$1.199,02`** (`IdMovimiento = 2280`, `AsignacionGasto`), coincidiendo con `Caja Efectivo Pesos` fila 1218 (`29/05/2018`, `Autonomos Lucy`, `-$1.199,02`, `IdPagoEfectivo = 1433`, `Caja = 'La Herencia'`). Efecto neto nominal en Lucy: **$0,00**.
   - **En Sergio (`Cuenta Sergio` filas 12 y 16) — columnas Debe/Haber invertidas en ambos asientos:**
     - Fila 12 (`07/05/2018`, `Sergio Giamberardini`, `Autonomos 04 2018`, `Pago ICBC`, `IdMovimiento = 1872`): cuando Sergio pagó por ICBC se anotó en **Debe `$2.842,12`** (`AsignacionGasto`) en lugar de Haber.
     - Fila 16 (`29/05/2018`, sin detalle, `Efectivo`, `IdMovimiento = 1876`): el día en que `Caja Efectivo Pesos` fila 1217 (`29/05/2018`, `Autonomos Sergio`, `-$2.842,12`, `IdPagoEfectivo = 1432`, `Caja = 'La Herencia'`) le reintegró el efectivo a Sergio (exactamente igual que la fila 1218 a Lucy), en `Cuenta Sergio` se anotó en **Haber `$2.842,12`** (`Devolucion`) en lugar de Debe.
     - **Consecuencia:** como **ambos** asientos (`1872` del `07/05/2018` y `1876` del `29/05/2018`) quedaron con Debe y Haber invertidos entre sí, **en pesos nominales ya se cancelan mutuamente (`-$2.842,12 + $2.842,12 = $0,00`)**, quedando únicamente una pequeña diferencia de cotización entre el `07/05/2018` (`64.6818 USD / 40.371 kg`) y el `29/05/2018` (`56.8639 USD / 38.384 kg`), es decir **`-7.8179 USD` y `-1.987 kg`**. Y en ARCA (`IdContacto = 119`), el pago de `04/2018` ya está acreditado por `IdPagoEfectivo = 1432` (`$2.842,12`).

3. **Período `05/2018` (`IdImpuesto = 539` Sergio `$2.842,12` / `IdImpuesto = 538` Lucy `$1.199,02`):**
   - Ambos socios están registrados con el signo normal:
     - Sergio pagó por ICBC el `04/06/2018` → **Haber `$2.842,12`** (`IdMovimiento = 1878`, fila 18) y recibió el reintegro de caja el `21/06/2018` → **Debe `$2.842,12`** (`IdMovimiento = 1881`, fila 21, `Motivo = 'Pago'`, `Caja Efectivo Pesos` fila 1231, `IdPagoEfectivo = 1717`).
     - Lucy pagó por Supervielle el `06/06/2018` → **Haber `$1.199,02`** (`IdMovimiento = 2281`, fila 8) y recibió el reintegro de caja el `21/06/2018` → **Debe `$1.199,02`** (`IdMovimiento = 2282`, fila 9, `Motivo = 'Pago'`, `Caja Efectivo Pesos` fila 1232, `IdPagoEfectivo = 1716`).

4. **Período `06/2018` (`IdImpuesto = 537` Sergio `$3.003,84` / `IdImpuesto = 536` Lucy `$1.267,25`) — explicación de `IdMovimiento = 1885`:**
   - Sergio pagó por ICBC el `05/07/2018` → **Haber `$3.003,84`** (`IdMovimiento = 1884`, fila 24, `"AFIP — Autonomos 06 2018"`).
   - El `24/07/2018`, `Caja Efectivo Pesos` fila 1249 registra el egreso de caja `Autonomos Sergio -$3.003,84` (reintegro en efectivo a Sergio, vinculado a `IdPagoEfectivo = 1580` en `Caja: La Herencia`), y `Cuenta Sergio` fila 25 (`IdMovimiento = 1885`) registra el correspondiente **Debe `$3.003,84`** (`24/07/2018`, `"AFIP — Autonomos 06 2018"`, `Efectivo`), mientras que en la fila inmediata siguiente (`IdMovimiento = 1886`, fila 26, y `Caja Efectivo Pesos` fila 1250) Sergio vuelve a aportar en efectivo `$16.003,84` (`$13.000 + $3.003,84`) a la caja.
   - Por lo tanto, **`IdMovimiento = 1885` está bien registrado como Debe** (es el reintegro en efectivo del Haber `1884`, igual que `1881` respecto de `1878`).

5. **Nota adicional detectada en `PagosSocioProveedor` sobre mayo/junio 2018 de Lucy (`2279` y `2281`):**
   - Los asientos `2279` (`07/05/2018`, `$1.199,02`) y `2281` (`06/06/2018`, `$1.199,02`) de Lucy habían quedado auto-vinculados por alias en `dbo.PagosSocioProveedor` hacia `IdContacto = 119`, a pesar de que esos dos meses fueron reintegrados por `Caja: La Herencia` (`2280` y `2282`) y ya están acreditados en ARCA mediante `IdPagoEfectivo = 1433` y `1716` (`Caja: La Herencia`). Por eso en la subcuenta `autonomos-lucy`esos dos meses figuran cobrados dos veces (`+$2.398,04`).

## Punto 5: aplicado en `WC` (`arca-bienes-sustitutos-planes-036`)

Con la confirmación de Sergio (**Q4**), se ejecutó `backend/scripts/arca_bienes_sustitutos_036.py --aplicar` (regla `arca-bienes-sustitutos-planes-036` en `dbo.AuditoriaCorrecciones`, respaldo verificado `WC_arca-bienes-sustitutos-036_20261025_202246_767449.bak`):

1. **15 obligaciones de planes incorporadas en `dbo.Impuestos` (`IdOrganismo = 119`, `IdTipoImpuesto = 13`) por `$1.427.555,70`:**
   - **Plan `U657364` (Bienes Sustitutos 2024):** 12 cuotas (`01 2024` a `12 2024`, vencimientos `16/07/2025` a `16/06/2026`) de **`$87.297,84`** cada una = **`$1.047.574,08`** (`IdImpuesto = 1311..1322`).
   - **Plan `W143471` (Bienes Sustitutos 2025):** 3 cuotas vencidas y debitadas hasta el corte `30/09/2026` (`01 2025` a `03 2025`, vencimientos `16/07/2026` a `16/09/2026`) de **`$126.660,54`** cada una = **`$379.981,62`** (`IdImpuesto = 1323..1325`).
2. **3 PDF oficiales de planes copiados a `ARCA/Giamigli/Bienes Sustitutos/` y vinculados en `dbo.ArcaDocumentos`:**
   - `Plan de Pagos - Bs Sustituto 2022 - Giamigli de Bolivar SA.pdf` (`T026731`), `Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf` (`U657364`) y `Plan de Pagos Bs Sustituto 2025 - GIAMIGLI DE BOLIVAR SA.pdf` (`W143471`), vinculados a sus obligaciones en `Impuestos` y a sus débitos en `Galicia`.
3. **32 débitos históricos de Galicia clasificados en `bienes-sustitutos` por `$914.443,36`:**
   - Plan `Q355709` (`8 × $15.483,08` = `$123.864,64`), Plan `R586663` (`12 × $25.630,61` = `$307.567,32`) y Plan `T026731` (`12 × $40.250,95` = `$483.011,40`).
   - **Resultado:** los 5 planes de 2022 a septiembre 2026 (`Q355709`, `R586663`, `T026731`, `U657364` y las 3 cuotas al corte de `W143471`) quedaron con **diferencia `$0,00` exacta** entre obligaciones y débitos bancarios (`$2.341.999,06` deuda = `$2.341.999,06` crédito).
   - El saldo actual de la subcuenta `bienes-sustitutos` (`-$130.735,83`) se compone exclusivamente de las obligaciones históricas 2012–2021 (`$126.956,19`, cuyos 27 pagos exactos en `Pagos efectivo`, `Banco Nacion` y `Galicia` ya existen en `IdContacto = 119` dentro de `por-identificar`) más un interés de 2019 (`IdImpuesto = 656`, `$3.779,64`).

## Estado actual de saldos por subcuenta en ARCA (`IdContacto = 119`) y próximos pasos para Claude Code / Codex / Gemini

- **Saldo contable `IdContacto = 119` (tanto al corte `30/09/2026` como total):** **`+$7.695.867,9389`** (`+$9.476.689,0789` previo `- $1.427.555,70` Bienes Sustitutos `- $3.972.687,80` obligaciones Autónomos CCMA `+ $3.619.422,36` pagos socio Autónomos CCMA).
- **Documentos registrados y verificados por SHA-256 en `dbo.ArcaDocumentos`:** **277 vínculos** en **250 movimientos** de la cuenta 119 (`24 passed` en `pytest backend/tests/test_arca_subcuentas.py`).

| Subcuenta | Deuda (`$`) | Crédito (`$`) | Saldo (`$`) | Movimientos | Estado / Pendiente |
|---|---:|---:|---:|---:|---|
| `iva` | `13.338.994,3400` | `16.737.734,1974` | `+3.398.739,8574` | 137 | Punto 2: cruzar remanente histórico (`MECON` / `SAF 363`) y definir exposición de compensaciones SCT. |
| `ganancias` | `1.756.614,0600` | `1.688.588,0300` | `-68.026,0300` | 35 | Punto 3: definir criterio de registración de DDJJ/anticipos/compensaciones SCT 2025/2026 sin duplicar gastos. |
| `sicore-ganancias` | `0,0000` | `4.153.833,4700` | `+4.153.833,4700` | 31 | Punto 3: definir exposición de obligaciones de retenciones practicadas (`IdTipoImpuesto = 20` excluido de vista) y 3 intereses pendientes (`$471,21`, `$54,58`, `$610,69`). |
| `autonomos-lucy` | `1.724.183,7300` | `1.654.365,2900` | `-69.818,4400` | 271 | Punto 4 aplicado; resta clasificar pagos históricos en efectivo de `Caja: La Herencia` (2011–2018) que están en `por-identificar` y revisar doble vínculo `2279/2281`. |
| `autonomos-sergio` | `4.100.878,3400` | `3.630.125,4000` | `-470.752,9400` | 262 | Punto 4 aplicado (`-$307.971,18` corresponde a `04/2026` y `08/2026` impagos al `30/09/2026` y pagados el `05/10/2026`; el resto a pagos históricos de `Caja: La Herencia` en `por-identificar`). Resta decisión Q3 sobre `1872`/`1876`. |
| `autonomos-pendientes` | `10,7500` | `0,0000` | `-10,7500` | 2 | Solo 2 intereses históricos menores (`IdImpuesto = 373` `$5,00` e `IdImpuesto = 930` `$5,75`). |
| `cargas-sociales` | `31.268.407,8500` | `20.671.648,7400` | `-10.596.759,1100` | 456 | Punto 1 resuelto en 2025–2026; pagos históricos de BNA/Galicia/Efectivo previos a 2025 siguen en `por-identificar`. |
| `bienes-sustitutos` | `2.472.734,8900` | `2.341.999,0600` | `-130.735,8300` | 121 | Punto 5 aplicado (2022–2026 en `$0,00`). Resta clasificar los 27 pagos históricos 2012–2021 (`$126.956,19`) desde `por-identificar`. |
| `otros-impuestos` | `654,2900` | `0,0000` | `-654,2900` | 11 | Obligaciones históricas menores. |
| `por-identificar` | `5.268.659,5000` | `16.748.711,5015` | `+11.480.052,0015` | 608 | Contiene los pagos históricos (`Banco Nacion`, `Galicia`, `Pagos efectivo` `Caja: La Herencia`) de Autónomos, Bienes Sustitutos (2012–2021), Cargas Sociales y Ganancias previos a 2025. |
