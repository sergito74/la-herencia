# La Herencia — Rediseño de Frontend "Tierra & Cultivo"

**Autor:** agroux-lead-product-architect (09) · **Fecha:** 2026-09-16 · **Alcance:** 7 módulos financieros/administrativos hoy implementados (todos read-only sobre SQL Server). Sin escritura, sin agricultura/ganadería operativa (tablas no existen aún).

---

## 1. Diagnóstico

El feedback del usuario ("esto no es un frontend, no tiene diseño ni funcionalidad") es correcto y verificable en el código:

1. **Cero sistema de diseño.** `tailwind.config.ts` tiene `theme.extend: {}` vacío. `globals.css` son 3 líneas (`@tailwind base/components/utilities`) sin variables CSS, sin fuente custom, sin modo oscuro. Cada color es una clase de Tailwind por defecto (`slate-50…900`, `blue-700`, `red-700`, `green-700`) repetida ad hoc en cada componente. No hay identidad "agro" en ningún píxel: podría ser el frontend de cualquier CRUD.
2. **Sin jerarquía visual entre navegación primaria y secundaria.** `NavHeader.tsx` distingue "top level" (Tesorería/Cuentas Corrientes/Compras) de "Otros movimientos" (dropdown) solo por presencia/ausencia de un menú desplegable, sin refuerzo visual (mismo tamaño, mismo peso salvo `underline` en el activo). No hay breadcrumbs, no hay indicador de sección actual más allá del subrayado, no hay selector de contexto (no existe aún Establecimiento/Campaña, pero tampoco hay *espacio reservado* para él — la barra es un `flex` de ancho fijo sin lugar para crecer).
3. **Tablas sin densidad ni interacción real.** El patrón se repite idéntico en los 7 módulos: `<table className="min-w-full divide-y divide-slate-200 text-sm">`, sin ordenamiento por columna, sin filtros rápidos (chips), sin ajuste de densidad, paginación fija en 50 con textos "Anterior/Siguiente". Es una tabla HTML por defecto con bordes, no un componente de datos.
4. **Estados sin codificación visual.** El campo `estado` de `Cobro de alquiler` (Arrendamientos) se renderiza como texto plano en la celda — no hay ni un solo badge de color en toda la aplicación. Los únicos usos de color semántico son `text-red-700`/`text-green-700` para deuda/crédito en Cuentas Corrientes, aplicados de forma inconsistente (no hay ese tratamiento en Impuestos, Remuneraciones, Ventas de Hacienda).
5. **Loading/empty/error son un `<p>`.** `"Cargando…"`, `"Ocurrió un error al…"`, `"Sin resultados para esta búsqueda."` — texto plano sin estructura, sin skeleton, sin ícono, sin distinción tipográfica del resto del body copy. Se siente "roto" más que "vacío".
6. **Sin diferenciación de perfil de usuario.** Todo el layout asume una única persona sentada en un escritorio con mouse: no hay hit-targets ≥44px, no hay vista simplificada para uso en campo/tablet (aunque hoy no aplica a estos 7 módulos financieros, la ausencia de cualquier mecanismo de adaptación es un problema estructural que se va a repetir cuando lleguen las pantallas de campo).
7. **Home (`page.tsx`) es una lista de links, no un dashboard.** Tarjetas `rounded-lg border ... hover:border-slate-400` sin ningún dato (sin saldo, sin "qué vence hoy", sin resumen) — es un índice de módulos, no un punto de entrada útil para la operación diaria, contradiciendo la guía ya registrada por 08 de que Tesorería/Cuentas Corrientes deberían ser el punto de entrada con saldo y vencimientos visibles.
8. **Puntos que SÍ están bien y hay que preservar:** el patrón de nunca ocultar nulls (`DetalleCompra.tsx` muestra "Sin asignar"/"Sin imputar" en itálica gris en vez de omitir), la trazabilidad de origen en Tesorería (`ReferenciaOrigen`), y la separación de "medios" de tesorería sin forzar un modelo único. Estas decisiones de datos son correctas — el problema es 100% de capa visual/interacción, no de modelo.

**Conclusión:** no hace falta "arreglar" lógica de negocio ni tocar contratos de datos — hace falta construir, desde cero, la capa de diseño (tokens, componentes, jerarquía) que hoy no existe, y aplicarla consistentemente a los 7 módulos ya construidos.

---

## 2. Design system "Tierra & Cultivo"

### 2.1 Paleta de color (hex)

