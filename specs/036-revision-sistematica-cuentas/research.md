# Research: Método sistemático de revisión de cuentas (036)

Decisiones de diseño tomadas antes de implementar. Todo lo marcado "medido" se verificó contra `WC` el 09/10/2026; lo marcado "inferencia" no se verificó todavía y se valida en la implementación.

## D1. Detector de pagos sin factura: emparejar, no recorrer saldos

**Decisión**: para cada cuenta se empareja cada pago (crédito) con la factura o combinación de facturas que suma su importe, en una ventana de fechas. Lo que queda sin emparejar son los **pagos sin factura**; las facturas que quedan sin pago son **facturas sin pago**. Pasadas, en este orden:

1. Un pago contra una factura, o contra 2 a 4 facturas (combinación), con diferencia de hasta $1 y facturas de hasta 600 días antes y hasta 7 días después del pago. Se prueban las 14 facturas libres más cercanas en fecha.
2. Pago más retención: si no hay emparejamiento directo, se prueba sumar al pago una retención cercana en fecha.
3. Corrida FIFO: pagos que cubren muchas facturas seguidas (más de 4) se emparejan contra las facturas libres más viejas hasta cubrir el importe.
4. Control de consistencia: pagos sin factura menos facturas sin pago debe explicar el saldo de la cuenta. Si no lo explica, la cuenta lo informa como "detector sin cerrar".

El crédito de tarjeta cuenta como pago con su propia factura (ya está vinculado en el resumen); el débito bancario que cancela la tarjeta no se considera (regla vigente, FR-016).

**Medido (prototipo en lectura, cuenta Jauregui sin las 10 facturas cargadas el 09/10/2026)**:
- Un recorrido simple del saldo acumulado marcó casi todos los pagos desde 2025 (cascada de falsos positivos): descartado.
- El emparejamiento encontró **los 8 pagos esperados** (20.000,04 de nov-2024; 79.114,02; 1.563.484,73; 30.017,03; 33.000,00; 39.011,00; 43.056,90; 46.044,04) y ninguno de los que sí tenían factura.
- También marcó 2 falsos positivos: el pago de $10.594,55 del 06/01/2025 (su retención de $14.405,49 está fechada 21 días antes, fuera de la ventana de ±5 días del prototipo) y un pago de $80.541,43 de 2021 que cubre más de 4 facturas. Ambos se resuelven con las pasadas 2 (ventana de 45 días para la retención) y 3. **Esto es inferencia: se confirma en la implementación con el caso testigo.**
- Quedaron además unos 43 pagos chicos anteriores a 2021 sin emparejar (cheques "48HS BANCOS" de 2015 a 2020, de la época en que los pagos no iban con una factura exacta). Se resuelven con la pasada 3 o quedan para decisión; es una razón para validar por antigüedad y no esperar cero en cuentas muy viejas (ver D8).

**Resultado de la implementación (T017, 09/10/2026, medido)**: con la fixture de Jauregui (antes del 09/10) el detector devuelve **exactamente los 8 pagos esperados** desde 2021 (con la retención de $18.515,27 sumada a la transferencia de $1.563.484,73, importe esperado $1.582.000,00) y ninguno de los que sí tenían factura. Los 2 falsos positivos del prototipo quedaron resueltos: el pago de $10.594,55 empareja con su retención de 21 días antes (ventana de 45 días) y el pago de 2021 que cubre más de 4 facturas se cubre por FIFO parcial. Los pagos anteriores a 2021 bajaron de 43 a 8 gracias al FIFO parcial. Un error inicial (devoluciones del proveedor tomadas como cobros de cliente) se corrigió separando los lados según el sentido de la cuenta. El control de consistencia necesita tolerancia de un centavo por movimiento más $1 por el redondeo acumulado de los emparejamientos.

**Medición sobre las 518 cuentas de `WC` (solo lectura, corte 30/09/2026)**: 2,07 segundos en total; la cuenta más lenta (contacto 119, AFIP, 1.802 movimientos) tarda 0,33 segundos. 90 cuentas tienen pagos sin factura desde 2021 (700 pagos); las de mayor importe son Enrique Baya Casal (226), Cargill (258), Banco Galicia (518), el contacto 400, AFIP (119), Banco Nación (369) y Folgado (420). El control de consistencia cierra en 517 de 518 cuentas; la única que no cierra es Banco Nación (369, entidad de la cola H).

