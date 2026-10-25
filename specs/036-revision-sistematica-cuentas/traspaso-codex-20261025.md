# Traspaso a Codex — 25/10/2026

Este documento es el punto de entrada para continuar. Reemplaza a `traspaso-codex-20261023.md`, cuyos pendientes que siguen abiertos están repetidos en la sección 4. Antes de empezar, leer `.specify/memory/agent-guidance.md` y `.specify/memory/constitution.md`. Todo lo de abajo está en `main` (último commit de esta tanda: cruce de cuentas de socios).

El detalle de cada paso, con evidencia, respaldos y reglas, está en [condominio-continuacion-ampliada-20261024.md](condominio-continuacion-ampliada-20261024.md), desde la sección «Cierre del Condominio — respuestas de Sergio A–J».

## 1. Hecho el 25/10

### Spec 041: impuestos particulares (cerrada, 39/39)
- Una boleta de impuesto se puede cargar a un socio (o al Condominio) desde la ficha (`ImpuestoParticularPanel`), con devoluciones vinculadas, anulación y padrón de partidas. En la grilla hay columna y filtro «A cargo de socio».
- Caso real: el Impuesto 3206 (Inmobiliario Complementario 3/2017) quedó a cargo del Condominio y devuelto (Debe 3153 / Haber 3150).
- Evidencia: `specs/041-impuestos-particulares/validacion.md`.

### Condominio LSC (socio 3): cerrado
| Punto | Resultado | Script / regla |
|---|---|---|
| 68 pagos «puente» 2011–2014 | 64 con débito HSBC del Condominio → Haber del socio 3 ($14.223,31); 3 en efectivo de Lucy → Haber del socio 2 ($470,22) | `condominio_68_pagos_cierre_036.py` |
| Cheques de la venta del camión | Los «$3.134» de la planilla son cheques Maignal de $3.143 (BNA 10626/10668/10721) → contacto 549; asientos 2990/2991/2993 corregidos | `bna_cheques_camion_3143_036.py` |
| AFIP jun-2011, cheque 2926, pago 581 (UATRE) | Cerrados sin cambios (ya estaban) | — |
| 3 BNA sin asiento | 18635 Debe $4.134 (IVA/IIBB del Condominio pagado por Giamigli); 10348 y 11240 Haber (transferencias del Condominio) | `condominio_h_bna_036.py` |
| 13 depósitos BNA sin contacto | 7 identificados como cobros de hacienda y 5 probables; quedan sin contacto a propósito (el cobro ya está en la cuenta del cliente) | ídem (solo auditoría) |
| Caja 3224 ($400.000) | Fecha corregida de 2024 a 11/09/2025 | regla `caja-condominio-3224-fecha-036` |
| 5 movimientos 2016 | Explicados con `Documents/Alquileres urbanos/Condominio LSC/Cajas/Cajas Abril - Junio 2016.pdf`: canje de cheques de Ferias por efectivo, mitad de Criado, gastos bancarios. Ninguno lleva asiento. | — |
| Motosierra Agropark 2016 | Pagada con la **Diners de Lucy**: 6 pagos forma 20 a Agropark; BNA 16502–16507 → contacto 390 como reintegro de Giamigli; Lucy neto 0 | `motosierra_diners_lucy_036.py` |

### Caja Giamigli 2011 – 13/07/2015: reconstruida
- El ajuste de «ingresos no identificados» (mov. 1947) bajó de $144.350,52 a 0. Quedó como «Aporte en efectivo Lucy (no registrado)» de $8.996,67, fechado 24/05/2013 y acreditado en el socio 2.
- Se agregaron:
  - 39 cobros en efectivo (forma 8);
  - 54 pagos en negro a Sierra;
  - 8 depósitos de efectivo en el BNA;
  - 7 cheques propios cobrados por caja;
  - 5 pagos de Access que faltaban.
- Inmobiliario nov-2011: lo pagó el BNA (10196 → ARBA). Se borró el pago 208 y se anuló el egreso 1333.
- Traspaso Sucesión → Giamigli: el cheque 18505 y el depósito 10431 abrieron la cuenta BNA 2 de Giamigli el 30/03/2012.
- El retiro de Sergio BNA 11350 ($2.000, 2014) va al socio 1, contacto 5670.
- Los saldos de la caja no cambiaron: $22.786,96 al 13/07/2015 y $381.785,15 al final.
- Scripts: `caja_giamigli_reconstruccion_2011_2015_036.py`, `caja_giamigli_5_pagos_2011_2015_036.py`, `caja_giamigli_arba_lucy_036.py`.

### Cuentas de socios: cruce sistema ↔ `Cajas Giamigli.xlsx`
- Todas las filas de las hojas de socios están en el sistema.
- Los asientos de más que tiene el sistema son decisiones documentadas.
- Las únicas filas que faltan son:
  - Lucy «Cambio» 27/04/2023: −$30, bajo el umbral;
  - Sergio Samsung: es el asiento 4, con $0,99 de diferencia;
  - Sergio fila 346 (−$485.400): anulada a propósito, el pago de balance 2025 va al Condominio.
- `MigracionCajasGiamigliRevision`: 66 filas de Cuenta Sergio/Lucy marcadas como resueltas.

## 2. Decisiones pendientes de Sergio (preguntadas el 25/10, sin respuesta)

1. **Planilla vs sistema.**
   - Propuesta: llevar las cuentas de socios solo en el sistema (Cajas y socios) y dejar `Cajas Giamigli.xlsx` como histórico.
   - Alternativa: generar un listado de los más de 100 asientos que la planilla no tiene y de la fila 346 que hay que quitar.
