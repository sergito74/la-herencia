# Traspaso a Codex — 23/10/2026

Este es el punto de entrada para continuar. Reemplaza a `traspaso-codex-20261022-tarde.md`; los pendientes de conciliación de ese documento siguen vigentes y están repetidos en la sección 4. Antes de empezar, leer `.specify/memory/agent-guidance.md` y `constitution.md`. Todo lo que se describe abajo está en `main`.

Se hicieron tres cosas desde el traspaso anterior:
- se cerró la spec 038 de cajas;
- se implementó la spec 039 de pastaje;
- se unificó el índice novillo en el INMAG;
- se rediseñó la parte de cajas y socios.

## 1. Spec 038: cajas de efectivo. CERRADA

- Las 57 tareas están cerradas y la evidencia está en `specs/038-gestion-cajas-efectivo/quickstart.md`.
- Las pruebas 038 pasan (81). El frontend compila (`tsc`).
- Comparación final de la vista de cuentas corrientes: 24.065 filas, con los mismos totales de deuda y crédito que antes de la migración.
- **No hay operaciones reales de caja cargadas todavía.** El sistema convive con la planilla `Cajas Giamigli.xlsx` hasta que Sergio confíe en él.
- **Cinco pruebas fallan desde antes, por datos vivos.** Ya fallaban antes de 038 y no son regresiones. Hay que actualizar lo que esperan:
  - `tests/contract/test_auditoria_cuentas_api.py::test_casos_conocidos_aparecen_solos`
  - `tests/contract/test_auditoria_cuentas_api.py::test_cuenta_en_dolares_con_diferencia_de_cambio_sugiere_la_nota`
  - `tests/contract/test_revision_cuentas_api.py::test_pagos_sin_factura_de_jauregui_tienen_la_forma_del_contrato`
  - `tests/contract/test_revision_cuentas_api.py::test_ficha_de_jauregui_tiene_los_siete_criterios_y_no_escribe`
  - `tests/test_vista_cuenta_tarjetas.py::test_ramas_nuevas_solo_tocan_contactos_de_tarjeta_salvo_uatre`

## 2. Rediseño de «Cajas y socios» (23/10). VERIFICADO por Codex; correcciones al final

Sergio pidió:
- un menú común para todas las cajas;
- ver las cuentas de los socios junto a las cajas;
- poder cargar, editar y borrar asientos;
- una experiencia más amigable.

**Hecho:**
- **Menú:** Finanzas → **Cajas y socios** (`/finanzas/cajas`) reemplaza a las tres entradas de caja y a «Cuentas de socios». `/finanzas/cuentas-socios` redirige a la nueva página.
- **Navegación interna:** `components/cajas-efectivo/CajasNav.tsx` muestra, en la página de cada caja y de cada socio, botones a Resumen, a las 3 cajas y a Sergio, Lucy, Ceci y Cond LSC.
- **Resumen:** `components/cajas-efectivo/CajasResumen.tsx` muestra una tarjeta por caja (saldo, último arqueo, «+ Movimiento») y una por socio (deuda actualizada, kg y US$).
- **Página de caja** (`CajaEfectivo.tsx`):
  - pestañas accesibles Movimientos / Arqueos / Comparar con la planilla;
  - botón principal «+ Nuevo movimiento», que abre un panel lateral; la URL `?nuevo=1` también lo abre;
  - el detalle y la anulación se ven en un panel lateral;
  - una vez anulada la operación, el botón **«Corregir»** abre el formulario con los mismos datos. En cajas, editar es anular y volver a cargar.
- **Cuenta de socio** (`CuentaSocio.tsx`):
  - «+ Nuevo asiento»: Debe (el socio debe) o Haber (a favor), valuado solo en kg INMAG y US$ a la fecha;
  - «Aporte / retiro en efectivo…»: es una operación de caja, con la caja elegible (`EfectivoSocioForm.tsx`);
  - en cada fila, **Editar** y **Anular**;
  - las filas generadas por una operación de caja muestran «De caja (op. N)» y no se tocan desde la cuenta del socio;
  - filtros: buscar, año y «ver anulados»; orden del más nuevo al más viejo.
