# Auditoría de diseño · Módulo Imputación de costos (18/11/2026)

Agente: 12 · Especialista en diseño visual de frontend. Pedido de Sergio: "esa forma de mostrar las imputaciones no es amigable… la última auditoría se quedó corta".
Alcance: Producción › Costos (Automática, Por documento, Costo por cultivo / campaña, Contratistas sin orden) + bloques "Control de costos" y "Para revisar".
Capturas reales (1440 px, 18/11 21:25): `scratchpad/diseno-imputacion/{documentos,automatica,resultado,sin-orden}.png`.

---

## 0. Diagnóstico general

El módulo está armado "de adentro hacia afuera": muestra la estructura de datos del motor (documento → renglón → fracción) en vez de responder las tres preguntas que se hace el usuario:

1. **¿Dónde fue a parar la plata?** (destino: cultivo/campaña, centro de costo, ganadería, stock)
2. **¿Hay algo que tenga que hacer yo?** (pendiente, requiere intervención, diferencia de control)
3. **¿Cuánto suma?** (totales por destino, por período, por proveedor)

Ninguna pantalla responde las tres de un vistazo. "Por documento" responde la 1 con un clic por documento, no responde la 2 sin filtrar, y la 3 sólo al pie de cada página de 20.

Problemas transversales:

| # | Problema | Dónde |
|---|----------|-------|
| T1 | Números con `toLocaleString` y sufijo "ARS" (no `$`), sin decimales fijos; viola la regla de formato | `documentos/page.tsx:117,123,137,141,333,343`; `ResumenImputacion.tsx:5`; `PropuestaCard.tsx:134-135` |
| T2 | **Bug de formato visible hoy**: el control muestra "total $ 114,950.00" y "$ -19.03" (formato EE.UU.) | `backend/src/features/imputacion/verificacion_externa.py:92` (`f"{…:,.2f}"`) |
| T3 | Estados técnicos en pantalla: "RequiereIntervencion", "Pendiente" crudos; "OT 123"; "fracción/fracciones"; "Motor (ARS)" | `documentos/page.tsx:79,123,139,320`; `PropuestaCard.tsx:137` |
| T4 | Rojo usado para una lista de avisos que no son errores del usuario (comprobantes ARCA sin cargar) y ocupa media pantalla arriba de todo | `ControlCostos.tsx:52-79` |
| T5 | No se usan los componentes del sistema: tablas `<table>` a mano, botones con clases sueltas, filtros con `<input type=date>` en vez de `RangoFechas`, `<select>` en vez de `Segmentos` | las 4 pantallas |
| T6 | Navegación del detalle fuera de contexto: "Revisar" lleva a `/imputacion?idDetalleCompra=` y "Abrir la compra" a otra página; se pierde el listado y los filtros | `documentos/page.tsx:157`; `ParaRevisar.tsx:39`; `ControlCostos.tsx:70` |
| T7 | Títulos "Imputación de costos · X" repetidos con el tab activo; la ayuda está en `?` y no hay KPI ni estado | `PageHeader` de las 4 pantallas |
| T8 | Sin estados de carga ni error en "Por documento" y "Automática" (`apiGet().then` sin `catch`) | `documentos/page.tsx:195-208`; `imputacion/page.tsx:93-96` |

---

## 1. "Por documento" (`frontend/src/app/imputacion/documentos/page.tsx`) — PRIORIDAD 1

