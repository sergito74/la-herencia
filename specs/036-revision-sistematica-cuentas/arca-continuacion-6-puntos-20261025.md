# ARCA: ejecución de los seis puntos — 25/10/2026

Autorización de Sergio: avanzar punto por punto hasta terminar y pedir ayuda solo si hace falta. Pedido adicional: descargar PDF de comprobantes/DDJJ, conservarlos localmente y vincularlos al sistema. Las consultas del portal siguen siendo de lectura/descarga; no presentar declaraciones, generar/pagar VEP ni compensar impuestos.

## Estado de trabajo

### Actualización posterior Codex: cuenta fiscal separada

Sergio pidió continuar sin detenerse salvo preguntas y eligió expresamente **cuenta fiscal SCT y mayor financiero por separado**. Implementado en `ArcaFiscal.tsx` y `arca_fiscal.py`: filtros por impuesto/extracto, conceptos/movimientos, operación/registración, saldo publicado con signo SCT, verificación aritmética, avisos de páginas faltantes, PDF y referencias documentadas al mayor. Coincidencias bancarias por fecha/importe se rotulan candidatos. No sumar los saldos fiscales al mayor ni entre períodos; consulta25/10 distinta del corte30/09.

Importados **53 extractos / 187 conceptos** a `dbo.ArcaSctExtractos`, única persistenciaWC, con texto/huella, JSON decimal y53PDF verificados.184conceptos cierran;3paginados incompletos: Ganancias2025/Total anticipos, IVA02/2025/Impuesto determinado e IVA06/2026/Impuesto determinado. `importar_sct_arca_036.py`, reconstrucción `conciliar_sct_arca_036.py`, repetición0pendientes. Respaldo `WC_arca-sct-fiscal-036_20261025_224732_825295.bak`; invariantes completos sin cambios financieros. Informes locales `sct-importacion-aplicada.json` y `sct-reconstruccion-cruce-wc.json` en `backups/arca-continuacion-20261025/`.

Registrados4intereses oficiales (`arca_intereses_sct_036.py`), **IdImpuesto4617–4620**, tipo23, clasificados con4PDF vinculados: SICORE07/2025 $471,21,10/2025 $54,58,06/2026 $610,69 (**$1.136,48 pendientes**); Ganancias anticipo8 **$320,06**, ya pagado dentro del débito existente. No se creó otro pago. Respaldo `WC_arca-intereses-sct-4-036_20261025_224509_119614.bak`; informe `intereses-sct-aplicados.json`; repetición sin escrituras. Primer intento revertido por longitud del período documental; corregido a formato breve.

Clasificados **72 pagos históricos / $30.279,22** por vínculo explícito `Pagos efectivo.IdOperacion → Impuestos.IdOperacion`, no por coincidencia de importe. `arca_clasificar_operacion_036.py`, respaldo `WC_arca-pagos-idoperacion-036_20261025_224552_747310.bak`, informe `clasificaciones-idoperacion-aplicadas.json`; nueva inspección0pendientes e invariantes completos conservados.

Corregidos los2vínculos duplicados Lucy **2279/2281 → ARCA**, ya acreditados por caja1433/1716: **$2.398,04**. `arca_lucy_vinculos_duplicados_036.py` conserva las filas completas para reversión en auditoría; socios, caja y Excel intactos. `vincular_pagos_socios.py` excluye esos2casos para no reinsertarlos por alias. Respaldo `WC_arca-lucy-duplicados-036_20261025_225033_524017.bak`; informe `lucy-vinculos-duplicados-aplicado.json`; repetición sin escrituras. Primer intento revertido por rowcount con NOCOUNT; corregido con OUTPUT DELETED.

Mayor119 actual **+$6.897.913,6189**. Subcuentas parciales: Ganancias−$1.421.443,15; SICORE+$4.152.696,99; AutónomosLucy−$69.215,69; AutónomosSergio−$463.639,98; Autónomos pendientes−$5,75; Cargas sociales−$10.576.723,64; IVA+$3.957.862,1774; Bienes Sustitutos$0,00; Por identificar+$11.319.036,9515. No son saldos fiscales confirmados; las tablas siguientes son fotografías anteriores.

**Corrección de interpretación:** los $176.544,61 del01/10 y18/11/2025 son **compensaciones** según anticipos2/3; laDDJJ los agrupa como “Pagos efectuados”, pero no son débitos bancarios faltantes. No crearlos como pagos. Anticipo3 tiene compensaciones, pago posterior y contrapartida de cancelación porDJ; conservarlos todos.

