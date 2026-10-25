# ARCA: análisis y subcuentas al 25/10/2026

## Estado y alcance

Sergio autorizó consultar ARCA con su acceso y representar a Giamigli, CUIT 30-71211460-2. Ingreso y selección de razón social verificados en Sistema de Cuentas Tributarias, Mis Facilidades y Mis Retenciones. Solo consultas y descarga; no presentaciones, pagos, compensaciones ni cambios de permisos. Ninguna credencial/cookie se guarda en el repositorio.

El corte contable sigue siendo **30/09/2026**. La consulta fiscal de deuda es del **25/10/2026**: no son estados al mismo corte. WC conserva **1.809 movimientos y saldo contable +$5.739.479,4089**. No es un crédito fiscal confirmado.

Sergio pidió implementar subcuentas antes de continuar la conciliación. Ya implementadas dentro de Cuentas corrientes → AFIP/ARCA, contacto119: resumen, filtros por subcuenta/fecha, saldo propio y apertura, detalle paginado, clasificación y reparto de un movimiento entre varios impuestos, historial, reversión y control de versión. Reglas/contrato: [arca-subcuentas.md](arca-subcuentas.md).

Solo se creó `ArcaClasificaciones` y se registraron **24 clasificaciones documentales** (9 reintegros IVA y15 cuotas Bienes Sustitutos). No se agregaron ni corrigieron obligaciones, pagos, bancos, cajas, certificados, cuentas de socios o Excel. Los reintegros quedaron clasificados como IVA; **todavía no se aplicaron a los certificados**.

## Hallazgos y pendientes por subcuenta

### Cargas sociales

Diez períodos carecen de obligación registrada. Los avisos de correo suman provisionalmente **$9.466.555,99**, pero no debe cargarse esa suma como deuda sin recuperar DDJJ/VEP, porque algunos avisos contradicen el pago.

| Período | Último importe avisado | Pago Galicia candidato | Diferencia / evidencia pendiente |
|---|---:|---|---|
| 05/2025 | 719.990,95 | 2608, mismo importe | Recuperar DDJJ/VEP |
| 06/2025 | 1.115.100,15 | 2667:1.115.100,17 | +0,02 |
| 07/2025 | **738.792,95** | 2734, mismo importe | Respuesta11/08 corrige expresamente el aviso copiado del mes anterior |
| 08/2025 | 818.525,58 | 2776:794.275,52 | −24.250,06; coincide con cuota sindical del aviso, hipótesis por confirmar |
| 09/2025 | 784.996,50 | 2825:803.511,77 | +18.515,27 |
| 01/2026 | 1.303.645,62 | 3046, mismo importe | Recuperar DDJJ/VEP |
| 02/2026 | 1.089.600,29 | 3086, mismo importe | Ídem |
| 03/2026 | 911.305,31 | 3138, mismo importe | Ídem |
| 04/2026 | 952.708,33 | 3210, mismo importe | Ídem |
| 05/2026 | 1.031.890,31 | 3269:1.509.786,04 | +477.895,73 |

Los seis F931 incorporados en el tramo previo siguen registrados: oct-dic2025 y jun-ago2026, $6.869.246,62; no repetir. Diciembre2025 tiene DDJJ confirmada $1.311.952,66 frente a Galicia2991 $1.548.334,45: identificar **$236.381,79**, sin crear pago nuevo.

F931 septiembre2026: aviso $1.064.446,70, vencimiento09/10/2026, separado como posterior al corte. No confundir los pagos de octubre2025 ya cargados con octubre2026 pendiente de extracto.

### IVA: retenciones recibidas y reintegros

Mis Retenciones, impuesto767, 01/01/2025–30/09/2026: **244 registros/$10.310.454,78**, compuestos por **16 retenciones régimen123/$9.802.854,07** y **228 percepciones régimen493/$507.600,71**. Exportación completa descargada, original conservado sin editar. Es un universo del impuesto767; falta verificar SIRE216 y cualquier régimen adicional aplicable antes de afirmar cobertura completa.

**Las16 retenciones están presentes** en los certificados de granos de WC: coincidencia única por número de comprobante normalizado e importe. Diez no coinciden por fecha al comparar fecha de liquidación con fecha de retención; no son diez certificados faltantes. Conservar ambas fechas y completar el vínculo fiscal, sin duplicar las retenciones.

Identificados nueve grupos únicos, disjuntos y cronológicamente posibles de26 certificados con devolución0 contra abonos bancarios: total **$13.179.515,62**.

