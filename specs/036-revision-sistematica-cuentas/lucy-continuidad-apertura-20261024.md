# Lucy, continuidad Sucesión y búsqueda de apertura — 24/10/2026

## Aclaraciones de Sergio
Los5 combustibles de2011 y Lioca consumidor final son gastos de la Sucesión, etapa previa a Giamigli: puede existir continuidad de cuentas. No tratarlos como gastos ajenos por su destinatario fiscal ni atribuir un aporte nuevo sin reconstrucción. Sobre apertura: no conoce respaldo, pidió buscarlo en disco. Naldo/Cooperativa/Easy: titular Lucy; Giamigli no reintegró y deben considerarse en su cuenta. No extender esa confirmación a Sodimac.

## Búsqueda de apertura y duplicados
Cajas Giamigli.xlsx/Cuenta Cond LSC: fila3,29/12/2023, aporte efectivo150000, acumulado150000, sin arrastre inicial visible. No es una apertura consolidada demostrada: es el primer movimiento de esa hoja. No sostener como hecho la hipótesis previa de que recogía financiación2011–2014. Cuenta Lucy empieza06/11/2017 con impuestos; sin Naldo/Cooperativa/Easy ni filas rotuladas apertura/saldo inicial. Deuda Giamigli - Giamberardini10.02.2023.xlsx confirma el mismo inicio de Lucy, sin esos proveedores. También revisadas Simulacion Prestamos Lucy.xlsx y Aportes de Capital Directores.xlsx sin liquidación consolidada localizada. Mutuo2018: préstamo27000USD compra de hacienda; no es consolidación demostrada de tarjetas2012–2014. Contrato07/03/2023: préstamo1330kg y1438USD, sin identificación de aquellos pagos. No se alteraron contratos, planillas ni mutuos.

EnWC se comprobaron todas las filas deLucy anteriores2015, coincidencias de fecha/importe y origenPagosEfectivo315/503/561, incluso otras cuentas de socio para ese origen. Sin representaciones previas. Ajustes decontacto390 revisados:70000/2021 y200000/2022, sin apertura de esos pagos. Evidencia privada apertura-lucy-busqueda-planilla.json y busqueda-deuda-apertura-lucy.json bajo backups/condominio-15-medios-036.

## Aplicado — auditoría135
Tres créditos/Haber a favor de Lucy, TipoDevolucion y OrigenPagosEfectivo, preservando los pagos y gastos existentes:

| Movimiento socio | Pago | Fecha histórica | Pesos históricos | Dólar BNA promedio billete | US$ | Kg |
|---|---|---|---:|---:|---:|---:|
|2970|315 Naldo|13/09/2012|1578,00|4,645|339,7201|0|
|2971|503 Cooperativa|05/12/2013|2253,04|6,20|363,3935|0|
|2972|561 Easy|07/03/2014|1250,97|7,81|160,1754|0|

Total5082,01 nominales,863,2890USD a favor. No presentar5082,01 como deuda actualizada de hoy. Regla histórica compartida: antes16/03/2020,100%USD; desde esa fecha50%kgINMAG/50%USD, con cotizaciones de la fecha o última anterior; pesos originales conservados. Confirmada contra avance-conciliaciones-20261022.md y cuentas_socios/valuacion.py. Al recordar Sergio las reglas se verificó sentido: Haber a favor deLucy, fechas históricas, USD positivos almacenados cuyo signo lo aplica TipoDevolucion, sin kg. Mutuo separado.

Solo se reconocen importes de pagos existentes: diferenciaEasy110,57 y centavoCooperativa siguen pendientes de documentación del importe financiado y su cancelación; no hay cierre externo ni aumento de pagos. La confirmación resuelve titular/reintegro, no aporta un resumen de tarjeta nuevo. Los tres pagos aún tienen etiquetaCajaCondominio histórica: la matriz ahora explicita financiaciónLucy y exclusión de aportesCondominio, sin borrarlos de su fuente. No sumar5082,01 a socio3.

Backup verificado WC_lucy_tres_tarjetas_036_20261024_114729_058205.bak en carpeta central SQL Server. Snapshot backups/condominio-15-medios-036/lucy-tres-tarjetas-20261024-114729.json. Todos los saldos decontactos y cajas y demás socios idénticos;Lucy aumenta3filas/5082,01/863,2890USD, kg idénticos. Ningún pago/gasto creado ni Access modificado. Repetición devuelve ya_aplicado_sin_escrituras; RuffPASS. Script lucy_tres_tarjetas_condominio_036.py.

Matriz posterior matriz-financiacion-20261024-114756.json/CSV: universo de fuentes165/841286,02 preservado (no saldo);3 pagos señaladosLucy, continuidadSucesión explícita. Pendientes: cierre de diferencias fiscales con tarjeta, Sodimac, reconstrucción de financiación histórica anterior a hojaCond y movimientos2016–2026;10 débitos con centavos y5 contradicciones; origen/reintegro de efectivos; originalesAFIP/UATRE y endoso de cheque. No declarar conciliación cerrada.


## Sodimac confirmado y aplicado — 24/10/2026
Sergio confirma tarjetaLucy, pago íntegro de factura624,29 y sin reintegro. Pregunta si hay particulares: verificado Det_Compras, todos IdDestino1=General/IdCentroCostos3=Adm.General, sin asignaciones particulares. Diferencia52,37 corresponde a2 C.TUBO neto41,24 +IVA8,66 +percepciónIIBB faltante2,47. No hay respaldo de pago parcial: el importe571,92 se originó junto a carga fiscal incompleta. La ausencia de recibo no justificaba sugerir un pago parcial como hecho.

Aplicado script lucy_sodimac_036.py con respaldo WC_lucy_sodimac_036_20261024_115243_710787.bak; snapshot backups/condominio-15-medios-036/lucy-sodimac-20261024-115244.json. Pago88 existente571,92→624,29, medio20 conservado; créditoHaberLucy624,29 con OrigenPagosEfectivo88, fecha29/02/2012,100%USD143,9451 (BNA promedio billete4,337 de fecha),kg0. No se crea otro pago/gasto ni se reactivan filas de caja; cuentaSodimac cambia+52,37 por pago corregido, otrascuentas/cajas/socios idénticos. Repetición sin escrituras yRuffPASS. No declarar cierre externo de toda la ficha por resolver este documento. Los4 créditosLucy suman5706,30 nominales y1007,2341USD históricos. DiferenciasEasy/Cooperativa siguen pendientes. Matriz excluye pago88 además de315/503/561 de aportesCond.
