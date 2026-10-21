# Avance de conciliaciones al 21/10/2026 (spec 036)

Estado para retomar las conciliaciones de cuentas corrientes (Claude o Codex). Todo lo de abajo está aplicado en la base
**WC** con backup verificado (`backup_verificado`) y scripts idempotentes en `backend/scripts/*_036.py`; la evidencia
(portales, mails, PDFs bajados) está en `backups/<cuenta>-conciliacion-*/` (gitignored).

## 1. Reglas acordadas con Sergio (aplican a todas las cuentas)

### Cierre
- Una cuenta con **saldo vivo** se cierra **al centavo contra la cuenta del proveedor** (portal, estado de cuenta, resumen).
  El umbral de $300 NO aplica a esas cuentas: si no, el arrastre sigue para siempre.
- Las diferencias de centavos se buscan y se cierran documento por documento; lo que queda como redondeo se registra con
  nota interna o con `AjustesCuentaCorriente` (ver herramientas).

### Cuentas con documentos emitidos en dólares (respuestas de Sergio 21/10/2026)
1. Al pesificar al vencimiento vale el TC de la factura; la diferencia de pesificación va en ND/NC asociada y se cancela por ese monto.
2. Siempre hay documento de ajuste (ND/NC) por la diferencia de cambio.
3. Esas notas vienen en pesos.
4. El momento de pesificación depende del proveedor: al recibir el valor (cheque/eCheq) o a la acreditación.
5. La cancelación de la factura sigue el punto 4.
6. Los acuerdos de pesificación suelen ser de palabra (a veces mail/WhatsApp): se deducen de montos y evidencia.
7. Si se ajusta a la acreditación, la diferencia se paga con transferencia o cheque complementario.
8. Si el dólar bajó, la diferencia queda a favor (raro).
9. El modo depende del momento y del acuerdo comercial.
10. Tarjeta: el precio se fija en pesos al pagar; sin ajuste posterior; los intereses van a la cuenta de la tarjeta.
11. Granos: el TC lo fija el acopiador al liquidar = **BNA comprador divisa del día hábil anterior** (185 de 219 LPG).
    Excepciones: dólar soja sept-2022 ($200, Cargill); los ajustes de una LPG conservan el TC de la original. Confirmar con el PDF.
12. Factura en US$ a TC pactado: igual se trata en dólares; solo cambia el momento de pesificación.
13. Retenciones: se calculan en pesos con el TC del documento en dólares.
14. Evidencia válida: recibo, orden de pago, mail, comprobante de cheque, WhatsApp (mails, Dropbox, etc.).
15. Si un pago no coincide con ningún TC razonable y no hay nota del proveedor: **Nota de Débito INTERNA por ajuste de tipo de cambio**.

### Regla `usd-tc-comprobante` (código: `src/features/auditoria_cuentas/bimonetaria.py`)
- Regla por cuenta en `AuditoriaConocidos` (Tipo `usd-tc-comprobante`, Clave = IdContacto). Con la regla, cada comprobante en
  US$ vale su US$ a su TC; los pesos valen lo que cancelan (FIFO, `valuar_usd_por_comprobante`); NC en US$ se pasan a pesos a
  su TC y se aplican primero a su factura vinculada (`CompraDocumentosRelacionados`); notas de diferencia de cambio en pesos
  vinculadas a un comprobante en US$ mueven pesos/TC de ese comprobante; valuaciones explícitas (`ValuacionProveedor`)
  cancelan por sus dólares fijos. En cuentas con liquidaciones de granos/hacienda (acopiadores) un peso solo cancela
  comprobantes **vencidos** (Cargill compensa la cosecha contra facturas vencidas).
- **Activa** en: Cargill 258, Allianz 515, Yanquelen 278, EDP 144, Catalpa 400, Debernardi 57, Gentos 442, Palaversich 440,
  El Paye 283, Galicia Seguros 575, Criadero Don Pedro 391, Syngenta 398, Tierras de Henderson 450, La Bragadense 472, Don Mario 396.
