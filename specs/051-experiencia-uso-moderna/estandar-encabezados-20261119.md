# Estándar de encabezados de hoja — 19/11/2026

Agente 12 (diseño visual). Pedido de Sergio: "en el encabezado se puede optimizar el espacio todavía; rediseñarlo y generar un estándar para las diferentes hojas y menúes".

## 0. Diagnóstico (Tesorería hoy, 1600×900)

| Zona | Alto | Problema |
|---|---|---|
| NavHeader | 53 | ok (bajar a 48: `py-1.5`) |
| Título + "Cargar extracto" | ~50 | fila entera para una palabra y un botón |
| Callout Informes del Estudio | ~45 | banner informativo fijo: es estado, no contenido |
| Segmentos de medio | ~40 | fila propia; entra al lado del título |
| TiraIndicadores | ~48 | `py-2` + bordes de tarjeta |
| FilterBar con etiquetas | ~85 | caja + etiquetas arriba = 2 líneas por control |
| **Primera fila de datos** | **~320** | objetivo ≤ 180 |

## 1. Anatomía estándar: dos filas bajo la navegación

```
y=0   ┌ NavHeader 48px ─────────────────────────────────────────────────────────────────────┐
      │ [LH] La Herencia  Finanzas▾  Producción▾  Ganadería▾  Contactos  ...      🔔  Sergio▾ │
y=48  ├ FILA 1 (h-10, 40px) — identidad + navegación + estado + acciones ─────────────────────┤
      │ Tesorería │ BNA · Galicia · ICBC · Fima · ML(3) · Caja │ ●Estudio al día ▾ │ [Cargar extracto] │
y=88  ├ FILA 2 (h-10, 40px) — indicadores + filtros en una línea ─────────────────────────────┤
      │ Saldo $ 12.345.678,90 · [Sin conciliar 167] · Últ. ext. 30/09 ┃ [📅 Este mes ▾] [🔍 Buscar…    ] [⚙ Más filtros] │
y=128 ├ thead sticky (32px) ─────────────────────────────────────────────────────────────────┤
y=160 │ primera fila de datos                                                                  │
```

Primera fila ≈ 160 px a 1600×900 (presupuesto ≤ 180).

Reglas:
- **Fila 1** (`flex h-10 items-center gap-3 border-b`): `h1 text-base font-semibold` → separador vertical → pestañas de sección (`Segmentos size="sm" variante="subrayado"`, scroll horizontal si no entran) → `flex-1` → chips de estado → acciones (máx. 1 primaria visible + menú "⋯" para el resto).
- **Fila 2** (`flex h-10 items-center gap-2`): a la izquierda indicadores compactos (≤ 3; el que filtra es un chip-toggle), separador `┃`, a la derecha filtros inline h-8 sin etiquetas arriba. Chips de filtros activos van en esta fila, antes de "Más filtros".
- **Nada** de banners informativos fijos. Lo que es estado (Informes del Estudio, sincronizaciones, avisos) es un **chip de estado** en Fila 1: punto de color + texto corto (≤ 3 palabras), tooltip con el detalle y clic → popover con detalle y acciones ("Ver detalle", "Actualizar"). Solo un error que bloquea el trabajo puede ocupar una línea `text-xs` (h-7) bajo la Fila 2, descartable.
- Fila 1 y Fila 2 son **sticky** junto con el thead (`sticky top-12 z-10 bg-surface`), así al scrollear se mantienen título, filtros y columnas.

### 1366×768: qué se pliega

```
│ Tesorería │ BNA · Galicia · ICBC · Fima · ML · Caja ▸ │ ● │ [Cargar extracto] │
│ $ 12,3 M · [Sin conciliar 167] ┃ [📅 Este mes ▾] [🔍 Buscar…] [⚙ 2] │
```
Prioridad de plegado (primero se va lo de arriba):
1. Pie/textos secundarios de indicadores (fecha "Último extracto" pasa al tooltip del saldo).
2. Texto del chip de estado → queda solo el punto de color (tooltip y popover iguales).
3. Filtros secundarios → dentro de "Más filtros" (el botón muestra contador de activos: "⚙ 2").
4. Pestañas que no entran → menú "Más ▾" al final de las pestañas (nunca segunda línea).
5. Acciones secundarias → menú "⋯".
Siempre visibles: título, pestaña activa, búsqueda, fechas, indicador que filtra, acción primaria.

## 2. API de componentes

### PageHeader (nueva forma; la actual sigue como `variante="simple"` para formularios)
```tsx
<PageHeader
  titulo="Tesorería"
  volver?: string | onVolver?: () => void
  ayuda?: string                       // ícono "?" con tooltip
  pestanas?: React.ReactNode           // normalmente <Segmentos size="sm" variante="subrayado" …/>
  estado?: React.ReactNode             // uno o más <ChipEstado/>
  acciones?: React.ReactNode           // botones h-8; usar <MenuAcciones> para el resto
  sticky?: boolean                     // default true en listados
>{/* children = Fila 2 (BarraHoja) */}</PageHeader>
```
Markup: `<header className="sticky top-12 z-10 -mx-6 bg-surface px-6">` → Fila 1 `flex h-10 items-center gap-3 border-b border-border` → children como Fila 2 (`flex h-10 items-center gap-2`). `h1 className="shrink-0 text-base font-semibold"`. Separador: `<span className="h-5 w-px bg-border" />`.