**Alternativas descartadas**: recorrer el saldo acumulado (cascada de falsos positivos, medido); usar `AplicacionesPago` como prueba de respaldo (las imputaciones automáticas están mal en origen, no sirven de evidencia); un modelo estadístico o de aprendizaje (no explicable para Sergio).

### Cuentas de clientes y mixtas (hallazgo C2 del análisis, 09/10/2026)

El prototipo se probó solo con una cuenta de proveedor. En clientes y cuentas mixtas (por ejemplo Cargill, donde `Venta Granos` figura como crédito y los cobros como deuda) **los papeles se invierten**: el cobro es el "pago" y el documento de venta es la "factura". El detector recibe el sentido de la cuenta (proveedor, cliente o mixta) y empareja en ese sentido; como respaldo cuentan todos los documentos que ya generan movimiento en la cuenta: facturas y notas, liquidaciones de venta de granos y de hacienda, y alquileres (FR-013). **Inferencia sin probar con datos**: la inversión se valida con una fixture de cliente o mixta (tarea T009b) antes de darla por buena.

## D2. Fecha esperada de la factura faltante

**Decisión**: la fecha aproximada es la fecha del pago menos la mediana de días entre factura y pago de las parejas ya emparejadas de esa misma cuenta en los últimos 24 meses, con 7 días si la cuenta no tiene parejas. Se muestra como rango (mediana ± 4 días), no como un día exacto. El importe esperado es el del pago más la retención asociada, si la hay.

**Medido**: en Jauregui las facturas se pagaron entre 1 y 8 días después (por ejemplo factura 15/09/2025 y pago 18/09/2025; factura 20/07/2026 y pago 21/07/2026).

## D3. La etapa se calcula, no se guarda

**Decisión**: la etapa actual de una cuenta es la primera cuya puerta de salida no se cumple, y se calcula cada vez a partir de los datos (pagos sin factura, hallazgos, vínculos de tarjeta, saldo externo, FIFO). Solo se guardan las confirmaciones humanas: inventario de fuentes (E0), marcas de pagos sin factura, saldos externos, decisiones y el cierre.

**Por qué**: una etapa guardada se desactualiza cuando cambia un dato; una calculada no. Es el mismo criterio con el que la 035 marca `revision-vieja`.

## D4. La ficha va en una tabla nueva; no se modifica `AuditoriaRevisiones`

**Decisión**: tabla nueva `RevisionFichas` (una fila por cuenta). `AuditoriaRevisiones` (035, estados `pendiente` y `revisada`) y su historial siguen como están: la pantalla de la 035 depende de ellos y su restricción de estados no admite los nuevos. El historial de la ficha reutiliza `AuditoriaRevisionesHistorial` (la columna `Accion` es texto libre) con acciones nuevas.

**Medido**: `AuditoriaRevisiones` tiene 51 filas (49 revisadas, 2 pendientes). Las 49 revisadas **no se toman como cerradas** (se revisaron con otros criterios); la ficha las muestra con la nota "revisada en la 035" como antecedente.

## D5. Cómo se elige la cola cuando una cuenta tiene varios problemas

**Decisión** (precedencia, de arriba hacia abajo; la primera que aplica gana y las demás se muestran como "otros problemas"):

1. **H** si el contacto es socio, entidad (`EXCLUIDOS` del recálculo FIFO, por ejemplo Condominio LSC) o tiene compras particulares.
2. **D** si tiene pagos sin factura (etapa E1).
3. **E** si hay contacto duplicado por CUIT o movimientos sin contacto (E2).
4. **C** si hay doble descuento con tarjeta (E3).
5. **G** si el pendiente es una retención sin certificado o un impuesto sin boleta (E4).
6. **F** si la cuenta es en dólares o mixta y no cierra (E4).
7. **I** si queda una diferencia sin explicar (causa `otros` de la 035) o Sergio la marcó como excepción.
8. **B** si el saldo está bien y solo faltan imputaciones por recalcular o hay hallazgos de plazo (E5).
9. **A** si no tiene nada pendiente.

La precedencia sigue el orden de las etapas: se resuelve primero lo que cambia el saldo y al final lo que solo cambia imputaciones. **Confirmado por Sergio el 09/10/2026 (clarify): se mantiene este orden.**

## D6. Dificultad para ordenar (decisión de Sergio, clarify)