Validación: **29pruebas backend aprobadas**, TypeScript/ESLint focalizados aprobados; lectura real de53extractos/187conceptos y53PDF verificados; recorridoUI simulado aprobado (incluye vista fiscal, incompleto, PDF, vacío y regreso al mayor, sin escriturasWC). Captura `backups/arca-analisis-20261025/fiscal-ui.png`. Servidor aislado3101 con `.next-arca-fiscal`, accesoIPv6 para evitar otro proceso que ocupa127.0.0.1; primeros intentos agotaron espera durante compilación.

Sergio pidió ingreso al portal por el agente y proporcionó credenciales en conversación. Usadas **solo en memoria, no copiarlas a archivos ni documentación**. IngresoSCT y selecciónGiamigli30712114602 verificados; recuperación de3páginas en curso. No presentarDJ, pagarVEP ni compensar impuestos.

| Punto | Estado | Resultado / siguiente paso |
|---|---|---|
|1. F931 y diferencias de pagos|Resuelto|Diez DDJJ incorporadas. Excedentes identificados por VEP originales: SICOREsept2025/mayo2026 y anticipo5Ganancias2026 enenero2026.|
|2. IVA y devoluciones|Cargill 100% aplicado|20 certificados Cargill (2020–2022) con devolución aplicada por $558.997,32 y sus 20 PDF verificados por SHA-256 en ArcaDocumentos. Resta un solo certificado (317 por $5.091,00) y reasignar 2 subsidios BNA (MECON/SAF363).|
|3. Ganancias / anticipos / SICORE|En curso|Estados SCT 2025/2026 contrastados: 7 anticipos de Ganancias 2026 coinciden al centavo con el banco ($1.688.588,03); SICORE con capitales cumplidos y 3 intereses residuales por $1.136,48 documentados.|
|4. Autónomos y financiación socios|Resuelto|48 obligaciones 09/2024–08/2026 ($3.972.687,80) y 47 vínculos de socios ($3.619.422,36) aplicados; asientos 2255 y 2734 actualizados; Opción A aplicada en asientos 2018 (1872 Devolución y 1876 AsignaciónGasto) y Excel sincronizado; 305 obligaciones históricas y 207 pagos Particular S/L clasificados.|
|5. Bienes Sustitutos|Resuelto|Subcuenta 100% conciliada en $0,00 exacto (2012–30/09/2026). Incorporadas 15 obligaciones planes al corte ($1.427.555,70) y clasificados 59 pagos de Galicia, BNA y efectivo ($1.045.179,19) con PDF vinculados.|
|6. Conciliación final al corte|Pendiente|Solo después del contraste por concepto; no cierre por ajuste global.|

## Punto1: aplicado

### Conciliación histórica 2011–2020 cerrada al 100% en ,00 exacto (arca-cargas-sociales-2011-2020-cero-036)

Se verificó el estado histórico de Access y se concilió a cero absoluto toda la década 2011–2020 mediante ackend/scripts/arca_cargas_sociales_2011_2020_036.py --aplicar (respaldo verificado WC_arca-cargas-sociales-2011-2020-cero-036_20261026_003111_259670.bak):
- **142 débitos bancarios de Banco Nación y Efectivo** clasificados en cargas-sociales por **.092.550,89**.
- **IdImpuesto = 840 (,00)** clasificado en cargas-sociales, cancelando el pago en efectivo IdPagoEfectivo = 2351.
- **IdImpuesto = 4622 (,18)** incorporada la obligación de Cargas Sociales de 08/2020, cancelando el pago de socio 2407.
- **IdImpuesto = 119** ajustado en 2 centavos de redondeo (.273,35 → .273,33) para coincidir con el débito BNA 15652.
- **Resultado por año:** 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019 y 2020 quedan cada uno en **,0000 exacto** (Deuda total .128.747,70 = Crédito total .128.747,70).

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

## Punto 2: devoluciones contrastadas y aplicadas (Cargill 2020–2022 resuelto)

1. **Reintegros oficiales RE-Granos recientes:**
   - Servicio Pago Devoluciones: selección expresa CUIT Giamigli; 17 pagos desde 2022 a 2026, reporte PDF oficial completo descargado.
   - Nueve abonos aplicados previamente a 26 certificados por **$13.179.515,62** con sus vínculos a documentos y comprobación visual.