### ChipEstado (nuevo, reemplaza Callout en encabezados)
```tsx
<ChipEstado tono="ok|aviso|error|info" texto="Estudio al día" detalle="8 informes, último 18/11"
  menu={<><button>Ver detalle</button><button>Actualizar</button></>} />
```
`inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-xs` + punto `h-2 w-2 rounded-full` del tono; clic abre popover (mismo patrón que RangoFechas: Escape y clic afuera cierran). Prop `compacto` → solo el punto.

### FilterBar `variante="inline"`
```tsx
<FilterBar variante="inline" onSubmit={…} masFiltros={<>…controles secundarios…</>} activos={2}>
  <RangoFechas compacto … />
  <BuscarInput placeholder="Buscar descripción, importe…" />
</FilterBar>
```
`inline`: `<form className="flex flex-1 flex-wrap items-center justify-end gap-2">` sin borde/fondo/padding. `FilterField` en modo inline no renderiza la etiqueta visible: la pasa a `aria-label` y a placeholder/prefijo dentro del control. `filterInputClass` → `h-8 rounded-md border px-2.5 text-sm`. `masFiltros` → botón "⚙ Más filtros" (`⚙ n` cuando hay activos) con popover de 2 columnas, etiquetas `text-xs` arriba (ahí sí). Búsqueda filtra al tipear (debounce 300 ms), sin botón "Filtrar".

### RangoFechas `compacto`
Sin etiqueta arriba; botón `h-8 px-2.5 text-sm` con ícono 📅 + `etiquetaRango` ("Este mes", "01/07/26–30/09/26"); `aria-label={etiqueta}`. Activo (≠ todas) en color finance como hoy.

### TiraIndicadores `compacta`
```tsx
<TiraIndicadores compacta items={[
  { titulo: "Saldo", valor: "$ 12.345.678,90", pie: "al 30/09" },
  { titulo: "Sin conciliar", valor: 167, aviso: true, activo: soloPend, onClick: togglePend },
]} />
```
`compacta`: `flex h-8 items-center gap-4 text-sm`, sin bordes ni fondo; cada ítem `titulo` `text-xs text-ink-muted` + `valor` `font-semibold tabular-nums`; `pie` va al `title` (tooltip) en vez de texto. Ítem con `onClick` = chip-toggle (`rounded-full border px-2.5 h-7`, activo `bg-finance-light text-finance`). Esto **reemplaza** los Segmentos "Todos / Pendientes 167": clic en "Sin conciliar 167" filtra; clic otra vez vuelve a todos.

### Segmentos `size="sm"` y `variante`
```tsx
<Segmentos size="sm" variante="subrayado" opciones={medios} valor={medio} onChange={setMedio} />
```
- `size="sm"`: botones `h-7 px-2.5 text-sm`, contenedor `h-8` (default actual queda `md`).
- `variante="subrayado"` (pestañas de sección/medio): sin fondo de contenedor; activo `text-ink-primary font-medium` + `border-b-2 border-finance` (o `agro` en Producción); inactivo `text-ink-secondary`. `aviso` = badge `text-[11px]` al lado.
- `variante="chips"` (actual): para opciones de filtro excluyentes.
- Desborde: `overflow-x-auto` + "Más ▾" con las que no entran (fase 2; fase 1 alcanza con scroll horizontal sin barra).

### Tesorería con la API

```tsx
<PageHeader
  titulo="Tesorería"
  pestanas={<Segmentos size="sm" variante="subrayado" opciones={medios} valor={medio} onChange={setMedio} />}
  estado={<ListadosEstudio modo="chip" />}
  acciones={<Button size="sm" onClick={abrirCarga}>Cargar extracto</Button>}
>
  <TiraIndicadores compacta items={[
    { titulo: "Saldo", valor: fmtMoneda(saldo, moneda), pie: `Último extracto ${fmtFecha(ultimoExtracto)}` },
    { titulo: "Sin conciliar", valor: pendientes, aviso: pendientes > 0,
      activo: filtro === "pendientes", onClick: () => setFiltro(f => f === "pendientes" ? "todos" : "pendientes") },
  ]} />
  <span className="h-5 w-px bg-border" />
  <FilterBar variante="inline" onSubmit={e => e.preventDefault()}
    activos={contarActivos(filtrosAvanzados)}
    masFiltros={<>{/* tipo de movimiento, contacto, importe desde/hasta */}</>}>
    <RangoFechas compacto valor={rango} onChange={setRango} />
    <input aria-label="Buscar" placeholder="Buscar…" className={`${filterInputClass} w-56`} value={q} onChange={e => setQ(e.target.value)} />
  </FilterBar>
</PageHeader>
<DataTable … stickyTop="top-[8rem]" />   {/* 48 nav + 80 encabezado */}
```
`ListadosEstudio modo="chip"` → `<ChipEstado tono={alDia ? "ok" : "aviso"} texto={alDia ? "Estudio al día" : "Estudio: 2 nuevos"} detalle="8 informes…" menu={Ver detalle · Actualizar}/>`; "Ver detalle" abre el panel lateral actual.

