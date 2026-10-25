# Continuación de cuentas — 25/10/2026

## Alcance y hallazgos iniciales

Sergio pidió seguir revisando y conciliando las cuentas pendientes. Se contrastó el traspaso con WC y los cierres documentados: la lista arrastraba estados antiguos. **No repetir correcciones ni reabrir cuentas cerradas por esa lista.** Corte principal: 30/09/2026; separar documentos/pagos de octubre.

- Zurra406: `cierre-zurra` aplicada el 08/10 (cinco cheques endosados, $9.789.485); ficha cerrada09/10 al corte, residuo nominal -$0,7906. Se preserva el cierre; no se le vuelven a cargar esos cheques ni se aplica otro FIFO. Antecedente actualizado en `project_zurra_pendiente.md`, apartado CERRADA, pese a su título antiguo.
- Municipalidad72: saldo nominal -$0,0011, luego de `municipalidad_boletas_036.py` y `municipalidad_cierre_036.py`; los $5,6M del traspaso son anteriores a esas correcciones. No registrar otra vez las boletas/reintegro de Lucy.
- Movistar71: factura de junio2025 **ya cargada**, IdDeuda2143523685, 2467-01359217, original20250614_Movistar.pdf. Ficha cerrada18/10. Saldo al corte -$237.478,73; actual -$481.119,52, incluye septiembre/octubre pendientes de reflejar con banco de octubre. No cargar junio otra vez ni cerrar octubre con pagos supuestos.
- Syngenta398: ficha cerrada18/10; retención histórica anulada y excluida de importación; ND/pago/valuación resueltos. Su saldo debe leerse con el motor bimonetario, no sumando monedas distintas de la vista base.
- Fideicomiso562: cuatro alquileres **ya cargados** y ficha cerrada al30/09. Nominal al corte -$0,0016; octubre -$1.695.439,357 después de su retención, pendiente del débito bancario. No confundir562 con La Esperanza Agropecuaria458, cerrada con resto -$1,2172.
- Iriarte123, Pardo632, GaliciaSeguros575, Transcom502, Ferias39 y derivados Pavón508/JyM47/Wallace600/YPF142/GMRA492/SENASA250/FUNDEBO41: existen cierres posteriores a sus memorias antiguas. Verificar corte/moneda y preservar decisiones; Ferias está reservado a Sergio y Lavalle32 sigue excluido a propósito (-$9.931,72).
- Criado210: mantiene -$3.550.540,3351 = $2.665.608,21 de NC reclamada + eCheq125 de $884.932,61, con fracción de centavo de cálculo. La nota de su ficha todavía dice pendiente la transferencia $275.500: esa cuestión se resolvió20/10 en DPPJ5668, según registro y evidencia; corresponde actualizar la nota, sin crear pagos.
- AFIP119: saldo contable positivo $12.608.726,0289; **no equivale a crédito fiscal confirmado por ARCA**. No hay obligaciones de Impuestos posteriores a junio2025, pero sí débitos bancarios hasta septiembre2026: faltan documentos de obligaciones. Es el siguiente trabajo financiero real.

## Evidencia recuperada para AFIP (preparada)

Consulta Outlook local solo lectura, conforme `.specify/memory/local-access.md`, sin enviar/mover/marcar mensajes. Se localizaron los avisos del estudio y se guardaron DDJJ, acuses y VEP en `backups/afip-f931-20261025/`, con `mails.json` (metadatos, contenido y hashes) y `textos.json`. Revisión visual de DDJJ junio y VEP julio/agosto: CUIT **30-71211460-2**, Giamigli de Bolívar S.A. Se sumaron los conceptos del cuadro VIII y se contrastaron con los importes bancarios; no se traslada el sindicato UATRE separado a AFIP.

