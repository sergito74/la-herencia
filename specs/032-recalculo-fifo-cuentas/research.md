# Research: Recálculo FIFO de cuentas corrientes

## R1. Fuente de vencimientos

- **Decision**: el vencimiento sale de la tabla `[Vencimiento Compras]`, uniendo su `IdCompra` con `Compras.IdDeuda`. Cada cuota es un débito separado. El importe de cada cuota es el total dividido en partes iguales, porque la tabla no guarda importes.
  - Una compra sin cuotas, o con una cuota igual a la fecha de emisión, es de contado y vence en su fecha.
  - En las ventas, el vencimiento es la fecha de la liquidación. Las tablas de venta no tienen una columna de fecha de pago pactada.
- **Rationale**: es la tabla que escribe el selector "Contado / A plazo". Los datos medidos están en la tabla de abajo. El campo `Compras.[Fecha Vto]` casi no se usa.
- **Alternatives considered**: usar `Compras.[Fecha Vto]`, descartado por incompleto.

| Condición | Compras |
| --- | --- |
| A plazo | 2.373 |
| Contado | 2.787 |
| Sin vencimiento | 1.280 |

Hay 64 compras con más de una cuota.

## R2. Tipo de cambio BNA vendedor del día anterior

- **Decision**: la fuente es la tabla existente `dbo.[Dolar BNA]`, con la columna `Vend_Divisa`.
  - La tabla tiene todos los días, incluidos los fines de semana, del 05/04/2010 al 30/09/2026, sin valores nulos. Se carga a mano desde "Parámetros".
  - Se reutiliza `backend/src/features/flujo_caja/cotizacion.py` (`cargar_serie`, `cotizacion_del_dia`), que ya la lee con `Vend_Divisa` y toma el último día hábil anterior.
  - La tabla `cotizacion_bna`, vacía, no se usa.
  - Para pagos posteriores a la última fecha cargada, el motor usa el TC implícito del pago y marca el renglón "TC implícito" hasta que se complete la serie.
- **Rationale**: es la serie que ya usa el flujo 030. Usar la misma columna mantiene consistentes los dos módulos.
- **Alternatives considered**:
  - `Vend_billete`: se descartó por consistencia con 030.
  - Cargar `cotizacion_bna`: es innecesario.