| Token | Hex | Uso |
|---|---|---|
| `background` | `#F8F9F6` | fondo de página (cálido, no blanco puro) |
| `surface` | `#FFFFFF` | tarjetas, tablas, paneles |
| `surface-sunken` | `#F1F0EA` | filas alternadas, headers de tabla, filtros |
| `border` | `#E3E0D6` | bordes stone, reemplaza `slate-200` |
| `border-strong` | `#C9C4B4` | bordes de foco/hover |
| `text-primary` | `#2B2A25` | texto principal (casi negro cálido, no `slate-900`) |
| `text-secondary` | `#6B6858` | texto secundario, reemplaza `slate-600` |
| `text-muted` | `#9C977F` | placeholders, "Sin asignar", metadata |
| `agro-primary` (agricultura) | `#2F5233` | verde hoja profundo — acento agrícola |
| `agro-light` | `#E7EEE3` | fondo suave para badges/secciones agrícolas |
| `livestock-primary` (ganadería) | `#8A5A2B` | ocre/cuero — acento ganadero |
| `livestock-light` | `#F3E7D8` | fondo suave para badges/secciones ganaderas |
| `finance-primary` (admin/finanzas — dominio actual) | `#3E5C76` | azul grisáceo tierra, identidad para los 7 módulos de hoy |
| `finance-light` | `#E6EBF0` | fondo suave de sección financiera |
| `status-success` | `#3F7D45` | cobrado / pagado / ok |
| `status-success-bg` | `#E4F0E5` | fondo badge éxito |
| `status-warning` | `#B5792A` | pendiente / próximo a vencer |
| `status-warning-bg` | `#FBEEDC` | fondo badge advertencia |
| `status-danger` | `#B23A2E` | vencido / error / deuda |
| `status-danger-bg` | `#F7E3E0` | fondo badge peligro |
| `status-neutral` | `#6B6858` | sin datos / no aplica |
| `status-neutral-bg` | `#EDEBE3` | fondo badge neutro |

Regla: **cada módulo financiero usa `finance-primary` como acento**; los acentos `agro-*`/`livestock-*` quedan reservados para cuando existan esas pantallas (sección 3.3) — no se usan hoy, pero se documentan para no tener que rediseñar la paleta después.

### 2.2 Tipografía

- Familia: `Inter` (o system-ui como fallback) para UI; sin fuente serif — se prioriza legibilidad de datos densos.
- Escala: `text-xs` (12px, metadata/badges), `text-sm` (14px, tablas/cuerpo — tamaño por defecto de la app), `text-base` (16px, formularios), `text-lg` (18px, subtítulos de sección), `text-xl` (20px, título de módulo), `text-2xl` (24px, título de página).
- **Regla obligatoria: `tabular-nums` en toda columna numérica, monetaria o de fecha** (montos, cantidades, `IdContacto`, números de documento, saldos, `precioUnitarioA/B`, pesos). Sin excepción — es requisito de legibilidad para comparar columnas alineadas, no estético. Aplicar vía clase utilitaria `.font-data` (ver 2.4).
- Pesos: `font-normal` cuerpo, `font-medium` encabezados de tabla y valores destacados, `font-semibold` títulos.

### 2.3 Espaciado / densidad

- Escala base 4px (estándar Tailwind), pero se define una **densidad de tabla "compacta"** para uso administrativo: celda `py-1.5 px-3` (vs. el `py-2 px-4` por defecto que usan hoy los módulos) — más filas visibles por pantalla, acorde al perfil "administración: máxima densidad" del brief.
- Contenedores de página: `max-w-6xl` (ya usado en `NavHeader`, se mantiene consistente con `page.tsx` que hoy usa `max-w-4xl` — unificar a `max-w-6xl` en toda la app).

### 2.4 Bordes, sombra, radios

- `radius-sm`: 4px (badges, inputs). `radius-md`: 8px (tarjetas, tablas — ya usado como `rounded-lg`). `radius-lg`: 12px (paneles/drawers).
- Sombra: una sola escala, `shadow-sm` para hover de tarjetas (ya en uso), `shadow-lg` para drawers/dropdowns (ya en uso en el dropdown de nav) — no introducir más niveles.

