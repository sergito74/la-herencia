# Quickstart: validar 031

Requisitos: backend y frontend levantados contra WC, y sesión de Administrador.

## 1. Tests

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q tests/test_vinculos_*.py tests/contract/test_integridad_vinculos_api.py
```

Las funciones de unificación, prorrateo, detección y reemplazo son puras y se testean sin tocar WC.

## 2. Control antes de corregir (línea de base)

Abrir `GET /api/integridad-vinculos/control`. Se espera que los totales sean del orden de la auditoría:

- ~180 documentos excedidos;
- ~1.736 aplicaciones con fecha incoherente (1.646 compras + 90 ventas hacienda);
- ~340 con moneda mezclada.

## 3. Fuente unificada en el flujo

En Finanzas → Flujo de caja por Rubro, abrir un mes con un "Pago Visa" vinculado a su resumen. En el detalle, el débito aparece repartido por los rubros de las facturas del resumen, con vía `tarjeta`, y ya no en "Pendiente de aplicar" (SC-002).

## 4. Propuesta y revisión

1. Generar un lote.
2. Revisar los grupos.
3. Destildar un ítem.
4. Elegir el candidato de un reemplazo ambiguo.
5. Intentar aplicar con ambiguos sin elegir → debe devolver 409.

## 5. Aplicar y revertir

1. Aplicar el lote. Verificar el `.bak` y el `RESTORE VERIFYONLY`.
2. El control debe dar 0 en `documento-excedido` y en `doble-imputacion` (SC-001).
3. Verificar que ninguna aplicación con `Origen='manual'` cambió (SC-006).
4. Revertir el lote. Los conteos del control deben volver a la línea de base (SC-004).
5. Volver a aplicar.

## 6. Bloqueo al guardar

Desde Aplicaciones de pago, aplicar a una factura ya pagada:

- Con un exceso > 2% → debe dar 422.
- Con un exceso ≤ 2% → debe guardar y mostrar la advertencia.

## 7. Rendimiento

Con el control completo, medir el tiempo de respuesta. Debe ser menor a 10 s (SC-005).

## Resultados de validación (2026-09-30, WC real)

### Línea de base del control (T017)

Antes de aplicar ninguna corrección:

| Categoría | Hallazgos |
|---|---|
| Facturas imputadas de más | 949 |
| Movimientos aplicados de más | 27 |
| Dobles imputaciones | 375 |
| Pago más de 60 días anterior a la factura | 3.057 |
| us$ contra pesos | 253 |

- El control completo tarda **0,7 s** (SC-005: menos de 10 s).
- El Flujo por Rubro de 12 meses pasa de 4,2 s a 4,8 s.
- Hay más casos que en la auditoría inicial (1.736 fechas, 180 excedidas) porque ahora se cuentan también las aplicaciones automáticas de **consumo de tarjeta → factura** (`OrigenMovimiento='tarjetas'`). Es un segundo lugar, paralelo a `Tarjetas_Resumenes_Lineas_Compras`, donde el FIFO aplicó consumos de 2025 a facturas de 2020 que ya tenían su consumo imputado.

### Fuente unificada en el flujo (T012, SC-002)

- **$23,97 M** en 181 movimientos bancarios dejan "Pendiente de aplicar" y pasan a sus rubros por herencia: pagos de resumen → consumos → facturas, y débitos de cheque → facturas del cheque.
- El neto total del período no cambia; solo se reparte distinto.

### Revisión del especialista contable (T025)

La persona `administracion-cuentas` revisó una muestra del lote. Se incorporaron estas reglas:

- **Factura excedida:** se anula primero lo de banco o efectivo y la cadena de tarjeta queda para el final. Si la aplicación supera el excedente, se ajusta parcialmente (anular + recrear por lo que cierra) en lugar de anularla entera.
- **Ventas con cobro muy anterior a la venta:** siempre certeza media, porque pueden ser anticipos o señas.
- **Reemplazos:** tope de 365 días hacia adelante.
- **Moneda mezclada:** si las pesificaciones de un mismo movimiento, sumadas, no entran en él, el ítem pasa a certeza media.
- **Pagos en efectivo:** se usa su importe para la regla de us$ (antes se pesificaban siempre).

Orden sugerido para aplicar:

1. Primero: doble imputación, fecha incoherente alta y los reemplazos únicos.
2. Ítem por ítem: documento excedido media, fecha incoherente media, moneda mezclada media y reemplazos ambiguos.

### Lote real (T026)

El lote **#3** quedó en estado **propuesto** y no se aplicó. Los lotes #1 y #2 se descartaron al ajustar las reglas.

| Grupo | Acción | Ítems |
|---|---|---|
| Doble imputación / alta | Anular | 372 (+34 reemplazos) |
| Documento excedido / alta | Anular | 654 (+35 ajustes) |
| Documento excedido / media | Anular | 286 (+36 ajustes) |
| Fecha incoherente / alta | Anular | 2.217 (+256 reemplazos) |
| Fecha incoherente / media | Anular | 674 (+64 reemplazos) |
| Moneda mezclada / alta | Pesificar | 15 |
| Moneda mezclada / media | Pesificar | 199 |
| Reemplazos ambiguos | Elegir de a uno | 722 |

Simulación sin escribir: si se aplica todo menos los ambiguos, el control queda así:

- fecha incoherente: 0;
- moneda mezclada: 0;
- documento excedido: 93;
- movimiento excedido: 29;
- doble imputación: 9.

Esos remanentes no se corrigen automáticamente: vienen de imputaciones manuales o de consumos de tarjeta en `Tarjetas_Resumenes_Lineas_Compras`, que la corrección no toca. Se revisan a mano desde el control. Por eso **SC-001 no llega a 0 de forma automática**.

### Pendiente (T026b)

Después de que Sergio aplique el lote, falta verificar SC-001, SC-004 y SC-006 sobre WC.

### Backups

- `WC_pre_031_20260930_205534_994598.bak`: antes de crear las tablas.
- Cada aplicación de lote toma su propio backup antes de escribir.
