# Auditoría de diseño — Finanzas › Tesorería (19/11/2026)

Agente: 12 · Especialista en diseño visual de frontend. Mismo método que `auditoria-imputacion-20261118.md`.
Capturas reales: `scratchpad/diseno-tesoreria/{bna,galicia,efectivo}.png` (1440 px).
Fuera de diseño propio (lo implementa otro agente en paralelo, acá solo se integra): **filtro "pendientes de conciliar"** y **conciliación automática LEY 25413**.

---

## 1. Diagnóstico general

La pantalla es un listado de movimientos con pestañas por medio, y debajo dos bloques sueltos de carga (PDF y Excel). Funciona, pero **no responde la pregunta que el usuario trae al entrar**: *"¿qué me falta conciliar y cuánto es?"*. Para saberlo hay que paginar de a 50 filas y mirar las pastillas una por una.

### Hallazgos transversales (archivo:línea)

| # | Hallazgo | Dónde | Tipo |
|---|---|---|---|
| T1 | **Sin resumen arriba**: no hay saldo actual, ni cantidad/importe sin conciliar, ni fecha del último extracto. Existe `GET /tesoreria/{medio}/cargas` pero la pantalla no lo usa. | `app/finanzas/tesoreria/page.tsx:40-47` | Funcionalidad |
| T2 | **N+1 de pedidos**: cada fila dispara `GET …/conciliacion` (estado) aunque el listado ya trae `estadoConciliacion`; 50 filas = 51 pedidos y una columna que "parpadea" con "…". El backend además calcula `esta_resuelto` fila por fila. | `ConciliarMovimiento.tsx:75-79,92`; `backend/src/features/tesoreria/router.py:71-79` | Rendimiento / aspecto |
| T3 | **4 links sueltos por fila** (Conciliar/Ver cuenta + Extracto + Origen + Traspaso) en dos columnas distintas; ruido visual en todas las filas, incluso las ya resueltas. | `MovimientosPorMedio.tsx:279-308` | Aspecto |
| T4 | **"Origen" se expande dentro de la fila** y rompe la altura de la tabla; muestra "Compra #idCompra" (id interno) e importe sin formato (`{c.importe ?? "—"}`). | `ReferenciaOrigen.tsx:33-52`; `MovimientosPorMedio.tsx:304` | Aspecto / premisa sin internos / formato |
| T5 | **Conciliar abre un `<dialog>` modal** que tapa el listado; no se ve el movimiento mientras se elige documento. Dos pestañas ("Documentos"/"Carga manual") con estilo de link subrayado. Hay paso de "Continuar → Confirmar" (confirmación en vez de deshacer). | `ConciliarMovimiento.tsx:203-305` | Flujo |
| T6 | **Traspaso pide "Id movimiento"** a mano y muestra "Banco Nación #123". Código interno en pantalla. | `VincularTraspasoInterno.tsx:~133-162` | Premisa sin internos |
| T7 | Estado **"Sin documento" en verde** (`tone: success`) igual que "Conciliado": no se distingue lo resuelto con papeles de lo resuelto sin papeles. | `ConciliarMovimiento.tsx:31` | Color con significado |
| T8 | **Columna Contacto vacía ("—") aunque el movimiento esté "Ya reconocido"**: el nombre del contacto existe (`contactoReconocido`) pero queda escondido en el title del link "Ver cuenta". | `MovimientosPorMedio.tsx:154`; `ConciliarMovimiento.tsx:180-192` | Información |
| T9 | **Sin búsqueda** por concepto, contacto o importe; solo rango de fechas. El endpoint no tiene `q` ni `estado`. | `MovimientosPorMedio.tsx:313-326`; `router.py:58-65` | Funcionalidad |
| T10 | **Sin totales** (Debe/Haber del período) ni pie de tabla. | `MovimientosPorMedio.tsx:333-344` | Funcionalidad |
| T11 | Columnas numéricas con encabezado alineado a la izquierda; Debe/Haber separados en dos columnas con "—" en la mitad de las celdas (medio ancho desperdiciado). Fecha marcada `numeric`. | captura `bna.png`; `MovimientosPorMedio.tsx:149-153` | Aspecto |
| T12 | **Carga de archivos partida en dos bloques al pie** ("Cargar resumen bancario en PDF" y "Excel"), lejos de la tabla que alimentan; el usuario tiene que saber qué formato trae. | `page.tsx:49-55`; `CargaExtractoPdf.tsx:55-60`; `CargaExcel.tsx:84-94` | Flujo |
| T13 | Rutas de Dropbox con el usuario de Windows embebidas en el front (`C:\Users\Sergio\…`) para armar el link "Extracto". | `MovimientosPorMedio.tsx:85-106` | Mantenibilidad (mover al backend) |
| T14 | `Segmentos` de medio no muestra pendientes por pestaña; no se sabe en qué banco hay trabajo sin entrar a cada uno. El medio elegido no se guarda en la URL (al recargar vuelve a BNA salvo `?medio=`). | `page.tsx:32,43` | Flujo |
| T15 | Errores por fila en rojo subrayado ("No se pudo leer la conciliación. Reintentar") repetidos 50 veces si cae el backend. | `ConciliarMovimiento.tsx:89-91` | Estados |

