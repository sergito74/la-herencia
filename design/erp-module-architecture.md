# Arquitectura de módulos ERP — La Herencia

**Autores**: `04-integrated-agro-management-engineer` (mapa de procesos y navegación) + `09-agroux-lead-product-architect` (traducción a estructura de sitio/navegación).

**Este documento reemplaza en autoridad** la sección de navegación de `design/agroux-frontend-redesign.md` (que agrupó Impuestos/Remuneraciones/Arrendamientos/Ventas de Hacienda bajo un "Otros movimientos" sin lógica de dominio, solo por orden de construcción). Donde haya conflicto, este documento manda para todo lo referido a agrupación de módulos, `NavHeader.tsx` y `page.tsx`. El resto de `agroux-frontend-redesign.md` (design system "Tierra & Cultivo", componentes) sigue vigente.

## 0. Diagnóstico (por qué el estado actual está mal)

La navegación de hoy agrupa por "cuándo lo construimos" (spec 002, 003, 004 como top-level; spec 005 entera metida en un dropdown "Otros movimientos"). Eso rompe tres cosas que un usuario de una empresa agropecuaria espera de un ERP:

1. **No hay noción de proceso de negocio**: Compras y Ventas de Hacienda son procesos comerciales opuestos (egreso vs. ingreso) pero hoy están en niveles de jerarquía distintos (top-level vs. dropdown), como si uno importara más que el otro.
2. **Tesorería y Cuentas Corrientes están separadas de lo que las alimenta**: son el destino de todo movimiento de plata, no un módulo aislado — deberían vivir junto a Compras/Ventas/Pagos como "Finanzas", no al lado de ellos.
3. **El vínculo real ya construido (`Origen`/`IdOrigen` en `vw_MovimientosCuenta_Base`) es invisible**: hoy cada módulo es una isla con su propia pantalla; el dato que conecta todo (una compra generó este movimiento de cuenta corriente) existe en el backend pero no hay ningún patrón de UI consistente para navegarlo.

## 1. Mapa de módulos de primer nivel

Un ERP agropecuario real se organiza por **proceso de negocio**, no por tabla de origen. Proponemos 5 módulos de primer nivel:

| # | Módulo top-level | Qué agrupa | Por qué junto |
|---|---|---|---|
| 1 | **Compras** | Compras a proveedores, imputación (rubro/centro de costo/destino/campaña) | Proceso de egreso de bienes/servicios — tiene identidad propia por volumen y complejidad de imputación; no es "solo un pago", es un documento con línea de detalle e impacto en costo. |
| 2 | **Ventas** | Ventas de Hacienda (migrado) + Venta de Granos (pendiente) | Proceso de ingreso comercial — hoy Ventas de Hacienda vive enterrada en un dropdown de "otros movimientos"; es tan importante como Compras y merece el mismo nivel jerárquico. |
| 3 | **Finanzas** | Tesorería (BNA, Galicia, efectivo, valores, tarjetas) + Cuentas Corrientes + Impuestos y Retenciones + Arrendamientos | Todo lo que mueve o refleja plata que no es la operación comercial en sí misma: medios de pago/cobro, el libro mayor por contacto, obligaciones fiscales, e ingresos de renta de arrendamiento. Cuentas Corrientes es el "estado de cuenta" que consolida Compras, Ventas, Tesorería, Impuestos y Remuneraciones — pertenece naturalmente a Finanzas, no al lado de Compras como hoy. |
| 4 | **Personal** | Remuneraciones (liquidaciones + pagos) | Proceso de RRHH — tiene su propio ciclo (liquidar → pagar) independiente de la operación comercial; separado de Finanzas porque conceptualmente es "gente", no "plata de terceros". |
| 5 | **Producción** (pendiente — placeholder en nav) | Agrícola: Órdenes de Trabajo, Resultado/Costos de Cultivos. Ganadera: manejo de rodeos, sanidad (nada migrado aún) | Es el corazón operativo de la empresa agropecuaria (lo que hoy no existe en el sistema migrado) — debe reservarse el lugar top-level ya, aunque hoy esté vacío/pendiente, para que cuando se migre no vuelva a colgarse de un dropdown residual. |

Nota sobre Remitos: es un documento de trazabilidad física de mercadería (salida/entrada de stock), no un movimiento financiero — cuando se migre va dentro de **Producción** (control de stock/Kardex), enlazado a Compras (remito de insumo comprado) y a Ventas (remito de venta de hacienda/granos), no como módulo propio de primer nivel.

## 2. Sub-secciones por módulo (migrado vs. pendiente)