### 2.5 Implementación — `tailwind.config.ts`

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#F8F9F6",
        surface: { DEFAULT: "#FFFFFF", sunken: "#F1F0EA" },
        border: { DEFAULT: "#E3E0D6", strong: "#C9C4B4" },
        ink: { primary: "#2B2A25", secondary: "#6B6858", muted: "#9C977F" },
        agro: { DEFAULT: "#2F5233", light: "#E7EEE3" },
        livestock: { DEFAULT: "#8A5A2B", light: "#F3E7D8" },
        finance: { DEFAULT: "#3E5C76", light: "#E6EBF0" },
        status: {
          success: "#3F7D45", "success-bg": "#E4F0E5",
          warning: "#B5792A", "warning-bg": "#FBEEDC",
          danger: "#B23A2E", "danger-bg": "#F7E3E0",
          neutral: "#6B6858", "neutral-bg": "#EDEBE3",
        },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      borderRadius: { sm: "4px", md: "8px", lg: "12px" },
    },
  },
  plugins: [],
};
export default config;
```

### 2.6 Implementación — `globals.css` (añadir bajo las directivas `@tailwind`)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --color-bg: #F8F9F6;
  --color-surface: #FFFFFF;
  --color-border: #E3E0D6;
}

body {
  background-color: var(--color-bg);
  color: #2B2A25;
  font-family: "Inter", system-ui, sans-serif;
}

/* Obligatorio en toda celda numérica/monetaria/fecha — ver sección 2.2 */
.font-data {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}
```

---

## 3. Árbol de navegación

### 3.1 Reorganización de los 7 módulos existentes

Criterio: frecuencia de consulta real (diaria vs. "cuando hace falta"), no el orden en que se construyeron. Se conserva la separación primaria/secundaria ya validada con 08, pero se refuerza visualmente y se agrega Home como panel real (no índice de links).

```
Home (Panel del día)                    ← nuevo: saldo consolidado, qué vence hoy/semana, accesos directos
├── Tesorería          (primario, diario)
│   └── por medio: BNA · Galicia · Efectivo · Valores propios · Valores recibidos · Tarjetas
├── Cuentas Corrientes  (primario, diario)
│   └── por contacto: saldo, movimientos, origen
├── Compras             (primario, frecuente)
│   └── detalle de compra → trazabilidad
└── Otros movimientos ▾ (secundario, "cuando hace falta")
    ├── Impuestos
    ├── Remuneraciones
    ├── Arrendamientos
    └── Ventas de Hacienda
```

Cambios concretos respecto a hoy:
- El header pasa de `flex` plano a dos niveles visuales reales: franja superior (logo + selector de contexto futuro, ver 3.3) y franja de navegación con **peso tipográfico y color de fondo distintos** entre ítems primarios (`finance-primary` como color activo, fondo `finance-light` on-hover) y el dropdown secundario (tono `ink-secondary`, sin color de marca).
- Home dejar de ser una grilla de cards-link y pasar a un panel con: saldo consolidado (Cuentas Corrientes), próximos vencimientos (cuotas de Arrendamiento con `estado ≠ Cobrado`, tarjetas por vencer), y accesos directos a los 3 módulos primarios — sin inventar KPIs que no salen de datos reales.
- Mantener "Otros movimientos" (no "Egresos") — la razón ya documentada por 08 sigue siendo válida (Arrendamientos y Ventas de Hacienda son ingresos).

### 3.2 Breadcrumbs

Agregar breadcrumb bajo el header en toda vista de detalle (hoy ausente): `Compras / Compra #12345` — usa el mismo componente para Cuentas Corrientes (`Cuentas Corrientes / Juan Pérez`) y detalle de Arrendamiento/Venta de Hacienda cuando se abra un drawer con URL propia.

### 3.3 Dónde engancha el futuro (Establecimiento → Potrero/Lote → Campaña) — *futuro / sin datos aún*

No hay tablas de Establecimiento/Potrero/Lote/Campaña en SQL Server hoy (confirmado en investigación previa del proyecto), por lo que esto es un placeholder de arquitectura, no una pantalla a construir:

- Reservar en la franja superior del header un slot para un **selector de contexto persistente** (Establecimiento actual, opcionalmente Campaña activa) — hoy renderiza `null`/oculto, pero el layout (`flex` con `gap`) debe dejarle espacio para no requerir un rediseño del header cuando se active.
- Cuando existan datos, este selector afecta el filtrado por defecto de pantallas nuevas de agricultura/ganadería, **no** a los 7 módulos financieros actuales (Compras/Tesorería/etc. ya tienen `idCampania`/`campania` como campo opcional de imputación, no como contexto obligatorio — no forzar el selector sobre ellos).
- La navegación de agricultura/ganadería colgaría como un tercer grupo primario junto a "Otros movimientos": `Producción` (labores, órdenes de trabajo, rendimientos — acento `agro`) y `Ganadería` (rodeos, sanidad, pesajes — acento `livestock`), cada uno subordinado al selector de Establecimiento/Campaña. **No diseñar contenido de estas pantallas ahora** — no hay schema real que las sustente; solo reservar el lugar en el árbol.

