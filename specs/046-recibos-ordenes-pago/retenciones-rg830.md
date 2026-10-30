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

## Decisiones de Sergio (pendientes)
1. ¿El sistema solo calcula, o también emite el certificado? ¿Quién presenta SIRE: el estudio contable?
2. ¿Qué se hace con los pagos con tarjeta o débito que deberían haber tenido retención?
3. La tabla de mapeo de rubros a códigos de régimen, a validar con el contador (arrendamiento rural, fletes, veterinarios).
4. ¿Se excluyen las compras de granos, hacienda y consignatarios?
5. ¿TC para los pagos en US$?
6. ¿Cómo se cargan los certificados de exclusión?

Fuentes: RG 5423 (consejosalta.org.ar), CPCECABA 01/2026, consejo.org.ar 06/2025, iProfesional 2026, blogdelcontador.com.ar (RG 4525).