- **Backend** (`cuentas_socios`):
  - `POST /api/cuentas-socios/{idSocio}/asientos` y `PUT /api/cuentas-socios/movimientos/{id}`. Editar anula el asiento y crea el corregido en la misma transacción, con auditoría en `AuditoriaReflejoSocio` (acciones `AsientoManual` y `EdicionAsiento`).
  - Solo se editan movimientos con Origen NULL o 'Manual' que no vengan de una caja.
  - La anulación se bloquea si el movimiento viene de una operación de caja 038.
  - `listar_movimientos` devuelve `idOperacionCaja` y `editable`.
  - Pruebas en `tests/test_cuentas_socios_repository.py`: 20 pasan, 2 son nuevas.

**Pendiente:**
1. **Recorrido en el navegador — resuelto por Codex:** el estado inicial era sin recorrido. Pasaba `tsc` y `eslint`, pero no se recorrió la interfaz. Revisar resumen, caja (nuevo, detalle, anular, corregir), socio (asiento, editar, anular, aporte/retiro) y rol Lectura.
2. **Hojas de la planilla que no tienen lugar en el sistema** (preguntarle a Sergio si las quiere):
   - `Caja Efectivo Dolares`: resuelta en 040. Son 1.655 filas de formato y seis movimientos reales, saldo US$360; caja GiamigliUSD.
   - `Sueldo Sergio`, `Caja Sindicatos` y `Caja Elisabet`.
3. **Paginación de la cuenta de socio:** `DataTable` recibe todas las filas filtradas en una página (hasta unas 500). Si molesta, paginar de a 50.
4. **Devoluciones viejas (`/devolucion`)** se guardaban sin kg ni US$. El formulario nuevo de asiento valúa; la devolución vieja sigue disponible pero conviene reemplazarla por el asiento.

## 3. Spec 039: contratos de pastaje. IMPLEMENTADA (T035 abierta)

Todo está en `specs/039-contratos-pastaje/`: spec con aclaraciones, plan, research, data-model, contrato de la API, tasks y evidencia en quickstart.

**Cómo se calcula** (decisiones de Sergio):
- Solo factura Giamigli de Bolívar S.A. (contacto 386); La Herencia es el establecimiento (`Establecimientos.Id=1`).
- Mes vencido, contado, IVA 21%.
- Se cobran cabezas-día por días calendario: el día de ingreso se cobra y el de egreso, muerte o faltante no.
- Las crías pagan desde el destete. Las bajas de crías al pie no restan cabezas cobrables.
- Precio: promedio simple del INMAG de los días con hacienda en el campo y con índice publicado, redondeado a centavos.
- Una liquidación confirmada queda fija. Si después cambian el índice o la bitácora, la diferencia se resuelve con una liquidación de ajuste en PDF más ND/NC. La ND/NC hereda la campaña de su factura.
- Campaña ganadera de julio a junio.
- El sistema no envía mails: deja el PDF en la carpeta del contrato.

**Caso que tiene que dar exacto:** septiembre 2026, Ganadera San Justo, 70 vaquillonas desde el 25/09, 5 kg por cabeza por mes:
- 70 kg × $4.155,02 = $290.851,40, más IVA $61.078,79, total $351.930,19;
- factura A 0002-00000008.

**Estado en WC:**
- Migración aplicada con respaldo (`backups/pastaje-039-schema/`).
- Rama `'Pastaje'` en `vw_MovimientosCuenta_Base` y `TipoDocumento 'Pastaje'` en AplicacionesPago.
- Contacto **5671 GANADERA SAN JUSTO SOCIEDAD SIMPLE**.
- Contrato 1 cargado por Sergio: vaquillonas, 5 kg, desde el 25/09.
- La bitácora y las liquidaciones están vacías.

**T035 pendiente**, desde la interfaz y con Sergio:
1. Ingreso de 70 vaquillonas el 25/09 con su número de DTe (lo tiene Sergio).
2. Preparar y confirmar la liquidación de septiembre.
3. Cargar el PDF `C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\04 2026 - 03 2027\20261006_Giamigli.pdf`.
4. Verificar el saldo del cliente en la cuenta corriente.

La pestaña Facturas avisa que hace falta una liquidación confirmada antes de cargar la factura.

**T036 pendiente:**
- recorrido de la interfaz con datos reales;
- medir SC-002 (liquidar en menos de 5 minutos);
- a los 30 días, medir SC-003: porcentaje de días INMAG cargados solos (meta: 95%).

**Pruebas:** `python -m pytest tests -q -k 039` → 35 pasan.

## 4. Índice INMAG: índice único del sistema (FR-019, aprobado por Sergio el 22/10)