- **Actualización**: el 2026-10-01 se completaron 160 días, del 24/04/2026 al 30/09/2026, con `backend/scripts/actualizar_dolar_bna.py`. La fuente es Errepar (https://www.errepar.com/cotizacion-dolar), validada contra los 23 días superpuestos de abril. El script es idempotente y se puede volver a correr para mantener la serie al día.

## R3. Moneda de las cuentas mixtas

- **Decision**: cada documento conserva su moneda.
  - Las compensaciones entre documentos USD se hacen en USD.
  - Un pago en pesos aplicado a un documento USD se convierte al tipo de cambio de R2.
  - El saldo de la cuenta se informa en la moneda dominante: USD si la mayoría de los débitos son USD, como en Cargill.
  - Las notas "Ajusta tipo de cambio" son débitos o créditos en pesos asociados a su documento USD, y se aplican primero a él.
- **Rationale**: Sergio pidió compensar en USD y usar una sola cuenta por contacto.

## R4. Fecha real de erogación

- **Decision**: se reutilizan `vinculos.fuente.cargar()` y `vinculos.cadenas`:
  - `emparejar_cheques` da la fecha de débito de cada cheque propio.
  - `_partes_de_resumenes` da la del débito de cada resumen de tarjeta.
  - Banco y efectivo usan la fecha del movimiento.
  - Valores recibidos usan la fecha de endoso.
- **Rationale**: esa lógica ya está probada en 031 y 030. Lo que falla en 031 es la corrección, no la lectura.

## R5. Notas de crédito y de débito

- **Decision**: las históricas son filas de `Compras` con su tipo de comprobante.
  - Una nota con documento relacionado (`CompraDocumentosRelacionados`) se aplica primero a ese documento.
  - Sin documento relacionado, es un crédito FIFO en su fecha.
  - Las tablas nuevas `nota_*_proveedor` tienen 0 filas, pero el motor las lee igual para el futuro.
- **Relevado (T005, 2026-10-01)**: `Compras.[Tipo documento]` toma los valores 'Factura' (5.965), 'Nota de Crédito' (233), 'Nota de Débito' (225) y 'C. Deposito Cereales' (5). El signo del total define el lado: 224 notas de crédito y 26 facturas tienen total negativo, y la vista las pone del lado Crédito. El motor usa el signo, no el tipo. `CompraDocumentosRelacionados` tiene 2 filas.
- **Percepciones (FR-018)**: `vw_Cns_Total_Compra.GranTotal` ya incluye Ingresos Brutos, Res. gral. 4169/96, Ley de Sellos y los conceptos no gravados. No hace falta un ajuste.

## R6. Cheques de terceros y e-cheqs de acopiadores

- **Decision**: se usa `[Valores Recibidos]` (Fecha Endoso, Destino) cuando existe la fila.
  - La tabla tiene solo 17 filas. Los e-cheqs de Cargill depositados son créditos bancarios del contacto en la fecha del movimiento.
  - Un e-cheq endosado sin fila en valores no se puede rastrear. El contacto queda como excepción con el motivo "endoso sin registro".
- **Rationale**: no se deduce un destinatario (FR-036).

## R7. Retenciones

- **Decision**: `Retenciones`, `Retenciones IVA Granos` y `Retenciones Ventas Hacienda` son créditos del contacto en la fecha del pago o cobro al que pertenecen.

## R8. Persistencia de la simulación y la reversión

- **Decision**: crear tres tablas: `RecalculoFifoEjecucion`, `RecalculoFifoAplicacion` y `RecalculoFifoContacto`.
  - **Simular** escribe solo en esas tablas.
  - **Aplicar** pasa por estos pasos:
    1. Respaldo verificado.
    2. En una transacción por contacto, anula las aplicaciones vigentes del contacto que no son cadena, con el motivo "Reemplazada por FIFO ejecución N".
    3. Inserta las aplicaciones nuevas con `Origen='fifo-032'`.
  - **Revertir** des-anula las aplicaciones de esa ejecución y anula las `fifo-032` que agregó.
- **Rationale**: las anulaciones son lógicas (columna `Anulada`) y la reversión es exacta sin restaurar el respaldo. El respaldo queda como red de seguridad (Constitución II).

## R9. Idempotencia

- **Decision**: el motor ordena todo con claves estables: (vencimiento, número de comprobante, id) para débitos y (fecha, medio, id) para créditos. Los importes se redondean a 2 decimales.
  - Antes de aplicar, se calcula una huella de las aplicaciones resultantes por contacto. Si coincide con la huella de las aplicaciones vigentes, el contacto no cambia.

## R10. Saldo inicial estimado

- **Decision**: el recálculo empieza el 19/04/2010. Si en algún momento los créditos acumulados superan a los débitos acumulados por más de la tolerancia, sin documento posterior dentro de 60 días, se propone un débito sintético de saldo inicial. Su importe es igual al exceso más antiguo no explicado y su fecha es la del primer movimiento.
  - El débito queda en estado "estimado" y no se aplica hasta que Sergio lo confirme.
  - Para las cuentas sin continuidad entre la etapa de Oscar y la de Giamigli, se verifica que el saldo al 29/06/2012 sea 0.

## R11. Aplicación continua

- **Decision**: cuando se asigna contacto a un movimiento o se guarda una compra o venta, se encola el contacto.
  - Un proceso al entrar al sistema, y uno cada hora mientras la aplicación está abierta, recalcula los contactos encolados.
  - Si los controles pasan, aplica. Si no, la propuesta queda en la bandeja.
- **Alternatives considered**: recalcular dentro de cada guardado, descartado porque frena la carga.
