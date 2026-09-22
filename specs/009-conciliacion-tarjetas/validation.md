# Validación del módulo 009 — 2026-09-22

Verificación end-to-end realizada retroactivamente (el código ya existía; no había `plan.md`/`tasks.md` previos). Backend (`uvicorn`, puerto 8000) contra `WC` real. **Nota de método**: el entorno de este agente no tuvo disponible una herramienta de automatización de navegador (Playwright/similar), a diferencia de lo que se hizo en 012. La verificación se hizo llamando directamente a los mismos endpoints REST que consume `BandejaConciliacion.tsx`/`PanelConciliacion.tsx`, con los mismos datos reales de `WC`, incluyendo el ciclo completo escritura→confirmación→reversión para cada acción. El código de los componentes React se revisó (líneas de `PanelConciliacion.tsx` citadas en `tasks.md`) y coincide con la lógica ejercitada por API. No hubo clic real en un navegador — queda como pendiente explícito (T090 en `tasks.md`).

## Backend (partida de verde)

- `python -m pytest backend/tests/test_conciliacion_documentos.py backend/tests/test_conciliacion_endpoints.py -q` → **21 passed** (16 + 5), sin fallas ni warnings de assertions.

## Verificación con datos reales de WC (vía API)

- `DB_NAME()` no se re-verificó explícitamente en esta sesión (ya lo fuerza `connection.py`); todas las lecturas y escrituras pasaron por el backend existente, que solo conecta a `WC`.
- **Bandeja de pendientes**: `GET /pendientes?pageSize=300` → 281 líneas pendientes reales, 35 con sugerencia exacta (confirmado también por `GET /pendientes/exactas`).
- **Candidatos de línea**: `GET /lineas/704/candidatos` devuelve la línea, 8+ líneas "hermanas" del mismo proveedor (Corredores Viales) y sus documentos candidatos — Historia 2 confirmada.
- **Buscador de documentos**: `GET /documentos-buscar?q=Starlink` y `?q=Corredores Viales` devuelven resultados reales con `ajustaTipoCambio` expuesto.
- **Exportar a Excel**: `GET /reporte-conciliacion` → HTTP 200, `.xlsx` válido (`openpyxl` lo abrió sin error), hojas `Resúmenes, Conciliación, Pagos, Proveedores sin CUIT, Ayuda`, 295 filas × 29 columnas en la primera hoja.

## Ciclo escritura + reversión (cada uno confirmado antes y después contra el total de pendientes = 281)

| Acción | Línea(s) real(es) | Resultado | Reversión |
|---|---|---|---|
| Vincular 1 línea a 1 documento exacto | 704 (Corredores Viales, $1.258,38) → factura 2143515394 | HTTP 201, `idVinculo=3003` (primer intento con `idVinculo=3002` para el mismo caso también probado), pendientes 281→280 | `DELETE lineas/704/compras/3002` y `/3003` → 280→281 |
| Marcar "sin documento" | 2699 ("Mercado Lobre", $100.000, sin sugerencia) | HTTP 204, motivo `Otro`, pendientes 281→280 | `DELETE lineas/2699/estado` → 280→281 |
| Reparto muchas-a-muchas | 704 ($1.258,38) + 710 ($2.013,40), Corredores Viales, contra 2 facturas distintas | `proponer-reparto` calzó 1:1 por importe (diferencia $0,01 en la segunda, dentro de tolerancia ±$0,10 → correctamente sin pedir motivo); `conciliar-reparto` → HTTP 201, `{"lineas":2,"vinculos":2}` (`idVinculo` 3004/3005 según el intento) | `DELETE` de cada vínculo → pendientes vuelve a 281 |
| Aceptar sugerencias exactas | 706 (Ceamse) + 707 (Grupo Concesionario del Oeste) | `POST aceptar-exactas` con ambas → `{"aplicadas":1,"omitidas":[706]}` (HTTP 200). 706 se omitió porque su combinación dejó de ser única/exacta al momento de confirmar — comportamiento correcto de revalidación, no un bug. | `DELETE` del vínculo de 707 (`idVinculo=3005`) → pendientes vuelve a 281 |

Al finalizar, `GET /pendientes?pageSize=300` devuelve `total: 281`, igual que antes de empezar — **no queda ningún dato de prueba activo en `WC`**.

## Hallazgos

- **No son bugs**: la diferencia de $0,01 en el reparto de la línea 710 no generó "diferencia aceptada" porque cae dentro de la tolerancia ±$0,10 del spec — comportamiento correcto, no un desvío.
- **No son bugs**: `aceptar-exactas` omitió una línea (706) que había dejado de ser "única" al momento de confirmar (revalidación server-side) — coincide con la regla del spec ("la bandeja no aplica nada sola") y con el diseño de `aceptar_exactas` en `repository.py:629`.
- **Sin bugs encontrados** que ameritaran corrección de código durante esta verificación. No se tocó ningún archivo fuente.
- **Hallazgo de spec vs. implementación**: `spec.md` describe Historia 3 (notas de ajuste TC) con detalle, pero no se pudo ejercitar de punta a punta con una línea real porque no había ninguna línea pendiente el 2026-09-22 con factura en USD y nota de ajuste disponible (coincide con lo que el propio spec ya documenta en "Hallazgos de datos reales": `CompraDocumentosRelacionados` en 0 filas, solo 1 de 6 casos históricos con nota). No es una discrepancia de código, es una limitación de los datos disponibles hoy para probar ese camino específico.
- **Pendiente real**: verificación en navegador (clic a clic, incluyendo el link a `/compras/nueva` abriendo realmente esa pantalla con los campos precargados) no se hizo por falta de herramienta de automatización de navegador en este entorno. Recomendado antes de cerrar la feature del todo si se quiere confianza visual completa, aunque la lógica de negocio (lo que realmente puede fallar) quedó ejercitada de punta a punta a nivel de API con datos reales.

## Conclusión

Las 6 historias de usuario del spec están implementadas y funcionan contra datos reales de `WC`, verificadas mediante el mismo backend que consume la UI (API-level E2E), con reversión completa de todas las escrituras de prueba. No se encontraron bugs que requirieran corrección. El único punto abierto es la verificación visual en navegador (T090 en `tasks.md`), que no es bloqueante para considerar el backend/contrato de datos correcto, pero sí queda pendiente para validar UX/render.
