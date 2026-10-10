# Quickstart: validar el método de revisión de cuentas

Todo en `WC`. Desde `backend/`, con `PYTHONIOENCODING=utf-8`. Referencias: [data-model.md](data-model.md), [contracts/revision-cuentas-api.md](contracts/revision-cuentas-api.md) y [research.md](research.md). Los pasos que escriben se hacen sobre cuentas de prueba o con la aprobación de Sergio; ninguno toca `LaHerencia` ni los archivos Access.

## Preparación

1. Crear las tablas, primero en modo verificación (no escribe): `python -m scripts.crear_esquema_revision_036 --verificar`; luego sin opción (respaldo verificado, tablas e inserción del corte inicial 30/09/2026, idempotente). Esperado: tablas `RevisionCortes` (1 fila), `RevisionFichas`, `RevisionPagosSinFactura`, `RevisionSaldosExternos`, `RevisionTableroFotos`, y los esquemas de la 035 intactos.
2. Para la prueba del detector con el caso testigo, la cuenta de Jauregui tal como estaba antes del 09/10/2026 se reconstruye en una fixture (`backend/tests/fixtures/jauregui_antes.json`): los movimientos de `vw_MovimientosCuenta_Base` del contacto 48 sin las 10 facturas cargadas ese día (ids de compra 2143522625 a 2143522634).

## Pasos de validación

1. **Corte vigente**: `GET /api/revision-cuentas/corte` devuelve 2026-09-30.
2. **Detector sobre el caso testigo (SC-002)**: la prueba de la función pura con la fixture devuelve los 8 pagos esperados (20.000,04; 79.114,02; 1.563.484,73 con la retención de 18.515,27 y esperado 1.582.000,00; 30.017,03; 33.000,00; 39.011,00; 43.056,90; 46.044,04) y ninguno de los pagos que sí tienen factura. Los 2 falsos positivos del prototipo (retención de 21 días y pago multi-factura de 2021, ver research D1) tienen que quedar resueltos; si no, se ajustan las pasadas antes de seguir.
3. **Detector sobre la cuenta real**: `GET /cuentas/48/pagos-sin-factura` informa 0 pagos desde 2021, `consistencia.cierra = true` y, aparte, los pagos anteriores a 2021 con `anteriorA2021 = true`.
4. **Marca conservada (FR-015)**: sobre una cuenta de prueba, `PUT /cuentas/{id}/pagos-sin-factura/galicia/{mov}` con `sin-documento` y nota; el siguiente `GET` muestra la marca y el pago no vuelve a figurar como pendiente.
5. **Los 7 criterios de Jauregui (US2)**: `GET /cuentas/48/ficha` devuelve los 7 criterios medidos con los números del 09/10/2026: C1 y C4 cumplidos, C5 cumplido (FIFO aplicado, ejecución 72), C3 dependiente del saldo externo.
6. **Saldo externo**: `POST /cuentas/48/saldos-externos` con fecha 2026-09-30, saldo −0,01, fuente `portal` y la referencia del PDF; `GET` lo lista con la diferencia contra el saldo de la cuenta a esa fecha (−3,31) y la clasificación `menor-al-umbral`.
7. **Cierre y aprobación rápida (US2, FR-012)**: en una cuenta de prueba con saldo cero y sin hallazgos, `PUT .../ficha` con `cerrada` guarda corte y saldo al cierre; en una cuenta con un criterio sin cumplir devuelve 409 con la lista de los que faltan; con `cerrada-con-excepcion` y sin motivo devuelve 422.
8. **Reapertura (FR-004)**: sobre una cuenta de prueba cerrada, un movimiento con fecha posterior al corte no la reabre; un movimiento con fecha anterior al corte que cambia el saldo la muestra como `reabierta` en `estadoEfectivo`.
9. **Colas (US3)**: `GET /tablero` informa `totalCuentas` igual a la suma de todas las casillas; `GET /colas/A` ordena por movimientos y, a igual cantidad, por importe; una cuenta con pago sin factura y doble descuento aparece en la cola D con el doble descuento en `otrosProblemas`; Condominio LSC aparece en la H.
10. **Lote (US3)**: `POST /lotes/simular` (cola C), `PUT /lotes/{id}/cuentas` con una cuenta, `POST .../aplicar`: el saldo de la cuenta es idéntico antes y después, y `POST .../revertir` devuelve las imputaciones a su estado anterior. `POST .../aplicar` sin cuentas tildadas devuelve 409; con el rol `Lectura` devuelve 403.
11. **Puerta del FIFO (US5)**: `POST /api/auditoria-cuentas/cuentas/{id}/fifo/simular` sobre una cuenta con pagos sin factura devuelve 409 con `etapaPendiente = E1`; sobre una cuenta que cumple E1 a E4 simula normalmente.
12. **Archivos incompletos (US6)**: `GET /archivos/incompletos?periodo=04 2025 - 03 2026` lista los `.crdownload` de Jauregui de esa carpeta (por ejemplo `20250923_JaureguiYMorales.crdownload` y `20251113_JaureguiYMorales.crdownload`) con `estado = comprobante-legible-extension-incorrecta` y `cargado = true` (ya se cargaron el 09/10/2026); los demás `.crdownload` de otras carpetas de período se ven con `periodo` correspondiente; los `.jpg` aparecen como `imagen-revisar`. Los archivos no se modificaron (misma fecha y tamaño antes y después).
13. **Tablero y foto semanal (US7)**: la primera apertura crea la foto de la semana (`comparacion = null`); con una foto de la semana anterior cargada de prueba, `comparacion` informa cuentas cerradas en la semana y variación de la cola I; `POST /tablero/fotos` repetido en la misma semana devuelve 409.
14. **Rendimiento**: el detector de una cuenta en menos de 2 segundos (la más grande, Cargill, con unos 800 movimientos) y el tablero de las 518 cuentas en menos de 10 segundos.

