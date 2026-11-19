# Densidad compacta y encabezados fijos (19/11/2026)

Pedido de Sergio: los encabezados ocupan demasiado y al scrollear se pierden los encabezados de columnas. Estándar completo en `.github/agents/12-frontend-visual-design-specialist.agent.md`, sección "Densidad y encabezados fijos".

## Estándar (resumen)

| Elemento | Hoy (aprox.) | Estándar |
|---|---|---|
| Zona fija antes de la 1ª fila (1600×900) | ~450 px (Tesorería) | ≤ 220 px |
| Título | text-2xl + descripción | `text-lg font-semibold`, acciones en la misma fila, `py-2` |
| Pestañas/Segmentos | fila propia con márgenes | `h-8 text-sm`, en la fila del título si entra |
| Indicadores | 3 tarjetas de ~110 px | tira de stats de una línea ≤ 36 px |
| Filtros | caja con borde ~120 px | una fila sin caja, controles `h-8`, "Más filtros" en popover |
| Bloques informativos | barra propia ("Informes del Estudio") | chip/ícono de estado junto al título, detalle en popover |
| Encabezado de columnas | se pierde al scrollear | `sticky top-16` (bajo la barra de 64 px), fondo opaco |
| Formularios largos | Guardar al final de la página | barra de acciones `sticky bottom-0`, encabezado del documento compacto |

## Tesorería: antes / después

Antes (900 px de alto):
```
 0 ┌ Barra de navegación (64) ─────────────────────────────┐
 64│ Tesorería  (título grande + descripción)              │
120│ ┌ Informes del Estudio ─────────── [ver] [descargar] ┐│
170│ └────────────────────────────────────────────────────┘│
180│ [Movimientos] [Inversiones] [Cajas]                   │
230│ ┌Saldo────────┐ ┌Sin conciliar──┐ ┌Último extracto─┐  │
   │ │ $ 12.345,67 │ │ 23            │ │ 30/09/2026     │  │
340│ └─────────────┘ └───────────────┘ └────────────────┘  │
350│ ┌ Filtros ──────────────────────────────────────────┐ │
   │ │ Medio [___]  Desde [__] Hasta [__]  Buscar [____] │ │
   │ │ Estado [___]                     [Cargar extracto]│ │
470│ └───────────────────────────────────────────────────┘ │
480│ Fecha | Concepto | Contacto | Importe | Conciliación   │ ← se pierde al scrollear
   │ ... ~16 filas visibles                                 │
```

Después:
```
 0 ┌ Barra de navegación (64) ─────────────────────────────┐
 64│ Tesorería  [Movimientos|Inversiones|Cajas]  ● Informes Estudio (2)  [Cargar extracto] │
104│ Saldo $ 12.345,67 · Sin conciliar 23 · Último extracto 30/09 │
136│ [Medio ▾] [Desde–Hasta] [Buscar concepto/contacto/importe] [Más filtros] │
172│ Fecha | Concepto | Contacto | Importe | Conciliación   │ ← sticky top-16
   │ ... ~28 filas visibles (casi el doble)                 │
```
Zona fija: 108 px después de la navegación (objetivo ≤ 220 cumplido con margen).

## Tablas a mano (no heredan el thead fijo de DataTable)

Prioridad A = listados de trabajo diario; B = paneles/detalle; C = tablas chicas (no necesitan sticky, solo densidad).

**A — migrar a DataTable o aplicar `sticky top-16`:**
- components/compras/ComprasGrid.tsx:360 (ya tiene sticky en 361; verificar top bajo nav)
- components/ordenes/OrdenesListado.tsx:103, 215 (sticky en 104)
- components/planificacion/PlanificacionAgricolaListado.tsx:150, 265 (sticky 152/154)
- components/ventas-hacienda/VentasHaciendaListado.tsx:167
- components/ventas-hacienda/VentaHaciendaGrid.tsx:116 (sticky 117)
- components/arrendamientos/ArrendamientosListado.tsx:160
- components/trabajos-eventuales/TrabajosEventuales.tsx:98
- components/flujo-caja/TablaFlujoCaja.tsx:77, 134; FlujoCajaRubro.tsx:347
- components/ordenes-pago/OrdenesPago.tsx:59, 70; FacturasAPagar.tsx:59, 93; FormularioOrdenPago.tsx:79, 90
- components/tarjetas-conciliacion/PanelConciliacion.tsx:513 (sticky 514), 691
- components/tarjetas-cuenta/TarjetaCuentaTabla.tsx:82; PanelControl.tsx:79
- components/pastaje/Facturas.tsx:72, 210; Liquidaciones.tsx:121, 167
- components/stock/BajasListado.tsx:143; ExistenciasListado.tsx:39; RecuentosListado.tsx:39
- app/imputacion/documentos/page.tsx:231 (sticky 192/207)
- app/produccion/contratistas/sin-orden/page.tsx:53
- app/finanzas/facturas-esperadas/page.tsx:16; components/facturas-faltantes/TableroFacturasEsperadas.tsx:79, AlarmasFaltantes.tsx:69
- components/documentos-nuevos/NuevosParaRevisar.tsx:58