- **De dónde sale:** `dbo.IndiceINMAG`, cargado desde mercadoagroganadero `haciinfo000011`. `dbo.IndiceNovillo` (`haciinfo000013`) era **otro índice**: queda solo como histórico y ya no se carga.
- **Carga diaria:** tarea de Windows **«LaHerencia - Indice INMAG»**, instalada y probada, todos los días a las 19 h. Corre `scripts/indice_inmag.py --liquidar`, que:
  - recupera los últimos 10 días;
  - del 1 al 10 de cada mes prepara los borradores de liquidación de pastaje del mes vencido.
- **Carga manual:** desde Ventas → Pastaje → contrato → pestaña Índice INMAG («Actualizar ahora»), o con `.venv\Scripts\python.exe -m scripts.indice_inmag`.
- **Cuentas de socios revaluadas:** 784 movimientos con kg desde el 16/03/2020, recalculados con el INMAG a su fecha (50% del importe ÷ INMAG). Respaldo `WC_socios_inmag_039_20261022_235724_741610.bak`; valores anteriores en `backups/pastaje-039-schema/socios-kg-inmag-plan-20261022.json`. Kg totales:

  | Socio | Kg |
  |---|---:|
  | Sergio | 15.375,276 |
  | Lucy | 14.145,580 |
  | Cond LSC | 2.457,413 |
  | Ceci | 27,789 |

- **Código:** `cuentas_socios/valuacion.py` y `repository.cotizaciones_actuales` leen `IndiceINMAG`. `scripts/cotizaciones_dolar_novillo.py` sigue cargando el dólar BNA y ahora actualiza el INMAG.
- **Ojo al comparar con la planilla:** Cajas Giamigli.xlsx valúa con el índice anterior, así que los kg de socios van a diferir de la planilla, alrededor de +1,6%. Es una diferencia esperada, no un error.
- **Error corregido:** en `IndiceNovillo.CabIngresadas`, el punto de miles hacía que «6.316» se guardara como 6. Se corrigieron 1.026 fechas; el plan está en `backups/indice-novillo/`.

## 5. Conciliaciones (036): pendientes, en este orden

Los pendientes del traspaso del 22/10 siguen igual. No se avanzó en conciliaciones desde entonces.

1. **Caja Condominio 2011–mar-2016:** cargar desde `Documents\Alquileres urbanos\Condominio LSC\Movimientos LSC.xlsx` (hoja Movs, TIPO CAJA 'EF'), al menos lo relacionado con Giamigli. Decisión de 038: el Condominio tiene su propio sistema.
2. **Vincular cajas, bancos y cuentas de socio de 2015 a 2026:**
   - aportes y retiros de Sergio, Lucy, Ceci y el Condominio;
   - cargas de la caja chica;
   - retiros y depósitos bancarios.

   Los egresos que pagó el Condominio y sus aportes en efectivo de 2011–2015 ($65.645,76 + $7.500) van a la cuenta de socio 3, sin duplicar con los depósitos bancarios. **Ahora conviene hacerlo con las operaciones 038**, que generan caja y socio juntos y se pueden auditar y anular. Atención: un movimiento histórico que ya está en `MovimientosCajaEfectivo` no debe volver a cargarse como operación nueva. Usar «Comparar con la planilla» o la importación para vincularlo.
3. **Cuentas de socio en conjunto:**
   - Lucy (contacto 390, socio 2): no tiene sueldo.
   - Condominio LSC (549, socio 3) y Virginia (564).
   - Ceci (socio 4).

   Con los asientos manuales nuevos se pueden hacer correcciones puntuales con valuación automática. Las correcciones masivas se hacen por script con respaldo, y antes hay que avisarle a Sergio.
4. **No identificados:** 13 depósitos BNA de 2011–2014 ($211.716,52) y el remanente de caja de $144.350,52 al 13/07/2015. Quedan como no identificados salvo que aparezca evidencia.
5. **Pendientes previos de 036:** AFIP (119), criterio C3 de Access, las 5 pruebas con datos vivos de la sección 1 y 56 PDF de compras sin archivo.
6. **Memoria:** siguen abiertos los puntos marcados como pendientes en `MEMORY.md` del agente Claude: Zurra 406, Municipalidad 72, Movistar jun-2025, Criado, Syngenta, Fideicomiso La Esperanza, Condominio y la barrida 036. No reabrir las cuentas cerradas: ver `feedback_no_repreguntar`, `feedback_reasignar_sin_reabrir` y `feedback_regla_cierre_cuentas`.

## 6. Reglas y avisos técnicos (vigentes)