### Lo que se ve hoy (captura `documentos.png`)
- Antes del primer documento hay ~520 px de bloques: caja roja de Control (5 ítems, 340 px), FilterBar de 6 campos, botón Exportar suelto. El primer documento aparece al pie de la pantalla.
- Cada documento es una tarjeta (`:297-338`) de ~180 px con: encabezado gris, título "Resumen por cultivo y campaña" (repetido en cada tarjeta, `ResumenImputacion.tsx:16`), un acordeón por destino (`:18`) y otro acordeón "Detalle por insumo y clasificación manual" (`:311`). Para una factura de peaje: **180 px para decir "Autopistas del Sol → Adm. General $ 6.572,88"**. Se ven 3-4 documentos por pantalla; con ~700 compras son ~35 páginas de 20.
- No hay columna de importe del documento ni estado en el encabezado: para saber si algo está pendiente hay que abrir dos acordeones.
- El total general está al pie (`:341-345`), después de 20 tarjetas, y sin formato de moneda.
- Moneda "Pesos" en texto (`:303`) mientras los importes dicen "ARS".
- Paginación "← Anterior / Siguiente →" a mano (`:348-368`), sin elegir tamaño.
- Filtros: "Para revisar / Solo lo aprobado automáticamente" + "Aprobado desde" son jerga del motor (`:276-284`). "Exportar a Excel (con estos filtros)" sólo considera 3 de 6 filtros en el rótulo (`:291`).
- Aprobar una fracción individual (`:143-154`) aprueba en realidad la **corrida entera** (`idCorrida`) — la acción dice menos de lo que hace.
- "Detalle por insumo": columnas "Campaña manual" y "Centro/Rubro manual" muestran lo que cargó la persona y "Motor" lo que calculó el sistema, pero sin marcar si coinciden: la comparación que importa queda para el ojo.

### Propuesta: tabla densa + panel lateral

```
Imputación de costos                                         [Exportar ▾]
[Automática] [Por documento] [Costo por cultivo] [Contratistas sin orden]

┌─ Total imputado ─────┐┌─ Por revisar ──────┐┌─ Pendientes ──┐┌─ Control ──────────────┐
│ $ 412.388.120,55     ││ 7 documentos       ││ 0             ││ 5 avisos  Ver ›         │
│ 712 documentos       ││ $ 3.120.400,00     ││               ││ hoy 21:16               │
└──────────────────────┘└────────────────────┘└───────────────┘└─────────────────────────┘

Período [Campaña 2026/27 ▾ | Este mes | Mes pasado | Personalizado]   Proveedor [Buscar…]
Destino: (Todos) (Soja 26/27) (Maíz 26/27) (Girasol 26/27) (Trigo 26/27) (Adm. General) (Ganadería) (En stock) +4
Estado:  [Todos | Por revisar 7 | Pendiente | Aprobado]          Agrupar por: [Documento | Destino | Proveedor]

 Fecha      Proveedor              Documento          Destino(s)                          Importe   Estado
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
 16/11/2026 Autopistas del Sol     FC 0840-00979484   (Adm. General)                    $ 6.572,88   ✓ Aprobado
 14/11/2026 Agronación             FC 0003-00012345   (Soja 26/27 62%)(Maíz 26/27 38%) $ 1.840.200,00 ✓ Aprobado
 12/11/2026 Bayá Casal             FC 0012-00004410   (En stock) (Trigo 26/27)         us$ 3.420,00   ● Por revisar
 10/11/2026 Pérez Servicios        FC 0002-00000871   (Girasol 26/27)                 $ 980.000,00   ● Pendiente
 …                                                                                 ⋮ (menú: Abrir compra, Ver remitos)
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
 712 documentos · Total con estos filtros                                        $ 412.388.120,55
                                                                     Filas: [50 ▾]   ‹ 1 2 3 … 15 ›
```

Clic en la fila → `SideDrawer` a la derecha, sin salir del listado:

```
┌─ FC 0012-00004410 · Bayá Casal ────────────── 12/11/2026  ✕ ┐
│ us$ 3.420,00  (≈ $ 4.104.000,00 al TC del comprobante)       │
│ ● Por revisar: la fecha no coincide con el ciclo del cultivo │
│                                                              │
│ Destinos                                                     │
│ ▇▇▇▇▇▇▇▇▇▇▇▇▇▇░░░░░░  Trigo 26/27     $ 2.900.000,00  71%    │
│ ▇▇▇▇▇░░░░░░░░░░░░░░░  En stock        $ 1.204.000,00  29%    │
│                                                              │
│ Renglones                                     Cargado | Sistema
│ Fungicida X 20 l        Trigo 26/27     =   Trigo 26/27 ✓    │
│   Lote 5 · 12 l · $ 1.740.000  ·  Lote 7A · 8 l · $ 1.160.000│
│ Urea 2.000 kg           Maíz 26/27      ≠   En stock  ⚠       │
│   (sin consumo todavía)                                      │
│                                                              │
│ ▸ De dónde sale (remitos y órdenes)                          │
│                                                              │
│ [Aprobar]  [Corregir destino]  [Abrir compra ↗]               │
└──────────────────────────────────────────────────────────────┘
```