**B — paneles y detalle:**
- app/finanzas/tarjetas/resumenes/[idResumen]/page.tsx:290, 328
- app/produccion/ordenes/[idOrden]/page.tsx:225, 294
- app/finanzas/tarjetas/compras-en-cuotas/[idPagoTarjeta]/page.tsx:41
- components/remitos/RemitoDetalleView.tsx:138; RemitoForm.tsx:301 (sticky 302); VinculacionPanel.tsx:179
- components/ordenes/HectareasAplicadasPanel.tsx:132, 154, 204; DistribucionLotesPanel.tsx:91; FormularioRetiroDocumento.tsx:85
- components/resultado-cultivo/ConsolidadoCampaniaView.tsx:120; FormularioCostos.tsx:75; FormularioResultados.tsx:72, 81, 103; FormularioAccess.tsx:69; DetalleCostosPanel.tsx:20; CostoPorParte.tsx:32; ResumenCampaniaCostos.tsx:28
- components/imputacion/ComparacionCultivoCampania.tsx:15
- components/tesoreria/Inversiones.tsx:102; CargaExcel.tsx:162; CargaExtractoPdf.tsx:96
- components/cuentas-corrientes/ArcaFiscal.tsx:45; ArcaSubcuentas.tsx:80
- components/cuentas-socios/ControlBancoSocio.tsx:30; PagoProveedorSocioForm.tsx:83
- components/aplicaciones-pago/AplicarPagoPanel.tsx:86
- components/impuestos/ImpuestoParticularPanel.tsx:111
- components/boveda/CorridasTabla.tsx:27; DocumentosTabla.tsx:29; EstadoCuentaPanel.tsx:32, 74; app/boveda/page.tsx:184
- components/stock/RecuentoUpload.tsx:162; components/cajas-efectivo/ImportacionCajaPanel.tsx:36

**C — chicas:** CotizacionesPanel.tsx:110, RetencionesConfig.tsx:46/59, pastaje/IndicePanel.tsx:66, FichaContrato.tsx:162, TarjetasSaldos.tsx:27, UnidadesProductos.tsx:69, TrazabilidadCompra.tsx:49, compras/descarga-peajes/page.tsx:59.

Nota: los `sticky` existentes en tablas a mano usan `top-0`; si la tabla no tiene contenedor con scroll propio quedan tapados por la navegación (64 px). Revisar cada uno contra el estándar `top-16`.

## Lista priorizada por pantalla (zona fija a compactar)

P1 (trabajo diario, tabla larga):
1. finanzas/tesoreria — informes Estudio (components/tesoreria/ListadosEstudio.tsx:35) a chip; 3 KpiCard a tira; filtros sin caja (MovimientosPorMedio.tsx).
2. compras — PageHeader + filtros de ComprasListado; ComprasGrid (formulario) con acciones fijas abajo.
3. finanzas/cuentas-corrientes y /saldos — CuentaCorriente.tsx (3 bloques de indicadores) a tira.
4. finanzas/cuentas-socios/[idSocio] — CuentaSocio.tsx (5 indicadores) a tira.
5. imputacion y imputacion/documentos — 3 bloques de encabezado; tabla :231 a sticky.
6. finanzas/tarjetas/conciliacion — BandejaConciliacion + PanelConciliacion:513/691.
7. produccion/ordenes — OrdenesListado:103/215 sticky bajo nav.
8. produccion/stock (+bajas, ajustes) — ExistenciasListado (5 indicadores), BajasListado (3).
9. finanzas/ordenes-pago — 6 tablas a mano.

P2:
10. produccion/resultado-cultivo y /[idCampania]/[idCultivo] — ResultadoCultivoView (16) y ConsolidadoCampaniaView (15) indicadores: tira de 2 líneas máx.
11. ventas/pastaje y /[id] — PastajeListado (4), FichaContrato (6).
12. ventas/hacienda, ventas/granos, personal/remuneraciones, personal/trabajos-eventuales, finanzas/impuestos, finanzas/arrendamientos, finanzas/tarjetas/* (resúmenes, cuotas, cuenta corriente, control), produccion/remitos/*, produccion/planificacion, finanzas/flujo-caja-real y -rubro, finanzas/facturas-esperadas, contactos.

P3 (formularios: barra Guardar/Cancelar fija abajo + encabezado compacto):
13. compras/nueva y [idCompra]/editar, ventas/*/nueva y editar, finanzas/impuestos/nueva y editar, produccion/ordenes/nuevo, editar, retiro (OrdenForm.tsx:359 ya tiene sticky: verificar), produccion/remitos/nuevo y editar, finanzas/tarjetas/resumenes/nuevo y editar.

P4: boveda, boveda/[id], cotizaciones, conciliacion-historico, migracion-cajas-giamigli, cajas, cajas-efectivo, descarga-peajes, login (sin cambios).

## Verificación
Captura a 1600×900 y 1366×768 de cada pantalla tocada: y de la 1ª fila ≤ 284 px desde el borde superior, y thead visible tras scrollear 1000 px.