- Toda escritura va solo a la base **WC**. Antes de un cambio de esquema o de una corrección masiva, hacer un respaldo con `src.features.vinculos.backup.backup_verificado`.
- `execute_write_transaction` no acepta DDL; para eso usar pyodbc con transacción explícita, como en `migrar_*_038/039`.
- En T-SQL, un CHECK no admite comparar condiciones entre sí con `=`; hay que escribirlo con AND/OR. Fue la causa del primer intento fallido de 039, que se revirtió.
- En Git Bash de esta PC, los heredocs largos con comillas a veces fallan («unexpected EOF»). Conviene escribir el script en el scratchpad y ejecutarlo.
- Formato de números: `formatMoneda`, `MoneyInput` y `NumberInput`; nunca `type=number` ni `toLocaleString`. El backend devuelve Decimal como string.
- Contactos: 375 es Sergio empleado y 5670 es Sergio socio. Los retiros iguales de los socios son retiro de ganancias. Sueldo devuelto a caja: opción A.
- Planilla por COM: verificar `ReadOnly` antes de guardar y hacer backup en `backups/`.
- Push a `main` autorizado de forma permanente, sin `--force`.


## Actualización Codex — 23/10/2026: caja USD y revisión del rediseño

Sergio autorizó agregar la caja de tenencias/movimientos de billetes en dólares y confirmó aportes/retiros de socios 100% US$, sin kg. Implementada en `specs/040-caja-efectivo-dolares/`; ver quickstart de 040 para respaldo y evidencias.

- Menú Cajas y socios → Giamigli US$. Libro independiente en USD, entradas/salidas, socios, ganancias, arqueos y comparación de hoja. No se agregaron las otras cajas pendientes.
- Corrección al dato del traspaso: la hoja de dólares tiene 1.655 filas de formato, pero solo seis movimientos. Se cargaron esos seis, con respaldo verificado, saldo US$360 según planilla. Las tres cajas en pesos mantienen sus saldos y cantidades. No se dedujeron asientos de socios de las ventas históricas de dólares.
- Navegador: rediseño recorrido con API simulada, 20 escenarios PASS, 123 peticiones interceptadas, sin JS errors y sin escribir pruebas en WC. Incluye edición/anulación de socio, caja USD y rol Lectura en ambos.
- Corregido el botón Corregir de caja: ahora recupera también aplicaciones, repartos y referencias originales, con nueva previsualización obligatoria.
- TypeScript y ESLint PASS; 65 pruebas focalizadas PASS y 18 USD/importación PASS tras el último ajuste de parser.
- Queda vigente el resto del traspaso: conciliaciones, DTe de las 70 vaquillonas, recuento físico real, otras hojas y pruebas con datos vivos. El nuevo saldo USD es el saldo de la fuente, no un arqueo actual.


## Nueva instrucción de Sergio — 23/10/2026 (limpieza Condominio)
Sergio pidió commitear/pushear lo terminado, mantener la comunicación compartida con Claude Code y luego limpiar/corregir la caja del Condominio, dejando solo vínculos con Giamigli. También señaló la confusión de mostrar caja y socio como dos entidades distintas.

Estado al iniciar: la importación 036 copió toda la hoja Caja Efectivo del Condominio (1.226 filas, saldo $0,23), sin filtro de relación. La aclaración 038 restringió operaciones nuevas, pero dejó esa historia como consulta; se debe corregir ese alcance para que el libro operativo muestre solo relaciones respaldadas. Se realizará con respaldo verificado, evidencia por fila y conservación de historia excluida; no se inventarán vínculos ni ajustes para mantener el saldo completo del Condominio. Todavía no se aplicó esta limpieza.


### Avance de la limpieza Condominio — aplicado, 23/10/2026
Primer commit/push cumplido: a160622. Se aplicó clasificación respaldada: 31 vínculos documentados activos; 1.195 filas archivadas fuera del libro operativo. Originales íntegros; ninguna alteración de socios/pagos/otras cajas. Evidencia, respaldo y decisiones en specs/038-gestion-cajas-efectivo/limpieza-condominio-20261023.md. El neto -$9.298.765,84 NO es deuda ni caja física; no usar como tal. Se unifica la entrada de Condominio, con secciones Cuenta con Giamigli / Movimientos vinculados. No reactivar el importador completo 036. La vinculación/conciliación con contrapartidas no forma parte de esta clasificación y sigue pendiente; no duplicar efectos de socio ni caja Giamigli. Validaciones finales completas: pruebas focalizadas, TypeScript/lint y navegador (22 escenarios, 129 API interceptadas, cero errores) PASS. Segundo commit/push aplicado: 58ebe14 (main).


