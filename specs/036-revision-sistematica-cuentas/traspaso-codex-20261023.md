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

## 2. Rediseño de «Cajas y socios» (23/10). PARCIAL: completar y verificar en el navegador

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
1. **Recorrido en el navegador:** nadie lo abrió todavía. Pasa `tsc` y `eslint`, pero no se recorrió la interfaz. Revisar resumen, caja (nuevo, detalle, anular, corregir), socio (asiento, editar, anular, aporte/retiro) y rol Lectura.
2. **Hojas de la planilla que no tienen lugar en el sistema** (preguntarle a Sergio si las quiere):
   - `Caja Efectivo Dolares` (1.655 filas): **no hay caja en US$ en el sistema**. Es la más importante.
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