- **No activar** donde la cuenta ya está valuada contra el libro US$ del proveedor (Lartirigoyen 61, FEDEA 217, Nidera 303,
  ASP 17, Folgado 420, Sunanco 449, ArPov 454, Nación Seguros 289): ya dan US$ 0 y la regla se cruza con esas valuaciones.
- Script genérico para vincular NC/ND en US$ a su comprobante: `python -m scripts.vincular_notas_usd_036 <IdContacto> [--aplicar]`.

### Cuenta informal XXXXXXXXX (97)
- Gastos sin proveedor identificado, pagos en efectivo, reglas flexibles. **No borrar duplicados.** Los pagos se buscan en
  `Documents/La Herencia/Administracion y gestion/Cuentas a pagar/Cajas Giamigli.xlsx` (Caja Efectivo Pesos, Caja chica campo).

## 2. Cuentas cerradas / auditadas en esta tanda (20-21/10/2026)

| Cuenta | Resultado | Scripts |
|---|---|---|
| Cargill 258 | Pesos = libro Cargill al centavo (−$83.951.138,17); US$ −60.000,10 (anticipos 901517036A/055A + US$ 0,10). Estados US$ de Cargill 2019-2021 iguales. Ficha cerrada con excepción. | `cargill_*_036.py` |
| Lartirigoyen, FEDEA, Nidera, ASP, La Bragadense, Don Mario, Folgado, ArPov, Nación Seguros, Sunanco | $0 y US$ 0 | `nidera_nd_internas_036`, `cierre_centavos_usd_036`, `vincular_notas_usd_036` |
| Guazzaroni Greco 604 | Igual al resumen del proveedor 22/06/2026; saldo US$ 13.605,79 no vencido (FC 3310/3313 canje, vto 31/12/2026; FC 4338 vto 30/05/2027) | `guazzaroni_auditoria_036` |
| Fideicomiso La Esperanza, Pérez, Agrovet, Carrefour, Coto, EESS Saladillo, Márgenes, Jauregui, Silva Rossi, Autopistas, GCO | Saldo = facturas posteriores al corte 30/09 (pagos de octubre en `Cuentas a pagar/Transferencias`); redondeos cerrados | `redondeos_cuentas_pesos_036` |
| Movistar 71 | Saldo = facturas sep/oct 2026 (pago después del corte) | — |
| Ministerio Desarrollo Agrario 447 | $0 (boleto de marca, exp. 705329) | `cuentas_sin_ficha_036` |
| SENASA 250 | $0 (9 aranceles con su boleta) | `cuentas_sin_ficha_036` |
| AgroNación administración anterior 5662 | $0: pagos de la empresa a la sucesión (continuidad tras reestructuración) | `cuentas_sin_ficha_036` |
| XXXXXXXXX 97 | $0 (32 pagos de la planilla de cajas + ajuste informal AJC97-260930) | `xxxx_pagos_caja_036` |
| Irma Miranda 46 | $0 (ajustes de sueldo pagados por socios vinculados; sueldo sep-2026 Lucy 01/10) | `irma_miranda_036` |
| Visa Galicia 532 | Saldo −$568.318,16 = resumen VI…7822346 (cierre 01/10/2026, vto 13/10): posterior al corte, pendiente justificado | — |
| UATRE 315 | $0: DEBIN 31/01/2025 $604.224,36 era boleta municipal → Municipalidad 72; DEBIN 28/08/2025 $130.000 = carga a Mercado Pago (traspaso interno); pago efectivo 395 duplicado de ML 23 borrado; redondeo $102,50 | `uatre_036` |
| Estudio Criado 115 | Saldo = FC 00003-00000881 (08/10/2026, posterior al corte); redondeo $0,45 (RDD115-260930) | `redondeos_cuentas_pesos_036` |
| Galicia 29/09/2026 $2.000.000 | Traspaso interno Galicia→BNA ya registrado (TraspasosInternosTesoreria) | — |

## 3. Pendientes (en orden)

1. **Condominio LSC 549 ($4.134)** — cheque propio 30990496 del 20/03/2012, comentario "IVA e IIBB Condominio": la empresa
   pagó impuestos del condominio. **EN PAUSA por Sergio (21/10/2026): lo quiere analizar y buscar más información; no
   registrar nada ni volver a proponerlo hasta que él lo retome.** El condominio es socio 3; su cuenta (41 mov. desde dic-2023, saldo a su
   favor $8.989.678 según planilla) se revisa con las cuentas de socios.