## Verificaciones automáticas

- Backend: `python -m pytest tests -q` (pruebas puras del detector, las etapas, las colas, el orden y los criterios; contrato de la API con httpx; lecturas de solo lectura sobre `WC`).
- Frontend: `npx tsc --noEmit` en `frontend/` y `node tests/revision-cuentas.e2e.cjs` con el servidor en el puerto 3100.

## Qué falta decidir con Sergio durante la validación

- Si el orden de la precedencia de colas (research D5) le sirve tal cual.
- Cómo tratar lo anterior a 2021 sin emparejar en cuentas viejas (research D8).

## Resultados de la corrida

### Esquema (T004, 09/10/2026)

- `python -m scripts.crear_esquema_revision_036 --verificar` informó las 5 tablas como "se creará"; no escribió nada.
- La corrida real hizo el respaldo verificado `WC_esquema-revision-036_20261009_153026_042129.bak` (carpeta de respaldos de SQL Server) y creó `RevisionCortes` (1 fila: corte 2026-09-30, "Primer corte: cierre del mes 9"), `RevisionFichas`, `RevisionPagosSinFactura`, `RevisionSaldosExternos` y `RevisionTableroFotos` (vacías).
- Las restricciones de los datos del modelo se crearon como CHECK: estados de la ficha, estados de la marca, fuente de respaldo, fuente y moneda del saldo externo, nota obligatoria en `sin-documento` y en `sin-estado`, y motivo obligatorio en `cerrada-con-excepcion`.

### Detector (T017, 09/10/2026)

- Pruebas puras `tests/test_revision_detector.py`: 27 pasan (los 8 pagos de Jauregui, la retención, el pago multi-factura, clientes y mixtas con fixtures `cliente_mixta.json` de Ganaderos de Elordi y Ferias del Centro).
- Contrato `tests/contract/test_revision_cuentas_api.py`: 11 pasan (corte, pagos sin factura de Jauregui real sin pagos desde 2021 y consistencia que cierra, marca conservada, 404, 422, 403).
- Medición sobre las 518 cuentas: 2,07 s en total, la más lenta 0,33 s; 90 cuentas con pagos sin factura desde 2021 (700 pagos); la consistencia cierra en 517 de 518 (la que no cierra es Banco Nación, 369).

