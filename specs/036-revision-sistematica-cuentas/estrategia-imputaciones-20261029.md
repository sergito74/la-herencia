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

## Grupo 2 — CERRADO (29/10/2026)

Son 92 cuentas pagadas solo con tarjeta y 847 facturas. Las 92 cierran con el FIFO (ejecución 130) y **ningún saldo cambió**.

- **Redondeos:** 254 facturas con diferencia ≤0,10% contra la tarjeta se redondearon a lo cobrado (`grupo2_redondeo_tarjeta_036`).
- **Vínculos:** 4 consumos de tarjeta estaban vinculados a la factura anterior y se pasaron a la propia: Corredores Viales, Grupo Concesionario del Oeste y 2 de Autopistas del Sol (`grupo2_revincular_tarjeta_036`).
- **RDD duplicados:** se quitaron las ND internas de redondeo RDD276 y RDD306 del 30/09. Duplicaban los centavos ya redondeados en las facturas (`grupo2_quitar_rdd_036`).
- **Asientos particulares:** los asientos negativos de Pagos efectivo ("Particular L/S", "La Herencia") cuentan como cargo en el FIFO y se cruzan en su fecha con el consumo de tarjeta que los pagó (`recalculo_fifo/entrada.py`). Sin este cambio Carrefour no cerraba.
- **Excepciones explicadas (no son errores):**
  - 9 facturas de octubre de 2026 que esperan el resumen de tarjeta.
  - Carrefour: la parte particular está en la factura y en su asiento.
  - Margenes Agropecuarios: 6 de 12 cuotas sin vencer ($144.000).
  - Nación Seguros: descuento del 5% y 3 facturas en US$ compensadas en la cuenta.
  - Cuentas en $0 cuyo resto se compensa con otro comprobante de la cuenta, que el FIFO ya imputa.
- **Queda:** de $0,01 a $0,08 de líneas de tarjeta sin imputar en Autopistas del Sol, Grupo Concesionario del Oeste y Carrefour.

## Grupo 3 — CERRADO (29/10/2026)

Son 250 cuentas chicas, de 1 a 5 facturas, con algún pago que no es tarjeta. Las 248 que cierran se aplicaron con el FIFO (ejecución 131, más la 132 para 3 cuentas que se redondearon después). Ninguna empeora.

- **Redondeos automáticos:** 23 facturas de 18 cuentas se redondearon a lo pagado, todas por debajo de 0,10% (`grupo3_redondeo_036`). Las 18 cuentas quedaron en $0.
- **Redondeos verificados a mano:** 8 facturas de PC Electro Tigre, Reynoso y Sabattini se llevaron a la suma exacta de su transferencia más su retención (`grupo3_redondeo_manual_036`).
- **No se tocan:**
  - Los asientos de centavos de 2011 ("La Herencia" $0,08, "NC" $0,02). Ya son ajustes de redondeo.
  - Las facturas en US$ (Criadero Don Pedro, Tierras de Henderson). Siguen la regla del TC del comprobante.
- **Excepciones:**
  - Gentos y Galicia Seguros, con pagos de más. Galicia Seguros ya espera respuesta de Sergio.
  - Electricidad Lavalle, con saldo real de $9.931,72, en la lista de pendientes.

## Grupo 1 — CERRADO (29/10/2026)

Son 19 proveedores con resumen de cuenta (carpeta "Resumenes de Cuenta"). Todos quedaron imputados y ningún saldo cambió, salvo los redondeos que se detallan abajo.

- **Con portal: se copia la imputación del proveedor.**
  - **Bayá Casal:** recibos y aplicaciones de su extranet (`aplicacion_baya_portal_036`).
  - **FEDEA:** emulación de su cuenta unificada (`aplicacion_fedea_portal_036`). Cerrada definitivamente en $0 / US$0 con el par de ajustes 161/162; no se opera más.
  - **Cargill y Lartirigoyen:** ya estaban.
- **Con resúmenes en papel o PDF: pares 1 a 1 y FIFO estricto, controlados contra el resumen.** En la Cooperativa Agropecuaria, los 29 resúmenes mensuales coinciden con el saldo del sistema a cada fecha, con diferencias de centavos.
- **Centavos:**
  - **Fracciones de centavo:** las facturas se llevan a su total al centavo, porque la vista calcula cantidad × precio × IVA sin redondear (`jym_centavo_exacto_036 <cuenta>`).
  - **Pares 1 a 1 con diferencia ≤0,10%:** la factura se redondea a lo pagado (`jym_redondeo_pares_036 <cuenta>`).
  - **Origen de los arrastres:**
    - Jáuregui: FC 0011-00010603 llevada a su ticket, $1.582.000.
    - Cooperativa Eléctrica: ajuste 19 (saldo inicial 2011) llevado a $268, lo pagado.
    - Cooperativa Agropecuaria: FC 00039-11092 redondeada a lo pagado.
    - Agrovet: FC 0003-67661 redondeada a lo pagado.
    - Cuatro Vientos: FC 0002-23 redondeada a lo pagado.
- **Motor FIFO:**
  1. Los documentos en US$ entran al motor en dólares. Antes la vista los pasaba pesificados y el motor los volvía a multiplicar por el TC. Con este cambio se re-imputaron 17 cuentas con documentos en US$.
  2. Desempate entre facturas del mismo vencimiento: va primero la de importe idéntico al pago.
- **Enlaces a PDF de Jáuregui:** 14 corregidos (`.crdownload` completos copiados a `.pdf`, archivos de la fecha).
- **Quedan fuera de mi alcance:**
  - **Esperan a Sergio:** Ferias del Centro ($143,12 de banco), Madelan ($11.190,33 de banco), Gentos y Galicia Seguros (pagos de más).
  - **Espera el extracto de octubre:** la Cooperativa Eléctrica. El portal no muestra impaga la boleta 233471 y muestra $125.553,71 a favor.
  - **Comprobantes que no están ni en disco ni en el mail:** 7 facturas de Jáuregui de 2023-24 (0008-3711, 0009-39283, 0011-33, 0011-3, 0011-325, 0009-48496, 0008-7875), la 0009-52613 y la 0005-51851 de 2016.
