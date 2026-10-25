# Continuación ampliada de pendientes — 24/10/2026

Sergio pidió no detenerse mientras se pueda avanzar sin su intervención. Se continúa con fuentes locales yWC; no volver a preguntar datos ya confirmados.

## Corrección de control de aplicaciones (aplicada)
La auditoría137 consultaba OrigenMovimiento='PagosEfectivo', pero AplicacionesPago usa 'efectivo'. La afirmación anterior de que no existían aplicaciones activas era incorrecta. Se informó aSergio, se corrigió elscript para consultar y fotografiar el origen real y se revisaron todas las aplicaciones de10 pagos.

Aplicado corregir_aplicaciones_diez_centavos_036.py:8 aplicaciones anuladas (5 cruces de centavos a facturas siguientes y3 aplicaciones superiores al banco),3 reemplazos;7 aplicaciones correctas conservadas. Queda1 aplicación por pago, a su propia factura, importe mínimo entre total fiscal y débito bancario. Los componentes documentales siguen en AjustesCuentaCorriente; no se atribuyen a caja o socio. Los4 vueltos no se aplican a otras facturas. Sin cambios en pagos/facturas/saldos de contactos/cajas/socios. Respaldo WC_aplicaciones_diez_centavos_036_20261024_120703_092630.bak; snapshot backups/condominio-15-medios-036/aplicaciones-diez-centavos-20261024-120704.json. Repetición sin escrituras. Esta corrección sustituye expresamente la afirmación de ausencia de aplicaciones del informe anterior.

## Fuentes nuevas, investigación en curso

Movimientos Condominios.xlsx/Gastos Campo identificaCondominio en6 pagos:177fila513;331fila738;360fila813;441fila1002;442fila1009;467fila1057. Copia Gastos Campo85/86/90 repite441/442/467: copias, no operaciones nuevas. Esto corrobora el registro histórico del financiador, no acredita por sí solo ausencia de reintegro ni sustituye recibo externo. Evidencia privados efectivos-fuentes-ampliadas.json.

Extracto Banco del mismo archivo identifica los5 candidatos14/40/362/530/660 como CombustibleCampo/Giamigli, con operación bancaria explícita:095313,103113,136332,129042,174398. Filas18,185,958,1134,1787; impuestos asociados y promoción de14fila17 separados. LosPDF HSBC coinciden con esos débitos. Los tickets dicenEfectivo: conservar contradicción. Además40:ticket efectivo173,74 frente banco173,75 (no coincide tampoco cobro exacto). No extender automáticamente la corrección deVisa a esos5. Evidencia contradicciones-clasificacion-banco.json.

Cheque2968 de07/03/2012 identificado: Movs386 número87678103; AportesCampo9; Maignal/Pagos Venta Camion.xlsx/Cheques3os12 indica DepósitoNación, Macro2968. BNA10327,07/03/2012,depósito2968 existe, contacto0. Es candidato muy respaldado para atribución549, todavía sin modificar banco/socio; comprobar no duplicación y conservar aporte fuente ya incluido. Cheque2926/87678128: MaignalCheques3os8 confirma origen pero Destino vacío; no resuelve el recibo/endoso.

Relevadas todas las hojas de Movimientos LSC desde Abr2016.xlsm (hastaOct26), MovimientosCondominios yMovimientosLSC. Evidencia reconstruccion-2016-2026-fuentes.json. CajaEfectivo deXLSM trae aportes2023–2026 y operaciones anteriores (retiro13645,84/20-04-2016, gastos bancarios490,15/26-04-2016 y cobrosmotosierra2203,85/2204); revisar contra las31 relaciones operativas y41 asientos sin importar gastos propios. Dos discrepancias de fecha visibles en fuente: aporte300000 deabril2024 figura10/04 allí y11/04 en hojaCuentaCond; fila1107 de400000 tiene año2024 dentro de tramo2025. No corregir por posición de fila sin corroboración.