### ¿Cómo concilia hoy un movimiento el usuario? (BNA)
1. Elegir pestaña → 2. paginar/buscar a ojo la fila "Sin conciliar" → 3. clic **Conciliar** (modal) → 4. elegir documentos (o pasar a "Carga manual" → buscar contacto → importe → **Continuar** → **Confirmar**) → 5. cerrar modal. **4 a 7 clics por movimiento**, sin sugerencia visible antes de abrir, sin conciliación en lote. Lo repetitivo (comisiones, IVA, retenciones, LEY 25413) se hace uno por uno — en la captura, 11 de 16 filas visibles son "Sin conciliar" y casi todas son gastos bancarios de rubro fijo.

---

## 2. Hallazgos por pestaña

- **Banco Nación**: los de T1–T15. Pares "COMISION PAQUETES / I.V.A. BASE / RETEN. I.V.A. RG.2408" se repiten cada mes con mismo importe y mismo destino → candidatos ideales a **regla** (como LEY 25413).
- **Galicia**: columnas Débitos/Créditos (otro nombre que BNA para lo mismo). Unificar a una sola columna "Importe" con signo visual (ver §3). Sin link a extracto (no hay carpeta mapeada).
- **Mercado Libre**: la etiqueta "Conducto" es buena idea pero se ve como borde gris sin explicación salvo `title`; pasarla a `StatusBadge` neutral "Puente" con tooltip. Mismo esquema que bancos.
- **Pagos en efectivo**: columnas Cuenta/Caja/Nro. documento; no hay saldo de caja ni contacto. Debería mostrar saldo de la caja elegida (KPI) y filtrar por caja (Segmentos con las cajas).
- **Valores propios / recibidos**: son carteras, no extractos. Lo que importa es **vencimiento y estado** (en cartera / depositado / cobrado / rechazado). Hoy "Cobrado" es texto crudo y no hay orden por vencimiento ni KPI "a vencer próximos 7/30 días". "Exportar a Excel" solo existe en propios.
- **Tarjetas**: lista de consumos sin estado; la conciliación vive en otra pantalla (008/009) y acá no hay ni un link. Agregar link "Conciliar en Tarjetas →" en el encabezado y estado (conciliada/pendiente) por línea.
- **Informes del Estudio**: el `Callout` de una línea está bien (aprobado el 18/11). Moverlo a la derecha del encabezado como indicador chico ("Informes del Estudio: al día") para que no empuje la tabla 50 px hacia abajo.

---

## 3. Propuesta

Referencia: bank feeds de Xero/QuickBooks (cola "Para revisar" con sugerencia por fila y botón "Aceptar") y Mercury (tabla densa + panel lateral).

### 3.1 Boceto — pestaña de banco

```
Tesorería  (?)                                   Informes del Estudio: al día ●   [Cargar extracto ▾]
[ Banco Nación 14 ][ Galicia 3 ][ Mercado Libre ][ Efectivo ][ Valores propios ][ Valores recibidos ][ Tarjetas ]

┌ Saldo al 11/11 ─────┐┌ Sin conciliar ───────┐┌ Sugerencias listas ─┐┌ Último extracto ─────┐
│ $ 429.893,34        ││ 14 mov · $ 98.340,12 ││ 9 · $ 84.120,00     ││ Octubre 2026 (PDF)   │
│                     ││ más viejo: 30/09     ││ [Aceptar todas]     ││ cargado 12/11 · Ver  │
└─────────────────────┘└──────────────────────┘└─────────────────────┘└──────────────────────┘

[ Pendientes 14 ][ Con sugerencia 9 ][ Conciliados 1.203 ][ Todos ]   🔍 concepto, contacto o importe   [Este mes ▾]

 ☐  Fecha       Concepto                       Contacto / sugerencia              Importe        Saldo   Estado
 ☐  11/11/2026  COMISION PAQUETES              ✦ Banco Nación · Gastos bancarios   −69.000,00  429.893,34  Sin conciliar  [Aceptar] ⋯
 ☐  11/11/2026  I.V.A. BASE                    ✦ Banco Nación · IVA                −14.490,00  498.893,34  Sin conciliar  [Aceptar] ⋯
 ☐  11/11/2026  GRAVAMEN LEY 25413 S/DEB       Impuesto débitos y créditos            −414,00  515.453,34  Conciliado (auto)        ⋯
 ☐  30/10/2026  EMIS TRANSFERENCIA/GIRO        Criado S.A.                      −1.396.407,00  524.345,14  Ya reconocido            ⋯
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    Período: 214 movimientos      Débitos $ 4.120.334,10   Créditos $ 3.880.000,00   Neto −$ 240.334,10
 [2 seleccionados: Conciliar juntos · Marcar sin documento · Traspaso interno]   ← barra flotante de lote
```