---

## 4. Guía de componentes

Catálogo mínimo viable, todos read-only para el alcance actual:

1. **`DataTable`** — reemplaza el `<table>` ad hoc repetido en los 7 módulos.
   - Ordenamiento multi-columna (click en header, indicador de dirección).
   - Chips de filtro rápido sobre la tabla (ej. Arrendamientos: chips "Pendiente" / "Cobrado" / "Vencido" que filtran client-side sobre la página cargada, sin reemplazar el filtro de servidor existente).
   - Paginación: mantener contrato actual (pageSize=50, server-side) pero con controles rediseñados (números de página, no solo Anterior/Siguiente).
   - Densidad compacta por defecto (ver 2.3); toda columna numérica/fecha usa `.font-data`.
   - Null-handling: preservar el patrón ya bueno de "Sin asignar"/"Sin imputar" en `text-ink-muted italic` — estandarizarlo como prop `emptyLabel` del componente, no repetirlo a mano por módulo.

2. **`StatusBadge`** — pill de color, mapea valores reales encontrados:
   - Arrendamiento `Cobro.estado`: **el dato real no tiene enum confirmado en data-model.md** (es un string libre) → antes de badgear, se necesita relevar los valores distintos que existen en producción (`SELECT DISTINCT Estado FROM [Detalle Cobro Alquiler]`, tarea del 01-sql-server-engineer). Hasta entonces, el componente debe soportar un modo "categoría desconocida" → `status-neutral`, y mapear explícitamente al menos `Cobrado`→`status-success`, `Pendiente`→`status-warning`, `Vencido`→`status-danger` una vez confirmados los strings reales.
   - Cuentas Corrientes deuda/crédito: reemplaza el actual `text-red-700`/`text-green-700` suelto por `StatusBadge` o al menos clase semántica `text-status-danger`/`text-status-success` consistente en las 7 pantallas donde aplique señal de signo monetario.
   - Referencia de origen (Tesorería): `sin_coincidencia`→neutral, `coincidencia_unica`→success, `ambigua`→warning.

3. **`SideDrawer`** — panel lateral para ver detalle sin abandonar el listado (hoy no existe ningún patrón de drawer/modal en la app).
   - Reemplaza el patrón actual de "card+tabla anidada" en Arrendamientos y Ventas de Hacienda (hoy todo inline, empuja el resto de la página hacia abajo).
   - Mantiene el patrón de navegación por URL para Compras (`/compras/[idCompra]`) — el drawer es para los módulos que hoy no tienen ruta de detalle propia, no un reemplazo universal.

4. **Estados vacío/carga/error** — tres componentes fijos (`LoadingState`, `EmptyState`, `ErrorState`) que reemplazan los `<p>` sueltos repetidos en cada módulo: `LoadingState` con skeleton de filas de tabla (no solo texto "Cargando…"); `EmptyState` con ícono + texto configurable (preserva los mensajes específicos por dominio ya redactados, ej. "Sin cobros registrados todavía."); `ErrorState` con mensaje + posibilidad de reintentar.

5. **`KpiCard`** — tarjeta de resumen para una futura vista "Dirección" (07-financial-direction-specialist): número grande (`.font-data`), etiqueta, variación opcional. Usar solo con datos reales agregables hoy (saldo total de Cuentas Corrientes, total de vencimientos del mes en Arrendamientos) — no inventar métricas (márgenes, rentabilidad) que requieran datos de costos que el sistema no expone aún.

6. **`FilterBar`** — estandariza el `<form>` de filtros repetido en los 7 módulos: mismos inputs (texto/fecha/select), mismo botón "Buscar", pero con soporte para **atajos de período** (según guía ya registrada por 08: preferir campaña/período sobre rango de fechas genérico cuando el dominio lo permite — aplica a Impuestos `periodoLiquidado`, Remuneraciones `periodoLiquidado`).

---

## 5. Especificación funcional por pantalla

### 5.1 Compras (`/compras`, `/compras/[idCompra]`)