Easy/Coop: revisados originales de nuevo. Coop recibeTarjeta2253,03 y vuelto0,00; pagoWC2253,04 incorrecto por0,01. Easy cobraTarjeta1362 y devuelve0,46,totalfiscal1361,54. TitularLucy/sin reintegro confirmado. PagoCoop503 tiene7 aplicacionesFIFO, su factura recibe tambiénBNA14405 por1317,93: reconstruir cadena antes de duplicar imputación. Easy561 tiene aplicación21107 a su propia factura1250,97. No trasladar el nombrePagosEfectivo al campoOrigenMovimiento: cada tabla usa su catálogo. **Actualización (Claude, 24/10):** la corrección SÍ quedó aplicada por `lucy_completar_easy_cooperativa_036.py` (regla `lucy-importes-fiscales-easy-coop-036`, respaldo `WC_lucy_easy_coop_importes_036_20261024_121141_106910.bak`, informe `backups/condominio-15-medios-036/lucy-easy-coop-20261024-121142.json`): pagos 503=2253,03 y 561=1361,54, créditos Lucy reemplazados por el importe fiscal, aplicación a la factura propia, y la aplicación BNA 12052 por 1317,93 anulada (queda disponible, no es deuda nueva). Repetición: `ya_aplicado_sin_escrituras`.


## Aportes BNA de la planilla atribuidos al Condominio — aplicado (Claude, 24/10)

Ejecutado el paso pendiente de la matriz («54 depósitos/transferencias según referencia: banco candidato, no todos atribuidos»), con la decisión ya registrada de Sergio: el universo de $733.781 de `Aportes de Capital Directores.xlsx / Depositos 1` son aportes del Condominio.

Script `backend/scripts/atribuir_aportes_bna_condominio_036.py` (inspección por defecto, `--aplicar` con respaldo). Regla: por cada fila de la planilla (salvo efectivo, cheque de avena a Torrontegui y préstamo/devolución 2016), un crédito en Movimientos BNA de **importe exacto** entre la fecha de la fila y +3 días, **candidato único**, sin contacto y sin aplicaciones, conciliaciones, traspasos ni reasignaciones. Valida que la planilla siga sumando 733.781 y guarda su SHA256.

- **35 atribuidos a 549 por $428.698** (regla `condominio-aportes-bna-sistematico-036`, respaldo `WC_condominio_aportes_bna_sistematico_036_20261024_122731_875246.bak`, informe `backups/condominio-ef-2011-2016-036/aportes-bna-sistematico-20261024-122732.json`): 25 cheques de la venta del camión a Maignal («DEP. CH. 48 HS»; incluye los cuatro de $2.968 — cheques Macro 87678102-105 —, entre ellos el 2968 del 07/03/2012 = BNA 10327), 5 transferencias «BCA.E.TR» y 9 transferencias Citi «TRANSF. INTERBANCARIAS» 2014-2015. Concepto bancario coherente en todos.
- Saldo nominal del contacto 549: −$296.987,50 → **−$725.685,50** (más crédito a favor del Condominio, exacto por el importe atribuido). Repetición: 49 ya atribuidos, 0 escrituras.
- No se superponen con los 13 depósitos en efectivo «no identificados» ($211.716,52); esa lista sigue igual.
- **Sin candidato (no tocados):** 3 cheques de $3.134 (04/10, 08/11 y 06/12/2012) sin depósito en BNA; el depósito de $15.000 «Sucursal Pacheco» del 06/02/2013 coincide con BNA 10790 del 04/02/2013, ya atribuido a 549 (probable misma operación con fecha distinta; no se duplicó).
- No se crearon caja, asientos de socio 3 ni kg/US$: la cuenta del socio 3 sigue pendiente de la matriz única (no sumar estos depósitos otra vez como aportes).

## Cinco tickets «Efectivo» con débito HSBC — aplicado (Claude, 24/10)