### 1. Compras
- ✅ Listado y detalle de compras, con línea de imputación (rubro/centro de costo/destino/campaña) — `specs/002-compras`
- ⏳ Pendiente: Órdenes de Trabajo con descuento de insumo (la compra es la entrada de stock; la orden de trabajo es la salida)
- ⏳ Pendiente: Remitos de recepción de insumos

### 2. Ventas
- ✅ Ventas de Hacienda: venta + líneas por comprador + retenciones (listado independiente) — `specs/005`
- ⏳ Pendiente: Venta de Granos
- ⏳ Pendiente: Remitos de despacho

### 3. Finanzas
- ✅ Tesorería: BNA, Galicia, efectivo, valores propios/recibidos, tarjetas, carga/validación de resúmenes Excel — `specs/003-tesoreria`
- ✅ Cuentas Corrientes: saldo y movimientos por contacto, con resolución de `origen` — `specs/004-cuentas-corrientes`
- ✅ Impuestos y Retenciones — `specs/005`
- ✅ Arrendamientos: contratos + cuotas de cobro — `specs/005`
- ⏳ Pendiente: conciliación de Cobros de Ventas (hoy Ventas de Hacienda no tiene un flujo de "cobro" propio documentado más allá de la retención)

### 4. Personal
- ✅ Remuneraciones: liquidaciones — `specs/005`
- ✅ Pagos de Remuneraciones: listado independiente (sin FK confiable a liquidación/empleado — bug real heredado de Access, documentado, no se debe fingir el vínculo) — `specs/005`
- ⏳ Pendiente: legajo de empleado, historial de pagos por persona (bloqueado por la falta de FK real — requiere decisión de negocio, no solo de UI)

### 5. Producción (todo pendiente, sin construir)
- ⏳ Agrícola: Órdenes de Trabajo (labores + descuento de stock/Kardex en tiempo real), Resultado de Cultivos, Costos de Cultivos
- ⏳ Ganadera: manejo de rodeos/tropas, categorías, pesajes, planes sanitarios (nada relevado en Access aún para esta parte específica del menú)
- ⏳ Remitos (documento transversal de stock, vive acá)

## 3. Vínculos lógicos entre módulos — cómo se navegan en la UI

Esta es la sección central. Cada vínculo de datos ya confirmado debe tener una forma de navegación concreta, no solo quedar documentado como relación de tablas.

### 3.1 Compra → Cuenta Corriente (ya construido, backend-side)
- **Dato**: `vw_MovimientosCuenta_Base.IdOrigen = Compras.IdDeuda` cuando `Origen = "Compras"`.
- **UI**: en el detalle de una Compra (`/compras/[idCompra]`), agregar una sección "Movimientos de cuenta corriente asociados" con un link directo a `/finanzas/cuentas-corrientes/[idContacto]?resaltarOrigen=compra:{idCompra}`. Inversamente, en la fila de un movimiento de cuenta corriente cuyo `origenTipo = "Compra"`, el número de documento es un **link clickeable** que va a `/compras/[idCompra]` (no solo texto). Si "sin movimientos asociados" (FR-009 de la spec), mostrar el estado explícito, no ocultar la sección.

### 3.2 Ventas de Hacienda → Cuenta Corriente (vía retención)
- **Dato**: `Origen = "Ret. Ventas Hacienda"`, `idOrigen` referencia la retención (no la venta — no hay clave confiable, documentado en `specs/005`).
- **UI**: en el movimiento de cuenta corriente, mostrar "Retención de venta de hacienda" como badge/chip clickeable que abre un drawer con el detalle de esa retención (contacto, documento, importe) — **sin pretender** linkear a una venta específica, ya que esa trazabilidad no existe en los datos reales. El badge debe decir explícitamente "retención asociada" para no insinuar un vínculo a la venta que no está confirmado.

### 3.3 Tesorería → Cuenta Corriente (todos los medios)
- **Dato**: mapeo cerrado `origenTipo → medio` en `vw_MovimientosCuenta_Base` (bna, galicia, efectivo, valores_recibidos).
- **UI**: mismo patrón que 3.1 — en cada fila de movimiento de cuenta corriente con `tipo: "tesoreria"`, el campo `medio` se muestra como badge de color distintivo por medio (ej. verde BNA, naranja Galicia) y es clickeable hacia el detalle del movimiento de tesorería original (`/finanzas/tesoreria/{medio}/{idMovimiento}`).

### 3.4 Impuestos / Retenciones / Remuneraciones / Arrendamientos → Cuenta Corriente
- **Dato**: `tipo: "impuesto" | "retencion" | "remuneracion" | "arrendamiento"` en el resolver de origen.
- **UI**: mismo patrón — badge con el tipo + link directo al registro fuente (`/finanzas/impuestos/{idImpuesto}`, `/personal/remuneraciones/{idSalario}`, `/finanzas/arrendamientos/{idAlquiler}`). Para `Pagos Remuneraciones` (sin FK confiable) **NO se debe simular** este vínculo — si algún día aparece como `origen` en cuenta corriente sin poder resolverse a una remuneración puntual, se muestra como "fuera de alcance" tal como ya lo maneja el backend, nunca inventando la asociación.