**Hoy:** `ComprasListado.tsx` — tabla plana con filtro por form, paginación 50. Detalle en ruta separada (`DetalleCompra.tsx`) con líneas anidadas y patrón "Sin asignar/Sin imputar" ya bueno. `TrazabilidadCompra.tsx` para trazabilidad.

**Qué está mal:** tabla sin ordenamiento (ej. no se puede ordenar por importe), sin indicador visual de imputación incompleta en el listado (hay que entrar al detalle para ver si falta imputar), filtro genérico sin atajos de período/campaña pese a que `idCampania` es un campo real.

**Rediseño:**
- Listado: `DataTable` con columnas Fecha, Proveedor, Tipo Documento, Nº Documento, Importe (`.font-data`, ordenable) + columna nueva "Imputación" con `StatusBadge` neutral "Sin imputar" cuando ninguna línea tiene `idRubro/idCentroCosto/idDestino/idCampania` — visible sin entrar al detalle.
- Detalle: mantener la ruta propia y el patrón de líneas anidadas (es correcto), solo migrar a tokens de color/tipografía del sistema y `.font-data` en cantidad/precio/iva.
- Filtro: agregar chip de atajo "Campaña actual" cuando exista contexto de campaña (futuro), sin bloquear el filtro de fecha libre existente.

### 5.2 Tesorería (`/tesoreria`)

**Hoy:** `MovimientosPorMedio.tsx` con columnas distintas por medio (correcto, no forzar modelo único), `ReferenciaOrigen.tsx` como expandible inline ("Ver referencia"), `CargaExcel.tsx` para importación.

**Qué está mal:** el selector de medio es probablemente un tab/select sin jerarquía visual fuerte; el "Ver referencia" es un link de texto plano, no comunica visualmente el resultado (`sin_coincidencia`/`coincidencia_unica`/`ambigua`) hasta expandir.

**Rediseño:**
- Tabs de medio (BNA/Galicia/Efectivo/Valores propios/Valores recibidos/Tarjetas) con estilo de tab real (subrayado + color `finance-primary` activo), no lista de links.
- Columna "Origen" con `StatusBadge` (mapeo de 4.2) visible directamente en la fila, sin necesidad de expandir — el expandible (`SideDrawer` o inline, mantener patrón actual de expansión que ya funciona razonablemente) queda para ver el detalle completo del match.
- `CargaExcel`: agregar `EmptyState`/`ErrorState` estandarizados para `errores` de previsualización (hoy es lista de strings simple — beneficia de jerarquía visual clara error vs. éxito).

### 5.3 Cuentas Corrientes (`/cuentas-corrientes`)

**Hoy:** búsqueda de contacto → selección → detalle inline (`CuentaCorriente.tsx`, `OrigenMovimiento.tsx`), sin cambio de ruta, link "Cambiar contacto".

**Qué está mal:** es el módulo de entrada diaria (según guía de 08) pero hoy es indistinguible visualmente de los demás — no hay saldo destacado, deuda/crédito en texto plano con color inconsistente.

**Rediseño:**
- Al seleccionar contacto: header de "ficha" con `KpiCard` de saldo actual (`saldoParcial` de `vw_MovimientosCuenta_Saldo`) destacado en `.font-data` grande, color `status-danger`/`status-success` según signo.
- `DataTable` de movimientos con columnas Fecha, Documento, Nº Documento, Deuda, Crédito, Origen (con `StatusBadge` de `origenTipo`: compra/tesorería/fuera_de_alcance/no_disponible) — hoy `fuera_de_alcance` probablemente se muestra igual que cualquier otro origen; debe distinguirse visualmente como "no trazable en este sistema" (neutral, itálica) vs. los origenes sí resueltos.
- Esta pantalla, junto con Tesorería, es candidata a integrarse al futuro Home/Panel del día (sección 3.1) mostrando saldos de los contactos más relevantes.

### 5.4 Otros movimientos: Impuestos, Remuneraciones, Arrendamientos, Ventas de Hacienda

Los cuatro comparten el mismo problema estructural: listados planos sin badges de estado, tablas anidadas inline sin drawer, sin distinción visual de fila padre vs. línea hija.

**Impuestos (`ImpuestosListado.tsx`, `RetencionesListado.tsx`):**
- Rediseño: `DataTable` + `FilterBar` con atajo de período (`periodoLiquidado`) en vez de rango de fecha genérico. Columna Importe en `.font-data`. Sin estados a badgear (no hay `estado` en el modelo) — foco en densidad y filtro por período/organismo.