| Galicia | Fecha | Reintegro | Certificados WC |
|---|---|---:|---|
|2010|16/07/2024|710.108,65|336|
|2172|17/10/2024|226.305,67|337|
|2362|24/01/2025|700.724,66|338|
|2416|27/02/2025|1.739.522,57|339–345|
|2455|14/03/2025|522.589,17|346,347|
|2559|16/05/2025|155.452,02|348|
|2788|16/09/2025|889.378,19|349,356,357|
|3288|25/06/2026|5.652.860,97|350–355|
|3346|27/07/2026|2.582.573,72|358–361|

Clasificación IVA aplicada; la aplicación fiscal certificado↔devolución sigue propuesta, pendiente de contrastar con Pago Devoluciones. Los dos abonos2026 suman $8.235.434,69, igual a sus diez certificados. Persiste **$804.500,0426** de diferencia histórica entre reintegros bancarios y registro de devoluciones una vez considerados estos grupos: investigar2016–2022 y originales; no generar un ajuste global.

Las anulaciones bancarias por $905.940,88 no son reintegros IVA. En marzo2025 hubo dos débitos de ese importe y una reversión repartida en874.912,88+31.028: queda un débito neto, no doble pago. Los31.028 no son UATRE confirmado; la boleta sindical pagada por21.889,02 ya está conciliada.

### Ganancias y anticipos

WC registra tres obligaciones Ganancias/$117.341,92 (última15/08/2023) y25 anticipos/$1.639.272,14 (último07/06/2024). Falta recuperar las DDJJ, anticipos determinados, compensaciones y pagos posteriores, por ejercicio, del Sistema de Cuentas Tributarias. Que no haya saldo de capital en el panel de deuda actual no demuestra que esos movimientos estén cargados en WC.

Mis Retenciones217 devuelve **15 retenciones recibidas/$4.072.669,41** en2025–sept2026. Su total está completamente identificado en WC: cinco certificados separados en `Retenciones Ventas Hacienda` por$3.093.742,82; retenciones netas incluidas en liquidaciones de hacienda por$587.884,09; alquiler138210679 por$391.042,50. No cargar otro crédito ni volver a descontarlas al cliente. El número fiscal del certificado y la fecha de retención pueden diferir de la referencia/fecha comercial registrada.

Pendiente de diseño de conciliación fiscal: exponer esos créditos tributarios con enlace al original ya contabilizado; hoy no integran como rama propia el mayor119. No convertir ese faltante de exposición en otra cobranza.

### Retenciones de Ganancias efectuadas / SICORE

Separadas de las retenciones recibidas por Giamigli. `Retenciones` registra las emitidas a proveedores; su ingreso a ARCA debe contrastarse con SICORE217/220, DDJJ y VEP. No sumarlas como créditos fiscales de Giamigli. El panel fiscal informa intereses de tres períodos SICORE; falta reconstruir pagos y obligaciones de estos conceptos en el mayor119.

### Autónomos Lucy y Sergio

Regla explícita de Sergio: **gasto de Giamigli financiado por cada socio desde su cuenta particular**. La financiación corresponde a Haber del socio, con la regla general50%USD/50%kg; no otro Debe por impuesto particular ni doble pago. La obligación fiscal puede estar bajo el CUIT personal: no queda saldada su revisión solo por consultar el CUIT de la sociedad. Se pudo verificar el acceso de Sergio; no se ha consultado aún CCMA de Sergio ni verificado acceso delegado a Lucy.

Hay307 obligaciones Autónomos/$1.852.385,02 hasta08/2024. No tienen beneficiario separado, por lo que inicialmente se muestran en **Autónomos — titular por identificar**. No inferir Lucy/Sergio por categoría o importe.

Al corte, los textos de socios identifican98 Haber Sergio/$3.986.527,49 y87 Haber Lucy/$1.313.259,01. Son universos de búsqueda, no financiación adicional para cargar: existen también207 pagos históricos ARCA con caja ParticularL/S y seis enlaces directos socio-proveedor, además de asientos con descripción genérica. Comparar por operación y respaldo, no sumar estas fuentes entre sí. Los movimientos de octubre quedan separados.

**Dos Debe Sergio a revisar** contra origen/planilla y pago:1872,07/05/2018,$2.842,12, Autónomos04/2018;1885,24/07/2018,$3.003,84, Autónomos06/2018. Su signo merece revisión ante la regla confirmada; no se modificaron por el texto solo. Completar obligaciones desde09/2024 e identificar qué créditos al socio ya tienen contrapartida ARCA.

### Bienes Sustitutos

Mis Facilidades confirma siete planes de Giamigli: N043365(2020), O853149(2021), Q355709(2022), R586663(2023), T026731(2024), U657364(2025) cancelados; W143471(2026) vigente.