### Cierre para continuidad Claude/Codex
Todo el trabajo solicitado quedó pusheado: a160622 (USD y validación inicial del rediseño) y 58ebe14 (depuración, protección de importación y entidad única Condominio). T058–T064 completas. WC ya tiene AlcanceHistoricoCaja y la vista operativa aplicadas con respaldo; no hace falta reimportar. Guía funcional vigente: no mostrar gastos propios/sin vínculo del Condominio, no sumar neto parcial como deuda o efectivo, y no duplicar sus 31 filas con nuevas operaciones. Los 1.195 históricos excluidos siguen disponibles en tabla original y snapshots para auditoría, fuera de la operatoria. No se reabrieron conciliaciones ni se tocó pastaje.


### Retoma de conciliaciones solicitada por Sergio — 23/10/2026
Punto de entrada consolidado: [retoma-conciliaciones-20261023.md](retoma-conciliaciones-20261023.md). Se contrastaron antecedentes para evitar reabrir375/P18/P31 o mantener una pausa Condominio/Virginia ya levantada. Siguiente paso: relevar EF2011–mar2016 del Condominio y cruzar con caja/bancos/socio3, sin duplicar. Esta retoma fue documental; no se aplicaron correcciones contables. Pendientes y criterios de precedencia en el nuevo registro compartido.


### Avance efectivo del siguiente paso — Condominio EF2011–mar2016
Registro compartido vigente: [condominio-ef-2011-2016-20261023.md](condominio-ef-2011-2016-20261023.md). Matriz122 filas producida; dos depósitos BNA10310/10824 ($22.150) atribuidos al549 con tres planillas de respaldo, backup verificado y auditoría128. Nada agregado a caja/socio; originales bancarios intactos salvo contacto. Saldo nominal549=-$296.987,50, no equivale a deuda actualizada del socio. Pendientes siguientes:18 pagos sin enlace explícito (no necesariamente faltantes), discrepancia PagoAFIP fuente/Pago581 UATRE y comprobación del resto de candidatos. No recargar el préstamo28/03/2016 ni duplicar aportes bancarios/caja. Scripts de inspección y evidencia local detallados en el registro; ambos agentes pueden continuar desde allí.


### Avance posterior: revisión de18 pagos
Ver [registro actualizado](condominio-18-pagos-20261023.md). Solo3 eran efectivo: vínculos caja3→pago223, caja4→222 y caja29→581 aplicados con respaldo/auditoría y saldos íntegros. Los otros15 están registrados como débito/valor3ros/tarjeta ajena; no generarles egresos de caja. AFIP/UATRE: pago581 e Impuesto228 comparten operación1046 de aporte sindicalabril2014; se conserva UATRE315 y concepto originalAFIP con nota de trazabilidad, sin reasignar. Falta original externo. Próxima investigación: los15 medios no efectivos y su representación en socio3, sin duplicar ni reabrir cuentas.


### Rastreo de15 pagos completado — 24/10/2026 (sin aplicación contable)
Registro vigente: [condominio-15-medios-20261024.md](condominio-15-medios-20261024.md), con matriz por pago y script de solo lectura. Total15=$32.042,94. Hallazgo: pago290/cheque95512293 por3031 (siembra avena, referencia Carlos Torrontegui) está incluido en Depositos 1 fila14 de los aportes733781: no es un aporte adicional ni un depósito BNA acreditado. Corregir la interpretación anterior de733781 como exclusivamente bancarios; conservar su titularidad Condominio confirmada por Sergio. Tres combustibles519,53 dicen efectivo en originales, aunque WC medio10. Naldo factura a cuenta corriente, sin identificación de tarjeta; Cooperativa difiere0,01; Easy PDF total1361,54 frente a pago1250,97 (diferencia110,57, percepción y detalle a revisar). Socio3:41 filas desde29/12/2023, sin representación individual de estos15 en2011–2014. Ausencia de coincidencia directa no descarta apertura/reintegro/pago agrupado. Sin cambios de saldo, caja, socios, aplicaciones o contactos; no se reabrieron cuentas. Siguiente: resolver evidencia faltante/diferencias y construir matriz única de financiación antes de registrar en socio3; no sumar planillas y pagos exportados como aportes distintos. AFIP/UATRE581 sigue como pendiente externo separado.