| Período F931 | Documento / generación | Importe | Galicia existente | Pago |
|---|---|---:|---:|---|
| 06/2026 | DDJJ10/07/2026; VEP1651061700 en el banco | 1.655.802,40 | 3321 | 13/07/2026 |
| 07/2026 | VEP1663700530, 06/08/2026 | 1.033.322,13 | 3372 | 10/08/2026 |
| 08/2026 | VEP1677451992, 07/09/2026 | 1.036.592,72 | 3439 | 08/09/2026 |

Total **$3.725.717,25** de obligaciones faltantes respaldadas por documentos y pagos ya existentes. Fecha de registro propuesta: fecha del documento/presentación, no inventar una fecha de pago ni un nuevo débito. Vencimientos según los avisos:13/07,10/08,09/09. El aviso de junio arrastra un rótulo «may-26» dentro de su tabla; el asunto, DDJJ y acuse identifican06/2026, que prevalece sobre ese rótulo.

## Aplicación de las tres obligaciones de 2026

Aplicado en WC con `backend/scripts/afip_f931_junio_agosto_2026_036.py --aplicar`: impuestos **4473,4474,4475**, tipo2 Cargas Sociales, organismo119. Respaldo verificado `WC_afip_f931_junio_agosto_2026_036_20261025_151751_439312.bak`; instantánea completa `backups/afip-f931-20261025/aplicacion-20261025-151752.json`; auditoría `afip-f931-junio-agosto-2026-036`.

Saldo contable: +$12.608.726,0289 → +$8.883.008,7789. Se conservaron los débitos existentes; no se crearon pagos ni asientos de caja/socios.

## Octubre–diciembre2025: búsqueda ampliada y aplicaciones

Se encontraron los originales en `C:/Users/Sergio/Documents/La Herencia/Administracion y gestion/Personal/F 931/`. Se excluyeron los PDF individuales de empleados y los archivos «Borrador DJ»; se revisaron visualmente los formularios globales originales (la extracción de texto tiene fuentes codificadas). CUIT30-71211460-2, período y suma de los ocho conceptos del cuadroVIII verificados. Originales preservados; copias y hashes en `backups/afip-f931-20261025/`.

| Período | Importe DDJJ | Banco | Registro nuevo |
|---|---:|---|---|
| 10/2025 | 878.919,65 | Galicia2869, 05/11/2025, VEP1540866121, exacto | Impuesto4476 |
| 11/2025 | 952.657,06 | Galicia2931, 09/12/2025, VEP1553619192, exacto | Impuesto4477 |
| 12/2025 | 1.311.952,66 | Galicia2991, 09/01/2026, **candidato** por1.548.334,45; diferencia236.381,79 sin explicar | Impuesto4478 |

- Octubre/noviembre: `--locales-2025 --aplicar`; auditoría `afip-f931-octubre-noviembre-2025-036`. Respaldo verificado `WC_afip_f931_junio_agosto_2026_036_20261025_152231_540794.bak`; foto `aplicacion-20261025-152232.json`. Fecha contable = fecha del pago comprobado porque el PDF no tiene fecha de emisión impresa; no se inventó una fecha fiscal.
- Diciembre: inicialmente se separó al no coincidir con el banco. El aviso de Estudio Criado del **07/01/2026** confirmó exactamente **$1.311.952,66**, período12/2025 y vencimiento09/01; por eso **sí se registró la obligación documentada**, sin afirmar que ese débito sea su cancelación exacta ni generar un ajuste por la diferencia. Aviso recuperado en `aviso-diciembre2025.json`; PDF SHA256 `d87462f875d0b9274c9e9531421202f0d446341fbcdfb43720668283d68b23b7`.
- Diciembre: `--diciembre-2025 --aplicar`; auditoría `afip-f931-diciembre-2025-036`; respaldo `WC_afip_f931_junio_agosto_2026_036_20261025_152404_719202.bak`; foto `aplicacion-20261025-152406.json`. Fecha de registro07/01 = aviso confirmado. Número de documento «F93112/2025-340707» usa el verificador del original, sin inventar un VEP.