- **U657364**, impuesto Acciones/Participaciones2024: capital819.296,68, intereses228.277,40;12 cuotas de87.297,84, julio2025–junio2026, **todas canceladas** en portal y debitadas en banco. Total1.047.574,08 sin obligaciones equivalentes registradas enImpuestos119.
- **W143471**, impuesto2025: tres cuotas pagadas al corte por379.981,62, confirmadas en portal y banco. El portal también confirma cuarta cuota pagada16/10/2026:126.660,54, posterior al corte, pendiente de extracto octubre. No registrar como deuda vencida las cuotas futuras.
- **T026731**, impuesto2023: portal confirma12×40.250,95, cancelado, total483.011,40; capital395.916,59/intereses87.094,81. Las seis cuotasenero–junio2025 ya están enImpuestos: no duplicar.

Quince pagos U/W por**1.427.555,70** ya clasificados en la subcuenta, sin agregar obligaciones. Antes de cargarlas decidir representación consistente de capital/interés y evitar impuesto anual más cuotas duplicados. Dos débitos adicionales RG5321, Galicia2647(04/07/2025)114.978,34 y2726(06/08/2025)118.969,99, siguen sin plan/concepto confirmado; no pertenecen por importe a los cronogramas consultados.

### Otros: deuda fiscal real y pagos sin concepto

Panel de deuda de Giamigli al25/10/2026,13 renglones: **$5.598,01** = capitalRENATEA201201/201202 **$95,61** + intereses **$5.502,40**. Capital47,81+47,80; interesesRENATEA647,66, SICORE1.136,48 y seguridad social3.718,26. Declaraciones pendientes de presentación:0 según ese panel; no equivale a certificado general de libre deuda.

Los intereses corresponden a SICORE202507/202510/202606; aportes y contribuciones202409/202505/202506/202604. No se pagaron ni se incorporaron como ajuste contable. Para cierre30/09 hay que obtener el estado a ese corte y conciliar su devengamiento.

Galicia2695,22/07/2025,$514.042,31, y3282,23/06/2026,$666.208,36, todavía requieren concepto fiscal. Una referencia VEP repetida en distintos débitos no demuestra doble pago. Mantener en Por identificar hasta recuperar comprobantes.

## Continuación concreta

1. Recuperar DDJJ/VEP de los diez F931 y los cuatro pagos con diferencias materiales; contrastar capital, intereses y otros conceptos.
2. Conciliar devoluciones IVA con su servicio oficial antes de aplicar los26 certificados; revisar percepciones228 y SIRE216.
3. Reconstruir Ganancias/anticipos y SICORE por ejercicio/período y vincular retenciones recibidas ya registradas, sin otra cobranza.
4. Revisar CCMA y financiación de Autónomos por socio, dos Debe2018 y faltantes desde09/2024, manteniendo sistema/Excel si se corrigen asientos.
5. Completar obligaciones de Bienes Sustitutos sin doble capital; identificar débitos extraordinarios y separar octubre2026.
6. Recién entonces comparar cada subcuenta con ARCA al mismo corte y resolver la diferencia histórica por documento. No hay cierre financiero de ARCA en esta tanda.

## Evidencia, respaldo y verificación

- Fuentes locales, correos, PDF, instantáneas y capturas: `backups/arca-analisis-20261025/` (ignorado porGit). Archivo IVA descargado como`.xls` pero su contenido real esXLSX; análisis por lectura de bytes, sin editar original.
- `analizar_arca_036.py` reproduce diez F931, nueve grupos de reintegro y quince cuotas; `clasificar_arca_evidencia_036.py` registra solo metadatos y su repetición da0pendientes.
- Esquema: backup verificado `WC_arca-subcuentas-036_20261025_162132_540146.bak`. Clasificaciones: `WC_arca-clasificaciones-036_20261025_165605_277433.bak`, ambos en directorio de backup de la instancia. ManifiestosJSON locales conservan rutas completas, originales y versiones.
- 28 pruebas focalizadas de invariantes/contrato/autenticación aprobadas; TypeScript sin errores; lint sin errores con advertencia preexistente useMemo enCuentaCorriente. Recorrido Chromium con API simulada: filtro vacío, validación de sumas, reparto, historial, reversión y rolLectura; no escribeWC.
- Primera captura mostróCSS incompleto de servidor3100 existente; repetido con compilación aislada3101 y revisado visualmente con estilos correctos. Lectura real validada por contrato:1809movimientos y sumaexacta de diez subcuentas igual al mayor119. Pruebas no modifican datos reales.