2. **Valuación de aportes anteriores al 16/03/2020.**
   - La regla vigente es 100% US$ al BNA de la fecha. Con esa regla, el Condominio queda con US$ 136.011 a su favor ≈ **$211,6 M** al 21/10/2026.
   - Hay que confirmar la regla o aplicar 50% US$ / 50% kg también antes de 2020.
   - **No usar los saldos valuados de socios para decisiones hasta que conteste.**

Saldos actuales, a favor del socio, valuados al 21/10/2026 (INMAG 3.926,16, dólar 1.520):

| Socio | US$ | kg | Deuda actualizada |
|---|---:|---:|---:|
| Sergio | 5.550,40 | 4.037,25 | $24.287.478 |
| Lucy | 2.534,57 | 717,18 | $6.668.312 (+ mutuo 2018 US$ 46.440) |
| Ceci | 57,47 | 27,79 | $196.459 |
| Condominio | 136.011,17 | 1.228,86 | $211.561.684 |

## 3. Reglas y datos nuevos (no volver a preguntar)

- **Sucesión:** comprobantes a nombre de la Sucesión (o consumidor final en esa época) = gasto de Giamigli. Fue la etapa previa del negocio, antes de la S.A.
- **BNA:** `Movimientos BNA.IdCuentaBancaria` 1 = cuenta de la Sucesión (sep-2010 a jun-2012); 2 = Giamigli S.A. (desde 30/03/2012); 3 = desde 2022.
- **Cobros en `Pagos efectivo`** (importe negativo). La forma de pago importa: 7 = depósito del cliente en el banco (no es efectivo de caja), 8 = efectivo, 9 = retiro de terceros, 13 = cheque. Tabla `Formas de pago - retiro`.
- **La Diners era de Lucy:** lo pagado con ella se compensa en la cuenta de Lucy, no en la del Condominio.
- **Sierra:** la cuenta «Blue» en Access es la parte en negro del sueldo, pagada en efectivo por la caja de Giamigli.
- **Cheques a Sergio** BNA 18405/18406 (2011, $40.000/$10.000): sueldos atrasados de la cuenta 375 (cerrada). Sin cambios.
- **Criado:** la «Devolución a Giamigli» mensual del Condominio es la compensación de la parte del Condominio que el Estudio le facturaba a Giamigli. Gasto propio del Condominio.
- **Restricciones de la base:**
  - `AplicacionesPago.Origen` solo admite `fifo-032`, `correccion-031`, `automatica-mejor-esfuerzo`, `automatica-exacta` o `manual`. La regla va en `NotaConciliacion`.
  - `CK_AuditoriaReflejoSocio_Accion`: solo Asignacion/Devolucion/ReversionAsignacion/ReversionDevolucion.
  - `MovimientosCuentaSocio`: US$/kg siempre positivos (el Tipo da el signo). Índice único `(Origen, IdOrigen)` para AsignacionGasto vigentes.
  - `Pagos efectivo` no tiene columna Anulada: los duplicados se borran con respaldo y snapshot en `AuditoriaCorrecciones`, como en los demás scripts 036.

## 4. Pendientes, en orden sugerido

1. Esperar las dos decisiones de la sección 2. Si Sergio elige seguir con la planilla, generar el listado de diferencias desde el script de cruce (copiarlo de la sección «Cuentas de socios» del registro).
2. **Caja Giamigli posterior a 2015:** el canje del 20/04/2016 (caja Giamigli 78 «Devolución a Condominio» −$10.000 y 79 «Ingreso Efectivo (Cheques Feria del Centro)» +$13.645,84) está registrado como efectivo. Según la rendición del Condominio, los $10.000 se cancelaron con cheques, no en efectivo. No se tocó: la caja 2016+ sale de la planilla con arqueos. Revisar solo si un arqueo no cierra.
3. **Cuentas no revisadas o en espera** (ver `MEMORY.md` de Claude y la sección 5 del traspaso del 23/10):
   - Zurra 406 (−$9,79 M, sin revisar);
   - Municipalidad 72 ($5,6 M);
   - Movistar jun-2025 (factura pendiente);
   - Criado (NC de $2.665.608,21);
   - Syngenta (retención de $7.583,62);
   - Fideicomiso La Esperanza (facturas de arrendamiento);
   - grupo 2 (Lavalle, Iriarte, Pardo, Galicia Seguros, Transcom, Ferias del Centro);
   - derivados (Pavón, J y M, Wallace, YPF, SENASA/FUNDEBO, consignatarios).
4. **Pendientes previos de 036:**
   - AFIP (119);
   - impuestos pagados sin boleta;
   - 56 PDF de compras sin archivo;
   - las pruebas con datos vivos;
   - pastaje 039 T035 (alta de San Justo desde la interfaz, con Sergio).
5. **Spec 041, uso futuro:** las boletas de Inmobiliario (60) y Tasa Vial (99) pueden incluir partidas de socios, de Oscar o del Condominio. Se cargan desde la ficha; Sergio no pidió una barrida.

Sergio pidió cerrar cuentas una por una, sin dejar pendientes. Antes de reasignar algo, mirar que la cuenta destino no esté cerrada (`feedback_reasignar_sin_reabrir`). No reabrir puntos cerrados (`feedback_no_repreguntar`). Escrituras solo en WC, con `backup_verificado` y `AuditoriaCorrecciones`.
