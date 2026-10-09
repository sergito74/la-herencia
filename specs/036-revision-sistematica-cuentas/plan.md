# Implementation Plan: Método sistemático de revisión, conciliación y FIFO de cuentas

**Branch**: `036-revision-sistematica-cuentas` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/036-revision-sistematica-cuentas/spec.md`

## Summary

Se arma el método para llevar cada cuenta de `WC` a "refleja la realidad financiera", con las piezas que la spec pide: una **ficha por cuenta** con siete etapas y siete criterios de cierre medibles; un **detector de pagos sin factura** que empareja cada pago con las facturas que suma (y detectó, en un prototipo sobre datos reales, los 8 pagos que faltaban en Jauregui); **colas** A a I con orden de las más fáciles a las más complejas y **lotes** reversibles por regla; **saldos externos** del proveedor para conciliar; una **puerta** que impide aplicar el FIFO antes de completar documentos; un **control de archivos incompletos** de Dropbox (solo lectura); y un **tablero** con foto semanal y lista de preguntas.

Enfoque técnico (detalle en [research.md](research.md)): un módulo nuevo `revision_cuentas` que reutiliza sin cambios las reglas de la auditoría (035), el recálculo FIFO (032) y la cuenta corriente de tarjetas (034). La etapa y la cola se **calculan** a partir de los datos (no se guardan), y solo se guardan las decisiones humanas (ficha, marcas, saldos externos, cortes, fotos). Los lotes son correcciones registradas de la 035 (mismo respaldo y reversión). No se agregan dependencias.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript con Next.js 14 (frontend)

**Primary Dependencies**: FastAPI, pyodbc, pydantic, pdfplumber, openpyxl; TanStack Query, Tailwind CSS (todas ya presentes)

**Storage**: SQL Server `WC`. Tablas nuevas: `RevisionCortes`, `RevisionFichas`, `RevisionPagosSinFactura`, `RevisionSaldosExternos`, `RevisionTableroFotos`. Se reutilizan `vw_MovimientosCuenta_Base`, `Compras`, `Tarjetas_Resumenes_Lineas_Compras`, `AplicacionesPago`, `AuditoriaRevisiones*`, `AuditoriaCorrecciones*`, `RecalculoFifo*`, `SaldosReferenciaAccess*`, `CuentasARevisar`, `ReasignacionesContacto`, `AjustesCuentaCorriente`, `Retenciones`. Lectura de archivos del disco local (carpetas de compras de Dropbox), sin escribir.

**Testing**: pytest (funciones puras con fixtures, contrato con httpx, lecturas de solo lectura sobre `WC`), `npx tsc --noEmit`, recorrido de navegador con Playwright (`frontend/tests/revision-cuentas.e2e.cjs`)

**Target Platform**: aplicación web local de escritorio (launcher), Windows

**Project Type**: aplicación web (backend + frontend)

**Performance Goals**: detector de una cuenta en menos de 2 segundos (la más grande, unos 800 movimientos); tablero de las 518 cuentas en menos de 10 segundos; revisión de archivos de un período en menos de 15 segundos

**Constraints**: solo se escribe en `WC`, nunca en `LaHerencia` ni en los Access; respaldo verificado antes de crear tablas y antes de aplicar cada lote; todo reversible, sin borrar filas; el sistema no accede a portales, bancos ni ARCA/ARBA; umbral de $300 solo en pesos y tolerancia relativa en dólares; la cuenta se cierra al corte (30/09/2026 el primero); textos en español simple

**Scale/Scope**: unas 518 cuentas con movimientos, unas 10.000 imputaciones, 303 contactos con FIFO aplicado antes del método, 37 contactos que el FIFO no cierra, 18 hallazgos de doble descuento, 5 tablas nuevas y unos 24 endpoints, 3 pantallas

## Constitution Check

*GATE: debe pasar antes de la investigación. Se vuelve a evaluar tras el diseño.*

| Principio | Cumple | Cómo |
|---|---|---|
| I. SQL Server es el sistema de registro | Sí | Todo vive en `WC` (producción desde el 25/09/2026); el Access solo aporta referencia y saldo inicial de cuentas viejas, de solo lectura |
| II. Protección de datos reales | Sí | Respaldo verificado antes de crear tablas y antes de cada lote; nada se escribe en `LaHerencia` ni en archivos Access; las lecturas de Dropbox no modifican nada |
| III. Procesos antes que tablas | Sí | Tablero → cola → cuenta → etapa → criterio → pago/factura; las pantallas siguen el camino de trabajo de Sergio |
| IV. Trazabilidad y significado financiero | Sí | Cada criterio muestra qué se midió, con signo, moneda, fecha de corte e identificadores reales; cada decisión y lote guardan quién, cuándo y por qué |
| V. Contrato primero y probado | Sí | Contrato en `contracts/revision-cuentas-api.md`; pruebas de contrato y del detector antes de la interfaz; el caso Jauregui es prueba de regresión |
| VI. Colaboración con especialistas | Sí | El agente financiero (07) aportó el método y las 25 preguntas; revisión de cierre con él al terminar (tarea final) |
| VII. Simplicidad y reversibilidad | Sí | Módulo acotado; reutiliza correcciones registradas, FIFO y revisiones existentes; la etapa se calcula, no se duplica; sin dependencias nuevas |
| VIII. Stack aprobado | Sí | Python, SQL Server, Next.js, TypeScript, Tailwind, TanStack Query |

Resultado: sin violaciones; no se requiere tabla de complejidad. Tras el diseño de la fase 1: sin cambios (ver también D14 de [research.md](research.md): la guía de agentes quedó desactualizada respecto de la Constitución y se señala, sin tocarla aquí).

## Project Structure

### Documentation (this feature)

```text
specs/036-revision-sistematica-cuentas/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── revision-cuentas-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # lo crea /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── src/features/revision_cuentas/
│   ├── __init__.py
│   ├── schemas.py          # respuestas: ficha, criterios, tablero, colas, lotes, archivos
│   ├── detector.py         # funciones puras: emparejar pagos con facturas (D1), importe y fecha esperados (D2)
│   ├── criterios.py        # funciones puras: los 7 criterios y la etapa de cada cuenta (D3)
│   ├── colas.py            # funciones puras: cola por precedencia (D5) y orden de dificultad (D6)
│   ├── datos.py            # carga de solo lectura: movimientos por cuenta, facturas, pagos, saldo al corte
│   ├── fichas.py           # ficha: leer, cambiar estado, cerrar, reapertura calculada (D7); historial
│   ├── evidencia.py        # saldos externos, inventario de fuentes, marcas de pagos sin factura
│   ├── lotes.py            # lotes de cola sobre AuditoriaCorrecciones: simular, tildar, aplicar, revertir (D10)
│   ├── archivos.py         # revisión de solo lectura de las carpetas de compras (D9)
│   ├── tablero.py          # agregados, comparación y foto semanal (D13)
│   └── router.py           # /api/revision-cuentas
├── src/features/auditoria_cuentas/router.py   # cambio acotado: puerta del FIFO (D11)
├── scripts/
│   └── crear_esquema_revision_036.py   # tablas nuevas y corte inicial, con respaldo y modo --verificar
└── tests/
    ├── fixtures/jauregui_antes.json
    ├── test_revision_detector.py
    ├── test_revision_criterios.py
    ├── test_revision_colas.py
    ├── test_revision_archivos.py
    └── contract/test_revision_cuentas_api.py

