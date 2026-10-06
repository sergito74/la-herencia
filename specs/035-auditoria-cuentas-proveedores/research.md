# Research: Auditoría de cuentas corrientes de proveedores

Hechos medidos en `WC` el 06/10/2026 y decisiones de diseño. Todo lo no verificado se marca como tal.

## D1. De dónde sale la fecha para medir el plazo

**Decisión**: el plazo se mide entre la fecha de la **factura** (`Compras.Fecha`) y la **fecha del movimiento de pago** (fecha del movimiento bancario, de efectivo, etc.), no la columna `Fecha` de `AplicacionesPago`, que es la fecha en que se creó la aplicación (en las 8.379 aplicaciones `automatica-exacta` es 25/09/2026, el día de la carga masiva).
**Fundamento**: la primera medición usó la fecha de creación y dio 6.100 aplicaciones; con la fecha del movimiento dan 2.194 (BNA 1.477 por $5,5 M; Galicia 717 por $33,4 M; unos 110 contactos), todas `automatica-exacta`.
**Alternativas descartadas**: usar la fecha de creación (da un falso positivo masivo); medir contra el vencimiento de la factura (solo 628 de 6.440 compras tienen vencimiento real).

## D2. Qué se considera "fuera de plazo" y qué se agrupa

**Decisión**: una aplicación está fuera de plazo si `fecha del movimiento − fecha de la factura` supera el plazo (24 meses) o si el pago es anterior a la factura por más de 60 días y no es un anticipo reconocido. Los hallazgos se **agrupan por movimiento de pago** (un movimiento aplicado a 100 facturas es un hallazgo, no 100): el caso Cargill, Galicia 3240, aplica a unas 90 facturas de 2019 a 2024 de un mismo contacto (258, verificado: es Cargill).
**Anticipos**: normalmente hasta 60 días (labores); mayores se marcan, no se descartan (decisión de Sergio, 01/10/2026).
**Excluidos del control de plazo**: aplicaciones con origen `fifo-032` (el FIFO ya las ordena por vencimiento) y `manual` (decisión explícita), que si superan el plazo se informan en el grupo aparte `fuera-de-plazo-decidido` (no cuenta como excepción); el control actúa sobre `automatica-exacta` y `automatica-mejor-esfuerzo`.

## D3. Doble descuento con tarjeta

**Decisión**: se marca cuando un pago bancario aplicado en forma automática cubre una factura que ya tiene un vínculo de tarjeta (`Tarjetas_Resumenes_Lineas_Compras`) por el mismo importe o más. Casos conocidos: Cooperativa (BNA 14417/14418) y Lartirigoyen (Galicia sobre ND 5212/5213/5216/5219).
**Corrección asociada**: dar de baja lógica la aplicación automática duplicada (`AplicacionesPago.Anulada = 1`, con motivo), nunca borrarla; reversible.
**Importante**: las aplicaciones no cambian el saldo (el saldo sale de los movimientos de la vista); la corrección ordena la imputación y quita el aviso, no cambia el saldo de la cuenta. Si el saldo no coincide con Access, la causa está en otro lado.

## D4. Cómo se explica la diferencia con el Access