- "Corregir destino" abre en el mismo panel los selectores Cultivo / Campaña por renglón (hoy en `PropuestaCard.tsx:142-166`) y "Aprobar" se transforma en "Aprobar con correcciones". Toast con "Deshacer".
- Agrupar por **Destino** convierte la tabla en filas-resumen (Soja 26/27 · 84 documentos · $ X) expandibles; responde "¿cuánto se fue a cada cultivo?" sin ir a otra pantalla.
- Agrupar por **Proveedor** idem, útil para el Estudio.

### Reglas de presentación
- Columnas: Fecha · Proveedor (con `ContactoLink`) · Documento (tipo abreviado FC/NC/ND + número) · Destino(s) en chips (máx. 2 visibles + "+N", con % si hay reparto) · Importe (moneda del documento, alineado a la derecha, tabular) · Estado (`StatusBadge`: Aprobado gris-verde, Pendiente ámbar, Por revisar ámbar con punto, Requiere intervención ámbar fuerte; rojo **sólo** para "no cierra el reparto").
- Chips de destino: un color neutro por familia (agricultura / ganadería / administración / stock), nunca rojo.
- NC con importe en negativo en el mismo tono, sin rojo.
- Fila de 36 px, una línea; proveedor truncado con tooltip.

---

## 2. Bloques "Control de costos" y "Para revisar" (`ControlCostos.tsx`, `ParaRevisar.tsx`)

Problemas:
- Se montan arriba de "Por documento" (`documentos/page.tsx:246-247`) y empujan la tabla fuera de la pantalla. Cuando hay 5 avisos ocupan 340 px.
- Caja roja (`ControlCostos.tsx:52`) para cosas que no son error del usuario: "Comprobante de ARCA que no está cargado" es una tarea pendiente, no una falla.
- Mezcla en una sola lista tipos distintos (orden ≠ factura de siembra / ARCA sin cargar) sin agruparlos.
- Razón social completa en mayúsculas de ARCA ("BANCO DE GALICIA Y BUENOS AIRES S. A.") en vez del nombre del contacto.
- Formato de importe en inglés (T2).
- "Controlar ahora" como link subrayado al costado; mientras corre dice "Controlando…" pero el título ya muestra una hora.
- "Para revisar" (`ParaRevisar.tsx:30`) es otro bloque amarillo con lista; manda a "Abrir la compra" (otra página).

Propuesta:
- Reemplazar ambos bloques por **dos KPI** ("Por revisar 7" y "Control: 5 avisos") en la fila de totales. Clic → filtra la tabla (Por revisar) o abre un `SideDrawer` "Control de costos" (avisos agrupados por tipo con contador: "Orden de siembra ≠ factura (2)", "Comprobantes de ARCA sin cargar (3)", cada ítem con acción "Cargar" / "Ver orden").
- `Callout` ámbar de una línea sólo si hay diferencias que afectan costo por cultivo ("2 diferencias pueden cambiar el costo de Girasol y Trigo 26/27 · Ver"). Rojo reservado a "el reparto no cierra".
- Backend: formatear con helper argentino en `verificacion_externa.py:92`, o mejor devolver `importe` y `moneda` numéricos y formatear en el front con `formatMoneda`.

---

## 3. "Automática" (`frontend/src/app/imputacion/page.tsx`)