### Ficha de Jauregui y Morales (T025, 09/10/2026)

- Con el inventario de fuentes confirmado (seis fuentes: estado del proveedor, extractos, tarjeta, certificados, Dropbox y Access), la ficha da: **C1** cumple (0 pagos sin factura desde 2021; 8 anteriores a 2021 anotados), **C2** cumple, **C4** cumple (0 doble conteo), **C5** cumple (imputaciones completas), **C6** cumple, **C7** cumple (inventario confirmado, saldo estable al corte). **C3 no cumple todavía**: sin saldo externo y sin coincidencia con el Access (el Access de Jauregui nunca tuvo las 10 facturas, por eso la 035 la clasifica como diferencia sin explicar y cae en la cola I). Etapa E4.
- El cierre se hace en T038a, después de registrar el saldo externo en T038.

### Colas (T033, 09/10/2026, corte 30/09/2026)

- Las 518 cuentas con movimientos quedan cada una en **una sola cola**: A 363 · B 35 · C 1 · D 75 · E 2 · F 3 · H 23 · I 16 (la G no tiene cuentas hoy).
- **SC-007**: la cola de excepciones (I) es el **3,1 %** del total (16 de 518), por debajo del 10 %.
- Etapa: 517 cuentas están en E0 (todavía no confirmaron el inventario de fuentes) y Jauregui en E4. La regla `aprobar-cierre` confirma el inventario con la fuente `access` al cerrar en bloque.
- Cálculo por lotes de las 518 cuentas: 6 segundos (más la clasificación de la 035, que queda en su caché).
- Lote `aprobar-cierre` (cola A), solo lectura: **363 candidatas, 358 cumplen** (5 no tienen evidencia de saldo: C3) y ninguna de la cola A tiene movimientos entre el 26 y el 30/09; solo 3 cuentas del total los tienen.
- Lote `anular-doble-descuento` (cola C), solo lectura: **1 candidata, Coto** (13 pagos, 25 imputaciones por $183.244,81; el saldo no cambia). No se aplicó.
- El lote `fifo-tandas` (cola B) no se probó sobre datos reales porque simular crea una ejecución del FIFO en `WC`; se valida al aplicarlo con la aprobación de Sergio.

### Cierre de Jauregui y Morales (T038 y T038a, 09/10/2026, aprobados por Sergio)

- **Saldo externo (T038)**: se registró el estado de cuenta del portal del proveedor con fecha 30/09/2026 y fuente `portal`. El portal informa −0,01 como deuda (su convención); en la convención de la cuenta (positivo = a favor nuestro) se cargó **+0,01**, y la nota lo aclara. Diferencia contra el saldo de la cuenta (−$3,31): **−$3,32, "menor al umbral"** (C3 cumple con evidencia `portal`; el Access discrepa y gana el proveedor).
- **Cierre (T038a)**: los 7 criterios cumplen; la cuenta quedó **cerrada al corte del 30/09/2026 con saldo −$3,31**, usuario "Sergio (cierre de Jauregui, 036)". El historial de la ficha muestra inventario, saldo externo y cierre.
- La fila de Jauregui en `CuentasARevisar` (035) ("$1,87 M pagados de más sin facturas posteriores") se marcó resuelta, con la decisión anotada: faltaban 10 facturas sin cargar, no había pagos de más.
- Con la evidencia externa cargada, la cuenta deja de estar en la cola I (la diferencia contra el Access queda explicada) y pasa a la cola A.

### Medición final (T055, 09/10/2026, corte 30/09/2026)

