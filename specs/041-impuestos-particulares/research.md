# Research — 041 Impuestos particulares

## R1. Dónde vive la marca
- **Decisión:** tabla nueva `dbo.ImpuestosParticulares` (una fila por carga: impuesto, socio, importe, motivo, partida, estado) y su Debe en `MovimientosCuentaSocio` con `Origen='ImpuestoParticular'`, `IdOrigen=IdCarga`.
- **Rationale:** `dbo.Impuestos` es heredada (no se agregan columnas, agente 07). El índice único `UX_MovimientosCuentaSocio_Origen` (Origen, IdOrigen) para Debe vigentes impediría varias cargas por impuesto si IdOrigen fuera el IdImpuesto; con IdCarga cada carga es única y se admiten varios socios por impuesto (FR-003).
- **Alternativas:** IdOrigen = IdImpuesto (rechazado: una sola carga por impuesto); columna en Impuestos (rechazado: tabla heredada).

## R2. Exclusión de costos
- `flujo_caja/atribucion.py::partes_desde_aplicaciones`: para `tipoDocumento='Impuesto'`, la parte cargada a socios (proporcional al importe del impuesto) va al rubro **"Cuenta de socios"** (centro "Socios"); el resto, al rubro del impuesto.
- `revision_cuentas/datos.py`: impuestos con carga total se muestran «cargado a socio» (no costo pendiente).
- `resultado_cultivo`: hoy no lee impuestos → sin cambios (supuesto de la spec).
- Cuenta corriente del organismo, vínculos/FIFO y conciliación: sin cambios (FR-005).

## R3. Valuación y signo
- `cuentas_socios.valuacion.a_fecha(importe, fecha_impuesto)`; magnitudes positivas, el Tipo da el signo (regla del 24/10/2026).

## R4. Estado devuelto/pendiente
- Devoluciones de la carga: (a) Haber nuevo cargado desde la ficha (`Origen='DevolucionImpuestoParticular'`, `IdOrigen=IdCarga`), o (b) vínculo a un Haber existente del mismo socio (caso 3206: Haber del 13/11/2017, devolución de Lucy). Estado: devuelto si Σ devoluciones ≥ importe; parcial si > 0; pendiente si 0. Lo no devuelto queda como deuda (aclaración 25/10).

## R5. Padrón de partidas
- `dbo.PartidasTitulares (Partida PK, IdSocio, IdCargaOrigen, Fecha, Usuario)`: se alimenta al guardar una carga con partida. Al crear o abrir un impuesto con partida conocida, aviso con propuesta de titular. Oscar → Condominio (socio 3).

## R6. Migración del caso 3206
- Script con respaldo: crea la carga (Condominio, $8.852,10, «Inmobiliario Complementario del Condominio»), anula el Debe manual del 25/10 y vincula como devolución el Haber manual del 13/11/2017. Idempotente; el saldo del Condominio no cambia.