frontend/
├── src/services/revisionCuentasApi.ts   # tipos y llamadas del contrato (mismo lugar que auditoriaCuentasApi.ts)
├── src/app/finanzas/revision-cuentas/
│   ├── page.tsx                     # tablero: colas por etapas, foto semanal, preguntas
│   ├── cola/[cola]/page.tsx         # cuentas de una cola, orden de dificultad, lote
│   └── archivos/page.tsx            # archivos incompletos de Dropbox
├── src/components/revision-cuentas/
│   ├── TableroColas.tsx
│   ├── ListaPreguntas.tsx
│   ├── ColaCuentas.tsx
│   ├── LoteCola.tsx                 # reglas, casillas sin tildar, aplicar y revertir
│   ├── FichaCuenta.tsx              # etapas, 7 criterios, cierre (se incorpora a la revisión de cuenta de la 035)
│   ├── PagosSinFactura.tsx
│   ├── SaldosExternos.tsx
│   ├── ArchivosIncompletos.tsx
└── tests/revision-cuentas.e2e.cjs
```

**Structure Decision**: módulo nuevo `revision_cuentas` junto a `auditoria_cuentas` en vez de crecer el router de la 035 (ya tiene unos 470 renglones). Reutiliza sus funciones (`_cuentas()`, `hallazgos`, `correcciones`, `fifo_plan`, `revision`) por importación, sin copiarlas. La ficha de una cuenta se muestra como un panel dentro de la pantalla de revisión de cuenta que ya existe (movimientos, correcciones y FIFO), para no duplicar esa pantalla.

## Orden de implementación (ligado a las prioridades de la spec)

1. **Esquema y corte**: crear las 5 tablas con respaldo y modo `--verificar`; insertar el corte 30/09/2026.
2. **Detector (US1, P1)**: función pura `detector.py` con la fixture de Jauregui; luego el endpoint y las marcas. Es lo más valioso y lo que más riesgo técnico tiene (D1), por eso va primero y se valida contra el caso testigo antes de seguir.
3. **Criterios, etapas y ficha (US2, P1)**: los 7 criterios medibles y la etapa calculada; cierre con excepción; reapertura al corte.
4. **Colas y lotes (US3, P1)**: precedencia, orden de dificultad, reglas de lote (cierre de la A, FIFO de la B, doble descuento de la C).
5. **Saldos externos (US4, P2)** y **puerta del FIFO (US5, P2)**.
6. **Archivos incompletos (US6, P2)**.
7. **Tablero, foto semanal y preguntas (US7, P3)** y las pantallas.
8. **Cierre**: revisión con el agente financiero (07), pruebas completas, medición de los criterios de éxito sobre las 518 cuentas, y actualización del estado de la spec.

## Riesgos y cómo se tratan

- **Falsos positivos del detector** en cuentas muy viejas o con pagos que cubren muchas facturas (medido en el prototipo, D1 y D8): se informa por separado lo anterior a 2021, se agrega la corrida FIFO y el control de consistencia; Sergio marca los casos dudosos y las marcas se conservan.
- **Rendimiento en cuentas grandes** por la búsqueda de combinaciones: se limita a las 14 facturas libres más cercanas y combinaciones de hasta 4; se mide con Cargill (unos 800 movimientos).
- **Cola I que crezca** y vuelva al "una por una": el tablero muestra su tamaño y la foto semanal su variación.
- **Cuentas con FIFO aplicado antes del método**: su etapa se calcula igual y pueden volver a una etapa anterior; no se deshace nada automáticamente (D11).
- **Reglas de lote** que cambian imputaciones: siempre con respaldo, casillas sin tildar de antemano, saldo idéntico antes y después y reversión; la regla de la cola C reemplaza las tareas T029 a T033 de la 035 que nunca se implementaron.
- **Guía de agentes desactualizada** (WC como "copia de trabajo"): se señala en D14; se corrige en un cambio aparte, con aprobación de Sergio.

## Complexity Tracking

Sin violaciones de la Constitución que justificar.