2. **Cuentas sin ficha — esperan respuesta de Sergio** (21/10/2026):
   - Virginia Giamberardini 564 (+$1.655.760): es Ceci (socia 4). 4 de las 5 transferencias son "Retiro por aportes varios" de la
     hoja *Cuenta Cond LSC* (14/09/2024, 11/11/2025, 11/12/2025, 11/03/2026); la de $485.400 del 10/09/2025 no figura. Depende del
     Condominio (EN PAUSA): no registrar.
   - J y M de la Serna 47: REGLA (Sergio 21/10): Complemento = cuenta B; precio B = 0; cobro B en efectivo (planilla) como
     Pagos efectivo tipo 3 caja La Herencia/Blue (`jym_cuenta_b_036`). Ventas = PDF. Queda −$127.328,30 = residuo 2017-2020
     (−5.033,94) + Galicia 2658 "GALICIA BROKER ASESO 30708099119" $20.174,34 (no es J y M; Galicia Seguros 575 está cerrada) +
     oct-2025 +17.879,98 + Breccia FC 00002-23 $120.000 (energizador Gacela, 11/05/2026) cargado como pagado por caja J y M
     sin estar descontado en ninguna liquidación. Preguntado a Sergio.
   - Municipalidad 72: boletas no descargadas generadas (`municipalidad_boletas_036`: tasa vial cuotas 2-6/2025 y 2-3/2026,
     5 guías SIN COPIA). Queda +$50.525,29: cuota 03/2021 ($35.864,32) pagada dos veces (Lucy 04/05/2021 y Galicia 31/05/2021)
     + diferencias chicas 2011-2022.
   - UATRE 315: el redondeo de $102,50 NO lo aceptó Sergio: revisar (ver respuesta 21/10).
   - ARBA 12 (+$7,12 M): ESPERAR a Sergio: baja la cuenta corriente del inmobiliario para separar percepciones/retenciones IIBB,
     liquidaciones IIBB e inmobiliario.
   - Sin mirar todavía: Banco Nación 369, Sergio 375, Giamigli de Bolívar 386, AFIP 119,
   Albina Iglina (Lucy) 390, Banco Galicia 518.
3. **Ya revisadas, quedan como pendientes justificados**: Sancor 171 (débito sep-2026 posterior al corte), Rivas 5666 y
   Sasso 5667 (facturas 14/10/2026), Electricidad Lavalle 32 (dejado a propósito por Sergio; no proponer la NC).
4. **San Cristóbal 4663**: NO tiene saldo cero (Sergio); revisar.
5. Cargill: pagar ND 7050-76972/77233 ($10.993,02); consultar a Cargill $145,15 (libro vs. composición).
6. Cargar extractos bancarios y resúmenes de tarjeta de octubre 2026 (cierran Fideicomiso, Pérez, Agrovet, Silva Rossi, etc.).
7. Ricardo Criado 210: esperando NC de $2.665.608,21.

## 4. Herramientas útiles
- `scripts/nd_interna_tc_036.py` → `crear(contacto, [(fecha, importe, nro_factura, motivo)], prefijos=('NDI','NCI'), texto=..., ajusta=True)`:
  nota interna en pesos con el reparto de la factura que ajusta (importe > 0 = ND). Para redondeos: `prefijos=('RDD','RDC'), ajusta=False`.
- `AjustesCuentaCorriente` (Lado Deuda/Credito): redondeos de cierre con motivo (precedentes Genta, Bermejo, Wallace, Irma).
- `bimonetaria.cargar_cuenta(id, refrescar=True)` → saldo en pesos/dólares por fila.
- Portales con autorización de solo lectura: Bayá Casal, Cargill (ver memorias de Claude); nunca acciones que envíen mails.
- Pagos de socios: `MovimientosCuentaSocio` (migrado de "Cajas Giamigli.xlsx") + `PagosSocioProveedor` (vínculo al contacto).