Problemas (captura `automatica.png`):
- Hoy está vacía (0 pendientes, 1.937 aprobadas): la pestaña por defecto del módulo es la que menos información tiene.
- Dos botones de proceso ("Calcular pendientes", "Generar listado para el Estudio") son tareas que, según el principio de Sistema autónomo, deberían correr solas; quedan como acciones primarias en la primera pantalla.
- Filtro "Todas" muestra sólo propuestas sin aprobar → el rótulo miente (`:93-96` trae `pageSize: 200` sin estado, y el vacío dice "No hay imputaciones para revisar").
- Cada propuesta es una `PropuestaCard` completa apilada (`:235-254`), con un checkbox separado arriba con texto "Seleccionar propuesta para aprobación" (`:249`). Cada tarjeta hace 2 consultas propias (`PropuestaCard.tsx:45-59`) → N+1.
- "Requiere intervención" muestra tarjetas rojas (`:200`) con el motivo y una flecha "→ acción", sin botón para hacer la acción.
- Duplica "Por documento": misma información, otro diseño.

Propuesta:
- **Fusionar** "Automática" dentro de "Por documento" como el filtro de estado "Por revisar / Pendiente". Una sola pantalla "Imputación de costos" con la tabla de la sección 1; selección múltiple con checkbox en la tabla y barra flotante "3 seleccionados · Aprobar".
- "Calcular pendientes" y "Generar listado para el Estudio" pasan a un menú `⋯ Más acciones` en el `PageHeader` (secundarias), con la última fecha de ejecución ("Listado para el Estudio: actualizado hoy 06:00").
- Requiere intervención: en el panel lateral, motivo en lenguaje llano + botón directo ("Vincular orden", "Ver orden").

---

## 4. "Costo por cultivo / campaña" (`/produccion/ordenes/resultado-cultivo` → `FormularioCostos`)

Problemas (captura `resultado.png`):
- Abre vacía: "Elegí cultivo y campaña." con dos `<select>` "Elegí…". Pantalla entera en blanco. No recuerda la última elección.
- Es la respuesta natural a "¿dónde fue la plata?" pero no está conectada con "Por documento" (el clic en un concepto va a comprobantes, pero desde Por documento no se llega acá).

Propuesta:
- Abrir con la **campaña vigente** preseleccionada y, sin cultivo elegido, mostrar un resumen de todos los cultivos de esa campaña (tabla: Cultivo · ha sembradas · Costo $ · Costo us$ · $/ha · us$/ha). Elegir un cultivo abre el formulario actual (decisiones de réplica Access cerradas 12/11: no tocar su contenido).
- Campaña con `Segmentos` (últimas 3) en vez de select; recordar elección en `localStorage`.
- Desde un chip de destino en "Por documento", enlace "Ver costo de Soja 26/27 ›".

---

## 5. "Facturas de contratistas sin orden" (`/produccion/contratistas/sin-orden/page.tsx`)

Problemas (captura `sin-orden.png`):
- Hoy vacía; el vacío es un `<p>` gris (`:51`) en vez de `EmptyState` que diga "todo vinculado".
- Ocupa una pestaña completa siendo un **filtro** de la misma lista de documentos.
- Tabla a mano, `rowspan` simulado con celdas vacías (`:67-74`); "(sin imputar) · (sin imputar)" duplicado (`:82`).
- Etiqueta "Contratista" pegada al select (`:36-37`), sin totales.

Propuesta:
- Convertirla en un filtro/agrupación de "Por documento" ("Contratistas sin orden" como chip de estado), o mantener la pestaña pero con `DataTable` + `EmptyState icono="ok"` y total. Si queda en 0 la mayor parte del tiempo, sacar la pestaña y mostrar el contador sólo cuando hay casos.

---

## 6. Navegación del módulo

Hoy 4 pestañas, dos casi siempre vacías. Propuesta:

```
Imputación de costos   [Documentos] [Costo por cultivo]          ⋯ Más acciones
```
- **Documentos**: tabla única (ex Automática + Por documento + Sin orden como filtros).
- **Costo por cultivo**: resumen de campaña + formulario Access.
- Badge en la pestaña Documentos con "Por revisar" (ya existe `/revisar/contador`).

---

## 7. Lista priorizada de cambios implementables

