# Primera etapa: simulación de 9 contactos

**Simulación**: ejecución N.º 2, del 2026-10-01. La N.º 1 se descartó porque usaba el motor anterior a la revisión financiera.

**Escrituras**: ninguna en `AplicacionesPago`. El resultado vive solo en las tablas `RecalculoFifo*`.

**Tiempo**: 5,5 segundos.

## Serie del dólar BNA (T004)

La serie `dbo.[Dolar BNA]` (`Vend_Divisa`) cubre todos los días del 05/04/2010 al 30/09/2026. La conciliación empieza el 19/04/2010, así que no hay huecos.

## Resultado por contacto

Importes en millones de pesos. Los documentos en dólares están pesificados al tipo de cambio de la factura.

- "Dinero sin aplicar" es el dinero que no encontró documento.
- "Cerraba" y "Cierra" usan el mismo criterio de FR-010: ningún documento sobreaplicado, y el dinero aplicado igual al menor entre lo pagado y lo facturado.

| Contacto | Facturado | Pagado/cobrado | Aplicado antes | Aplicado después | Dinero sin aplicar | Cerraba | Cierra | Tendencia | Motivo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cargill (258) | 453,61 | 548,83 | 61,80 | 456,81 | 118,42 | No | No | igual | pago de más, aplicado distinto |
| J y M de la Serna (47) | 70,24 | 62,24 | 61,38 | 68,31 | 0 | No | Sí | mejora | — |
| Ganaderos de Elordi (384) | 61,32 | 61,32 | 60,24 | 65,87 | 0 | No | Sí | mejora | — |
| Jauregui y Morales (48) | 6,61 | 8,48 | 4,35 | 6,68 | 1,87 | No | No | igual | pago de más, aplicado distinto |
| Miguel Basterrechea (220) | 5,73 | 5,39 | 5,29 | 5,55 | 0 | No | Sí | mejora | — |
| Coop. Eléctrica Bolívar (23) | 4,00 | 3,66 | 3,44 | 3,66 | 0 | No | Sí | mejora | — |
| Supermercado Actual (249) | 1,46 | 1,46 | 2,73 | 1,46 | 0 | No | Sí | mejora | — |
| Colombo y Colombo (340) | 1,03 | 1,03 | 1,03 | 1,03 | 0 | Sí | Sí | igual | — |
| Autopistas del Sol (276) | 0,51 | 0,50 | 0,83 | 0,50 | 0 | No | Sí | mejora | — |

## Lectura

- **Ninguna cuenta empeora.** Colombo cerraba y sigue cerrando.
- **J y M y Elordi no cerraban por poco.** La diferencia era de $0,86 M y $1,08 M de cobros que no estaban vinculados a ninguna liquidación, en su mayoría en efectivo. El recálculo los aplica.
- **Supermercado Actual y Autopistas del Sol tenían documentos sobreaplicados.** Eran consumos de tarjeta imputados dos veces. Ahora el aplicado coincide con lo facturado.
- **Jauregui queda como excepción.** Se pagaron $1,87 M más que lo facturado y no hay facturas posteriores. Faltan facturas o hay pagos duplicados.
- **Cargill queda como excepción.** El dinero supera a los documentos en unos $95 M. Además, quedan $118 M de dinero sin aplicar. Probablemente faltan liquidaciones de granos o compras, o hay e-cheqs endosados sin registro en Valores Recibidos.
- **Anticipos largos:** quedan marcados para revisar, pero no hacen fallar la cuenta. Las medianas de días de adelanto son las de la tabla de abajo.

| Contacto | Mediana de días de adelanto |
| --- | --- |
| Coop. Eléctrica Bolívar | 17 |
| J y M de la Serna | 98 |
| Jauregui y Morales | 111 |
| Cargill | 211 |

## Revisión financiera (checkpoint)

El especialista financiero (07) revisó el motor el 2026-10-01 y encontró tres problemas bloqueantes. Los tres se corrigieron antes de esta simulación:

1. **Compensación sin orden de fechas.** Se compensaban compras y ventas de toda la historia antes de aplicar el dinero. Ahora hay un solo recorrido cronológico: cada documento compensa lo pendiente del otro lado a su fecha.
2. **"Cierra" incompleto.** No verificaba que lo aplicado fuera el menor entre lo pagado y lo facturado. Ahora se verifica por cuenta proveedor y por cuenta cliente (control "aplicado distinto").
3. **"Cerraba" circular.** Se comparaba contra el propio FIFO. Ahora antes y después se miden con el mismo criterio, contra lo pagado y lo facturado.

También se corrigieron cuatro puntos más:

- **TC del anticipo:** se toma el día anterior al pago.
- **Moneda de la cuenta:** es USD si hay documentos en dólares.
- **Reintegros:** se marcan para revisión.
- **Elección manual:** se marca solo si pide más que el total del documento.

Queda abierto el punto 8: las conciliaciones de tesorería con documento se tratan como elección explícita. Ver la nota en spec FR-024.

## Pendiente de Sergio

- [x] Revisar la simulación y confirmar la aplicación a los 7 contactos que cierran. Sergio lo aprobó el 2026-10-01.

## Aplicación (2026-10-01)

**Ciclo de validación (T022)**:

1. Se aplicó la simulación N.º 2.
2. Se revirtió.
3. Quedaron las mismas 8.390 aplicaciones vigentes, con los mismos identificadores y la misma suma de $534.351.767,63 (SC-006).

**Ajustes antes de la aplicación definitiva**:

- **Copias de tarjeta.** Las copias automáticas de consumos de tarjeta que ya tienen su vínculo real en `Tarjetas_Resumenes_Lineas_Compras` se reemplazan. En Coop. Eléctrica, Supermercado Actual y Autopistas del Sol vinculaban cada consumo a otra factura y duplicaban importes.
- **Retenciones y compensaciones.** Ahora se guardan en `AplicacionesPago`, con los orígenes nuevos `retenciones`, `ret-*` y `comp-*`.
- **Documentos en us$.** Se guardan al TC de la factura. La diferencia de cambio queda en el recálculo.

**Aplicación definitiva**: se usó la simulación N.º 3, con respaldo `WC_032-aplicar-3_20261001_135205_630698.bak`.

| Concepto | Cantidad |
| --- | --- |
| Contactos aplicados | 7 |
| Aplicaciones nuevas | 660 |
| Aplicaciones anteriores anuladas | 1.086 (484 eran copias de tarjeta) |

**Verificación (simulación N.º 4 y aplicación N.º 5)**:

- Con los vínculos reales, 6 de los 7 contactos cierran en el "antes".
- Volver a aplicar no cambió nada: los 7 quedaron sin cambios (SC-005).
- Autopistas del Sol conserva $1.596 sobreaplicados en 7 facturas. Son copias de consumos de tarjeta que no están imputados en el módulo de tarjetas. El recálculo no decide a qué factura corresponden: hay que imputarlos desde la pantalla de tarjetas.

**Lotes de 031 (FR-016)**: el lote 4 quedó descartado y `POST /api/integridad-vinculos/lotes` responde 410.

## Pendiente

- Cargill y Jauregui, uno por uno.
- Segunda etapa: simular todos los contactos y aplicar por volumen.