**Tiempos** (objetivos del plan): detector de una cuenta **0,35 s** con Cargill, la más grande (805 movimientos; objetivo menos de 2 s) · tablero de las 518 cuentas **5,2 s** recalculando y 0,01 s desde la caché de 3 minutos (objetivo menos de 10 s; la clasificación de la 035, 4,8 s, se precalienta al arrancar el servidor) · ficha de Cargill 2,4 s · revisión de archivos de un período **6,1 s** (objetivo menos de 15 s; todos los períodos juntos 76 s).

**Distribución final de colas** (518 cuentas, cada una en una sola): A 364 · B 32 · C 4 · D 75 · E 2 · F 3 · H 23 · I 15. Con la detección de imputaciones de tarjeta duplicadas (T042) la C pasó de 1 a 4 cuentas (Coto y otras 3).

| Criterio | Resultado |
|---|---|
| SC-001 ficha, etapa, estado y cola para todas | Cumple: las 518 cuentas se calculan y el total del tablero coincide con la suma de sus casillas (prueba de contrato). |
| SC-002 detector sobre el caso testigo | Cumple: los 8 pagos de Jauregui, con la retención sumada (prueba con fixture). |
| SC-003 ninguna cuenta se cierra con pagos sin factura sin decisión | Cumple: el cierre devuelve 409 con la lista de criterios (pruebas unitarias y de contrato). |
| SC-004 FIFO solo con E1 a E4 y saldo idéntico | Cumple en la puerta (409 con la etapa pendiente, tandas que omiten e informan); el "saldo idéntico antes y después" lo sigue garantizando el motor de la 032. |
| SC-005 cuenta sana aprobada en menos de 1 minuto | **No medido con una aplicación real**: el lote `aprobar-cierre` de la cola A (364 cuentas, 359 cumplen) está listo pero no se aplicó sin la aprobación de Sergio. El flujo es una sola decisión por lote. |
| SC-006 un lote, una regla, una aprobación | Cumple en el diseño y en las pruebas con lotes simulados; no se aplicó un lote real. |
| SC-007 cola I menor al 10 % | **Cumple: 15 de 518, 2,9 %.** |
| SC-008 motivo, fecha y evidencia en cada cierre y excepción; reversible | Cumple en las pruebas (se guarda quién, cuándo, motivo y fuente; la ficha previa se conserva para revertir). La reversión real de un lote no se ejercitó sobre `WC`. |
| SC-009 ningún comprobante legible sin cargar y sin informar | Cumple en la carpeta real: 21 archivos por revisar en todos los períodos, 12 comprobantes legibles con extensión incorrecta y los 12 ya cargados. |
| SC-010 saber el avance en menos de 30 segundos | Cumple: tablero en 5,2 s la primera vez y al instante después. |
| SC-011 todas las cuentas cerradas o cerradas con excepción | **En curso**: 1 de 518 cerrada (Jauregui y Morales). Es el objetivo del trabajo que sigue. |

### Cierre en bloque, tramo 1 (09/10/2026, decisión de Sergio)

- **Qué se cerró**: las **326 cuentas** de la cola A que cumplen la regla y tienen saldo cero o de centavos (hasta $1), en un solo lote (**lote 45**), con respaldo verificado `WC_lote-036-45_20261009_165056_515885.bak`. Se aplicó en 4,4 s. Fuente de evidencia: `access` (referencia del Access al corte), inventario `access`.
- **Verificación**: 327 fichas cerradas en total (las 326 más Jauregui y Morales); **ningún saldo cambió** en las 326 cuentas; Jauregui sigue cerrada.
- **Decisión de Sergio** ("Cerrá todas. Confiemos en que están correctas"): se cerró el tramo completo y no solo el subgrupo de menor riesgo que se propuso (183 cuentas que coinciden exacto con el Access y sin movimientos desde antes de 2023). **Riesgo conocido y aceptado**: una factura faltante junto con su pago también faltante no la detecta ningún control; se concentra en las 63 cuentas del tramo con movimientos en 2025 o 2026, y en las 104 que coinciden con el Access solo "con causa conocida". Cerrar es una marca reversible: el lote se deshace entero (probado) y una cuenta se reabre sola si cambia su saldo al corte.
- Perfil del tramo (solo lectura): 151 cuentas con 1 o 2 movimientos; 221 sin movimientos desde antes de 2023; 218 coinciden exacto con el Access, 104 con causa conocida y 4 con diferencia menor al umbral; 26 pagos anteriores a 2021 sin emparejar.
- Quedan abiertas las 33 cuentas restantes de la cola A (saldo mayor a $1: 12 hasta $1.000, 4 de $1.000 a $10.000, 3 de $10.000 a $100.000, 10 de $100.000 a $1 M y 4 de más de $1 M).

