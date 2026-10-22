# Cajas de efectivo y cuentas de socios: diagnóstico y plan (22/10/2026)

Pedido de Sergio, 22/10/2026: revisar en conjunto Lucy, Condominio LSC, Virginia y el lado socio de Sergio, junto con las cuentas de Giamigli (efectivo y bancos), y crear o reconstruir la **cuenta efectivo de Giamigli** y la **caja chica**. Reconstruir la historia con toda la información disponible.

**Saldos actuales informados por Sergio:**

| Caja | Saldo |
|---|---:|
| Caja efectivo Giamigli | **$381.785,15** |
| Caja chica | **$96.907** |

## Diagnóstico (solo lectura)

| Fuente | Qué tiene | Saldo |
|---|---|---:|
| Planilla `Cajas Giamigli.xlsx`, hoja "Caja Efectivo Pesos" | 1.844 movimientos (17/02/2011 → 15/10/2026). La columna Saldo termina en 381.785,15, pero la suma de importes da **$154.037,63** (la columna de saldo arrastra algo más: saldo inicial o recuentos; investigar) | 381.785,15 |
| Planilla, hoja "Caja chica campo" | 100 movimientos (07/10/2020 → 15/10/2026) | 96.907 |
| Planilla, hoja "Recuento Caja Efectivo" | 80 arqueos (06/2020 → 10/2026), con diferencia constante de ~$249,10 | — |
| Planilla, otras hojas | "Caja Efectivo Dolares" (6, 2023), "Caja Sindicatos" (41, 2019–2021), "Caja Elisabet" (3, 2019) | — |
| WC `MovimientosCajaEfectivo` (migración 027 + 4 cargas de la barrida) | Caja "GiamigliSA": 1.147 movimientos. Caja "CampoChica": 100 | GiamigliSA **$635.999,83** (no coincide); CampoChica **$96.907** (coincide) |
| WC `MigracionCajasGiamigliRevision` | 66 filas de la planilla no migradas (62 sin fecha, 2 sin importe, 2 con Debe y Haber a la vez) | — |
| WC `Pagos efectivo` (Access) | Pagos por "caja" asignados a contactos: La Herencia 1.561, Condominio 308, Particular L 256, Particular S 205, Ferias del Centro 104, J y M 63, CampoChica 47, GiamigliSA 29, etc. | — |
| WC `Caja Efectivo` (Access, 1.424) y `Cajas` (catálogo de 14) | Tablas heredadas, sin uso en la vista | — |

**Por qué no coincide la caja de Giamigli:** la migración 027 (FR-003/FR-008) **no copió** los movimientos de la planilla que ya existían en Access como pago a un proveedor (misma fecha, proveedor e importe). Esos pagos están en `Pagos efectivo`, en las cajas "La Herencia" y otras. La caja migrada tiene 1.147 de 1.844 movimientos: le faltan unos 630 egresos, que están en Access. Hoy no existe un libro de caja único y completo.

## Plan propuesto (por etapas, con aprobación de Sergio en cada una)

1. **Libro de caja Giamigli completo.** La planilla manda (1.844 movimientos). Se reconstruye 1:1 y cada fila se vincula con su contraparte: pago a proveedor en Access (`Pagos efectivo`), traspaso bancario (retiro o depósito BNA/Galicia), movimiento de socio (aporte o retiro de Sergio, Lucy, Ceci o del Condominio) o gasto sin comprobante. Validación: el saldo de la columna de la planilla y los arqueos de "Recuento". Explicar la diferencia entre la suma de importes ($154.037,63) y el saldo ($381.785,15).
2. **Caja chica.** El saldo ya coincide. Vincular cada "Aporte" con su salida en la caja grande o en el banco.
3. **Bancos ↔ caja.** Identificar todos los retiros de efectivo y depósitos (incluidos los hechos a través de las cuentas de los socios, como los de 2016–2017) como traspasos internos.
4. **Socios en conjunto.** Revisar a la vez Sergio (socio 1 / contacto 5670), Lucy (socio 2 / contacto 390), Condominio LSC (socio 3 / contacto 549), Ceci (socio 4) y Virginia (564), con la caja y los bancos como hilo común. Aplicar a Lucy la separación empleada/socia que se aplicó a Sergio. Usar las reglas vigentes: compras particulares, retiros de ganancias, opción A para cobros devueltos a caja.
5. **Cierre.** Ficha de cada cuenta, con su saldo externo o su justificación.

## Preguntas abiertas para Sergio

1. ¿La hoja "Caja Efectivo Pesos" es la fuente de verdad del efectivo de Giamigli desde 2011?
2. ¿Las cajas de Access "La Herencia" y "GiamigliSA" son la misma caja física? ¿Y "Condominio"? ¿Era otra caja, del Condominio?
3. ¿Se levanta la pausa de Condominio LSC y Virginia para este trabajo?

## Respuestas de Sergio (22/10/2026)

1. La hoja "Caja Efectivo Pesos" no es necesariamente la fuente de verdad, pero es lo mejor que tenemos: se usa como base.
2. Las cajas de Access "La Herencia" y "GiamigliSA" son la misma caja física. "Condominio" y Condominio LSC son lo mismo.
3. Se levanta la pausa de Condominio LSC y Virginia.
4. **Lucy no tiene sueldo:** no hace falta separar su cuenta en empleada y socia.

## Etapa 1: libro de caja de Giamigli (APLICADO, `caja_giamigli_libro_completo_036.py`)

- Columnas nuevas en `MovimientosCajaEfectivo`: **FilaPlanilla** (fila de la hoja) e **IdPagoEfectivo** (pago de Access del mismo egreso).
- Las 1.147 filas ya migradas quedaron vinculadas a su fila de la planilla. Se agregaron las 697 omitidas por la 027; 651 quedaron vinculadas a Access (487 en la caja "La Herencia" y 164 en "Condominio"). Las 46 sin pago en Access son gastos chicos de 2011–2015.
- Apertura **PROVISORIA** del 13/07/2015 por **$227.747,52** = ingresos de 2011–jul-2015 que la planilla no registra. La columna Saldo de la hoja arranca en la fila 486 (14/07/2015) con $15.491,20.
- **Libro GiamigliSA: 1.845 movimientos, saldo $381.785,15 = saldo real.** Caja chica (CampoChica): $96.907 = saldo real, sin cambios.
- Corrección durante la carga: dos movimientos existentes con Concepto NULL (557 y 565, $180 y $800) se habían reinsertado; se borraron los duplicados. El script ya filtra con ISNULL.
- Este libro **no entra** en `vw_MovimientosCuenta_Base`: no duplica las cuentas de los contactos, que se llevan por `Pagos efectivo`.

**Siguiente (etapas 2–3):**
- Reconstruir la apertura de $227.747,52: ingresos de caja de 2011–2015 a partir de los retiros del BNA, la caja Condominio de Access (308 pagos) y los aportes.
- Vincular las cargas de la caja chica y los retiros y depósitos bancarios como traspasos.
- Revisar las 46 filas sin pago en Access: varias figuran en Access como Particular S (pagadas por Sergio), pero la planilla las muestra como pagadas por la caja.
