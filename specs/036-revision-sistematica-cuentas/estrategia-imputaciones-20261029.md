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

## Reparación del 30/10/2026 — `jym_centavo_exacto_036`

El script del 29/10 tomaba como objetivo `vw_Compras_ImporteDocumento` y escalaba los renglones para que `GranTotal` diera ese número. Donde las dos vistas difieren, cambió el total real de la factura y rompió cuentas cerradas:

- **Madelan (444):** había pasado de −$0,04 a +$11.190,33. Las 2 facturas volvieron al PDF ($567.845,69 y $2.271.382,75, a $70.000 por cabeza). Cuenta en **$0**.
- **Ferias del Centro (39):** había pasado de −$1,81 a +$143,12. Las 2 facturas volvieron al precio original ($15.200 y $18.000). Cuenta en **$0**.
- **Catalpa (400):** sin cambio neto. Sigue en $2.647.371,85, como en el cierre del 17/10 (excepción $21.955,35). Después, por decisión de Sergio, se cerró en **$0 y US$ 0** con el ajuste interno 163 (Deuda $21.955,35 al 08/02/2024): la retención 0000-2024-000005 se había practicado pero no se descontó de la transferencia del 14/02/2024. FIFO aplicado; ficha cerrada sin excepción.

Las 3 cuentas se volvieron a imputar con el FIFO (ejecución 141 y la siguiente de Catalpa), con respaldo. El script quedó corregido: ahora redondea `GranTotal`. Revisé las 1.015 facturas que tocaron los dos scripts de redondeo, y el resto de las diferencias con LaHerencia son redondeos aprobados o correcciones al PDF (Cooperativa 2025, EDP). También revisé el saldo al corte de todas las fichas cerradas, y fuera de esto no hay otras cuentas rotas.

Correcciones al informe del grupo 1:
- **Gentos:** está en $0 y sin pagos de más.
- **Galicia Seguros:** está en US$ 0. El débito de $2.154.648 y su devolución del 30/06/2025 no rompen el saldo.
- **Nidera:** la factura 0303-7648 ya estaba partida, de antes, en $41.705,68 más la ND interna de $198.598,77.

## Grupo 4 — IMPUTADO (30/10/2026)

Son 88 cuentas corrientes con más de 5 facturas, sin las del grupo 1 (`grupo4_diagnostico_036`, `grupo4_cierre_036`). Se pasaron centavos a 1.692 facturas, se redondearon los pares de hasta 0,10% y se aplicó el FIFO estricto. Antes y después se controló el saldo de cada cuenta y la comparación contra el respaldo. Lo único que se movió más de $0,50 es EESS Saladillo: −$4,00 de pares, que acercan el saldo a cero.

**Errores encontrados y corregidos en el camino:**
- **Pares en facturas en cuotas:** el script llevaba el total de la factura al importe de una cuota. Afectó 18 facturas (17 de Pérez, 1 de Zurra). Se restauraron desde el respaldo `grupo4-redondeos` y ahora el script omite las cuotas.
- **Notas de crédito en US$ vinculadas a su factura:** desde el cambio del 29/10, el importe fijo se dividía dos veces por el TC (en Guazzaroni, US$ 2,52 en vez de 3.442,53). Se corrigió y se re-imputaron Guazzaroni, Folgado y Sunanco.
- **TC del comprobante siempre:** el motor convertía el pago en pesos de un documento en US$ al BNA del día. Ahora usa siempre el TC del comprobante (regla del 21/10). Se re-imputaron las 22 cuentas con documentos en US$, salvo las de portal, sin que cambie ningún saldo.
- **Devoluciones a la tarjeta:**
  - Un reintegro atado a su nota de crédito ahora la cancela, en lugar de quedar con los lados cruzados.
  - Un reintegro atado a su factura (se cobró de más y se devolvió la diferencia) lo cancela el sobrante del cargo de esa compra.
  - Así se cerraron los restos viejos de Coto.
- **Regla de importe idéntico:** había 518 aplicaciones "manuales" automáticas del 18/10 ("Barrida 036: mismo importe…") en Movistar y EESS Saladillo. Se anularon y se reemplazaron por FIFO. Por esas aplicaciones, en Movistar las notas de crédito de mayo de 2024 habían quedado imputadas a la factura de junio.

**Saldos abiertos reales, verificados:**
- **Banco Nación $137.500:** es la última cuota de capital del préstamo 19136529 ($1.100.000 en 8 cuotas de $137.500, 7 pagadas). Los préstamos 14464193 y 22021399 están cancelados.
- **Guazzaroni US$ 13.605,79:** facturas 3310, 3313 y 4338, de canje directo. La NC 13569 anula las facturas 3231 y 3233 ("cambia cond. de pago").
- **Documentos posteriores al corte o casos conocidos:** Fideicomiso La Esperanza, Estudio Criado, Pérez, Ricardo Criado (recibo 4511), Basterrechea (factura 545), Movistar (septiembre y octubre de 2026), EESS Saladillo, Gomería Manghi, Buira, Sancor, Martín Silva Rossi y Coto (factura de octubre).

**Caso menor:** en Coto, el ingreso Galicia 706 ($851,10 del 08/08/2022) es el sobrante devuelto del pago Galicia 701. El motor no cruza dinero contra dinero sin vínculo, así que el FIFO lo deja abierto. No cambia el saldo.