**Remuneraciones (`PagosRemuneracionListado.tsx`, `RemuneracionesListado.tsx`):**
- Rediseño: **dos listados separados y claramente rotulados** (reforzando la distinción liquidación vs. pago ya documentada por 08, dado que no hay FK confiable entre ambos) — usar dos secciones con encabezado explícito "Liquidaciones" y "Pagos" en vez de que la separación dependa solo de la URL/tab. Advertencia visual permanente (no un tooltip escondido) tipo nota: "Los pagos no están vinculados a liquidaciones individuales en el sistema origen" — traduce al usuario una limitación real de datos en vez de dejar que la infiera.
- Importe de Remuneración: aclarar en el header de columna que es "Importe (calculado)" ya que es una suma de ~15 conceptos, no un campo directo — coherente con Principio IV (nunca presentar un valor sin explicar su origen/fórmula).

**Arrendamientos (`ArrendamientosListado.tsx`):**
- Hoy: card padre + tabla de cuotas anidada, `estado` en texto plano.
- Rediseño: fila padre del Arrendamiento con `KpiCard` inline de progreso de cobro (cuotas cobradas / `cantidadCuotas`), y tabla de cuotas con `StatusBadge` de `estado` (pendiente confirmación de valores reales, ver 4.2) + columna Fecha de Vencimiento resaltada con `status-warning` si está vencida y no cobrada (regla de interacción, ver sección 6).
- Considerar migrar la tabla de cuotas a `SideDrawer` abierto desde la fila del arrendamiento, liberando el listado principal para verse como una lista de contratos (no una lista de contratos con tablas gigantes incrustadas).

**Ventas de Hacienda (`VentasHaciendaListado.tsx`, `RetencionesVentaHaciendaListado.tsx`):**
- Hoy: card + líneas anidadas, `consignatario` a nivel header, `comprador` a nivel línea — la distinción existe en datos pero hay que verificar que el label en UI diga literalmente "Consignatario" y "Comprador" (no "Cliente" genérico) para no romper la decisión ya tomada por 08.
- `precioUnitarioA`/`precioUnitarioB`: mostrar ambos campos explícitamente con su propio header de columna (no intentar unificarlos ni calcular "el" total — el data-model ya documenta que las escalas son inconsistentes). Agregar un ícono/tooltip breve "Datos de origen, unidades no siempre consistentes" en el header de columna en vez de dejarlo sin explicación.
- Retenciones de Venta de Hacienda: listado independiente (ya es así, correcto, porque no hay join key confiable) — mantener sin forzar anidamiento bajo la venta.

---

## 6. Reglas de interacción y validación

**Vigentes ahora (solo lectura, sin autorización de escritura):**
- Distinguir visualmente `estado` de cuota de Arrendamiento (Cobrado/Pendiente/Vencido) con `StatusBadge` de color — no solo texto plano (gap actual confirmado en diagnóstico).
- Resaltar en `status-danger` toda cuota con `fechaVencimiento < hoy` y `estado ≠ Cobrado` — es una regla de presentación derivada de datos ya disponibles, no requiere escritura.
- Marcar visualmente compras sin imputación completa (`idRubro`/`idCentroCosto`/`idDestino`/`idCampania` todos nulos en todas las líneas) — presentación, no modificación de datos.
- Toda columna con signo (deuda/crédito, importe) debe usar color semántico consistente (`status-danger` para deuda/negativo, `status-success` para crédito/positivo) en las 7 pantallas, no solo en Cuentas Corrientes como hoy.
- Origen `fuera_de_alcance`/`no_disponible` debe presentarse visualmente distinto (neutral/itálica) de un origen resuelto — para no sugerir falsamente que hay trazabilidad donde no la hay (Principio IV).
- Exportar/imprimir un listado filtrado: es solo lectura de datos ya cargados, se puede habilitar sin autorización adicional (generación de CSV/PDF client-side).

**Diferidas — requieren autorización de escritura, fuera de alcance actual (Principio II de la constitución):**
- Confirmar/cerrar una labor agrícola con descuento automático de insumos de stock.
- Alertas de stock insuficiente al planificar una aplicación.
- Control de período de carencia sanitaria antes de habilitar una venta o faena de hacienda.
- Cualquier edición inline de montos, estados de cobro, o reconciliación manual de "Ver referencia" en Tesorería (hoy es heurística de solo lectura; convertirla en una acción de "confirmar coincidencia" implicaría escribir un vínculo, lo cual requiere autorización explícita + backup verificado).
- Carga de nuevas Remuneraciones/Pagos, Arrendamientos o Ventas de Hacienda vía UI (hoy 100% de origen es Access/SQL Server directo).