### 3.5 Contacto como eje transversal
- **Dato**: `Contactos.IdContacto` aparece en Compras (proveedor), Ventas de Hacienda (comprador/consignatario), Cuentas Corrientes, Impuestos (organismo), Remuneraciones (empleado), Arrendamientos (arrendador).
- **UI**: cualquier nombre de contacto en cualquier tabla del sistema (proveedor, comprador, empleado, organismo, arrendador) debe ser un **link uniforme** a `/finanzas/cuentas-corrientes/{idContacto}` — es la vista 360° del contacto. Esto es el vínculo más barato de implementar y el de mayor valor percibido: "clic en cualquier nombre → ver todo lo que le compramos/vendimos/pagamos".

### 3.6 (Futuro) Órdenes de Trabajo → Stock/Insumos → Compras
- **Dato pendiente**: al cerrar una OT se descuenta insumo del Kardex; el insumo fue dado de alta por una Compra.
- **UI a construir cuando se migre**: en el detalle de una Compra de insumo, sección "Consumido en" listando las OT que descontaron ese lote; en la OT, cada línea de insumo linkea a la compra de origen del stock (FIFO o el criterio que defina `01-sql-server-engineer`).

### 3.7 (Futuro) Ventas → Cobros → Cuenta Corriente
- **Dato pendiente**: hoy Ventas de Hacienda no tiene un flujo de cobro documentado aparte de la retención. Cuando se defina cobro real, seguir el mismo patrón 3.1 (badge clickeable en ambas direcciones).

## 4. Reorganización concreta

### 4.1 `NavHeader.tsx` — nueva estructura

Top-level: 4 ítems visibles + 1 placeholder deshabilitado. Elimina el dropdown "Otros movimientos".

```
TOP_LEVEL_MODULES = [
  { href: "/compras",   label: "Compras" },
  { href: "/ventas",    label: "Ventas" },          // nuevo grupo, hoy solo contiene /ventas-hacienda
  { href: "/finanzas",  label: "Finanzas", submenu: [
      { href: "/finanzas/tesoreria",          label: "Tesorería" },
      { href: "/finanzas/cuentas-corrientes", label: "Cuentas corrientes" },
      { href: "/finanzas/impuestos",          label: "Impuestos y retenciones" },
      { href: "/finanzas/arrendamientos",     label: "Arrendamientos" },
    ] },
  { href: "/personal",  label: "Personal", submenu: [
      { href: "/personal/remuneraciones", label: "Remuneraciones" },
    ] },
  { href: "/produccion", label: "Producción", disabled: true, title: "Próximamente — Órdenes de Trabajo, Cultivos, Ganadería" },
]
```

`Ventas` es top-level con un solo ítem hoy (`/ventas/hacienda`) porque es un placeholder deliberado: cuando se migre Venta de Granos, ambos cuelgan del mismo submenu sin volver a reordenar la jerarquía. Compras se mantiene simple (sin submenu) porque hoy es una sola pantalla; cuando se agregue Órdenes de Trabajo con impacto de stock, evaluar si pasa a tener submenu propio o si Producción absorbe esa vista con un link cruzado desde Compras.

El componente de submenu (dropdown en hover/click) ya existe en el código actual para "Otros movimientos" — reutilizar ese mismo patrón para Finanzas y Personal en vez de escribir uno nuevo.

### 4.2 Rutas — mantener o mover

Recomendación: **mover las rutas** para que la URL refleje la jerarquía nueva (mejor para bookmarks/breadcrumbs futuros), no solo reorganizar el menú:

| Ruta actual | Ruta nueva |
|---|---|
| `/tesoreria` | `/finanzas/tesoreria` |
| `/cuentas-corrientes` | `/finanzas/cuentas-corrientes` |
| `/impuestos` | `/finanzas/impuestos` |
| `/arrendamientos` | `/finanzas/arrendamientos` |
| `/remuneraciones` | `/personal/remuneraciones` |
| `/ventas-hacienda` | `/ventas/hacienda` |
| `/compras` | `/compras` (sin cambio) |

Implementación: mover las carpetas bajo `frontend/src/app/` a la nueva estructura de rutas anidadas de Next.js (`app/finanzas/tesoreria/page.tsx`, etc.), y actualizar todos los `href` internos (NavHeader, Home, links cruzados entre módulos de la sección 3). Si el volumen de links internos a actualizar es alto, se puede hacer en dos pasos: (1) mover rutas y actualizar navegación, (2) recién ahí implementar los links cruzados de la sección 3 sobre las rutas ya finales — para no tener que tocarlos dos veces.

