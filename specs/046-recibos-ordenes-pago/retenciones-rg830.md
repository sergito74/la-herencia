# Retenciones de Ganancias RG 830 en la OP (T018), informe del 30/10/2026

Agente de dirección financiera, con fuentes públicas. Las tablas (alícuotas, no sujeto, mínimo) NO se dejan fijas en el código: se toman del simulador de ARCA (https://servicioscf.afip.gob.ar/calc-rg830/), porque la RG 5423 y sus actualizaciones cambian los importes.

## Reglas que se pueden implementar
1. **Momento y base:** se retiene en cada pago, incluidos los anticipos y los pagos a cuenta. La base es el neto de IVA, sin percepciones ni otros tributos. En un pago parcial, la base es la parte proporcional del neto gravado.
2. **Acumulación por mes:** se suman los pagos del mes (el mes del pago, no el de la factura) al mismo CUIT y del mismo código de régimen. Al total se le resta el no sujeto una vez por mes, se aplica la alícuota y se descuentan las retenciones ya practicadas en el mes.
3. **Facturas mixtas:** se clasifica cada renglón (78 bienes, 94 servicios, transporte, arrendamientos, 119 profesiones, comisiones) y el pago se prorratea por el neto de cada concepto. La clasificación es una sugerencia que se puede editar. El mapeo a códigos lo valida el contador.
4. **Cuándo no se retiene:**
   - Monotributistas vigentes. La RG 2616 se muestra como alerta, no se calcula.
   - Proveedores exentos (EX) o no alcanzados (NC).
   - Proveedores con certificado de exclusión vigente, que se carga a mano con su vigencia.
   - Pagos al Estado.
   - Compras de granos, que tienen su propio régimen.
5. **No inscriptos (NI):** la alícuota es mayor y no se descuenta el no sujeto.
6. **Mínimo ($240):** si el cálculo da menos, no se retiene. El pago siguiente del mes vuelve a calcular sobre el total acumulado.
7. **US$:** BNA vendedor del día hábil anterior al pago (norma, verificar). Es distinto del TC del comprobante que se usa en la cuenta corriente.
8. **Registro de cada retención:** número de certificado, régimen, base, alícuota, importe, fecha, CUIT, OP y estado. La retención cancela la factura por el total. Evitar el doble conteo con las retenciones cargadas desde los PDF de SICORE (convención ' B').

## Riesgos (los confirma una persona antes de emitir la OP)
- El padrón puede estar atrasado.
- Hay que confirmar el concepto de cada renglón.
- Si faltan pagos del mes cargados en el sistema (tarjeta, efectivo), la base queda corta.
- Al anular y volver a emitir una OP, no retener dos veces.
- El agente de retención responde solidariamente: el cálculo es siempre una propuesta que alguien confirma.

## Decisiones de Sergio (30/10/2026)
1. **El sistema solo calcula la retención.** El certificado lo emite el Estudio Criado. El sistema prepara el mail a administracion@estudiocriado.com, con copia a rcriado@estudiocriado.com, y adjunta las facturas del pago. Formato tomado de los mails enviados entre 2021 y 2026:
   - **Asunto:** "Giamigli de Bolivar S.A. - Retencion" (o "Retenciones").
   - **Texto:** "Hola Karen, buen día. Te mando adjunta(s) factura(s) para hacer el cálculo de la retención de acuerdo al siguiente detalle:"
   - **Tabla:** Fecha | Vencimiento | Fecha pago | Proveedor | Tipo Documento | Nro. Documento | Moneda | Forma de pago | Importe, y para US$ también Tipo Cambio | Importe pesos.
   - **Cierre:** "Gracias! Saludos, Sergio".
2. **Pagos ya hechos con tarjeta o débito:** quedan como están. La regla rige de acá en adelante.
3. **Mapeo de rubros a códigos:** el sistema arma un borrador, lo valida el contador y lo ratifica el estudio.
4. **Granos, hacienda y consignatarios:** se excluyen.
5. **TC en US$:** el que usa el estudio. Contra "Detalle de Pagos.xlsx" (53 pagos en US$ de 2021 a 2026), 48 usan el **TC de la factura**, que suele ser el BNA vendedor divisa del día anterior a la factura. Otros 3 son facturas que no están en Compras, con TC impreso propio. En 2 se usó el BNA del pago. Regla: TC del comprobante, la misma que [[feedback-regla-usd-tc-comprobante]]; si la factura no tiene TC, BNA vendedor divisa del día hábil anterior al pago.
6. **Certificados de exclusión:** se cargan a mano, con su vigencia.

## Hallazgo sobre la base (Detalle de Pagos)
La base es el importe sin IVA. Ejemplo, Lartirigoyen 0149-11970, julio de 2023: $1.400.628,24 / 1,21 = $1.157.544, menos $224.000 = $933.544, por 2% = **$18.670,88**, igual al certificado. En el mismo mes, la 0149-11992 también descontó el no sujeto (no se acumuló con la anterior), y el resultado es $19.251,58. Sergio 30/10: se aplica el criterio de AFIP (acumulación mensual por proveedor y concepto, no sujeto una vez por mes); lo de Lartirigoyen fue un error del estudio.

Fuentes: RG 5423 (consejosalta.org.ar), CPCECABA 01/2026, consejo.org.ar 06/2025, iProfesional 2026, blogdelcontador.com.ar (RG 4525).