### Plan Condominio ejecutado parcialmente con evidencia nueva — 24/10/2026
Punto de continuación: [condominio-ejecucion-plan-20261024.md](condominio-ejecucion-plan-20261024.md). Aplicada auditoría130 con respaldo verificado: Easy original1361,54 (detalle/percepción), Cooperativa2253,03 (IVA por alícuota), pago561 conservado1250,97 y aplicación21107 reemplaza8568 que refería a peaje2022. Fichas22/29 esperando-evidencia;130 sin cambio. No se modificaron pagos/cajas/socios ni otras cuentas;549 sigue-296987,50. Dos intentos revertidos íntegros antes de la aplicación buena; snapshot y backup en registro.
Nuevas carpetas de HSBC2011–2014 localizadas: ARBA333/378 por20009,40 comprobados en cuenta del Condominio; AFIP95 en cuenta titulada Oscar, cuatro identifican aIrma y junio es candidato. Pregunta a Sergio pendiente sobre clasificación patrimonial de esa cuenta; no llevar esos pagos automáticamente a socio3. Maignal identifica cheque87678128 por2926 y95512293 por3031, falta recibo/endoso del primero. Sin resumen/titular de tres tarjetas aún.
Matriz única producida:165 operaciones fuente al unir61 aportes y105 pagos quitando3031 repetido;841286,02 es universo de fuentes, NO saldo. Los7500 efectivo y préstamo/devolución10000 también están dentro de733781. De140 puentes caja65645,76,72 ya representados y68/15109,68 quedan separados pendientes; no sumarlos como aportes nuevos. Ningún asiento ni kg/US$ agregado a socio3. Continúa completar pruebas/reintegros y68 puentes/vínculos posteriores, sin importar gastos propios del Condominio ni tocar Access. Auditoría campañas posterior solo excepción conocida; scripts Ruff PASS, repetición idempotente PASS. No declarar conciliación cerrada.


### Respuesta de Sergio — HSBC Oscar, 24/10/2026
Sergio respondió «1»: la cuenta HSBC a nombre de Oscar Vicente se administraba como fondos del Condominio LSC. Queda resuelta la clasificación patrimonial consultada; pagos190/191/193/194 por380 con identificación deIrma y fondos Condominio. Pago192/junio95 mantiene pendiente boleta/identificación fiscal, no el patrimonio de la cuenta. Matriz actualizada sin crear pagos, asientos ni modificar titularidad; no importar otros gastos de la cuenta. Pendientes restantes en condominio-ejecucion-plan-20261024.md.


### Continuación 24/10 — medios y destinatarios
Aplicadas auditorías131–133:49 débitos y1 tarjeta documentados,100 filas históricas de caja anuladas sin cambiar saldo;18 pares pendientes. Jumbo/Sodimac originales corregidos con respaldos. Sin asientos socio3. Detalle aplicado y controles en [condominio-puentes-68-20261024.md](condominio-puentes-68-20261024.md). Control visual completo de68 originales:62 Giamigli,5 Sucesión,1 consumidor final; dos rutas documentales incorrectas pendientes de corregir. Registro individual y fuentes en [condominio-destinatarios-68-20261024.md](condominio-destinatarios-68-20261024.md). No trasladar automáticamente estos importes a socios. Sergio pregunta ahora si los comprobantes están en Access: pendiente comprobar directamente su presencia allí, separando registro histórico de los puentes creados en WC.


### Presencia en el sistema Access comprobada — 24/10/2026
Lectura puntual y exclusiva de SELECT sobre LaHerencia, base enlazada por los archivos Access; no se abrieron ni modificaron archivos accdb. Coinciden los identificadores de las68 compras y los68 pagos: ninguno falta en origen. Comparación normalizada contra WC vivo:50 diferencias de medio y1 diferencia de importe (pago31/Jumbo356→511,79), correspondientes a auditorías131–133; ninguna diferencia de contacto u operación. No confundir esos documentos históricos con los puentes compensatorios creados después en WC. Evidencia privada: backups/condominio-15-medios-036/comparacion-access-68-20261024.json. La presencia en Access no valida destinatario, destino económico, saldo ni aporte de socio.

Pendientes inmediatos: justificar relación económica de pagos13,14,15,16,18 (Sucesión) y75 (consumidor final); corregir enlaces documentales375/568 con respaldo; resolver18 medios/reintegros sin prueba suficiente, las tarjetas y las diferencias fiscales; contrastar apertura/compensaciones de socio3 y continuación2016–2026 antes de nuevos asientos. Ninguna escritura financiera en este control de destinatarios/origen.