### 4.3 `page.tsx` (Home) — nueva estructura

Reemplazar la grilla plana de 3 + 4 tarjetas por una organizada en las mismas 5 secciones del nav, con Producción visible pero marcada "Próximamente":

```
<Home>
  H1 "La Herencia"

  Sección KPIs (se mantiene: cuotas de arrendamiento pendientes/vencidas — dato real)

  Grid de 4 tarjetas grandes top-level (una por módulo con contenido):
    Compras | Ventas | Finanzas | Personal
    (cada tarjeta linkea al índice del módulo o, si tiene una sola pantalla,
     directo a ella — Compras y Ventas van directo; Finanzas y Personal
     listan sus 4/1 sub-ítems dentro de la misma tarjeta, no en tarjetas aparte)

  Tarjeta "Producción" en gris/deshabilitada al final: "Órdenes de trabajo,
  cultivos y ganadería — próximamente", sin link activo.
</Home>
```

Esto es la traducción directa de la sección 1: la Home dejar de listar "3 principales + 4 otros" y pasa a listar "los 5 procesos de negocio del campo", con el 5to marcado como vacío a propósito en vez de omitido — comunica que el sistema sabe que ahí falta algo, no que se olvidó.

## 5. Árbol de navegación final

```
La Herencia
├── Compras
│   └── (listado + detalle de compra, con sección "Movimientos de CC asociados")
├── Ventas
│   └── Hacienda
│       └── (listado + detalle, con retenciones asociadas)
│   └── Granos [pendiente]
├── Finanzas
│   ├── Tesorería
│   │   ├── BNA
│   │   ├── Galicia
│   │   ├── Efectivo
│   │   ├── Valores propios / recibidos
│   │   └── Tarjetas
│   ├── Cuentas Corrientes
│   │   └── (por contacto: saldo + movimientos con origen resuelto y linkeado)
│   ├── Impuestos y Retenciones
│   └── Arrendamientos
│       └── (contrato + cuotas de cobro)
├── Personal
│   └── Remuneraciones
│       ├── Liquidaciones
│       └── Pagos (listado independiente, sin vínculo a liquidación — bug heredado documentado)
└── Producción [pendiente — placeholder deshabilitado]
    ├── Agrícola
    │   ├── Órdenes de Trabajo (con Kardex de insumos)
    │   ├── Resultado de Cultivos
    │   └── Costos de Cultivos
    ├── Ganadera [sin relevar aún]
    └── Remitos (transversal: recepción de insumos y despacho de ventas)
```

## 6. Plan de migración

1. **NavHeader.tsx**: reemplazar `TOP_LEVEL_MODULES` + `OTROS_MOVIMIENTOS_MODULES` por la estructura de 5 ítems con submenús de la sección 4.1. El componente de dropdown ya existe (usado hoy por "Otros movimientos") — generalizarlo para aceptar cualquier ítem con `submenu`, en vez de tener un solo dropdown hardcodeado.
2. **Rutas**: mover carpetas de `frontend/src/app/` según la tabla de 4.2. Actualizar todos los `href` que apunten a las rutas viejas (buscar por string literal `"/tesoreria"`, `"/cuentas-corrientes"`, `"/impuestos"`, `"/arrendamientos"`, `"/remuneraciones"`, `"/ventas-hacienda"` en todo `frontend/src`).
3. **page.tsx (Home)**: reescribir según 4.3 — 4 tarjetas de proceso + 1 placeholder de Producción, manteniendo el KPI de cuotas de arrendamiento tal cual (es dato real, no se toca su lógica).
4. **Vínculos cruzados (sección 3)**: implementar en un paso posterior, ya sobre las rutas nuevas, empezando por 3.5 (contacto → cuenta corriente, el más barato y de mayor impacto transversal) y 3.1/3.3/3.4 (badges de origen clickeables en cuenta corriente) antes que 3.2 (retención de venta de hacienda, más delicado por la falta de FK confiable).
5. **No tocar** backend ni contratos de API en esta migración: todos los datos para los vínculos de la sección 3 ya están expuestos por `specs/002` a `specs/005` (`origenTipo`/`idOrigen` resuelto) — este es un cambio de frontend (estructura de rutas + componentes de link), no de datos.
6. **Fuera de alcance de este documento**: la implementación de Producción (Órdenes de Trabajo, Cultivos, Ganadería) — solo se reserva el lugar en la navegación. Su diseño funcional requiere primero relevar los formularios Access pendientes documentados en `project_access_forms_analysis.md` y consultar a `05-agricultural-production-specialist`/`06-livestock-health-specialist`.
