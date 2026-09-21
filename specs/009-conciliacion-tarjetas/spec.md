# Feature Specification: Conciliación manual de consumos de tarjeta

**Feature Branch**: `009-conciliacion-tarjetas`
**Created**: 2026-09-22
**Status**: Draft (diseño acordado con el usuario, 2026-09-22)

**Input**: Mejorar la experiencia para analizar y seleccionar a mano las líneas de consumo de los resúmenes de tarjeta (008) que no quedaron conciliadas con un documento de Compras. Escribe exclusivamente contra `WC`.

## Reglas de negocio acordadas

- Una línea de consumo del resumen está en **pesos**. Los documentos (Factura, NC, ND) pueden estar en dólares.
- Conciliar una línea puede requerir **2 o más documentos** (Factura + NC + ND), y esos documentos pueden ser de **proveedores distintos** dentro de la misma línea.
- Un documento en dólares se **pesifica con su propio tipo de cambio**. La diferencia de cambio entre la cotización de la tarjeta y la del documento se documenta con una **Nota de Crédito/Débito de ajuste** (documentos marcados `Ajusta Tipo Cambio`) asociada a la factura. La conciliación cierra **exacta en pesos** (±$0,10) con la factura pesificada más esas notas. Ya no se tolera un desvío de tipo de cambio.
- Si la suma no cierra, el usuario puede **aceptar la diferencia con un motivo** (ajuste de tipo de cambio sin nota, redondeo, otro con texto libre).
- Una línea sin documento (impuestos, intereses, compra nunca cargada) se marca **"sin documento / no aplica"** con motivo, y sale de pendientes. Desde ahí se puede ir al **alta de Compras** ya existente con proveedor, fecha e importe precargados (no hay alta nueva dentro del panel).
- No se registra quién ni cuándo concilió (sin auditoría). Sí se puede quitar un vínculo o estado.
- La bandeja **no aplica nada sola**: el botón "Aceptar N sugerencias exactas" muestra una vista previa y recién ahí confirma. Solo entran las combinaciones exactas en pesos; las que dependen de dólares sin nota de ajuste nunca.

## Pendiente

Una línea está **pendiente** si no tiene ningún vínculo a Compras (`Tarjetas_Resumenes_Lineas_Compras`) y no tiene estado (`Tarjetas_Resumenes_Lineas_Estado`).

## User Stories

1. **Bandeja de pendientes** (`/finanzas/tarjetas/conciliacion`): líneas sin conciliar de todos los resúmenes, con filtros por tarjeta, proveedor y período; ordenadas primero por las que tienen sugerencia exacta. Cada fila abre el panel. La ficha del resumen abre el mismo panel.
2. **Panel de conciliación** (pantalla dividida): a la izquierda la línea, otras líneas pendientes del mismo proveedor y el PDF del resumen; a la derecha la canasta de documentos (proveedor de la línea + buscador para sumar documentos de otros proveedores), sugerencias, total vs línea, y las acciones Vincular / Aceptar diferencia con motivo / Sin documento.
3. **Notas de ajuste**: al elegir una factura en dólares se destacan las NC/ND de ajuste de tipo de cambio del proveedor, más cercanas en fecha primero. Al vincular, la relación factura–nota se guarda en `CompraDocumentosRelacionados`. Si falta la nota, el panel indica el importe aproximado que faltaría (tipo de cambio implícito, solo como pista).
4. **Muchas líneas contra muchos documentos**: tildar varias líneas pendientes y varios documentos; el sistema propone un reparto editable y lo guarda de una vez.
5. **Aceptar sugerencias exactas** con vista previa.
6. **Sin documento / no aplica** con motivo, y acceso al alta de Compras precargada.

## Datos

Nueva tabla en `WC` (mismo criterio que `CompraDocumentosRelacionados`: infraestructura de esta app, no existe en `LaHerencia`):

`dbo.Tarjetas_Resumenes_Lineas_Estado` — `IdLineaConsumo` (PK), `Estado` (`SinDocumento` | `DiferenciaAceptada`), `Motivo`, `Detalle` (nullable), `ImporteDiferencia` (money, nullable).

Como el `PUT`/`DELETE` de un resumen recrea sus líneas (008), también borra sus filas de estado, igual que ya hace con los vínculos.

## Hallazgos de datos reales (2026-09-22)

- `CompraDocumentosRelacionados` tiene 0 filas: hoy ninguna nota está asociada a su factura.
- 175 documentos están marcados `Ajusta Tipo Cambio` (166 NC/ND en pesos de proveedores con facturas en dólares).
- De 6 líneas históricas con factura en dólares que necesitaban ajuste, solo 1 se explica con una nota del proveedor: habrá diferencias, por eso "aceptar con motivo" es parte central.
- El importe de un documento en dólares se redondea a 2 decimales antes de pesificar (el stored total trae más decimales que la factura impresa).

## Fuera de alcance

Auditoría (quién/cuándo), tabla de cotizaciones oficiales, alta de compras dentro del panel, conciliación automática sin confirmación.