**Decisión**: orden por cantidad de movimientos de la cuenta (menos primero) y, a igual cantidad, por volumen en pesos (menor primero). La cantidad de movimientos sale de `vw_MovimientosCuenta_Base`; el volumen, de la misma fuente que ya usa `fifo_plan.py`. Reemplaza al puntaje 0/1/2 de la 035 (`revision.dificultad`) solo dentro de las colas nuevas; la 035 sigue usando el suyo en su pantalla.

## D7. Corte y reapertura

**Decisión**: el cierre guarda la fecha de corte (primer corte: **30/09/2026**) y el saldo de la cuenta a esa fecha. Una cuenta cerrada se muestra como reabierta cuando su saldo recalculado a esa misma fecha difiere del guardado en más de la tolerancia de la cuenta ($1 de redondeo en pesos, la tolerancia relativa vigente en dólares), igual que `estado_de_revision` de la 035. Los movimientos posteriores al corte no entran en esa comparación. El corte vigente es único para todas las cuentas (tabla `RevisionCortes`, la fila más nueva manda).

**Inferencia a validar**: la comparación se calcula al leer la ficha; para el tablero se calcula en lote (una sola consulta de saldos por corte).

## D8. Criterio para cuentas muy viejas

**Decisión**: el método se aplica desde el inicio de cada cuenta, pero para el detector se informa por separado lo anterior a 2021, y las cuentas cuyo saldo inicial viene del Access usan ese saldo como apertura. Lo anterior a 2021 sin emparejar no bloquea el cierre si el saldo coincide con la evidencia disponible; queda anotado como excepción con motivo.

**Por qué**: 43 de los 53 pagos sin emparejar de Jauregui son anteriores a 2021 y de la época de cheques por importes sueltos; exigir cero ahí haría que ninguna cuenta vieja cierre. **Confirmado por Sergio el 09/10/2026 (clarify)**: los pagos sin factura anteriores a 2021 no bloquean el cierre si el saldo cierra contra la evidencia; se listan aparte y se anotan como excepción con motivo (FR-013b).

**Decisión sobre el saldo inicial del Access (hallazgo U1 del análisis, acordada el 09/10/2026)**: el saldo inicial del Access (`SaldosReferenciaAccessDetalle`) queda **fuera de la primera entrega**. Mientras tanto, el control de consistencia informa "sin apertura" en las cuentas que arrancan antes de 2011 y no lo cuenta como detector sin cerrar. Se incorpora cuando aparezca la primera cuenta vieja que no cierre por esa causa.

## D9. Archivos incompletos de Dropbox

**Decisión**: lectura de solo lectura de las carpetas de compras por período fiscal (`<raíz>\Compras\04 AAAA - 03 AAAA+1`). Se clasifica cada archivo por extensión y contenido: PDF o imagen legible, `.crdownload` con contenido legible (comprobante con extensión incorrecta), vacío o ilegible. Para saber si el comprobante está cargado se busca su número de documento (normalizado, sin ceros a la izquierda) en `Compras` de cualquier contacto y se compara la ruta con el campo "documento original". Nunca se renombra, mueve ni borra nada. La raíz de Dropbox es un parámetro de configuración, no una constante del código.

**Medido**: `pdfplumber` ya es dependencia del backend; leyó sin problemas los `.crdownload` de Jauregui (tienen contenido PDF completo) y distinguió los `.jpg` de imagen (no son legibles como texto; se informan como "imagen: revisar a mano").

## D10. Lotes: se reutiliza la corrección registrada de la 035

**Decisión**: un lote es una fila de `AuditoriaCorrecciones` (regla `lote-<cola>-<regla>`) con una fila por cuenta en `AuditoriaCorreccionesCuentas` (casillas sin tildar de antemano, saldo antes y después, detalle), con el mismo respaldo verificado y la misma reversión que ya existen. No hay tabla de lotes nueva. Reglas del primer corte: aprobar cierre de cuentas de la cola A, FIFO por tandas de la cola B (delega en `recalculo_fifo` y `fifo_plan`), anulación de doble descuento de la cola C. La cola D no tiene regla automática (necesita el documento); la E, F, G y H se resuelven con las herramientas existentes (reasignación, notas de ajuste, impuestos) y se registran como decisiones.

**Medido**: `AuditoriaCorrecciones` ya guarda `Regla`, `Estado`, `Parametros`, `Resumen`, `Respaldo`, y `AuditoriaCorreccionesCuentas` guarda `Tildada`, `SaldoAntes`, `SaldoDespues`, `IdsAplicacion`. La regla de doble descuento de la 035 (tareas T029 a T033) **no está implementada**: esta spec la implementa como regla de lote de la cola C y esas tareas de la 035 quedan reemplazadas por esta.

