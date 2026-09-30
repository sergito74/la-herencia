# Data model: 029

Diseño propuesto; las tablas nuevas todavía no existen ni se ejecutó DDL. Importes ARS con Decimal a 2 decimales en dominio, decimal(19,2) en tablas nuevas; money existente al insertar Impuestos. Fechas de auditoría UTC, fecha de boleta calendario del pago.

## Entidades existentes

- `dbo.Impuestos`: insertar Fecha, IdOrganismo, IdTipoImpuesto, Importe; período y número solo si conocidos, de otro modo NULL; Documento Original con ruta validada o NULL; IdOperacion no se inventa.
- `dbo.[Tipo Impuesto]`: reutilizar tipo válido del organismo o crear una fila por organismo llamada `Sin identificar (generada desde el pago)`. Revalidar bajo bloqueo para evitar duplicados.
- Pagos de los seis medios, Contactos, ReasignacionesContacto, ConciliacionesTesoreria, Tarjetas_Resumenes_Lineas_Compras y vista de cuentas: lectura; no modificar datos existentes.

## BackfillImpuestosLotes

IdLote uniqueidentifier PK (idempotencia); IdOrganismo int FK Contactos; Estado varchar(20) confirmado/revertido; HuellaPropuesta y HashSolicitud char(64); Usuario nvarchar(100); Fecha datetime2; BackupId nvarchar(100); Cantidad int; Total decimal(19,2); FechaReversion/UsuarioReversion nullable. CHECK cantidad positiva, total positivo. Un lote pertenece a un organismo. Se inserta dentro de la misma transacción que boletas y vínculos; fallas no dejan lote parcial.

## BackfillImpuestosBoletas

IdRegistro bigint identity PK; IdLote FK; IdImpuesto int nullable FK Impuestos, con índice UNIQUE filtrado WHERE IdImpuesto IS NOT NULL (se pone NULL solo al revertir y borrar la boleta propia); IdImpuestoHistorico int inmutable; OrigenCreacion varchar(20) comprobante/generada; TieneComprobante bit; ArchivoHash char(64) nullable; SnapshotCreacion nvarchar(max), JSON validado de campos originales; Version rowversion. Las filas de procedencia sobreviven a la reversión. En una misma transacción se eliminan vínculos propios, se pone IdImpuesto en NULL en todas las filas revertidas y se eliminan las boletas propias intactas; los índices filtrados admiten múltiples registros históricos con NULL. IdImpuestoHistorico y ArchivoHash conservan la evidencia histórica. Generada sin adjunto tiene marca visible; adjuntar cambia TieneComprobante, nunca OrigenCreacion. Índice UNIQUE sobre ArchivoHash filtrado WHERE ArchivoHash IS NOT NULL AND IdImpuesto IS NOT NULL; además verificar otros módulos bajo transacción.

## BackfillImpuestosVinculos

IdVinculo bigint identity PK; IdLote FK; Medio varchar(20) allowlist; IdMovimiento bigint; IdOrganismo int; IdImpuesto int FK; Importe decimal(19,2) positivo; HuellaPago char(64). Índice UNIQUE `(Medio,IdMovimiento)` porque cada pago elegible completo produce una sola boleta y no se aceptan distribuciones/parciales. No hay FK polimórfica a pagos: revalidación explícita con consultas allowlist. Esta tabla NO participa como crédito en cuenta corriente. Sí participa como consumo en saldo documental compartido.

En reversión se elimina el vínculo activo y se conserva su snapshot en auditoría. De este modo se libera la unicidad para una nueva propuesta posterior sin perder historia. Nunca crear a la vez un vínculo 029 y una conciliación contable nueva por el mismo pago.

## BackfillImpuestosEventos

IdEvento bigint identity PK; IdLote FK; IdRegistro FK nullable; Tipo confirmar/adjuntar/cambiar_tipo/revertir; Usuario, Fecha; Antes/Despues nvarchar(max) JSON. Insert-only; incluye IDs históricos de boletas y vínculos aun después de reversión. No almacenar contenido binario del PDF ni datos ajenos al lote.

## Objetos no persistidos antes de confirmar

- Pago: clave canónica, referencia contable, contacto efectivo, fecha, concepto, importe, medio, huella.
- Diagnóstico: respaldado, probable, faltante, pendiente o excluido con motivo; totales por categoría y saldo completo sin corte. Suma faltantes no se fuerza a coincidir con saldo global.
- Archivo: identificador opaco, ruta canónica interna, SHA-256, organismo/fecha inferidos, reconocido/ambiguo/usado/ilegible. Cobertura completa de búsqueda explícita.
- Tipo propuesto: modo existente con IdTipoImpuesto válido del organismo, o modo generico simbólico sin ID; el catálogo se resuelve solo al confirmar.
- Preparación: token firmado con finalidad, usuario, huella y fecha UTC emitida por servidor; evidencia operativa de backup firmada fuera de Git, sin persistencia paralela de datos de negocio.
- Propuesta: política versionada, huella, filas seleccionadas/corregidas/excluidas, origen elegido, tipo, adjunto, totales, saldo proyectado y diferencias. Estado en navegador y recalculado en servidor; no tabla de borradores ni archivos de negocio paralelos.

## Invariantes y transiciones

1. Solo egreso real positivo normalizado a organismo vigente; cobros, reintegros, retenciones, traspasos y sin asignar no generan deuda.
2. `importeNuevo = importePagoCompleto`; respaldos parciales/colisiones no generan. La tolerancia 0,10 clasifica coincidencias, no permite sobregirar capacidad (tope 0,01 del contrato existente).
3. Ausencia de boleta no basta: validar otros respaldos y presencia única del pago en cuenta. Caso contrario pendiente con motivo.
4. Selección revisada → revalidación/backup → transacción → confirmado; cualquier cambio concurrente devuelve conflicto sin escrituras.
5. Confirmado → adjunto/corrección auditados, con versión; solo boletas 029. Confirmado → revertido solo si no hubo cambios/dependencias posteriores; conflicto revierte toda la operación de reversión.
6. El saldo documental suma vínculos de Tesorería + Tarjetas + 029 una sola vez. Todas las escrituras consultan esta misma capacidad bajo el bloqueo común.