Decisión de Sergio (24/10): **vale el extracto bancario**; los cinco tickets de combustible 14, 40, 362, 530 y 660 se pagaron con la tarjeta de débito del HSBC del Condominio (el «Efectivo» del ticket es error de la estación). Script `backend/scripts/conciliar_cinco_debitos_efectivo_036.py`, mismo tratamiento que los diez débitos con centavos: medio 3→10 e importe = débito HSBC (operaciones 095313, 103113, 136332, 129042, 174398 del Extracto Banco), componente documental 036-CENT-P{id} en AjustesCuentaCorriente por la diferencia con la factura (14: +0,01; 40: +0,02; 362 y 530: −0,01; 660: sin componente, el pago pasa de 510,12 a 510,13 = factura), 10 filas de caja Giamigli (egreso + puente) anuladas con nota, y una sola aplicación a la factura propia (se anulan los cruces de 0,02 y 0,03 de los pagos 530 y 660). Regla `condominio-cinco-debitos-ticket-efectivo-036`, respaldo `WC_condominio_cinco_debitos_036_20261024_123313_955373.bak`, informe `backups/condominio-15-medios-036/cinco-debitos-20261024-123315.json`. Cajas y socios intactos; solo se mueven los proveedores de esos pagos por los centavos de factura. Repetición sin escrituras.

## Historia 2011–2016 de la cuenta de socio del Condominio (socio 3) — aplicado (Claude, 24/10)

Decisión de Sergio (24/10): «Sí, cargar en socio 3», valuada como Sergio y Lucy (antes del 16/03/2020: 100% US$ al dólar BNA billete de la fecha). Script `backend/scripts/socio3_historia_condominio_036.py` sobre la matriz única (`matriz_financiacion_condominio_036.run`), cada operación una sola vez:

| Grupo | Asientos | Importe |
|---|---:|---:|
| A. Planilla «Depositos 1» (aportes; préstamo 2016 al Haber y su devolución al Debe) | 61 | neto $733.781 |
| B. Pagos directos del Condominio por Giamigli (Movs «Compra Giamigli» EF) | 101 | $102.423,01 |
| **Total neto a favor del Condominio** | **162** | **$836.204,01** |

Excluidos de B: pago 290 (cheque de la avena = fila 14 de A) y los pagados por Lucy sin reintegro (315 Naldo, 503 Cooperativa, 561 Easy; Sodimac 88 no está entre los 105). Las dos filas Movs 1709/1919 sin pago único son Cooperativa y Easy (importes corregidos), también de Lucy. Origen `CondominioHist036`; IdOrigen negativo = fila de la planilla, positivo = IdPagoEfectivo. Regla `socio3-historia-condominio-2011-2016-036`, respaldo `WC_socio3_historia_condominio_036_20261024_123457_272588.bak`, informe `backups/condominio-15-medios-036/socio3-historia-20261024-123457.json`. Otros socios intactos.

**Error de signo corregido en el momento:** en `MovimientosCuentaSocio` el US$ y los kg se guardan siempre **positivos** y el Tipo (Devolucion/AsignacionGasto) da el signo. La primera carga guardó el US$ de los 161 Haber en negativo (el saldo salía al revés); se corrigió con `ABS` sobre esas 161 filas y se arregló el mismo error en `cuentas_socios.repository._insert_asiento` (asientos manuales del 23/10, sin filas cargadas todavía) y en su prueba.

Socio 3 resultante (203 movimientos): saldo nominal −$5.656.204,01; **US$ −131.927,68 y −1.228,86 kg** a favor del Condominio; deuda actualizada al 21/10/2026 (INMAG 3.926,16, dólar 1.520): **−$205.354.786,61** a favor. La cuenta corriente del contacto 549 (−$725.685,50, lado bancario) no se tocó: igual que Sergio 375/5670, contacto y socio son dos vistas del mismo hecho.

**Para que Sergio revise:** la valuación 100% US$ de 2011–2016 multiplica mucho el peso de esos aportes en pesos de hoy (US$129.432 de aportes ≈ $197 millones). Es la regla vigente de 036 para todas las cuentas de socios, pero conviene que la vea antes de usar el saldo.

## Tramo 2016–2026 del socio 3: diferencias que necesitan a Sergio (Claude, 24/10, sin aplicar)

Comparados los 31 movimientos operativos de la caja Condominio con Giamigli contra los 41 asientos del socio 3 (2023–2026). Los aportes mensuales en efectivo coinciden uno a uno, salvo:

