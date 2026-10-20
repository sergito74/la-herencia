# Control vigente para terminar Bayá y continuar con campañas

Sergio confirmó el 20/10/2026 este orden: primero terminar Bayá; después revisar auditoría general de campañas, paso a paso y sistemáticamente. Este documento es índice de control actual; las entradas anteriores del quickstart conservan antecedentes que pueden estar resueltos.

## Método de cierre de Bayá

1. Completar comparación documental (original, moneda, importe, impuestos, fechas y duplicados), separando documentos facturados de compras firmes PENDIENTE. Los PENDIENTE no se eliminan para hacer coincidir el saldo facturado.
2. Revisar pagos por operación completa: banco/tarjeta/cheque + retención + recibo + notas de cambio + aplicación. Reproducir créditos USD y componentes en pesos, sin duplicar el pago bancario de una tarjeta ni modificar importes fiscales.
3. Resolver y comprobar imputaciones contra comprobantes del proveedor; coincidencia de importe no equivale a imputación correcta.
4. Reconstruir por separado historia previa al período visible del portal, movimientos posteriores y pedidos/remitos no facturados. No convertir saldos migrados del proveedor en facturas nuevas ni crear un ajuste global de apertura.
5. Cotejar al mismo corte documentos, créditos y saldo por moneda con resumen/composición de deuda; distinguir vencido, facturado a vencer y firme sin facturar. Cerrar solo con diferencias resueltas o excepciones individualizadas aceptadas por Sergio.

## Avance aplicado en esta continuación

Con respaldo verificado y auditoría antes/después:

| Fuente | Nominal pesos conservado | Crédito USD proveedor | Evidencia |
|---|---:|---:|---|
| Retención 99 / 2023-25 | 157.357,15 | 245,89 | RG25 y RI30422, 14/06/2023; componente pesos 96.598,84 cancela ND92923 |
| Retención 153 / 2024-22 | 139.879,45 | 3,36 | RG22 y RI44686, 28/06/2024; componente pesos 136.812,57 cancela ND108915 |
| Venta 177 / COE330223253060 | 3.134.051,64 | 14.020,94 | CA78185, 03/05/2023; aplicación incluye NC100961 parcial |
| Venta 1230 / COE330223253039 | 187.546,31 | 818,20 | CA78182, 03/05/2023; componente pesos 3.737,68 a ND90696 |

Se añadieron cuatro valuaciones, sin cambiar certificados, liquidaciones, kilos, precios, gastos ni aplicaciones. No se duplicaron pagos. Saldo en pesos sin cambio. Efectos sobre saldo USD del sistema: retenciones −541,02; canjes +28,60 (signo de la aplicación: crédito positivo). No son nuevas deudas ni ajustes fiscales. Las imputaciones de esos grupos aún se deben validar íntegramente; no se declaran cerradas por haber corregido valuaciones.

Scripts: `baya_casal_retenciones_mixtas_036.py`, `baya_casal_canjes_valuacion_036.py`. Respaldos verificados `WC_baya-retenciones-mixtas-036_20261020_110445_104011.bak` y `WC_baya-canjes-valuacion-036_20261020_110714_748610.bak`. PDFs RG descargados y validados por extracción de texto en `backups/baya-conciliacion-20261019/`; PDFs CA originales ya conservados en carpeta documental Bayá/20261019. Auditorías JSON junto a esos respaldos documentales.

### Pago junio 2026 (Galicia 3274 + RG19)

Creada `dbo.ValuacionProveedorEventos`. Transferencia $40.596.244,94 = CA145870 USD 25.650,70 + CA145871 USD 179,78 (10/06, TC 1441) + CA146076 USD 2.355,69 (16/06, TC 1432,50) = USD 28.186,17. Retención 240 ($621.445,56) USD 431,26 a TC 1441. Saldo pesos sin cambio; saldo USD +13,90 (queda USD −28.957,15 incluyendo PENDIENTE). Script `baya_casal_aplicaciones_junio2026_036.py`, respaldo `WC_baya-aplicaciones-junio2026-036_20261020_120016_769778.bak`.

### Anticipo 2021 (BNA 16334 / RI3114)