**Decisión**: `diferencia = saldo de WC al corte − saldo de referencia del Access`. Se descompone, sin releer `LaHerencia`, en: (a) fuentes que el Access no contaba en la cuenta corriente (tarjetas, ventas de hacienda y granos, conciliación de tesorería, cobros de seguro, ajustes internos, pagos por socio, Mercado Pago); (b) reasignaciones de contacto registradas en `ReasignacionesContacto`; (c) filas cargadas solo en `WC` (extractos y datos posteriores al congelamiento de `LaHerencia`). Si lo que queda sin explicar es menor a $300 en pesos, la cuenta es "coincide con causa conocida" o "diferencia menor al umbral"; si no, cae en la causa que corresponda o en "otros".
**Cambio de diseño (06/10/2026, medido)**: para explicar las diferencias fila a fila se guarda la referencia del Access en `dbo.SaldosReferenciaAccessDetalle` (17.765 filas hasta el 25/09/2026, cargadas con `scripts/cargar_referencia_detalle_035.py` leyendo `LaHerencia` en solo lectura; reproduce el `SaldoAccess` de los 513 contactos con diferencia de $0). La comparación fila a fila reemplaza a la lista fija de fuentes.
**Resultado de la validación (T011, 06/10/2026)**: de 495 cuentas comparadas (excluidas las entidades de `EXCLUIDOS`), 292 coinciden tal cual, 177 coinciden con causa conocida, 6 tienen diferencia menor a $300, 4 no tienen referencia y 16 quedan en "otros" (menos de 30, SC-006): Marcelo Sierra, Movistar, Carrefour, Don Mario, Agro Hueso, Wagen, Martín Silva Rossi, Allianz, Ernesto Adán Hernández, Fideicomiso La Esperanza, Syngenta, Electrónica FLA, Ceamse, La Esperanza Agropecuaria y otras de pocos pesos; coinciden con las correcciones deliberadas que ya figuraban en la memoria. Tarda 1,4 segundos. La cifra del 01/10 (325 + 137 + 26 + 25) usaba una tolerancia de 0,5% y no es comparable uno a uno.
**Punto que se validaba**: que esta descomposición reproduzca la clasificación del 01/10/2026 (325 coinciden tal cual, 137 al quitar fuentes que el Access no contaba, 26 al quitar filas nuevas, 25 correcciones deliberadas). Es el criterio de aceptación SC-005 y la primera tarea de verificación. Si no la reproduce, se ajusta la lista de fuentes antes de seguir.
**Alternativas descartadas**: leer fila por fila `LaHerencia` en cada corrida (lento, depende de una base viva que Access sigue escribiendo); guardar una copia fila por fila (más datos a mantener sin necesidad hoy).

## D5. Fecha de corte

**Decisión**: 25/09/2026 (`SaldosReferenciaAccess.FechaCorte`). El saldo de `WC` se calcula con los movimientos de la vista hasta esa fecha inclusive; lo posterior se informa como "posterior al corte" y no entra en la comparación. La fecha de corte se lee de la propia tabla de referencia, no se fija en el código.

## D6. FIFO completo

**Decisión**: se reutiliza `recalculo_fifo` tal cual (`POST /api/recalculo-fifo/ejecuciones` con alcance, `aplicar`, `revertir`). Simulación 11 (01/10/2026, todas las cuentas): 435 de 485 cierran. Falta correrla con todos los contactos, revisar las que no cierran (quedan en `CuentasARevisar`: hoy 8, todas abiertas) y aplicar por tandas con respaldo.
**Qué cambia**: solo imputaciones (`Origen = 'fifo-032'`), no saldos. El historial (FR-017) ya existe en `RecalculoFifoEjecucion` y `RecalculoFifoAplicacion`; esta feature lo muestra en la pantalla de auditoría.
**Por qué no se rehace**: el motor, sus controles y la reversión exacta ya fueron aprobados y probados en la 032 (ejecución 3, 7 contactos).

## D7. Correcciones por regla

**Decisión**: una regla de corrección es una función con tres pasos: **simular** (por cuenta: qué cambia, saldo antes y después), **aplicar** (solo cuentas tildadas, con respaldo verificado previo, en una transacción) y **revertir** (deshace exactamente lo aplicado). Primera regla: "anular aplicaciones automáticas duplicadas con tarjeta" (D3). Reglas siguientes se agregan una por una según los grupos que aparezcan (por ejemplo, "anular aplicaciones fuera de plazo y dejar que el FIFO reimpute").
**Registro**: `AuditoriaCorrecciones` (qué regla, quién, cuándo, respaldo, resumen) y `AuditoriaCorreccionesCuentas` (por cuenta: saldo antes y después, detalle de lo cambiado) permiten revertir sin depender de la memoria.

## D8. Parámetros

**Decisión**: el plazo y el umbral se guardan en `AuditoriaParametros` (clave, valor, usuario, fecha) y cada corrida del control informa con qué valores se calculó. Valor inicial del plazo: 24 meses (aclaración del 06/10/2026). El umbral de $300 es de pesos; para cuentas en dólares la comparación es exacta salvo la tolerancia de 0,5% del FIFO.

## D9. Fuera de alcance confirmado

Impuestos sin boleta, residuos menores (cash proveedores Galicia, Gorosito), caja efectivo y sueldos: no se agregan a la vista. Las cinco tarjetas y Mercado Pago ya están cerradas por la 034.

## Riesgos abiertos

- Que la descomposición de D4 no reproduzca la clasificación previa (se valida primero).
- Cuentas con canjes (Cargill y otros acopiadores) pueden parecer excepciones sin serlo: se miden en dólares y con el criterio de compensación ya acordado.
- Memoria de proyecto con 4 a 11 días de antigüedad: las cifras de saldo se vuelven a medir en la primera corrida.