## D11. Puerta del FIFO

**Decisión**: los endpoints de simulación y aplicación del FIFO de una cuenta (`/api/auditoria-cuentas/cuentas/{id}/fifo/...`) consultan la ficha y devuelven 409 con el motivo si la cuenta no completó E1 a E4. Los 303 contactos con FIFO aplicado antes del método (8 tandas) conservan sus imputaciones; su ficha los muestra como "FIFO aplicado antes del método" y su etapa se calcula normalmente (pueden volver a una etapa anterior si el detector encuentra faltantes).

**Por qué**: es el caso de Jauregui; aplicar FIFO antes de completar documentos obliga a repetirlo.

## D12. Evidencia externa y portales

**Decisión**: el sistema no se conecta a ningún portal, banco, ARCA ni ARBA. Los saldos externos los carga Sergio (o un agente con su autorización expresa y de a un acceso, regla de oro) con fecha, fuente y referencia al archivo guardado. Los comprobantes que se bajen de un portal se guardan en la carpeta de compras del período, igual que el 09/10/2026.

## D13. Tablero y foto semanal

**Decisión**: el tablero se calcula en vivo. La foto semanal se crea cuando se abre el tablero y todavía no existe la de la semana actual (semana que empieza el lunes), y también con un botón; no hay proceso programado porque el launcher se apaga solo. La foto guarda un resumen por cola, etapa y estado con el importe en juego (no copia de cuentas).

## D14. Discrepancia detectada en la documentación

La guía compartida de agentes (`.specify/memory/agent-guidance.md`) todavía describe a `WC` como "copia de trabajo" y a `LaHerencia` como "oficial". La Constitución v1.4.0 (25/09/2026) dice que `WC` es la base de producción y `LaHerencia` está congelada. Este plan sigue la Constitución. **Pendiente de Sergio**: actualizar la guía en un cambio aparte (no se tocó aquí).

## D15. Qué hallazgos invalidan la evidencia del Access (hallado al implementar, 09/10/2026)

**Decisión**: para que el saldo coincidente con el Access cuente como evidencia (C3, FR-017b) solo importan los hallazgos que **afectan el saldo**: contacto duplicado, movimientos sin contacto, impuestos sin boleta, y los pagos sin factura pendientes. Los hallazgos de **imputación** (plazo de 24 meses, sobrepago, notas sin imputar, doble conteo con tarjeta) no cambian el saldo y no invalidan la evidencia.

**Por qué**: si cualquier hallazgo invalidara la evidencia del Access, una cuenta con hallazgos solo de imputación quedaría sin evidencia de saldo (C3 sin cumplir) y la puerta del FIFO (que exige E1 a E4) no la dejaría simular, aunque el FIFO es justo lo que arregla esos hallazgos: un círculo. **Sigue valiendo lo que dijo Sergio**: para cerrar una cuenta hacen falta los 7 criterios, y C4, C5 y C6 exigen cero hallazgos de imputación; por eso una cuenta con cualquier hallazgo no se cierra en bloque. Además, "coincide con el Access" incluye las cuentas con causa conocida y las de diferencia menor al umbral, que la 035 ya cuenta como "coinciden" y no como excepción.

## D16. Revisión final con el agente financiero (T056, 09/10/2026)

Revisión de solo lectura del agente 07 sobre `criterios.py`, `detector.py` y el final de `quickstart.md`, con una consulta a `WC`. **Límite**: el agente informó que no leyó `colas.py`, `lotes.py`, `dobles.py`, `evidencia.py`, `spec.md` ni `research.md`; sus comentarios sobre colas y D15 salen de `criterios.py` y del quickstart. Lo que contrastó en `WC` coincide con lo informado (1 ficha, cerrada; 1 saldo externo de Jauregui con +0,01 y la nota del signo).

**Hallazgos y qué se hizo**

