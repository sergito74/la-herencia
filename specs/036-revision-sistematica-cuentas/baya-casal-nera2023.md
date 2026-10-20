# NERA2023 — pago y retención según libro del proveedor

Aplicado20/10/2026 por instrucción de Sergio: replicar la cuenta corriente del proveedor. Banco1375 yretención109 no se duplican ni se modifica su importe nominal, fecha ni contacto. No se registra otro consumo de tarjeta o préstamo por el mismo pago.

## Aplicaciones

RI33178/29-08-2023 acredita$9.880.147,75; las diferencias de cambio están enND96887, por lo que el principal se imputa a pesos de origen de cada factura, no a pesos actualizados másND otra vez:

| Documento | Aplicación pesos |
|---|---:|
| FC320048 | 1.249.385,78 |
| FC320049 | 3.868.981,71 |
| FC336203 | 147.396,75 |
| ND96827 | 229.028,28 |
| ND96887 | 4.385.355,23 |
| Total | 9.880.147,75 |

Retención109/cert2023-36$95.267,22 se aplica aFC336203 el11/01/2024, respaldada porRG36/RI37632 original descargado. No se anticipa a agosto ni se imputa aFC320049 como antes. Anuladas lógicamente9aplicaciones erróneas del pago yretención; creadas6documentales. Otras aplicaciones a esas facturas no se anulan sin cotejar sus propios comprobantes, dado que algunos pagos son parciales.

## Monedas y fechas

- Banco: proveedor reconoceUSD26.786,96 el29/08/2023, más componente$506.051,12 enpesos que cancelaIVA deND96887. Se conserva la separación; no convertir todo por349,95.
- Retención: reconoceUSD322,94 el11/01/2024 aTC295. Original delcertificado deagosto intacto.
- Banco real1375 sigue por$9.880.148,00 del24/08/2023, descripciónFinanciaciónGaliciaRural yleyendaSyngenta. No se cambia banco para imitar el recibo; la diferencia$0,25 permanece como discrepancia de tesorería.
- ValuacionProveedor tiene registro de banco con importe reconocido$9.880.147,75,fecha29/08/USD26786,96 yretención confechaenero/USD322,94. Columna opcional `ImporteReconocidoPesos` evita que$0,25 genere saldo externo ficticio. Fuente bancaria original se conserva eimporte discrepante en auditoría.

Verificados6aplicaciones, sumas exactas deRI yretención, bancos/certificado/documentos de compra intactos y carga real de cuenta con fecha/importes/eventosUSD correctos. La representación de cuenta distingue la recepción enpesos del eventoUSD; pesos no se duplican en el evento.20tests bimonetarios pasaron (incluye prueba nueva deimporte reconocido sin mutación delbanco).

## Pendientes de otras etapas

LaFC320049 del sistema aún totalizaUSD19.357,04 frenteUSD19.375,91 reconocido. Es una discrepancia de carga de factura, no motivo para alterar el pago documentado. Revisar precio deurea0,62 frenteoriginal0,6218 (antecedente ya localizado). No declarar sobrepago real por capacidadSQL incorrecta ni corregir por ajuste genérico. No se cierra toda la cuenta ni se ejecutaFIFOglobal.

Respaldo verificado `WC_baya-nera2023-036_20261020_104251_833467.bak`; script `backend/scripts/baya_casal_nera2023_036.py`; auditoría local `backups/baya-conciliacion-20261019/nera2023-correccion-*.json`. Recibos fuente `RI_0006_00033178.pdf` y `RG36_RI37632.pdf` con textos parseados en la misma carpeta. La ampliaciónnullable devaluaciones es compatible con registros existentes.