**Total incorporado: seis obligaciones, $6.869.246,62. Saldo contable AFIP final: +$5.739.479,4089. No es un crédito fiscal confirmado por ARCA.** Las cinco coincidencias exactas se documentan en auditoría; no se aplicó FIFO global mientras sigan faltando obligaciones y evidencia externa.

## Seguimiento visible en el sistema

`actualizar_seguimiento_cuentas_20261025_036.py --aplicar`, con servicio normal de fichas e historial:

- AFIP119: creada ficha **esperando-evidencia**, con las seis cargas, el importe por explicar y la discrepancia diciembre. No se cerró la cuenta ni se cargó un saldo externo como si fuera confirmado.
- Criado210: conserva **esperando-evidencia**; nota corregida para no volver a preguntar por los$275.500 ya resueltos. Verificado Galicia2104 → contacto5668 DPPJ. Sigue pendiente NC2.665.608,21 y débito eCheq125 de octubre.
- Respaldo verificado `WC_seguimiento_cuentas_20261025_036_20261025_152455_905922.bak`; foto `backups/continuacion-cuentas-20261025/seguimiento-20261025-152457.json`; auditoría `seguimiento-cuentas-20261025-036`. Los controles financieros completos antes/después de estas notas son idénticos.

## Verificaciones y pendientes reales

- Foto reproducible de **22 cuentas**, con estado y saldo al corte/actual, usando el motor bimonetario cuando corresponde: `backend/scripts/relevar_pendientes_actuales_036.py`; instantáneas e informe final en `backups/continuacion-cuentas-20261025/`.
- GaliciaSeguros575: el motor indica **USD0 como saldo que gobierna**, con $8,22 residuales en pesos de diferencias de redondeo entre importes documentales y tarjeta; no se lo confunde con una deuda nueva de USD ni se genera otro ajuste. Transferencia/reversión de2025 se compensan. Se preserva el cierre y se deja registrada la precisión de moneda.
- Se ejecutaron las tres variantes del script de obligaciones y el de seguimiento por segunda vez: **las cuatro devuelven `ya_aplicado_sin_escrituras`**. En cada carga se controlaron banco origen, ausencia de duplicados, hashes de originales y variación exacta de119; las demás cuentas, cajas y socios permanecieron iguales. No se modificó el Excel de socios porque esta tanda no cambió asientos de socios.
- No se reabrieron las cuentas cerradas del grupo2/derivados. Lavalle y Ferias respetan sus restricciones. Municipalidad y SENASA están contablemente conciliadas por los trabajos anteriores (no tenían ficha formal), sin inventar un cierre externo nuevo.
- **Criado:** NC no encontrada en los PDF actuales ni entre correo pertinente recibido20–25/10 en Entrada/Administración/Estados Contables. Resultado y alcance exacto en `busqueda-criado-reciente.json`; no equivale a asegurar que el proveedor no la emitió. No se enviaron correos ni se generó una NC interna para reemplazarla.
- **Octubre:** bancos todavía cargados hasta30/09 (BNA) y29/09 (Galicia). Para reflejar los pagos posteriores de Movistar, Fideicomiso y eCheq125 se requiere el extracto/movimiento bancario de octubre. No duplicar comprobantes ya cargados para hacerlos cerrar.
- **AFIP siguiente:** recuperar DDJJ/VEP de los otros períodos desde05/2025, identificar planes y pagos no asociados, aclarar Galicia2991 contra VEP/comprobante de pago, y conciliar obligaciones/pagos/retenciones con estado externo de ARCA. El archivo de correo «Recibos de Sueldo y Cargas Sociales» no devolvió documentos de2025/2026; los formularios encontrados están en la carpeta local indicada y en Entrada. No usar los simuladores de Excel como declaraciones presentadas.
- Después de AFIP: boletas sin original y compras sin archivo. Sus cantidades históricas deben recontarse antes de repetir búsquedas: ya se detectó que el traspaso anterior mezclaba estados viejos y actuales.
