# Quickstart: Flujo de caja por Rubro

Solo lectura contra `WC`: no requiere backup.

## Escenario 1 — Vista mensual en pesos, últimos 12 meses

`GET /api/flujo-caja/por-rubro?fechaDesde=2025-10-01&fechaHasta=2026-09-30&granularidad=mensual`

**Esperado**:
- Saldo inicial con Nación, Galicia CC, FIMA y total.
- Ingresos por rubro y egresos por centro de costo con subtotales.
- Filas "Pendiente de aplicar" e "Histórico sin aplicar" si corresponde.
- Sección de internos con Colocación y Rescate FIMA y Traspaso entre bancos (siempre presentes); los traspasos BNA→Galicia aparecen con sus dos lados y no inflan los ingresos.
- Para cada período, `saldoFinal` = saldo inicial acumulado + neto operativo + internos. El saldo final de Nación + Galicia CC coincide con el saldo real de los extractos a fin de cada mes (SC-001).

## Escenario 2 — Nada queda afuera

Sumar todas las celdas (ingresos + egresos + internos) del rango.

**Esperado**: el total es igual a la suma de todos los movimientos BNA + Galicia del rango (SC-002).

## Escenario 3 — Granularidad no altera el total

Pedir el mismo rango en `semanal`, `mensual`, `trimestral` y `anual`.

**Esperado**: el total de ingresos, egresos e internos del rango es idéntico en las cuatro (SC-003).

## Escenario 4 — Reparto por importe aplicado

Tomar un pago con aplicaciones a documentos de rubros distintos. Si no hay ninguno real, usar un test con monkeypatch.

**Esperado**: el pago aparece partido en esos rubros, cada uno por su importe aplicado; si hay remanente, está en "Pendiente de aplicar".

## Escenario 5 — Detalle de una celda

`GET /api/flujo-caja/por-rubro/detalle?...&periodo=2026-02&seccion=egresos&centroCosto=Personal&rubro=Sueldos`

**Esperado**: el `total` del detalle es igual al valor de la celda en el Escenario 1 (FR-006).

## Escenario 6 — Dólares

`moneda=USD` para el rango 2025-10-01 a 2026-09-30.

**Esperado**:
- Hasta abril de 2026 hay importes en USD, y cada parte del detalle muestra su cotización y fecha de cotización.
- Desde mayo de 2026, `sinTipoCambio` lista las celdas afectadas, porque la serie `Dolar BNA` termina el 2026-04-23.
- La pantalla lo avisa en vez de mostrar valores inventados (FR-005).

## Escenario 7 — Exportar

`GET /api/flujo-caja/por-rubro/exportar?...` y abrir el `.xlsx`.

**Esperado**: mismas filas, subtotales y períodos que en pantalla; importes numéricos, no texto.

## Escenario 8 — Pantalla

En Finanzas → "Flujo de caja por rubro":
- Cambiar granularidad y moneda.
- Hacer clic en una celda y ver el panel de detalle.
- Desde un movimiento "Pendiente de aplicar", abrir el flujo existente de aplicación de pagos.
- Los negativos se ven con signo y en rojo.

## Resultados de validación (2026-09-30, WC real)

- SC-002: el neto del rango coincide exacto con el flujo real (018): $2.594.378,49 en ambos.
- Rendimiento: consulta ARS ≈ 4,2 s sin contención.
- USD: funciona; 800 movimientos posteriores al 23-04-2026 quedan en "sin tipo de cambio" porque la serie Dólar BNA termina ese día (hay que actualizarla).
- Hallazgo de datos: el saldo Galicia calculado difiere del extracto en $208,63 constante desde 2026-03; desde el 02-03-2026 los movimientos Galicia se cargaron sin columna Saldo, así que no hay extracto contra el cual ubicar la diferencia.
- FIMA: la cifra es "colocado menos rescatado", no el saldo real (rescates incluyen rendimiento).
- T027 (revisión en navegador) queda pendiente: requiere login del usuario.