## 3. Menús

**NavHeader** (`h-12`, `py-1.5`, `px-4`):
```
│ [LH] La Herencia │ Finanzas▾ Producción▾ Ganadería▾ Contactos Informes▾ │        🔍 Ir a…  🔔3  SG▾ │
```
- Ítems `h-8 px-2.5 text-sm rounded-md`; activo `bg-surface-sunken font-medium` (el módulo de la página actual).
- Menús desplegables: `min-w-[14rem] py-1`, ítems `h-8 px-3 text-sm`, grupos con encabezado `text-[11px] uppercase text-ink-muted` (ya existe). Abrir por clic y hover-intent (150 ms), cerrar con Escape; navegación con flechas.
- Sin submenús de 3 niveles: si un módulo tiene > 12 destinos, agrupar en columnas dentro del mismo desplegable.
- Usuario/configuración en un solo menú de avatar a la derecha. Nada de textos de versión, conector o ids.

**Pestañas de sección** (RemitosSubNav, sub-nav de Órdenes, Tesorería, etc.): siempre `Segmentos size="sm" variante="subrayado"` (o `<SubNav>` con links y el mismo estilo) dentro de `pestanas` de PageHeader, **nunca** fila propia. Si la sección es una ruta, usar Link con `aria-current="page"`. Contador de pendientes como badge. Máximo 7 visibles + "Más ▾".

## 4. Otras hojas

**Listados (Compras, Órdenes, Remitos, Contactos)**: exactamente la anatomía de 2 filas. Fila 1: título · pestañas (estado: Todas/Pendientes/…) · chip de estado · "+ Nueva" primaria. Fila 2: 2-3 indicadores (total del filtro, cantidad, pendientes) + Fechas + Buscar + Más filtros (proveedor, campaña, cultivo, rubro). Primera fila ≤ 180 px. Totales en tfoot sticky.

**Formularios (nueva compra / orden)**:
```
│ ← Compra 0003-00012345 · Agronación · 12/11/2026      [Borrador]        Total $ 1.234.567,00 │  h-10 sticky
│ grid 4 col (Proveedor, Tipo/Nº, Fecha, Vto, Moneda/TC…) etiquetas text-xs, campos h-8         │
│ renglones (DataTable editable, thead sticky)                                                   │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Subtotal · IVA · Total                                     [Cancelar] [Guardar] [Guardar y nueva] │  sticky bottom-0
```
- PageHeader `variante="simple"` con `volver`, título = identidad del documento (tipo + número + contacto), estado como ChipEstado, total a la derecha. Sin pestañas.
- Barra de acciones fija abajo, siempre visible, con totales a la izquierda.
- Secciones colapsables (Imputación, Retenciones, Documentos relacionados) con encabezado h-8.

**Detalle / cuenta corriente**:
```
│ ← Agronación │ Movimientos · Pendientes · Documentos │ ●Cerrada │                [Nuevo pago] [⋯] │
│ Saldo $ 0,00 · US$ 0,00 · Vencido $ 0 ┃ [📅 Todas ▾] [🔍 Buscar…] [⚙]                         │
```
- Igual que listado: la entidad es el título, sus vistas son pestañas, sus totales son indicadores. Datos de la ficha (CUIT, condición IVA) en el tooltip/popover del título, no en un bloque.
- Avisos (AvisoCuentaContacto) como ChipEstado tono aviso, no banner.

**Tableros (Inicio, Resultado)**: sin tabla principal → pueden usar tarjetas; título h-10 igual.

## 5. Verificación
Captura a 1600×900 y 1366×768 de cada hoja tocada: medir y de la primera fila (≤ 180 / ≤ 190), confirmar que nada pasa a segunda línea a 1366 y que al scrollear quedan visibles Fila 1, Fila 2 y thead.

## 6. Orden de implementación sugerido
1. Segmentos `size`/`variante`, TiraIndicadores `compacta`, RangoFechas `compacto`, FilterBar `inline` (+ `masFiltros`), ChipEstado.
2. PageHeader con `pestanas/estado/acciones` y sticky; DataTable con `stickyTop` configurable.
3. Tesorería (ListadosEstudio `modo="chip"`) → medir.
4. Compras, Órdenes, Remitos (RemitosSubNav → pestanas), cuentas corrientes, formularios.
5. NavHeader h-12.