---

## 7. Plan de implementación por fases

Riesgo de cambiar el "read path": **ninguno** — los 7 módulos son 100% lectura sobre SQL Server; ningún cambio de esta fase toca queries, contratos de API ni escritura. El riesgo es puramente de UI/regresión visual, mitigable con revisión manual módulo por módulo.

1. **Fase 0 — Fundaciones (sin tocar pantallas):** cargar `tailwind.config.ts` y `globals.css` con los tokens de la sección 2. Cero cambio visible todavía (los componentes actuales siguen usando clases `slate-*` hasta que se migren).
2. **Fase 1 — Shell de navegación:** rediseñar `NavHeader.tsx` (jerarquía primario/secundario, breadcrumb, slot reservado para selector de contexto futuro) y `page.tsx` (Home como panel real con saldo/vencimientos en vez de índice de links). Es el cambio de mayor impacto percibido con menor superficie de código.
3. **Fase 2 — Componentes base:** construir `DataTable`, `StatusBadge`, `LoadingState`/`EmptyState`/`ErrorState`, `FilterBar` como componentes compartidos en `frontend/src/components/ui/`. Antes de aplicar el `StatusBadge` de Arrendamiento, relevar con 01-sql-server-engineer los valores reales distintos de `Estado` en `[Detalle Cobro Alquiler]`.
4. **Fase 3 — Migración módulo por módulo** (orden por frecuencia de uso real, no por orden de construcción): Cuentas Corrientes → Tesorería → Compras → Arrendamientos → Ventas de Hacienda → Impuestos → Remuneraciones. Cada módulo migra sus listados/detalles a los componentes de Fase 2 sin cambiar ninguna llamada a `services/*Api`.
5. **Fase 4 — `SideDrawer` y KPIs:** introducir el drawer para Arrendamientos/Ventas de Hacienda, y `KpiCard` en Home + ficha de Cuentas Corrientes.
6. **Fase 5 — Reserva de futuro:** agregar el slot de selector de Establecimiento/Campaña en el header (oculto/deshabilitado hasta que existan datos), sin construir ninguna pantalla de agricultura/ganadería — eso queda bloqueado a que 01-sql-server-engineer confirme el schema real.

Cada fase es demoable y reversible de forma independiente; no requiere un "big bang" de rewrite total.

---

## 8. 2026-09-16 — Polish de navegación (respuesta a feedback "no se ve moderno/profesional")

**Contexto:** feedback directo del usuario de que la estructura de menús no se ve moderna/profesional y pedido explícito de investigar sistemas reales en la web antes de tocar el código. Se verificó primero (fuera de este documento) que los tokens de color de `tailwind.config.ts`/`globals.css` están intactos y sirviéndose correctamente — la percepción de "colores cambiados" fue muy probablemente caché de navegador, no una regresión real. El diagnóstico de este research confirma que el problema no es la paleta "Tierra & Cultivo" en sí (orgánica, cálida, coherente con el dominio agropecuario) sino la **falta de pulido de componente**: sin íconos, header de una sola densidad visual, dropdown sin transición, sin ningún elemento que señale "sistema real" (usuario, notificaciones).

### Research (fuentes concretas)

- **Odoo (v17+ Enterprise)**: migró de menú horizontal a barra superior con app switcher (grid de 9 puntos) + menú vertical dentro de cada app — confirma que un ERP moderno separa "cambiar de módulo" (franja superior) de "navegar dentro del módulo". Fuente: apps.odoo.com (`ui_app_switcher`), Medium "The Quiet Revolution... How Odoo Grew Up Between v14 and v19".
- **SAP Fiori — Launchpad Shell Bar** (`sap.com/design-system/fiori-design-web`, "Shell Bar" usage guidelines): la shell bar es una franja *siempre visible* con branding, botón de back, búsqueda enterprise, notificaciones y menú de usuario — separada de la navegación de módulos/apps. Este es el patrón concreto que se adoptó: franja superior (branding + selector de contexto futuro + notificaciones + usuario) distinta de la franja de navegación por proceso de negocio.
- **Xubio / Auravant** (referencias LatAm): Auravant es agricultura de precisión con foco geoespacial (fuera del alcance de este proyecto, principio explícito "sin GIS"); Xubio es gestión/contabilidad pyme genérica. Ninguno documenta públicamente su sistema de navegación en detalle accesible por búsqueda — no se encontró suficiente material concreto de sus pantallas como para citarlos como referencia de patrón específico; se usaron como validación de tono "profesional pyme argentina" más que como fuente de patrón de UI.
- **shadcn/ui blocks** (`shadcn.io/blocks/navbar-*`): confirma como estándar de SaaS moderno 2026 la combinación breadcrumb + búsqueda + notificaciones + avatar de usuario en la barra de dashboard, y el patrón de command palette (Cmd+K). Se adoptaron breadcrumb (ya existía, ver §3.2, usado en Compras/Cuentas Corrientes) + notificaciones/usuario; **no** se agregó una búsqueda global falsa ni command palette porque hoy no hay un índice de contenido real que buscar y un input de búsqueda no funcional sería una funcionalidad fingida (viola Principio IV de la constitución) — queda para cuando exista una fuente real de datos a indexar.

