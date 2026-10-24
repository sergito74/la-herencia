# Diez débitos con centavos conciliados — 24/10/2026

Sergio autorizó avanzar sin más consultas y pidió reporte detallado al terminar. Alcance aplicado:10 pagos del subconjunto18 con comprobación concordante entre ticketVisa débito y resumenHSBC. No son10 pagos nuevos. No se extendió el criterio a los5 tickets que dicenEfectivo ni a3 sin débito identificado.

## Qué se comprobó

En cada caso se revisó visualmente el ticket: total fiscal, cobroVisa y vuelto/complemento. Se exigió coincidencia exacta entre cobroVisa del original y movimientoHSBC, comercio concordante, fecha0–5 días posterior y hashSHA256 de ambos originales. La búsqueda con tolerancia solo encontró candidatos; la aplicación usa10 importes explícitos verificados. Compras actuales redondeadas al centavo coinciden con total fiscal. Ningún pago tenía aplicaciones activas: no se dejó una aplicación por encima de la capacidad bancaria corregida.

## Resultado individual aplicado

| Pago | Fecha original | Factura | Total fiscal | Débito HSBC | Fecha banco | Componente separado |
|---|---|---|---:|---:|---|---|
| 516 | 2013-12-20 | 2566-00173283 | 183,99 | 184,00 | 2013-12-23 | Vuelto 0,01 |
| 562 | 2014-03-14 | 2566-00181621 | 178,91 | 178,92 | 2014-03-14 | Vuelto 0,01 |
| 604 | 2014-06-05 | 2566-00190774 | 255,51 | 255,52 | 2014-06-06 | Vuelto 0,01 |
| 611 | 2014-06-27 | 2566-00193093 | 173,72 | 173,73 | 2014-06-27 | Vuelto 0,01 |
| 625 | 2014-08-06 | 2566-00197092 | 194,19 | 194,18 | 2014-08-06 | Complemento «Su pago» 0,01 |
| 715 | 2015-03-06 | 2521-00158215 | 230,13 | 230,12 | 2015-03-09 | Complemento «Su pago» 0,01 |
| 725 | 2015-04-10 | 2525-00086067 | 202,54 | 202,53 | 2015-04-10 | Complemento «Su pago» 0,01 |
| 733 | 2015-04-23 | 2525-00086500 | 200,80 | 200,78 | 2015-04-24 | Complemento «Su pago» 0,02 |
| 739 | 2015-05-08 | 2525-00087195 | 280,74 | 280,73 | 2015-05-08 | Complemento «Su pago» 0,01 |
| 752 | 2015-06-05 | 2936-00003703 | 230,02 | 230,00 | 2015-06-05 | Complemento «Su pago» 0,02 |

Total fiscal2130,55; banco2130,51. Cuatro vueltos suman0,04 y seis complementos0,08. No confundir suma absoluta de componentes0,12 con diferencia neta0,04.

## Qué se cambió en WC

1. Diez pagos existentes: medio3→10 y monto igual al débito real; fecha histórica, contacto30, operación y demás referencias conservados. No se inserta otro débito bancario ni pago.
2. Diez componentes documentales en AjustesCuentaCorriente, identificados individualmente por prefijo036-CENT-P{id}, factura, total fiscal y cobroVisa. Cuatro de ladoDeuda por vuelto y seis de ladoCredito por complemento del ticket: compensan exactamente la diferencia de cada pago sin modificar su factura. Son componentes del pago respaldados por el original; no una deuda nueva, un gasto nuevo ni un ajuste global para forzar cierre. No se les atribuye caja, persona o patrimonio sin evidencia. Cada componente tiene fecha del pago original y auditoría compartida137.
3. Veinte renglones históricos compensatorios de caja anulados:10 egresos ficticios y10 aportes opuestos usados en la reconstrucción. El neto de cada par es0. Se conservan filas, importes originales y referencias, añadiendo nota de que el pago bancario sigue vigente. No se anulan los pagos.
4. Matriz de financiación incorpora los componentes documentales, separando importe histórico de fuente, pago bancario vigente y componente. No se vuelve a sumar el origen bancario a su fuente de financiación ni se convierte el componente en aporte.

## Verificaciones y respaldo

Auditoría137, regla condominio-diez-debitos-centavos-036. Snapshot de antes/después y fuentes/hash: backups/condominio-15-medios-036/diez-centavos-20261024-120107.json. Respaldo verificado previo: C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_condominio_diez_centavos_036_20261024_120106_810024.bak.

- Igualdad exacta de saldos de todos los contactos, cajas y socios antes/después. Misma cantidad bruta e importes de historia de caja;20 filas activas menos, mismo saldo operativo por caja.
- Socios: ninguna fila, USD o kg agregado/modificado. No se alteran los créditosLucy registrados en el tramo anterior.
- Diez pagos siguen vigentes, total2130,51. Componentes6 créditos0,08 y4 débitos0,04. Facturas y sus líneas intactas. No se modifica Access ni LaHerencia.
- Segunda ejecución de --aplicar devuelve ya_aplicado_sin_escrituras; RuffPASS. No se cerró una ficha de proveedor ni una campaña nueva. No se ejecutaron pruebas automáticas que generen datos financieros.

## Estado general y próximos pasos

Del universo68:59 débitos documentados,1 tarjetaSodimac (financiadaLucy) y8 pendientes. Se conservan140 puentes históricos en la matriz,72 pertenecen al universo principal;120 filas de caja ya anuladas por reclasificaciones de medios, sin pérdida de historia. Los165 registros fuente/841286,02 siguen siendo universo de fuentes y no saldo de deuda. La financiaciónLucy identificada se excluye de aportesCond.

Ocho pendientes concretos:14,40,362,530,660 tienen candidato bancario cercano pero ticketEfectivo;177,331,360 dicenEfectivo y no tienen candidato. No se les aplicó el tratamiento deVisa por analogía. La continuidadSucesión aclarada porSergio se conserva y no elimina por sí sola las contradicciones del medio.

Además continúan: diferenciasEasy110,57 yCooperativa0,01 (titularLucy y no reintegro ya aclarados); origen/reintegro de otros3 combustibles519,53; reconstrucción históricaCond y2016–2026 sin apertura consolidada localizada; boletaAFIP junio2011, comprobante sindical04/2014, recibo/endoso cheque2926 y ruta cheque2968. No requiere nuevas respuestas de Sergio para lo aplicado hoy; no se declaran cerrados estos pendientes por falta de documentación.