| Hallazgo del agente | Tratamiento |
|---|---|
| Riesgo 1: cerrar ~360 cuentas de la cola A con evidencia circular (el Access contra `WC`) sin una muestra externa. Recomienda dividir el lote por saldo, contrastar una muestra de unas 15 cuentas con un estado externo real y probar la reversión en una cuenta de prueba antes de aplicar. | **No se aplicó ningún lote.** Queda como condición para que Sergio decida el cierre en bloque (T058 no lo incluye). Se deja registrado, no implementado. |
| Riesgo 2: el detector solo ve pagos sin factura; una factura faltante con su pago también faltante no se detecta (fue el caso de Jauregui, que apareció por el saldo externo), y el FIFO parcial puede absorber pagos contra facturas impagas. | Límite conocido del método: la evidencia externa (C3) es la que cubre ese hueco. Se anota; la marca `parcial` y la confianza "media" ya lo señalan. |
| Riesgo 3: C5 no aplica en clientes, dólares y mixtas, y `HALLAZGOS_DE_SALDO` es una lista fija de tres causas. | Anotado. Un hallazgo nuevo de la 035 que mueva el saldo tiene que agregarse a esa lista (`criterios.py`). |
| Signo de los saldos externos: riesgo operativo si se carga mal. | **Mitigado ahora**: el formulario pide "Le debemos nosotros / Nos debe el proveedor" y el importe sin signo; el sistema guarda el signo (positivo = a favor nuestro). Prueba de navegador actualizada. |
| Las cuentas cerradas por `access` deberían distinguirse de las cerradas con evidencia externa. | El cierre en bloque ya deja la fuente `access` en el historial (`evidencia`) y la nota "Cierre en bloque (lote N)"; se pueden listar y reabrir por lote con la reversión. |
| C7 no aporta en el cierre en bloque (la regla confirma el inventario sola). | Anotado: C7 solo agrega trazabilidad real en cierres individuales. |
| Banco Nación (369): la consistencia no cierra. | Es una entidad de la cola H (excluida del método de proveedores); se revisa con sus reglas propias. |

**Decisiones de Sergio sobre el cierre en bloque de la cola A (09/10/2026)**: (1) se cierra **por tramos de saldo**, empezando por los chicos y dejando los grandes para después (la pantalla del lote permite tildar solo las cuentas hasta un saldo máximo); (2) **no se exige muestra de 15 cuentas contra un estado de cuenta real** (impracticable: no hay tantos estados disponibles); (3) se **prueba antes el "deshacer"**.

**Prueba del deshacer sobre `WC` (09/10/2026)**: lote real 43 de la cola A (364 cuentas, 359 cumplen) con una sola cuenta tildada (Aberturas Rodríguez, saldo cero, sin ficha previa): se aplicó en 5,1 s con respaldo verificado (`WC_lote-036-43_...bak`), la cuenta quedó cerrada al corte del 30/09/2026 con inventario `access`, y al revertir (0,0 s) la ficha volvió a `pendiente` con todos los campos del cierre vacíos. Jauregui siguió cerrada. El lote 43 queda como registro `revertida`.

**Reparto de las 359 cuentas que cumplen, por saldo absoluto**: 326 con saldo cero o de centavos (hasta $1) · 12 hasta $1.000 · 4 de $1.000 a $10.000 · 3 de $10.000 a $100.000 · 10 de $100.000 a $1 M · 4 de más de $1 M (la mayor, $9,67 M).

## D17. Propuesta para la guía de agentes (T057, aprobada y aplicada el 09/10/2026)

`.specify/memory/agent-guidance.md` todavía llama a `WC` "copia de trabajo" y a `LaHerencia` "oficial", y dice que no se escribe en `LaHerencia` "durante el desarrollo". La Constitución v1.4.0 (25/09/2026) dice que `WC` es la base de producción y `LaHerencia` está congelada. **Cambio propuesto (no aplicado)**: en la sección "Bases de datos y archivos Access", reemplazar el primer y el tercer punto por: "`WC` es la base de producción (corte del 25/09/2026): las escrituras normales de la tarea van ahí, con respaldo verificado antes de cualquier cambio no trivial. `LaHerencia` está congelada: no se escribe ni se usa para nada salvo lecturas puntuales de verificación." y quitar la frase sobre una futura "puesta en marcha desde `WC` a la base oficial", que ya ocurrió.

## Supuestos de este plan

- Python 3.13, FastAPI, pyodbc, pydantic, `pdfplumber` y `openpyxl` ya están en el backend; Next.js 14, TypeScript, Tailwind y TanStack Query ya están en el frontend. No se agrega ninguna dependencia.
- El volumen es de unas 518 cuentas con movimientos y unas 10.000 imputaciones; la cuenta más grande (Cargill) tiene cerca de 800 movimientos.
- Solo Sergio usa el sistema; el rol de solo lectura existe (autenticación 016) y las acciones de cambio se ocultan para ese rol.