Libro bimonetario del portal (consulta solo lectura 20/10/2026, con aplicaciones): RI3114 $504.278,14 del 09/06/2021 dolarizado en CA7479 USD 5.146,31 (TC 95) y CA7480 USD 67,62 (TC 95,50) el 02/07/2021, y CA53679 USD 68,62 (TC 130) el 17/08/2022; CA53680 es neutra. El portal no tiene PDF de CA7479/7480; evidencia en `backups/baya-conciliacion-20261019/portal-ctacte-2021-2022-aplicaciones-20261020.html/.txt`. Agregada `ValuacionProveedor.FechaReconocimientoPesos` (09/06/2021; el débito BNA del 03/05 queda intacto). Total USD 5.282,55 = proveedor; saldo USD −107,34, pesos sin cambio. Script `baya_casal_anticipo2021_036.py`, respaldo `WC_baya-anticipo2021-036_20261020_121735_697286.bak`.

### Grupos de pago iguales al portal (20/10/2026)

`baya_casal_valuaciones_portal_036.py`: 13 grupos (BNA 16333; Galicia 5/423/466/719/1268/1324/1673/2979/3251/3274; Tarjetas 5583/654; retenciones 9/13/49/100/221/234/240) con el USD que acreditó el proveedor (RI/CA/RG del libro bimonetario). RG26 (ret. 100) tomada solo en pesos → 0 USD. CA144661 y CA145870 aplican banco + retención juntos: reparto proporcional a pesos. Galicia 3274 corregido a los USD del portal (25.684,39 + 182,49 + 2.312,47; ret. 240 431,82). Variación USD −197,71 (la esperada), pesos sin cambio. Respaldo `WC_baya-valuaciones-portal-036_20261020_123817_736888.bak`. Matriz: 33 de 39 grupos coinciden.

### Historia previa al portal (2015-2020) — resuelta 20/10/2026

El portal arranca en 2020 con saldo 0. Todas las facturas USD previas (39.511,94) se pagaron en pesos y cada ciclo cierra exacto en pesos al TC de sus facturas: 2015 (FC en pesos), 2017-18 (TC 17,50: canje de granos 2017 + hacienda 2018 − devoluciones de Bayá; dif. $0,18), may-2019 (TC 45/47), dic-2019 (TC 66), feb-jun 2020 (TC 70/65; dif. $26,54), jun-2020 (TC 73). El sistema pasaba cada movimiento con el BNA del día: USD 5.685 a favor ficticios (4.800,73 del ciclo 2017-18). `baya_casal_historia_pre2020_036.py` valúa cada fila en pesos de cada ciclo al TC del ciclo: saldo al 30/06/2020 USD 0,01. Respaldo `WC_baya-historia-pre2020-036_20261020_132550_149803.bak`.

### Excepciones y ajustes 20/10/2026

- Retenciones 54 (2022-15) y 183 (2024-40): **excepción aprobada por Sergio**, valuadas USD 0. La 54 era el resto de FC292987 (USD 263,79 a TC 124,24); la 183 completaba RI52670 a TC 1.045, pero Bayá aplicó el cheque a TC 1.031,50 sin ella. `baya_casal_retenciones_excepcion_036.py`.
- FC235074 y BNA16332: pago exacto a TC 93,5 (USD 393,25); ambos anteriores a la migración del portal. Retención 7 (2021-000003, $3.919,97, USD 41,89) no registrada por Bayá: **pendiente de confirmar si va como excepción**.
- Comprobantes al centavo contra PDF (portal/Dropbox): FC357850 (precios 4 decimales), ND63227, NC78177, ND83045, ND92923, NC133873 (renglones financieros ARS), y 18 más con precios escalados (`baya_casal_centavos_036.py`, `..._centavos2_036.py`, `..._centavos3_036.py`). Cuando el renglón del libro del portal difiere de su propio PDF (NC109246, NC120722, NC133873, ND134486, ND134645), manda el PDF.

### Cheque 8092 — resuelto 20/10/2026

eCheq 00008092 librado por Jorge y Martín de la Serna SRL (CUIT 33-59409247-9), pagadero 09/06/2026, recibido y endosado a Bayá desde Banco Nación (listado `BNA/Cheques/Listado de ECHEQs recibidos.xls`). Cobra las liquidaciones de hacienda 0003-00017092 y 0003-00017137 (remate 13/05/2026, vto 12/06): $5.996.744,06 − IVA transferido 29/05 $137.473,35 − efectivo 18/05 $61.710,00 = $5.797.560,71 exacto. Cargado en Valores Recibidos (emisor J y M, receptor Bayá) con valuación USD 3.931,99 (CA145717). `baya_casal_cheque8092_036.py`, respaldo `WC_baya-cheque8092-036_20261020_141059_752916.bak`.

### Cuenta replicada (20/10/2026)

