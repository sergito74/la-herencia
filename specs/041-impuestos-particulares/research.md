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
- Devoluciones de la carga: (a) Haber nuevo cargado desde la ficha (`Origen='DevImpParticular'`, `IdOrigen=IdCarga`), o (b) vínculo a un Haber existente del mismo socio (caso 3206: Haber del 13/11/2017, devolución de Lucy). Estado nominal: devuelto si Σ vínculos vigentes = importe; parcial si0<devuelto<importe; pendiente si0. No se admite sobredevolución; el importe por vínculo es explícito y está acotado por remanentes de carga y Haber. Lo no devuelto queda como deuda (aclaración 25/10).

## R5. Padrón de partidas
- `dbo.PartidasTitulares (Partida PK, IdSocio nullable, IdCargaOrigen nullable, Estado, TitularOscar, Fecha, Usuario)`: se alimenta al guardar una carga con partida. Al crear o abrir un impuesto con partida conocida, aviso con propuesta de titular. Oscar → Condominio (socio 3).

## R6. Migración del caso 3206
- Script con respaldo: crea la carga (Condominio, $8.852,10, «Inmobiliario Complementario del Condominio»), anula el Debe manual del 25/10 y vincula como devolución el Haber manual del 13/11/2017. Idempotente; el saldo del Condominio no cambia.


## R7. Compatibilidad, idempotencia y protección

- WC verificado en lectura: MovimientosCuentaSocio.Origen es varchar(20). DevImpParticular tiene 16 caracteres e ImpuestoParticular 18. No ampliar esa columna compartida.
- La devolución usa IdVinculo identity, estado e índice único filtrado, en vez de la PK compuesta inicial, para poder corregir enlaces sin perder historia. Siguen siendo tres tablas nuevas.
- Cada carga/vínculo persiste UUID y huella. No deduplicar por socio e importe: impediría cargas legítimas iguales. Un reintento tras anular nunca reactiva asientos.
- Proteger datos financieros del impuesto y movimientos ligados, incluyendo las operaciones de origen que puedan anularlos. No basta con proteger el panel 041.

## R8. Padrón y anulaciones

- Consultar la partida ingresada como dato auxiliar o recuperada de cargas existentes. No añadir una relación oculta a Impuestos ni afirmar que se detectó una partida desconocida.
- Derivar titulares de cargas vigentes: uno permite propuesta; varios producen estado ambigua; ninguno, sin_cargas. No elegir el último titular ni repartir deuda automáticamente.
- TitularOscar es una declaración de procedencia, no otro socio: siempre exige socio 3. Una declaración vigente en la partida impide cargas a otro socio.
- Anular carga anula sus vínculos y recalcula el padrón sin tocar los Haber. Anular vínculo solo libera capacidad nominal. Se conservan registros, auditoría y claves.

## R9. Manuales y valuación

- Ventana de tres días corridos sobre la fecha histórica: mismo socio, importe exacto, Debe Manual/NULL vigente. Es una selección explícita, nunca automática, aun si solo hay un candidato.
- Verificados en lectura: 3149 es Debe 8852,10 al 07/11/2017, 501,5354 USD y kg 0; 3150 es Haber 8852,10 al 13/11/2017, 505,8343 USD y kg 0. El 25/10/2026 es fecha de registro manual, no de la operación histórica. La migración conserva ese saldo.
- Devolución nominal del impuesto no significa saldo indexado cero. Informar el alcance nominal y no compensar la diferencia de cotizaciones automáticamente.
