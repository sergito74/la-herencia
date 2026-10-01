# Research: Integridad de vínculos (031)

Relevamiento hecho sobre el código y la base WC el 2026-09-30.

## R1. Causa raíz de las aplicaciones automáticas erróneas

- **Hallazgo**: `aplicaciones_pago/sugerencia.sugerir` hace un FIFO puro. Toma los documentos pendientes del contacto, del más viejo al más nuevo, sin mirar la fecha del movimiento. El saldo pendiente sale de `documentos.documentos_pendientes`, que solo lee `AplicacionesPago`. Las facturas pagadas con tarjeta o cheque figuran "abiertas" y el FIFO las toma: por eso aparecen transferencias de 2019 aplicadas a facturas de 2023. Además, `saldoPendiente` está en la moneda del documento: para facturas en dólares compara us$ contra pesos.
- **Decisión**: corregir `sugerir` y `documentos_pendientes`, no solo los datos. Si no, el próximo uso de la conciliación, automática o manual, vuelve a producir los mismos errores. Tres cambios:
  - El saldo pendiente se calcula desde la fuente unificada (R3).
  - Solo son candidatos los documentos con fecha ≤ fecha del movimiento + 60 días.
  - El saldo de documentos en dólares se pesifica con el TC de la factura.
- **Alternativas**: solo limpiar los datos. Se descarta porque el defecto vuelve a aparecer.

## R2. Vínculo cheque propio ↔ débito bancario

- **Hallazgo**: no hay una tabla que una `[Valores propios]` con su débito. El débito BNA trae el número de cheque en el concepto ("48HS. BANCOS 003620071") y Galicia lo trae como "Echeq Galicia Nro: 120". Con número de cheque + importe exacto se emparejan 122 de 670 débitos "48HS. BANCOS" del BNA.
- **Decisión**: emparejamiento determinístico por número de cheque (contenido en el concepto) + importe (±0,01) + fecha de débito ≥ fecha de emisión. Los débitos sin pareja siguen siendo movimientos comunes, sin herencia. `[Valores propios]` llega hasta 2021, así que los Echeq de Galicia recientes no se emparejan hasta que se carguen sus cheques.
- **Alternativas**: tabla manual de vínculos cheque ↔ débito. Queda como mejora futura si el emparejamiento resulta insuficiente.

## R3. Fuente unificada de vínculos

- **Hallazgo**: cinco tablas guardan vínculos y cada consumidor lee algo distinto:
  - `AplicacionesPago`: la leen el flujo 030 y `documentos_pendientes`.
  - `Tarjetas_Resumenes_Pagos` → `Tarjetas_Resumenes_Lineas` → `Tarjetas_Resumenes_Lineas_Compras`: pago → resumen → consumo → factura.
  - `ConciliacionesTesoreria`: medio → documento, incluye valores propios, Mercado Libre y Galicia, con documentos Compras, Impuestos y Remuneraciones.
  - `BackfillImpuestosVinculos` (029).
- **Decisión**: un módulo Python `features/vinculos/` que arma, en una o pocas consultas en bloque, dos niveles:
  - **Nivel documento**, para saber cuánto tiene pagado cada factura. Se suman las vías sin duplicar: tarjeta (consumos), valor propio (cheques) y aplicaciones directas. Una aplicación directa de un débito que ya pertenece a la cadena de esa factura no suma.
  - **Nivel movimiento**, para saber qué documentos paga cada movimiento de dinero. Un débito de resumen hereda los consumos imputados del resumen, en proporción al pago sobre el total del resumen. Un débito de cheque hereda los documentos del cheque.

  El flujo 030, `documentos_pendientes` y el control de integridad consumen este módulo.
- **Alternativas**: una vista SQL nueva en WC. Se descarta porque el prorrateo y las reglas de precedencia son más claros y testeables en Python, y así no hace falta cambiar el esquema para leer.
- **Dos niveles (FR-017)**: a nivel documento, los consumos imputados y los cheques conciliados cuentan como pagados aunque no se hayan debitado; si no, el FIFO los volvería a ver abiertos. A nivel movimiento, solo cuenta lo debitado.
- **Nota**: el saldo de cuentas corrientes por contacto (`vw_MovimientosCuenta_Base`) se calcula con los pagos del circuito heredado, no con aplicaciones. No cambia. Lo que sí cambia es el estado pagado o pendiente de cada factura.

## R4. Alcance de ventas

- **Hallazgo**: 90 de 240 aplicaciones a Venta Hacienda usan un movimiento más de 60 días anterior a la venta. Venta Granos: 0 de 17.
- **Decisión**: la detección y la corrección se aplican también a ventas, con las mismas reglas.

## R5. Lotes, backup y reversión

- **Decisión**: reusar el patrón de lotes de 029 (`backfill_impuestos`): tabla de lote + ítems, estados, backup `COPY_ONLY, CHECKSUM` + `RESTORE VERIFYONLY` antes de escribir, y reversión por lote.
  - Anular = `Anulada=1` con `MotivoAnulacion`, `UsuarioAnulacion` y `FechaAnulacion`, columnas que ya existen en `AplicacionesPago`.
  - Pesificar = anular la aplicación en us$ y crear una nueva en pesos, así se conserva la original.
  - Los reemplazos son aplicaciones nuevas con `Origen='correccion-031'`.
- **Alternativas**: modificar el importe en el mismo registro (UPDATE). Se descarta porque pierde la trazabilidad (principio IV).

## R6. Certeza y agrupación para la revisión

- **Decisión**:
  - **Certeza alta**:
    - doble imputación con cadena confirmada;
    - moneda mezclada;
    - fecha incoherente > 365 días.
  - **Certeza media**: fecha incoherente entre 61 y 365 días.
  - **Reemplazo ambiguo**: más de un candidato. Se elige de a uno.

  Los reemplazos con candidato único se agrupan con su anulación.

## R7. Bloqueo al guardar (FR-012)

- **Decisión**: una función `verificar_exceso(documento | movimiento, importe_nuevo)` en `features/vinculos/`, llamada desde:
  - `aplicaciones_pago.repository.crear` (y de ahí la conciliación histórica);
  - `tarjetas_resumenes` (imputación de consumos);
  - `conciliacion_tesoreria`.

  Devuelve 422 si el exceso supera el 2%, y una advertencia en la respuesta si está dentro del 2%.

## R8. Rendimiento

- **Decisión**: la fuente unificada se arma con 5 consultas en bloque (≈ 12 k filas en total) y se indexa en memoria por documento y por movimiento. El objetivo es menos de 10 s para el control completo (SC-005). No hay caché, igual que en 030.
