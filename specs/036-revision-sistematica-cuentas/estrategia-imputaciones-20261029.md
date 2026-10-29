# Estrategia para cerrar las imputaciones de pagos — 29/10/2026

Aprobada por Sergio el 29/10/2026. Reemplaza los intentos de resolver todas las cuentas con una sola regla: el emparejamiento por importe idéntico (`regla_029`) quedó apagado en el código.

## Estado de partida

- **Saldos:** 484 fichas cerradas, 10 cerradas con excepción y 6 esperando evidencia. El saldo de cada cuenta **no se toca**.
- **Lo que falta es la imputación**, es decir, qué pago canceló qué factura. De eso depende el estado de cada factura y el rubro y el comprobante que muestra el Cash Flow.
- **Estado de las 452 cuentas con facturas de compra:**

  | Estado | Cuentas |
  |---|---|
  | FIFO-032 sin revisar | 292 |
  | Restos de la conciliación 020 | 87 |
  | Sin imputaciones | 62 |
  | Manuales revisadas | 11 |

- **Hechas:** Cargill (avisos del portal), Lartirigoyen (extranet) y Jáuregui y Morales. En Jáuregui se revisó la integridad, se llevaron 27 facturas al total del ticket y se aplicó el FIFO estricto; faltan los redondeos de los pagos.

## Grupos (cada uno con su fuente de verdad)

| Grupo | Cuentas | Fuente de verdad | Método |
|---|---|---|---|
| 1. Proveedor con resumen o portal (Bayá Casal, FEDEA, Syngenta…) | ~15 | Resumen del proveedor | Copiar sus imputaciones. Nunca FIFO. |
| 2. Pagadas solo con tarjeta | 92 | Vínculo consumo→factura del resumen de tarjeta | Usar el vínculo. Sin FIFO. |
| 3. Cuentas chicas (1 a 5 facturas) | ~250 | Factura y su pago | 1 a 1 automático; lo que no cierra va a una lista de excepciones. |
| 4. Cuenta corriente con muchas facturas (Criado, Agrovet, Coop. Agropecuaria…) | ~45 | Facturas y pagos completos | Integridad primero, después FIFO estricto. Una por una. |
| 5. Cuentas en US$ | 26 | Comprobantes en US$ | Regla del TC del comprobante; casi todas son también del grupo 1. |

**Orden:** grupos 2 y 3 (automáticos), después el 1 y por último el 4, de mayor a menor movimiento. Al terminar cada grupo, un resumen de una página: cuentas imputadas, excepciones y su causa.

## Reglas comunes (fijas)

1. **FIFO estricto:** las compras se ordenan por fecha de vencimiento (sin vencimiento cargado = contado = fecha de emisión) y los pagos por fecha de erogación. El pago va primero a la factura vencida más vieja.
2. **Integridad antes del FIFO:** que no falten facturas ni pagos y que no haya duplicados. Se verifica contra el comprobante, el extracto o los mails del proveedor.
3. **Facturas mal cargadas contra el ticket:** se llevan al TOTAL impreso, siempre con el comprobante a la vista. El método es escalar los precios de los renglones, como en `cargill_fracciones_036` y `jym_redondeo_tickets_036`.
4. **Diferencias entre una factura y su pago 1 a 1.** Se trabaja con porcentajes y criterio; nunca con montos fijos.
   - **Hasta 0,10%:** redondeo automático; se redondea la factura a lo pagado. En el historial son 761 de los 965 pares 1 a 1.
   - **Entre 0,10% y 1%:** se clasifica por la causa.

     | Causa | Señal | Qué se hace |
     |---|---|---|
     | Redondeo en el pago | El pago es un número redondo (pesos enteros, decenas) y la factura no | Se redondea la factura |
     | Descuento o bonificación | El mismo porcentaje se repite en ese proveedor o medio de pago (p. ej. 0,17% en tarjetas YPF/Saladillo) | Se registra como descuento |
     | Retención | Coincide con una retención o un certificado | Se imputa la retención |
     | Diferencia de cambio | Documento o pago en US$ | Regla del TC del comprobante |
     | Sin causa | — | A revisar con el comprobante |

   - **Más del 1%:** nunca es redondeo; se revisa la causa.
   - En la planilla de cada cuenta se muestra cada diferencia con su porcentaje y la causa asignada, para que Sergio pueda corregir el criterio caso por caso.
5. **Nada de imputaciones por centavos:** si el FIFO aplica menos de un 0,10% de una factura con otro pago, la diferencia se resuelve en la factura según el punto 4.

## Cómo se trabaja

- Antes de mostrar un resultado, se verifica contra el comprobante. Las alarmas se presentan como "a verificar".
- Las planillas de revisión llevan todas las filas y una columna "¿Cambia?".
- Antes de cada grabación se toma un respaldo y se controla el saldo por cuenta con `refrescar=True`. Cada corrección queda registrada en `AuditoriaCorrecciones`.
