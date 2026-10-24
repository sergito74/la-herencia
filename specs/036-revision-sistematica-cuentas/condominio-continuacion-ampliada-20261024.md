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