### Decisión de arquitectura

Se mantiene **top nav de dos franjas** (no sidebar). Justificación: con 5 módulos (y Producción como 6to eventual) un top nav horizontal con dropdown por módulo sigue siendo legible sin sidebar; el patrón Fiori/Odoo confirma que la franja superior fija (shell bar) es el elemento que faltaba, no un cambio a sidebar. Se reserva la decisión de sidebar para si el árbol de navegación crece más allá de ~7-8 módulos de primer nivel.

### Cambios implementados

1. **`frontend/src/components/layout/NavHeader.tsx`** (reescrito):
   - Ícono SVG inline por módulo (Compras/Ventas/Finanzas/Personal/Producción) — sin agregar dependencia de librería de íconos (no hay ninguna en `package.json`; se usan `<svg>` inline por reversibilidad, principio VII).
   - Shell bar superior ahora incluye, además del selector de Establecimiento (placeholder ya existente): botón de notificaciones deshabilitado (`title="Notificaciones — próximamente"`) y placeholder de cuenta de usuario deshabilitado (`title="Cuenta de usuario — autenticación pendiente de implementar"`) — mismo patrón honesto ya usado en el selector de contexto (deshabilitado + `title` explicativo, nunca fingiendo una función que no existe).
   - Header con `sticky top-0` y `shadow-sm` (visualmente "flota" sobre el contenido al scrollear, patrón shell bar).
   - Ítems de nav y leafs de dropdown ahora usan fondo `bg-finance-light` + `rounded-md` como estado activo (antes solo `border-b-2` + subrayado) — más cercano al tratamiento de "pill" activo visto en Odoo/shadcn.
   - Dropdown con `shadow-lg` + `ring-1 ring-black/5` + transición de entrada (`@keyframes fadeIn` agregado a `globals.css`) + chevron que rota al abrir.
2. **`frontend/src/app/globals.css`**: se agregó `@keyframes fadeIn` (translateY + opacity) para la transición del dropdown — no se tocó ningún token de color.
3. **`frontend/src/components/ui/Toast.tsx`** (nuevo): sistema de notificaciones toast sin dependencia nueva (contexto de React + `setTimeout`), con tonos `success`/`danger`/`neutral` mapeados a los tokens `status-*` existentes. Justificación: reemplaza el "éxito/error silencioso" en la primera acción de escritura real de la app (marcar cuota de arrendamiento como cobrada), siguiendo el estándar de feedback transitorio no bloqueante confirmado en los patrones de shadcn/ui.
4. **`frontend/src/app/providers.tsx`**: envuelve la app en `<ToastProvider>`.
5. **`frontend/src/components/arrendamientos/ArrendamientosListado.tsx`**: la mutación `actualizarEstadoCuota` ahora dispara `showToast(...)` en éxito ("Cuota marcada como cobrada/pendiente.") y en error ("No se pudo actualizar el estado de la cuota. Intentá de nuevo.") en vez de invalidar la query en silencio.

### No implementado ahora (descartado explícitamente, no solo diferido)

- Búsqueda global / command palette: requiere un índice real de contenido navegable; hoy sería una caja de búsqueda decorativa sin función — se descarta por Principio IV, no se difiere como TODO.
- Sidebar colapsable: no se justifica con 5 módulos; revisar si el árbol crece.
- Breadcrumb en la franja del header (además del ya existente por página en vistas de detalle): redundante con el breadcrumb de página actual (`Breadcrumb.tsx`, usado en Compras/Cuentas Corrientes) — no se duplica.