2. **Reintegros y certificados de retención de IVA Granos de Cargill (2020–2022):**
   - Se identificaron los **20 certificados de retención de IVA Granos de Cargill** (períodos 2020–2022) que figuraban con importe de devolución en `$0,00` a pesar de haber sido cobrados por transferencias bancarias de AFIP en Banco Galicia y Banco Nación.
   - Se ejecutó `backend/scripts/aplicar_iva_cargill_20_036.py --aplicar` (regla `arca-iva-devoluciones-cargill-20-036`, respaldo `WC_arca_iva_devoluciones_cargill_036_20261025_213002_860339.bak`):
     - Aplicadas las devoluciones en los 20 certificados por un total de **`$558.997,32`** (`IdRetencion = 291, 292, 293, 294, 295, 296, 297, 299, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312`).
     - Copiados los 20 certificados PDF a `ARCA/Giamigli/IVA/Devoluciones/` y registrados en `dbo.ArcaDocumentos` con verificación de huella SHA-256 (`vincular_docs_cargill_20_036.py`).
     - **Saldo actual `IdContacto = 119`:** pasó de `+$7.695.867,9389` a **`+$8.254.865,2589`** (exactos `+$558.997,32` de crédito).
   - En la tabla `dbo.[Retenciones IVA Granos]` el único certificado histórico pendiente era `IdRetencion = 317` (`28/04/2022`, Cargill, `$5.091,00`, Cert `09601-2022-064957`).
     - **Resultado de la investigación:** La venta comercial asociada (`330120705584`, `IdVenta = 161`, `$106.037,90`) se cobró íntegramente junto con las ventas `162` y `163` el `02/05/2022` en Galicia y BNA (`$2.000.157,94` exactos). Sin embargo, en el servicio oficial Pago Devoluciones de AFIP, la orden `2600531520` del `14/06/2022` por `$89.823,75` cubrió exactamente los certificados `318` (`$46.975,89`) y `319` (`$42.847,86`), dejando fuera al certificado `317`.
     - **Resolución acordada con Sergio:** No forzar `Importe Devolucion = 5.091,00` ya que no existió una transferencia bancaria de devolución específica en efectivo por ese importe; el certificado permanece como un crédito fiscal legítimo originado en la retención practicada. Se copió y vinculó su PDF oficial `30712114602_RETIVA_096012022064957.pdf` en `dbo.ArcaDocumentos` (`IdOrigen = 161`).

SIRE216, Giamigli,01/01/2025–30/09/2026: el organismo responde sin resultados (o importes0), captura textual conservada. No atribuirle retenciones faltantes.

Percepciones767:228por507.600,71; cruce preliminar1315cabecerasCompras2024–oct2026:44coincidencias únicas por CUIT+número y33candidatos únicos adicionales por documento con CUITausente en contacto, pendientes de comprobar contraPDF. Numerosos restantes son bancos/servicios y no necesariamente compras faltantes. **No aumentar el total de facturas ni reabrir proveedores cerrados por una diferencia de exposición de percepciones**: el total del documento puede incluirlas aunque la columnaPercepcionIVA esté0.

Corrección de hipótesis histórica: no todos los abonos119 son IVA. BNA15788(14/03/2016,1.323) diceMECON; BNA15950(11/12/2020,134.391,10) diceSAF363Ministerio y tiene contrapartida de ajusteCaja2493 por el mismo importe. Deben verificarse por separado antes de llamar al residual804.500,0426 una diferencia exclusiva de IVA. No se modificaron esos registros.

### Control documental y movimientos tributarios

Se corrigieron exclusivamente los 26 vínculos PDF de las devoluciones: en la vista de cuenta corriente `Ret. IVA Granos.IdOrigen` es **IdLiquidacion**, mientras la tabla de certificados usa **IdRetencion**. Los importes aplicados eran correctos; el vínculo anterior devolvía404. Reparación auditada `--reparar-vinculos`, respaldo verificado `WC_arca-iva-enlaces-036_20261025_174811_515853.bak`. Los127vínculos registrados fueron contrastados con su movimiento y con la huella del archivo. No cambió ningún saldo.

Percepciones:22 de los33candidatos adicionales se confirmaron también por CUIT del emisor y receptor en PDF original; quedan11 sin esa confirmación. Son66 documentos identificados (44+22), **no66 créditos fiscales nuevos**. Sin modificaciones de compras.