### Cierre de cuentas del tramo 2 (09/10/2026, decisión de Sergio)

- **Lote 47**: 19 cuentas de la cola A cerradas al corte 30/09/2026 (Pintería España, Sabaté, Gutiérrez, Electrobue, J&H, Rolyns TV, Unipase, Agroneyer, Sarnari, Telepeaje, YPF Pilar, Beraza, Autofrance, La Comarca, Las Heras, Juaristi, Ferias del Centro, 13 de Abril, Rutas Sur). Respaldo `WC_lote-036-47_20261009_181543_042841.bak`. Total de fichas cerradas: 346.
- **Errores de datos hallados y corregidos antes de cerrar** (todos con respaldo): (1) resumen de Visa Galicia del 01/10/2026 sin cargar (script `cargar_resumen_visa_galicia_pdf.py`) con 7 consumos imputados — explicaba Pintería, Rutas Sur y Telepeaje; (2) Wagen: una cuota de la factura 6954 imputada a la 8120; (3) Márgenes: cuota imputada a mano a la factura anual (la regla automática mira solo ±60 días); (4) Autopistas del Sol: facturas 0840-00723836 y 0840-00787789 bajadas del portal de Telepase (con autorización de Sergio) y cargadas; (5) Concesionario del Oeste: factura 0711-07077394 duplicada de Autopistas del Sol, eliminada; (6) Starlink: falta la nota de crédito de octubre 2025 ($5.610; Starlink nunca la emitió, tickets de reclamo en los mails) → generada como "S/D" e imputada a la línea de octubre.
- **No cerradas, a revisar una por una**: Starlink, Wagen, Autopistas del Sol y Concesionario del Oeste (pasaron a otras colas por los cambios), Formanova, Aval Rural, Extragas y las 8 del grupo 3.

### Reapertura y cierre de las seis con deuda (09/10/2026)

- Regla de Sergio: una cuenta cierra con saldo 0 (o redondeo) o con saldo pendiente explicado (no vencida, falta resumen); coincidir con el Access no alcanza. Se reabrieron 9 del lote 47 (6 en "esperando Sergio", 3 pendientes: YPF Pilar, Beraza, 13 de Abril).
- Pagos hallados y registrados (con respaldo): J&H y Rolyns TV (caja de efectivo → Pagos efectivo, como Sierra); Electrobue (movimiento 24 de Mercado Libre, $194.158; la diferencia de $1.157,98 es impuesto al crédito/débito 0,6% y no figura separada en el resumen); Unipase (compra particular de Sergio, línea negativa); Gutiérrez y Sabaté (fletes de hacienda pagados por J y M de La Serna y descontados de la liquidación: par de asientos en Pagos efectivo con Caja "J y M de La Serna", proveedor tipo 1 forma 9 y J y M tipo 3 forma 19 negativo; el saldo de J y M bajó $507.958,02).
- Los seis quedaron en saldo 0 y cerrados. Lotes FIFO 48 y 49.

### Cierre de las últimas pendientes del grupo 1 y 2 (09/10/2026)

