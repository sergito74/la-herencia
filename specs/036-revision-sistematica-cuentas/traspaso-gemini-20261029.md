# Traspaso a Gemini — imputaciones de pagos (spec 036), 29/10/2026

Escrito por Claude Code para el agente que sigue con el trabajo. Antes de tocar nada, leer [GEMINI.md](../../GEMINI.md), la guía compartida y la estrategia vigente: [estrategia-imputaciones-20261029.md](estrategia-imputaciones-20261029.md). La estrategia tiene las reglas fijas aprobadas por Sergio y el cierre de los grupos 2 y 3.

## Qué es el trabajo

Los **saldos** de las cuentas de proveedores ya están conciliados y **no se tocan**. Lo que falta es la **imputación**: qué pago canceló qué factura (tabla `dbo.AplicacionesPago`). Se trabaja por grupos, cada uno con su fuente de verdad.

| Grupo | Estado |
|---|---|
| 2. Pagadas solo con tarjeta (92 cuentas) | **Cerrado** 29/10 (ejecución FIFO 130) |
| 3. Cuentas chicas, 1 a 5 facturas (250) | **Cerrado** 29/10 (ejecuciones 131 y 132) |
| 1. Proveedor con resumen o portal (~15: Bayá Casal, FEDEA, Syngenta…) | **Sigue ahora** |
| 4. Cuenta corriente con muchas facturas (~45: Criado, Agrovet, Coop. Agropecuaria…) | Después del 1, de mayor a menor movimiento |
| 5. Cuentas en US$ (26) | Casi todas caen en el grupo 1 |

Ya hechas aparte: Cargill (avisos del portal), Lartirigoyen (extranet) y Jáuregui y Morales (falta el punto de "Pendientes sueltos").

## Reglas que no se discuten (Sergio)

- **Grupo 1: copiar las imputaciones del resumen del proveedor. Nunca FIFO ni automático.** Si el proveedor emite resumen, ese resumen manda.
- **FIFO estricto (grupo 4):** compras por fecha de vencimiento (sin vencimiento = contado = fecha de emisión), pagos por fecha de erogación, y el pago va primero a la factura vencida más vieja. **Antes del FIFO, integridad:** que no falten ni sobren facturas o pagos, verificado contra el comprobante.
- **Redondeos:** se redondea la **factura** a lo pagado, nunca se imputan pagos por centavos. Se trabaja con **porcentajes y criterio**, no con montos fijos ni ventanas de días:
  - **Hasta 0,10%:** automático.
  - **Entre 0,10% y 1%:** por causa (redondeo del pago, descuento, retención, TC).
  - **Más del 1%:** nunca es redondeo.
- **No romper saldos:** el saldo de cada cuenta antes y después, al centavo. Lo controla `bimonetaria.cargar_cuenta(ct, refrescar=True)` (`backend/src/features/auditoria_cuentas/bimonetaria.py`); sin `refrescar` devuelve un valor en caché.
- **US$:** cada cuenta se lleva al TC del comprobante, y las diferencias van con ND/NC, nunca con el BNA del día.
- **Verificar antes de informar:** ningún hallazgo automático se presenta como error sin cruzarlo con el comprobante (PDF). Las alarmas van rotuladas "a verificar".
- **Planillas:**
  - Llevan todas las filas y una columna "¿Cambia?".
  - Se abren directo en Excel con `Start-Process`; los enlaces del chat no abren.
  - No se suben a git, porque tienen datos financieros.
- **No repreguntar** lo que Sergio ya cerró. Antes de reabrir una cuenta, revisar las memorias y la spec.
- **Escrituras:** solo en la base `WC`, nunca en `LaHerencia`. Tomar un respaldo antes de grabar (`backup_verificado`) y registrar la corrección en `dbo.AuditoriaCorrecciones`.
- **Portales externos** (bancos, proveedores, ARCA, ARBA): solo con autorización explícita de Sergio. Los que tienen autorización de solo lectura están en la bóveda (spec 042): Cargill, Bayá Casal y ARCA de Lucy.
- **Cuenta 97 ("XXXXXXXXX", proveedor genérico):** sin tocar hasta saber de quién es.

## Herramientas (desde `backend/`)

- **Motor FIFO:** `src/features/recalculo_fifo/`.
  - `entrada.armar(ids)` arma los movimientos.
  - `motor.recalcular(...)` calcula el FIFO.
  - `ejecuciones.simular(ids, usuario)` guarda una simulación y devuelve su `idEjecucion`.
  - `ejecuciones.aplicar(id, ids, True, usuario)` toma su propio respaldo y graba.
  - La regla de importe idéntico (`regla_029`) está **apagada**; no volver a usarla.
- **Cómo llevar una factura a su total:** escalar `[Precio Unitario]` de `Det_Compras` con el factor `(objetivo − (GranTotal − TotalDetalle)) / TotalDetalle`. Si la factura no tiene renglones, ajustar `[Gastos Varios]`. Hay ejemplos en `scripts/grupo3_redondeo_036.py` y `scripts/jym_redondeo_tickets_036.py`.
- **Diagnóstico por grupo:** `scripts/grupo2_tarjeta_diagnostico_036.py` y `scripts/grupo3_diagnostico_036.py` sirven de plantilla. Son de solo lectura y llevan `--aplicar` aparte.
- **Para que Sergio revise el FIFO de una cuenta:** `scripts/revision_imputaciones_029_036.py <salida.xlsx> <ids> --todas`.

## Siguiente paso: grupo 1

1. Listar las cuentas con resumen o portal: Bayá Casal, FEDEA (217), Syngenta, Criado y las que tengan resumen en los mails o en `Documents`.
2. Para cada una, ubicar la fuente:
   - **Bayá Casal:** portal; ver la memoria `reference_portal_baya_casal`.
   - **FEDEA:** su portal mostró saldo 0.
   - **Las demás:** resúmenes en PDF o en mails (Outlook por COM, solo lectura).
3. Copiar sus imputaciones a `AplicacionesPago` con `Origen='manual'`. El modelo es `scripts/aplicacion_cargill_avisos_036.py`.
4. Al terminar el grupo, entregar un resumen de una página: cuentas imputadas, excepciones y su causa.

## Pendientes sueltos

- **Jáuregui y Morales:**
  - Aplicar la regla de redondeo por porcentaje a los pares 1 a 1.
  - Llevar 3 facturas al total del ticket: 0003-00085357 → 15.190,00; 0007-00002353 → 40.390,00; 0011-00010603 → 1.582.000,00.
  - Volver a correr el FIFO.
  - Hay 4 facturas sin PDF en disco; hay que volver a bajarlas o pedirlas.
- **Enlaces rotos:** documentos de compras que apuntan a archivos `.crdownload` o a rutas relativas.
- **Centavos de tarjeta sin imputar:** de $0,01 a $0,08 en Autopistas del Sol, Grupo Concesionario del Oeste y Carrefour.
- **Excepciones del grupo 3:** Gentos y Galicia Seguros tienen pagos de más (Galicia Seguros espera respuesta de Sergio). Electricidad Lavalle tiene un saldo de $9.931,72, en la lista de pendientes.
- **Planillas .xlsx de la 036 sin commitear:** a propósito, porque tienen datos financieros.