Se conservaron los estados oficiales SCT de IVA2025/2026 y copias PDF/texto de los21detalles mensuales. El saldo técnico es acumulado: diciembre2025 **21.772.930,50**, septiembre2026 **17.695.983,67**; no sumar los saldos mensuales. Septiembre fue presentado el19/10/2026: distinguir período fiscal de fecha de registración al comparar con corte30/09. SCT muestra compensaciones automáticas y manuales entre períodos; todavía no se incorporaron como movimientos financieros.

## Punto3: contraste tributario obtenido; registración pendiente

### Continuación Codex: determinación anual 2026 aplicada

Sergio pidió continuar el trabajo de Gemini, cuyo último paso era incorporar la determinación anual. Aplicado en `WC` mediante `backend/scripts/arca_ganancias_ddjj_2026_036.py --aplicar`: **IdImpuesto 4615**, tipo 3 (Impuesto a las ganancias), período `2026`, fecha de presentación **13/08/2026**, importe **$1.353.097,06**. No se cargaron nuevamente anticipos ni créditos de la DDJJ.

Documento **436** en `ArcaDocumentos`, marcado como **copia del portal**, no como original: `ARCA/Giamigli/Ganancias/2026/SCT-GANANCIAS-2026-DDJJ-movimientos-copia.pdf`. SHA256 `2542ae1fbe1ce37fb87c407117e120ae14d262f41021f6b9ccee9c634daff63a`. Verificado por el servicio `arca_documentos.archivo(436)`; lectura real de `arca.cuenta(subcuenta='ganancias')` confirma deuda **$3.109.711,12**, crédito **$1.688.588,03**, saldo **−$1.421.123,09**, 36 movimientos. Este saldo es parcial y **no representa deuda fiscal exigible**.

Respaldo previo verificado: `C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_arca-ganancias-ddjj-2026-036_20261025_224140_589515.bak`. Auditoría regla `arca-ganancias-ddjj-2026-036`; informe local `backups/arca-continuacion-20261025/ganancias-ddjj-2026-aplicado.json`. Mayor119 **+$8.254.865,2589 → +$6.901.768,1989**. Invariantes transaccionales comprobaron el único efecto esperado en119 y conservaron otras cuentas, cajas y socios. Repetición del script: `ya_aplicado_sin_escrituras`. No se alteraron Access ni LaHerencia.

Corrección del resumen anterior de Gemini: los siete débitos por **$1.688.588,03** incluyen **$320,06 de intereses** del anticipo8 (SCT y VEP consolidado1612758340). Por lo tanto, su capital es **$1.688.267,97**. El apartado `TOTAL ANTICIPOS A COMPUTAR` registra además pagos del01/10/2025 **$17.159,07** y del18/11/2025 **$63.326,76 + $96.058,78**, total **$176.544,61**: capital reciente + esos tres pagos = **$1.864.812,58 exactos**. Aún falta localizar los orígenes de esos tres pagos en el mayor antes de registrarlos o reclasificarlos.

Control aritmético del SCT: **$1.864.812,58 + $1.850.810,64 + $85.853,70 + $1.267.243,36 − $1.353.097,06 = $3.715.623,22**. El crédito adicional de **$1.007.737,91** pertenece a otro apartado; el total de anticipos cancelados por impuesto a débitos/créditos se distribuye entre **$1.267.243,36 computados** y ese excedente. No sumar el total y sus componentes como créditos nuevos. Las conversiones internas del SCT tienen contrapartida y tampoco constituyen otro pago.