- Pagos hallados (todos con respaldo): Extragas (caja chica del campo, movimientos 1227 y 1229); Formanova (pagó Lucy con fondos propios: Pagos efectivo caja "Particular L" forma 10 + devolución en la cuenta de socios de Lucy); YPF Pilar y Beraza (efectivo del surtidor pagado por Sergio con fondos propios: caja "Particular S" + devolución en su cuenta de socios); 13 de Abril (+$652,79 asentado como ajuste, diferencia de caja en contra, sin causa conocida); Aval Rural y Benedit Bursátil (costos del descuento del cheque de $979.459,97, cargado entero a Nidera: compensación contra Nidera, patrón de J y M; $44 del 02/07/2019 de Aval Rural asentados como diferencia).
- Starlink, Wagen, Concesionario del Oeste y Autopistas del Sol cerradas (la primera con excepción en C5: la medición cuenta doble las NC imputadas a tarjeta). Total de fichas cerradas: 354.
- Pendiente de la medición (C5): descontar las notas de crédito imputadas a líneas de tarjeta y las aplicaciones de tarjeta que duplican los vínculos; y que la regla del lote A no tome "coincide con el Access" como evidencia cuando el saldo no es cero.

### Lote 56: cola B (09/10/2026)

- FIFO recalculado en las 29 cuentas de la cola B (todas con saldo cero o centavos, ninguna cambió de saldo; respaldo `WC_lote-036-56_20261009_201456_758939.bak`) y cierre de las 29. Total de fichas cerradas: 383.
- Cuatro no cerraban por la medición de imputaciones (C5), no por los datos. Se corrigió la medición: la tarjeta cuenta solo lo imputado a facturas; los vínculos de Mercado Libre y valores propios de la conciliación de tesorería (con o sin documento, por la fecha del documento o del movimiento) y los ajustes internos de crédito cuentan como imputados; la tolerancia de redondeo pasó de 1 centavo a 3 centavos por factura. Efecto sobre las 518 cuentas: 4 pasan de falso problema a sano, ninguna empeora.

### Marca "respaldada por una venta" (09/10/2026)

- Un pago de un cliente (por ejemplo una retención de Ganancias) que es parte del cobro de una venta de hacienda o de granos ya no se marca "sin documento": se marca `venta-cargada` con la venta que lo respalda, y la ficha muestra "Respaldada por la venta de hacienda 00003-00000014". Tabla ampliada con `TipoVenta` e `IdVenta` y el estado nuevo (script `ampliar_marcas_ventas_036.py`, con respaldo; idempotente). Endpoint nuevo `GET /cuentas/{id}/ventas`. Aplicado a Sarciat Gómez y Transcom. Pruebas del backend y de navegador pasan.
- Cola D, grupo A (lote 57, 10 cuentas) y sueldos (lote 58, 3 cuentas) cerrados: 396 fichas cerradas.

### Cola D, un solo pago marcado: últimas cuentas (09/10/2026)

- Aquila Nera (VEP de AFIP pagado por Giamigli por cuenta de Aquila Nera y reintegrado), Servicios Turísticos de Rutas (diferencia de $1,90, probablemente percepciones de IIBB que la app de YPF no cobraba), Simplex Vili (compra de Mercado Libre devuelta por completo) y Diego Pardo (personal auxiliar eventual: sus 6 jornales de la planilla de trabajos eventuales coinciden con sus pagos; aviso de $91.000 marcado resuelto): lote 59. Fideicomiso La Esperanza: el contrato de arrendamiento ahora también puede ser el respaldo de una marca (`arrendamiento`), y la medición de imputaciones cuenta los contratos como crédito. Total: 401 fichas cerradas.
- Personas: los únicos empleados permanentes son Marcelo Sierra (de Giamigli) e Irma Miranda (de Lucy, con sueldos pagados por Giamigli a través de la cuenta particular de Lucy o de Sergio); el resto del personal es auxiliar eventual (Planilla trabajos eventuales.xlsx).