- Una sola columna **Importe** con signo (débito `−` en texto normal, crédito en tono `finance`); rojo nunca.
- **Contacto / sugerencia**: el contacto real si está resuelto; si no, la sugerencia (✦, en gris) con botón **Aceptar** en la fila. Un clic concilia los casos obvios.
- **Estado** con `StatusBadge`: Sin conciliar (neutral), Parcial (warning, con "faltan $ x"), Conciliado (success), Ya reconocido (success suave), Sin documento (**warning suave**, no verde), Traspaso interno (info), Conciliado (auto) para LEY 25413.
- Menú **⋯** (`rowActions`): Conciliar…, Ver extracto del mes, Ver origen, Traspaso interno…, Ver cuenta del contacto, Quitar conciliación.
- Clic en la fila (`onRowClick` + `selectedKey`) abre el panel lateral.
- Los **Segmentos de estado** usan el filtro de pendientes que está implementando el otro agente; solo agregan contadores y las opciones "Con sugerencia" y "Conciliados".

### 3.2 Boceto — panel lateral de conciliación (`SideDrawer`)

```
┌ Movimiento ────────────────────────────── ✕ ┐
│ 11/11/2026 · Banco Nación                   │
│ COMISION PAQUETES                           │
│ −$ 69.000,00          Pendiente $ 69.000,00 │
│ [Ver extracto de noviembre]                 │
├ Sugerencias ────────────────────────────────┤
│ ● Banco Nación – Gastos bancarios  $ 69.000 │
│   igual al mes pasado (08/10)   [Usar]      │
│ ○ Factura 0003-1234 Criado  $ 69.000 16/10  │
├ Buscar documento o contacto ────────────────┤
│ 🔍 ______________________   (lista tildable │
│    filtrada por contacto + tipo doc)        │
├ Reparto ────────────────────────────────────┤
│ Criado S.A.  ............  $ 69.000,00  ✕   │
│ Queda sin asignar          $ 0,00           │
├─────────────────────────────────────────────┤
│ Otras: [Sin documento…] [Traspaso interno…] │
│                         [Conciliar]  (P)    │
└─────────────────────────────────────────────┘
```
- Reemplaza el `<dialog>` modal; el listado sigue visible y con ↑/↓ se pasa al siguiente pendiente sin cerrar (flujo "cola", como Xero).
- Documentos y carga manual en un solo flujo: si no hay documento, el buscador ofrece el contacto; desaparece la pestaña "Carga manual".
- Sin paso "Continuar → Confirmar": se guarda y el toast ofrece **Deshacer** (usa el `DELETE …/conciliacion/{id}` existente).
- Respetar la regla de [documentos relacionados]: lista tildable filtrada por proveedor + tipo, no buscador de texto libre como única vía.
- Traspaso interno: candidatas con texto "Galicia · 11/11/2026 · $ 500.000,00 · TRANSF. PROPIA"; el campo "Id movimiento" se reemplaza por búsqueda por fecha/importe en el otro medio.

### 3.3 Carga de extracto unificada

Un solo botón **Cargar extracto** en el encabezado → `SideDrawer` con zona de arrastre que acepta `.pdf,.xls,.xlsx`; detecta banco y formato (el backend ya detecta `medio_detectado` en Excel y banco en PDF), muestra vista previa con contadores "Nuevos 42 · Ya cargados 180 · Incompletos 0" y **Confirmar carga**. Al terminar: toast + la pestaña salta al banco cargado con el segmento "Pendientes" activo ("42 movimientos nuevos para conciliar"). Se borran los dos bloques del pie.

### 3.4 Valores y efectivo
- Valores propios/recibidos: KPI "En cartera $ · vencen en 7 días $ · rechazados n"; Segmentos de estado (En cartera / Depositados / Cobrados / Rechazados); orden por vencimiento; badge de vencido (warning). Exportar a Excel en ambas.
- Efectivo: Segmentos por caja, KPI saldo de la caja, columna Contacto.

---

## 4. Lista priorizada