1. **Mismo pago con año distinto:** caja 3224 $400.000 del 11/09/**2024** ↔ socio 2794 $400.000 del 12/09/**2025** (Codex ya había marcado la fila 1107 de la planilla con año 2024 dentro del tramo 2025). Probablemente la caja tiene el año mal; no se corrigió sin confirmación.
2. **«Pago Balance Giamigli»:** caja 3225 $1.456.200 del 10/09/2025 sin asiento en socio 3; socio 2781 $811.100 del 14/09/2024 (repartido como retiros de Lucy, Ceci y Sergio por $270.366,67 c/u) sin movimiento en la caja. ¿Son dos balances distintos (2024 y 2025) y falta cargar el de 2025 en el socio, o es el mismo con importes/fechas distintos?
3. **2016, seis movimientos de la caja Condominio sin asiento en socio 3:** retiro Giamigli $13.645,84 y honorarios Criado $3.818 (20/04/2016), gastos bancarios Giamigli +$490,15 (26/04/2016), cobro de cuotas 1/6 y 2/6 de motosierra de Giamigli +$2.203,85 y +$2.204 (27/06 y 20/07/2016). Los egresos serían aportes (Haber) y los ingresos dinero de Giamigli retenido por el Condominio (Debe), pero el retiro de $13.645,84 cae el mismo día que la devolución del préstamo de $10.000 (fila 62 de la planilla, ya cargada) y puede estar relacionado.

Pendientes que siguen del bloque Condominio: los 3 cheques de $3.134 (2012) sin depósito en BNA; AFIP junio 2011 ($95) sin boleta; recibo/endoso del cheque 2926 a Jáuregui y Morales; original sindical 04/2014 (pago 581); los 13 depósitos BNA en efectivo y el remanente de caja de $144.350,52 siguen no identificados.

## Cuenta de socio = cuenta oficial; el contacto solo marca el banco (Sergio, 24/10)

Sergio: «no confundamos cajas con cuentas corrientes». Criterio aplicado en el sistema:
- La **cuenta de socio** (Finanzas → Cajas y socios) es la única cuenta oficial de cada socio, valuada en US$/kg.
- El **contacto** del socio (Sergio 5670, Lucy 390, Condominio 549, Ceci = Virginia 564) solo identifica de quién es un movimiento de banco o un pago. En Cuentas corrientes su saldo se muestra como «Saldo nominal (no es deuda del socio)», con aviso y enlace a la cuenta de socio; en el listado de saldos llevan la marca «socio». 375 sigue siendo Sergio empleado (solo sueldos).
- Vínculo en `backend/src/features/cuentas_socios/contactos.py` (`SOCIO_CONTACTO`), endpoints `GET /api/cuentas-socios/contactos` y `GET /api/cuentas-socios/{id}/control-banco`.
- **Control con el banco** en la cuenta de cada socio: movimientos de banco del contacto sin asiento (mismo importe, ±5 días). Estado al 24/10: Condominio 52 de 55 (sin asiento: 18635 −$4.134 «cobrado por caja» impuestos del Condominio, 10348 $5.971,50 y 11240 $10.000, ya marcados por Codex); Sergio 35 de 44 (9 sin asiento, $3.130.360); Lucy 44 de 58 (14 sin asiento, $2.925.804,15). Esos 23 movimientos son la próxima revisión del bloque socios.

## Revisión caso a caso del control banco ↔ cuenta de socio (24/10, con Sergio)

- Duplicado propio anulado: asiento 3142 (socio 3, «Sergio — Retiro por aporte pago balance» 2025) — la parte de Sergio ya estaba en su cuenta (2966, Cuenta Sergio fila 346 / P31).
- Galicia 2782 ya estaba reasignada a 5670 desde el 22/10 (el 375 que mostraba era el contacto original del extracto).
- 01/08/2022 $400.000: lote del servicio de haberes repartido por el banco en $200.000 a Sergio y $200.000 a Lucy (extractos personales Galicia de ambos, «Honorarios de profesionales» 01-08); planilla: una «Devolución por aporte pagos varios» de $200.000 en cada cuenta, ya cargadas.
- El control ahora reconoce: (a) transferencias repartidas en 2–3 asientos del mismo día, del socio, de otro socio o «<socio> — …» en la cuenta del Condominio (importe exacto); (b) pases banco → caja Giamigli («Aporte Efectivo» del mismo importe ±2 días: sin efecto en la cuenta de socio); (c) retiros de ganancias explicados al reasignar. Sergio: 44 de 44 explicados. Ceci 5 de 5. Lucy: 6 sin explicar. Condominio: 3 (conocidos).
- **Pago de balance 2025 — evidencia:** caja Condominio 3225 «Pago Balance Giamigli» −$1.456.200 (10/09/2025) = 3 × $485.400; ese día Giamigli transfirió $485.400 a Sergio («Reembolso gastos»), Lucy («Gastos de representación») y Ceci («Pago a proveedores recibido»), según los extractos personales. La caja de ahorro en pesos de Sergio en Galicia no tiene ninguna extracción en efectivo en 2025 (12 resúmenes revisados). Mismo mecanismo que el balance 2024 (reasignación 2182: «el pago a Criado fue en efectivo desde la caja Condominio»; tres transferencias de $270.360). La explicación del 22/10 para P31 («compensación por gastos pagados desde su cuenta personal») no se sostiene con esta evidencia. Propuesta pendiente de OK: tratar 2025 como 2024 (todo en la cuenta del Condominio) y anular 2966 en la cuenta de Sergio.

### Lotes de «Servicio acreditamiento de haberes» Galicia — verificado con resúmenes (24/10)

| Fecha | Resumen Galicia Giamigli (Dropbox/Giamigli de Bolivar SA/Bancos/Galicia/Extractos/2022) | Caja de ahorro Sergio | Caja de ahorro Lucy |
|---|---|---|---|
| 26/05/2022 | `CUIT_30712114602_31-5-2022.pdf`: SERVICIO ACREDITAMIENTO DE HABERES 200.000,00 — lote 0129254801 — HONORARIOS PROFESION | `…30-05-2022 - Sergio.pdf`: HONORARIOS DE PROFESIONALES 100.000,00 — GIAMIGLI DE BOLIVAR 30712114602 | `…19-08-2022 - Galicia Lucy.pdf`: HONORARIOS DE PROFESIONALES 100.000,00 — GIAMIGLI DE BOLIVAR 30712114602 |
| 01/08/2022 | `CUIT_30712114602_31-8-2022.pdf`: 400.000,00 — lote 0134501146 — HONORARIOS PROFESION | `…05-09-2022 - Sergio.pdf`: 200.000,00 — GIAMIGLI DE BOLIVAR 30712114602 | `…19-08-2022 - Galicia Lucy.pdf`: 200.000,00 — GIAMIGLI DE BOLIVAR 30712114602 |

Un débito por lote en la cuenta de la empresa; un crédito por beneficiario con el ordenante Giamigli. Lote de un solo beneficiario como control: 31/05/2022 $125.000, lote 0129241695 «ACRED.HABERES», solo en la cuenta de Sergio. (Extractos personales en `Documents/Estudio Contable/DDJJ Fisicas 2022/`.)

### Lucy, caso a caso (25/10, con Sergio)
- 19/11/2021 lote Galicia 302 $150.150 = Sergio 75.070 + Lucy 75.080 (extractos personales nov-2021), depositados en caja Giamigli como «Aporte Efectivo» el mismo día: se agregó el ingreso faltante (Debe) en las cuentas de ambos; no se anularon los asientos de la planilla (decisión de Sergio).
- 04/10/2024 Galicia 2139 $250.000 «Transf Inmed Cp» a la CUIT de Giamigli = BNA 9344 crédito del mismo día: traspaso interno (evento 20), sin contacto; no era de Lucy.
- 10/08/2017 BNA 18536 $30.000 a Lucy: retiro de ganancias (Sergio), sin asiento.
- 03/01/2025 Galicia 2319 $150.000 «Reembolso gastos» (lote …10389811; resumen Lucy 16/04/2025): faltaba en Cuenta Lucy; cargado como «Devolución por aporte pagos varios» (Debe). Independiente del lote …10217625 de $250.000 del 30/12/2024, que sí estaba.
- 13/11/2017 BNA 18537 $8.852,10 de Lucy = devolución del **Inmobiliario Complementario** cuota 3/2017 pagado por Giamigli el 07/11/2017 (BNA comp. 4394 «PAGO ARBA INMOBIL.COMPLEM»). Sergio: es gasto del Condominio (lo pagan los 3 socios). Impuesto 3206 → tipo nuevo «Impuesto Inmobiliario Complementario», período 3 2017, respaldo extracto BNA nov-2017; cuenta del Condominio: Debe 8.852,10 (07/11) y Haber 8.852,10 (13/11); BNA 18537 reasignado de 390 a 549. **Pendiente técnico:** no hay mecanismo para sacar un impuesto de los costos de Giamigli (en compras existe la línea particular); hoy el impuesto 3206 sigue contando como costo aunque lo recupera la cuenta del Condominio. **Resuelto 25/10 con la spec 041** (impuestos particulares): carga 3 al Condominio, Debe 3153 reemplaza al manual 3149, Haber 3150 vinculado, estado devuelto; ya no cuenta como costo de Giamigli.
- 03/06/2016 BNA 18535 $1.042,05 «DEB.TRAN.INTERB-LINK»: en las planillas originales (Base Nación Access, Resúmenes BNA) figura SIN contacto, «Pago por transferencia»; el resumen PDF no trae destinatario. El contacto de Lucy fue asignado después, sin fuente. Sin resúmenes de Lucy de 2016.

## Cierre del Condominio — respuestas de Sergio A–J (25/10/2026)

**Aplicado:**
- **A/B/C (68 pagos puente 2011–2014)** — `backend/scripts/condominio_68_pagos_cierre_036.py`, regla `condominio-68-pagos-cierre-036`, respaldo `WC_condominio_68_pagos_cierre_036_20261025_133100_448916.bak`:
  - 64 pagos con débito HSBC del Condominio (medio 10) → Haber del socio 3, $14.223,31. Incluye los comprobantes a nombre de la Sucesión (13, 14, 15, 16, 18, 75): la Sucesión fue la etapa previa de Giamigli (Sergio), y los 5 tickets «Efectivo» con débito HSBC exacto (14, 40, 362, 530, 660).
  - 3 combustibles en efectivo (177, 331, 360; $470,22) → Haber de Lucy (socio 2): el efectivo lo puso Lucy, sin reintegro.
  - Sodimac 88 ya estaba en Lucy. Otros socios intactos; repetición sin escrituras.
- **D** — los «$3.134» de la planilla Movs son los cheques Maignal 122750/51/52 de **$3.143** (`Maignal/Cuotas y pagos Venta Maignal.xlsx`, Listado Cheques), depositados en BNA el mismo día: 10626 (04/10/2012), 10668 (08/11/2012), 10721 (06/12/2012). `bna_cheques_camion_3143_036.py`: contacto 549, respaldo `WC_bna-cheques-camion-3143-036_20261025_132925_058873.bak`. Asientos 2990/2991/2993 del socio 3 corregidos a $3.143 con US$ recalculado (mismo script de A/B/C).
- **E** — AFIP junio 2011 (pago 192, $95) = cargas sociales de Irma, como los otros 4; ya estaba en el socio 3 (asiento 3050). Cerrado sin boleta.
- **F** — cheque 87678128 $2.926: pago 28 en Jáuregui y Morales, aplicado a su factura (FIFO 032, aplicación 18336) y en el socio 3 (3068). Sin recibo; Sergio lo da por aplicado.
- **G** — pago 581 queda en UATRE. Cerrado.
- **I** — no existe liquidación de apertura: la cuenta del socio 3 se arma con los movimientos detectados (historia 2011–2016 + estos cierres).

**Investigado, falta OK de Sergio:**
- **H1** BNA 18635 21/03/2012 −$4.134 «COBRADO POR CAJA» (cheque Giamigli 30990496) = Movs fila 430 del 21/03/2012 «Pago IVA e IIBB» del Condominio en efectivo por $4.134. Giamigli pagó un impuesto del Condominio → Debe del socio 3. El 24/04/2012 el Condominio emitió un cheque 48 hs de $4.134 rotulado «IVA / IIBB Condominio» (Movs 501), sin depósito correspondiente en el BNA de Giamigli: no hay prueba de reintegro.
- **H2** BNA 10348 27/03/2012 +$5.971,50 = extracto del Condominio (Movimientos Condominios, Extracto Banco fila 372 / Movs 437) 28/03/2012 «TRAN.ELECTRONIC PC BANKING A CBU 0110164120016400017094» «Transferencia al Campo». Aporte del Condominio → Haber del socio 3.
- **H3** BNA 11240 13/02/2014 +$10.000 = extracto del Condominio fila 1188 / Movs 1864 «TRANSF. ELECTRONICA ... A CBU 0110164120016400292800» «Transferencia a Giamigli». Aporte → Haber del socio 3. (El cobro de Pastorino $10.000 del 30/01/2014 es de la caja de Giamigli, no se relaciona.)
- **J** 13 depósitos BNA sin contacto ($211.716,52): 7 coinciden el mismo día y por el mismo importe con cobros en efectivo de ventas de hacienda ya registrados ($193.000,10): 9885 = pago 110 (11/02/2011, $30.000); 9890 = pago 111 (14/02/2011, $30.000); 10640 = pago 408 (18/10/2012, $20.000); 10906 = pago 450 (10–11/05/2013, $13.000); 10990 = pagos 449+451 (17/07/2013, $30.000); 11076 = pago 477 (01/10/2013, $30.000; banco $30.000,10); 11533 = pagos 696+697+698 (10/12/2014, $40.000). 16987 ($3.285 = pagos 108+109) ya estaba. Quedan 5 por $15.431,42: 10431 $1.000 (30/03/2012), 10509 $2.222,42 (26/06/2012), 10857 $1.209 transferencia (05/04/2013), 11245 $7.000 (21/02/2014, día siguiente al cobro Pastorino 551 $11.212), 11272 $4.000 (13/03/2014, dos días después del cobro Pastorino 560 $6.000).
- **Caja Giamigli 2011–jul-2015:** 137 cobros en efectivo hasta el 13/07/2015 ($742.922,04) no están en el libro de caja GiamigliSA (solo 1 de 138). Es la explicación más probable del ingreso «no identificado» de $144.350,52, pero cargar los cobros (ingresos) y los depósitos (egresos) cambia el saldo de la caja: hay que reconstruirla completa antes de aplicar.
- Control lateral: los 8 DEP.EFECTIVO asignados a Ferias del Centro / Casa Maineri no duplican cobros en efectivo (ningún cobro ±5 días).

### Aplicado tras el OK de Sergio (25/10, «H: Adelante», «J: Adelante con lo identificado»)
- `backend/scripts/condominio_h_bna_036.py`, regla `condominio-h-bna-036`, respaldo `WC_condominio_h_bna_036_20261025_134219_983737.bak`: socio 3 Debe $4.134 (BNA 18635) y Haber $5.971,50 (10348) y $10.000 (11240), Origen `BNACondominio036`. Control banco ↔ socio 3: 0 movimientos sin asiento.
- J: 7 depósitos identificados y 5 probables (11245/11272 Pastorino; 10431/10509/10857 caja Giamigli) registrados en AuditoriaCorrecciones; siguen sin contacto (el cobro ya está en la cuenta del cliente).
- Saldos: socio 3 −$5.682.291,82 / US$ −136.011,17; Lucy (socio 2) $2.237.592,08 / US$ −47.257,65.

### Corrección del diagnóstico de la caja Giamigli 2011–jul-2015
Los «137 cobros en efectivo ($742.922)» eran todos los cobros con importe negativo en Pagos efectivo, con cualquier forma de pago. Según `Formas de pago - retiro`, para cobros: 7 = depósito en cuenta (el cliente depositó en el banco), 8 = efectivo, 9 = retiro de 3ros, 13 = cheque. Los depósitos 9885/9890/10906 (pagos 110/111/450, forma 7) son depósitos directos del cliente, no efectivo de caja. **Efectivo real: 38 cobros forma 8 por $320.673,65 + cobro 408 ($20.000).**
Borrador de reconstrucción (sin aplicar): ingresos de efectivo $340.673,65; egresos por depósito de ese efectivo en BNA $135.431,52 (10640, 10990, 11076, 11533, 11245, 11272, 10431, 10509, 10857); neto +$205.242,13 contra el remanente no identificado de $144.350,52. Además hay 98 pagos en efectivo de Access caja «La Herencia» fuera del libro ($85.197,98): 39 ($5.677,60) coinciden con egresos del libro sin pago vinculado; 59 ($79.520,38) no están en el libro. Con todo, la caja quedaría −$18.628,77 al 13/07/2015 frente a la planilla, y quedan como candidatos 9 cheques BNA «COBRADO POR CAJA» sin contacto ($8.822,10).

### Caja Giamigli 2011–jul-2015 reconstruida (25/10, OK de Sergio)
`backend/scripts/caja_giamigli_reconstruccion_2011_2015_036.py`, regla `caja-giamigli-reconstruccion-2011-2015-036`, respaldo `WC_caja_giamigli_reconstruccion_2011_2015_036_20261025_135754_804585.bak`:
- +39 cobros en efectivo ($340.673,65); −54 pagos en efectivo a Sierra, parte en negro del sueldo ($74.262,50); −8 depósitos del efectivo en BNA ($134.431,52); +7 cheques propios cobrados por caja ($5.822,10).
- Remanente no identificado (mov. 1947): $144.350,52 → **$6.548,79**. Saldos sin cambio: $22.786,96 al 13/07/2015 y $381.785,15 al final.
- Cheque 18505 (cuenta BNA 1, Sucesión) ↔ depósito 10431 (apertura de la cuenta BNA 2 de Giamigli, 30/03/2012): aporte de la Sucesión para abrir la cuenta (Sergio); traspaso interno, fuera de la caja.
- Cheque BNA 11350 $2.000 (07/05/2014) = retiro de Sergio: contacto 5670 y Debe en el socio 1 (Origen Banco Nacion, IdOrigen 11350).
- Pendientes con Sergio (dentro del remanente): pagos 2137 (Sergio empleado $2.500, Blue, 22/09/2012), 363 (AgroNacion adm. anterior $1.677,58, cierra con su factura del mismo día), 1563 (Municipalidad, guías del 13/03/2014, $542,50), 2638 (XXXXXXXXX $300 07/10/2013; el mismo día el pago 474 de $300 sí está en el libro; la cuenta XXXX da saldo 0 con ambos), 708 (Agrovet $237,80, aplicado a la factura 0001-00077521).
- 25/10: aplicados los 5 pagos (`caja_giamigli_5_pagos_2011_2015_036.py`, respaldo `WC_caja_giamigli_5_pagos_036_20261025_140116_039192.bak`); remanente $11.806,67.
- Investigación del remanente: sin él, el saldo acumulado de la caja es negativo de sep-2011 a may-2014 (mínimo −$20.201,77 en may-2013) y positivo desde jun-2014. Candidato concreto: Inmobiliario nov-2011 (boleta 70, $2.810) figura pagado por débito Link BNA 10196 (04/11/2011, sin contacto) y en efectivo, pago 208 (10/11/2011, egreso de caja 1333). Descartados: no hay egresos de Sierra duplicados; no hay egresos de caja que coincidan con cheques del mismo contacto; los cheques BNA al contacto XXXXXXXXX (pagos 160/161/162/303/312, forma 1 «valor propio») no están en la caja. Preguntas abiertas a Sergio: cheques BNA a Sergio cobrados por caja 18405 ($40.000, 12/10/2011) y 18406 ($10.000, 28/12/2011); aportes de socios en efectivo 2011–2013 sin registro.
- 25/10, cierre del remanente (`caja_giamigli_arba_lucy_036.py`, regla `caja-giamigli-arba-lucy-036`, respaldo `WC_caja_giamigli_arba_lucy_036_20261025_141021_968929.bak`): Inmobiliario nov-2011 pagado por BNA 10196 (ahora contacto ARBA); pago 208 borrado (snapshot en la auditoría) y egreso de caja 1333 anulado. El remanente $8.996,67 pasa a «Aporte en efectivo Lucy (no registrado)» fechado 24/05/2013 y se acredita en Lucy (socio 2), US$ 1.716,92 («Todo a Lucy»). Los cheques a Sergio 18405/18406 ($40.000/$10.000, 2011) eran sueldos atrasados (cuenta 375, cerrada): sin cambios. **La caja Giamigli 2011–jul-2015 ya no tiene ingresos no identificados.** Saldos de caja sin cambio.