| Prio | Cambio | Esfuerzo | Archivos |
|------|--------|----------|----------|
| P1 | Rehacer "Por documento" como `DataTable` de una fila por documento (Fecha/Proveedor/Documento/Destinos en chips/Importe/Estado) con `onRowClick` → `SideDrawer` de detalle, aprobación y corrección | M | `documentos/page.tsx`, nuevo `components/imputacion/DocumentoDrawer.tsx`, `ChipsDestino.tsx` |
| P1 | Fila de KPI arriba (Total imputado, Por revisar, Pendientes, Control) y total con filtros en el pie de tabla; quitar los bloques Control/Para revisar del flujo de la página | S | `documentos/page.tsx`, `ControlCostos.tsx`, `ParaRevisar.tsx` |
| P1 | Formato argentino en todo el módulo: `formatMoneda` en vez de `toLocaleString` + "ARS"; corregir `verificacion_externa.py:92` | S | T1, T2 |
| P1 | Estados con `StatusBadge` y textos llanos ("Por revisar", "Requiere tu decisión"); sacar "OT", "fracción", "Motor" | S | `documentos/page.tsx`, `PropuestaCard.tsx` |
| P2 | Filtros: `RangoFechas` con atajos (este mes, mes pasado, campaña), chips de Destino, `Segmentos` de Estado; aplicar al cambiar (sin botón Buscar); filtros en la URL | S-M | `documentos/page.tsx` |
| P2 | "Agrupar por Destino / Proveedor" con subtotales | M | necesita endpoint (abajo) |
| P2 | Fusionar "Automática" y "Contratistas sin orden" como filtros de la tabla; selección múltiple + "Aprobar seleccionados"; procesos en menú secundario | M | `imputacion/page.tsx`, `RemitosSubNav.tsx` |
| P2 | Panel "Control de costos" en `SideDrawer`, agrupado por tipo, ámbar; rojo sólo para reparto que no cierra | S | `ControlCostos.tsx` |
| P3 | "Costo por cultivo" abre con campaña vigente y resumen de todos los cultivos | M | `FormularioCostos`, endpoint resumen |
| P3 | Estados de carga/error (`LoadingState`/`ErrorState`) y `EmptyState` en todas | S | 4 pantallas |
| P3 | Trazabilidad en el panel con remitos y órdenes legibles ("Remito 0001-123 del 02/10 → Orden de pulverización del 05/10, Lote 5"), sin ids | S | `PropuestaCard.tsx:198-221` |

## 8. Endpoints de lectura necesarios

1. **`GET /api/imputacion/documentos/resumen`** (lista liviana) — misma firma de filtros que `/documentos` + `destino` (clave de destino) + `orden` + `pageSize` hasta 100. Por documento devuelve: fecha, proveedor, idContacto, tipo abreviado, número, moneda, importe del documento, `destinos: [{clave, etiqueta, importe, porcentaje}]`, `estado` agregado (peor estado de sus fracciones), `motivoRevision` en texto llano. Sin renglones (eso lo pide el panel). Hoy `/documentos` manda todas las fracciones de 20 documentos.
2. **`GET /api/imputacion/documentos/{idCompra}`** — detalle para el `SideDrawer`: renglones con cargado vs sistema y si coinciden, fracciones por lote, motivo de revisión, trazabilidad resumida.
3. **`GET /api/imputacion/documentos/totales`** — mismos filtros; devuelve `{total, cantidad, porEstado:{…}, porDestino:[{clave, etiqueta, importe, cantidad}]}`. Alimenta KPI, chips de destino con contador y "Agrupar por destino". (Parte existe en `total_general_documentos`.)
4. **`GET /api/imputacion/destinos`** — catálogo de destinos usados (cultivo+campaña, centros, ganadería, stock) para los chips.
5. `GET /api/imputacion/control`: agregar `importe` y `moneda` numéricos y `nombreContacto` del sistema por problema (en lugar del texto ya formateado).
6. (P3) `GET /api/ordenes/costos/resumen-campania?idCampania=` — cultivos de la campaña con ha y costo, para el arranque de "Costo por cultivo". Ver si `/api/imputacion/comparacion` ya lo cubre.

Ninguno escribe; las acciones (aprobar, aprobar lote, tamiz/renglón) ya existen.