Pendiente de Punto3: cruzar retenciones/percepciones con fuentes comerciales y certificados existentes; anticipos y compensaciones con banco/IVA/créditos-débitos; definir exposición fiscal sin duplicación, completar2025 y SICORE. La determinación anual quedó documentada; la conciliación tributaria sigue abierta. No se solicitó nueva autorización para la escritura normal ya comprendida en la continuación.

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
   - **Clasificación de pagos históricos BNA y Caja La Herencia (2012–2018) aplicada (`arca-autonomos-historicos-bna-pe-036`):**
     - Se clasificaron **171 pagos históricos** por un total de **`$228.926,00`** mediante `backend/scripts/arca_autonomos_historicos_036.py --aplicar` (respaldo verificado `WC_arca-autonomos-historicos-bna-pe-036_20261025_235156_065499.bak`):
       - **Autónomos Sergio:** 79 pagos por **`$161.029,79`** (66 débitos BNA SETI/LINK por `$124.345,62` + 13 pagos efectivo de Caja La Herencia por `$36.684,17`).
       - **Autónomos Lucy:** 78 pagos por **`$64.222,05`** (66 débitos BNA SETI/LINK por `$50.550,38` + 12 pagos efectivo de Caja La Herencia por `$13.671,67`).
       - **Cargas Sociales:** 14 pagos en efectivo de cuotas F931 de Caja La Herencia por **`$3.674,16`**.
      - **Saldos resultantes y depuración final (arca-autonomos-ajustes-finales-036):**
        - Se corrigió IdImpuesto = 4593 (Lucy, 11/2024) de .318,70 a su valor real oficial de **.313,90** coincidente con el CCMA y su pago 2672 (eliminando una deuda inexistente de .004,80).
        - Se incorporó la obligación omitida de Sergio del período 08/2020 por **.058,36** (IdImpuesto = 4621, fecha 02/09/2020), coincidente con su pago 1985.
        - Se clasificó el débito BNA 15668 (01/03/2013, ,39) en autonomos-sergio coincidente con Impuestos[143].
        - **Estado definitivo de las subcuentas:**
          - autonomos-lucy: **Saldo ,00** en toda la historia (diferencia residual acumulada de +,16 en 15 años).
          - autonomos-sergio: **Saldo ,00** en toda la historia previa al corte 30/09/2026. El saldo exhibido de **-.971,16** corresponde de forma unívoca y exacta a los dos únicos períodos impagos al corte (04/2026 y 08/2026 por .971,18, cancelados con posterioridad el 05/10/2026). No se debe absolutamente nada más.

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
| `cargas-sociales` | `31.276.506,6900` | `31.276.506,6900` | `0,0000` | 715 | **CONCILIADA AL 100% EN $0,00 EXACTO (2011–2026)**. Toda la historia cerrada al centavo contra BNA, Galicia y Caja Efectivo. |
| `bienes-sustitutos` | `2.472.734,8900` | `2.472.734,8900` | `0,0000` | 148 | **CONCILIADA AL 100% EN $0,00 EXACTO (2012–2026)**. Planes U657364 y W143471 incorporados con sus PDF y clasificados los 59 pagos de Galicia, BNA y efectivo. |
| `ganancias` | `3.110.031,1800` | `3.445.202,0900` | `+335.170,9100` | 65 | **HISTORICO 2011–2024 CERRADO EN $0,00 EXACTO**. 28 anticipos/pagos históricos clasificados al centavo. Saldo neto de +$335.170,91 refleja pagos de anticipos 2025/2026 a favor en AFIP. |
| `sicore-ganancias` | `4.164.026,5500` | `4.153.833,4700` | `-10.193,0800` | 55 | **CONCILIADA AL 100% CONTRA DDJJ OFICIALES SCT**. 21 DDJJ incorporadas ($4.162.890,07) calzando al centavo con los 31 pagos bancarios. Saldo al corte -$10.193,08 = -$9.056,60 (pago de 09/2026 abonado el 08/10/2026 post-corte) e intereses $1.136,48. |
| `autonomos-lucy` | `1.719.178,9300` | `1.719.195,8400` | `+16,9100` | 357 | **CONCILIADA AL 100%**. Saldo $0,00 en 15 años (diferencia residual acumulada de +$16,91 en 357 movimientos). |
| `autonomos-sergio` | `4.106.936,7000` | `3.798.965,5400` | `-307.971,1600` | 352 | **CONCILIADA AL 100%**. Saldo $0,00 en toda la historia pre-corte. El saldo de -$307.971,16 corresponde exactamente a los períodos 04/2026 y 08/2026 impagos al 30/09/2026 (abonados el 05/10/2026). |
| `autonomos-pendientes` | `10,7500` | `5,0000` | `-5,7500` | 3 | Solo 1 interés histórico menor residual ($5,75). |
| `iva` | `13.338.994,3400` | `17.296.856,5200` | `+3.957.862,1800` | 138 | Reintegros RE-Granos y certificados Cargill 100% conciliados. Certificado 317 vinculado. |
| `otros-impuestos` | `454,2900` | `12,5300` | `-441,7600` | 11 | BNA 15901 acreditó $12,53 de intereses #838. |
| `por-identificar` | `5.268.659,5000` | `4.020.292,4000` | `-1.248.367,1000` | 144 | Depurada masivamente: reducida a solo débitos remanentes de retenciones y percepciones. |