| Prio | Mejora | Esfuerzo | Archivos |
|---|---|---|---|
| **P1** | Usar `estadoConciliacion` del listado y no pedir estado por fila (cargar el detalle solo al abrir el panel); el backend calcula estados en una consulta por página. | M | `ConciliarMovimiento.tsx`, `MovimientosPorMedio.tsx`, `backend/src/features/tesoreria/router.py`, `estado_resolucion.py` |
| **P1** | Fila de KPI (saldo, sin conciliar cant./importe, último extracto) + contadores en Segmentos de medio. | M | `page.tsx`, `MovimientosPorMedio.tsx`, nuevo `ResumenMedio.tsx`, endpoint resumen |
| **P1** | Segmentos de estado con contadores (integra filtro pendientes del otro agente) + búsqueda concepto/contacto/importe + pie con totales. | M | `MovimientosPorMedio.tsx`, `repository.get_movimientos` (`q`, `estado`, totales) |
| **P1** | Acciones de fila en menú ⋯ (`rowActions`) y panel lateral (`SideDrawer`) en lugar de modal + 4 links + Origen expandido. | M-L | `MovimientosPorMedio.tsx`, `ConciliarMovimiento.tsx` → `PanelConciliacion.tsx`, `ReferenciaOrigen.tsx`, `VincularTraspasoInterno.tsx` |
| **P1** | Quitar internos y arreglar formato: "Compra #id", "#idMovimiento", campo "Id movimiento", importe sin `formatMoneda`; "Sin documento" a warning; Contacto visible cuando está reconocido. | S | `ReferenciaOrigen.tsx`, `VincularTraspasoInterno.tsx`, `ConciliarMovimiento.tsx:31`, `MovimientosPorMedio.tsx` |
| **P2** | Sugerencia en la fila + botón **Aceptar** y "Aceptar todas" (reglas recurrentes: comisión, IVA, retención RG 2408 — mismo mecanismo que LEY 25413). | L | backend `matching.py`/reglas, `MovimientosPorMedio.tsx` |
| **P2** | Selección múltiple y conciliación en lote (mismo contacto/rubro, sin documento, traspaso). | M | `DataTable` (checkbox), endpoint lote |
| **P2** | "Cargar extracto" único (PDF o Excel) en drawer, salto a pendientes al confirmar. | M | `page.tsx`, fusionar `CargaExcel.tsx` + `CargaExtractoPdf.tsx` → `CargarExtracto.tsx` |
| **P2** | Deshacer en vez de "Continuar/Confirmar"; navegación ↑/↓ entre pendientes con el panel abierto. | S-M | `PanelConciliacion.tsx`, `Toast` |
| **P2** | Columna única Importe con signo (BNA, Galicia, ML, efectivo); encabezados numéricos a la derecha; nombres iguales entre bancos. | S | `MovimientosPorMedio.tsx:145-222`, `DataTable` |
| **P3** | Valores: KPI cartera/vencimientos, segmentos de estado, export en recibidos. Efectivo: segmentos por caja + saldo. | M | `MovimientosPorMedio.tsx`, `repository.py`, `exportacion.py` |
| **P3** | Tarjetas: estado por línea + link a su conciliación. Informes del Estudio como indicador en el encabezado. Medio en la URL. | S | `page.tsx`, `ListadosEstudio.tsx` |
| **P3** | Mover rutas de extractos Dropbox al backend (`urlExtracto` en cada fila). | S | `MovimientosPorMedio.tsx:85-106`, `repository.py` |

## 5. Endpoints de lectura necesarios

| Endpoint | Para qué | Estado |
|---|---|---|
| `GET /tesoreria/{medio}/movimientos?estado=&q=&fechaDesde=&fechaHasta=` → `items`, `total`, **`totales{debitos,creditos}`**, `estadoConciliacion`, `contacto` resuelto, `saldoPendiente`, `sugerencia{texto,importe,tipo}`, `urlExtracto` | tabla, filtros, pie, fila con sugerencia | ampliar (el filtro `estado` lo agrega el otro agente) |
| `GET /tesoreria/{medio}/resumen` → `saldoActual`, `fechaSaldo`, `sinConciliar{cantidad,importe,masViejo}`, `conSugerencia{cantidad,importe}`, `ultimoExtracto{periodo,formato,fechaCarga}` | KPI | nuevo (puede reusar `/{medio}/cargas`) |
| `GET /tesoreria/resumen` → pendientes por medio | contadores en pestañas de medio | nuevo |
| `GET /conciliacion-tesoreria/{medio}/movimientos/{id}/candidatos` | sugerencias del panel | existe |
| `GET /traspasos-internos/{medio}/movimientos/{id}/traspaso-interno` con búsqueda por fecha/importe | traspaso sin ids | ampliar |
| `POST …/conciliar-lote` (varios movimientos) | lote | escritura nueva (P2) |

Reglas aplicadas: formato `$ 1.234,56` con helpers de `lib/format`; rojo solo para error de carga/alerta; nada de ids ni códigos en pantalla; castellano rioplatense.