- Retención 7 también excepción (USD 0), como 54 y 183: certificados emitidos y depositados que Bayá nunca acreditó ($168.791,21 en total, ≈USD 430; no se reclaman).
- Fechas y vencimientos según PDF (`baya_casal_fechas_pdf_036.py`): 115 comprobantes revisados, TC coincide en todos; FC357848/49/50 al 12/03/2024 y 7 vencimientos.
- Fechas de reconocimiento/aplicación del proveedor (`baya_casal_fechas_aplicacion_036.py`): cheques diferidos Galicia 423/466 (11/06/2021), 2580/2581 (01/08/2024, TC 932,50), 3251 (15/04 y 29/05/2026); Galicia 719 en dos aplicaciones; RG33 y pago FC348391 en enero 2024.
- **Comprobación**: saldo USD facturado (sin PENDIENTE ni PED.43194/NC) igual al portal en los 49 cierres de mes desde 2020 dentro de USD 1; al corte sistema USD 2.055,36 vs portal USD 2.055,85. Residuo USD 0,49 = ajustes de centavos del proveedor (CD26292/CA26293 +0,50, RI37633 −0,03, CA100879, redondeos).
- Pendientes de facturar fuera del corte: PENDIENTE 56078, 68476, 68485, 59111 (USD 29.416,36).


## Cola de trabajo vigente

El script de solo lectura `backend/scripts/baya_casal_matriz_pagos_actual_036.py` recalcula los 39 grupos del relevamiento inicial con las reglas/valuaciones actuales. Conserva referencia externa del 19/10; no es una consulta actualizada al portal, ni certifica documentos o imputaciones. La falta de fuente visible tampoco autoriza anular pagos. Informes JSON en `backups/baya-conciliacion-20261019/matriz-pagos-actual-*.json`.

Orden para revisar cada grupo una sola vez:

- Primero operaciones con documentos completos: pagos 2021–2022, tarjeta FC292987 y diferencias de conversión. Comenzar con FC261752/RI7384, FC263993/RI9194 y FC314873/RI24763: créditos externos directos, sin asignar conversiones agregadas entre fuentes sin evidencia.
- Después operaciones con aplicación diferida o varios tipos de cambio: anticipos 2021, pagos junio/julio2023, enero2024, abril/junio2026 y FC432399. Revisar fecha de entrega, recepción y aplicación antes de cambiar fecha del sistema.
- Después créditos sin reconocimiento localizado: retenciones54/183 y conjunto FC235074/BNA16332/ret7. Certificados y pagos existentes se conservan mientras no exista evidencia que los invalide.
- Mantener cheque8092 por 5.797.560,71 separado: endoso y recibo existen; origen recibido aún desconocido por decisión previa de Sergio. No atribuirlo a Cargill por conjetura. Registrar como excepción pendiente, no fingir que está incorporado.
- Completar pedidos/remitos y puente histórico. Revisar también devolución comercial de 23 bolsas de maíz: NC cambiaria135583 no sustituye la devolución física/comercial.
- Solo entonces comprobación final contra proveedor. Saldo facturado externo del relevamiento: USD2.055,85, vence30/06/2027; no confundir con saldo integral que incluye PENDIENTE. Todas las obligaciones vencidas canceladas según Sergio.

## Segunda etapa: campañas

No abrir una revisión indiscriminada por renglón. Partir del informe general y agrupar por documento/proceso:

1. **Vínculos productivos ausentes:** 41 renglones, 13 documentos, 7 contactos. Ordenar primero por efecto en costos y campaña vigente; revisar documento entero y origen de su reparto. Un primer documento sirve para validar el patrón antes de extenderlo al resto de su grupo.
2. **Discordancias:** 13 renglones en 11 documentos. Todos apuntan a No Aplica; revisar la evidencia productiva y el motivo de exclusión. No decidir que el texto gana sobre el vínculo.
3. **No Aplica sin vínculo:** 199 renglones. Agrupar por naturaleza del gasto/ajuste; distinguir clasificación correcta de error real. No asignarlos automáticamente a campaña ni presentarlos todos como costos omitidos.
4. **Sin asignación:** una línea de redondeo fiscal, excepción motivada; no forzar un cultivo.
5. Por lote homogéneo: evidencia → propuesta acotada → respaldo → corrección → importe/cantidad/destino conservados → vista de costos y resultado por campaña → repetir auditoría. Mantener estados pendiente, confirmado, corregido y excepción con IDs y motivo en registro compartido.
6. Una vez conocidos los patrones, revisar los puntos de carga/importación que los producen para evitar recurrencias. No imponer campaña obligatoria globalmente: existen ajustes y gastos sin destino productivo legítimos.

Procedimiento ejecutable, alcance y clasificación en `auditoria-campanias.md`. Esta etapa no está terminada ni se corrigieron masivamente sus hallazgos.
