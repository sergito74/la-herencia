# Modelo propuesto — 038

Diseño aditivo pendiente de verificar contra WC antes de generar DDL. No modifica saldos iniciales ni vuelve a importar historia.

## OperacionesCajaEfectivo (nueva)
IdOperacion bigint PK; ClaveIdempotencia uniqueidentifier UNIQUE; HuellaSolicitud char(64); Tipo varchar(40); Fecha date; Concepto nvarchar(255); Cuenta varchar(20) A/B para nuevas operaciones; IdContacto/IdSocio opcionales con referencia válida; Estado Vigente/Anulada; Usuario y FechaCarga UTC; MotivoAnulacion, UsuarioAnulacion, FechaAnulacion; Intermediario y Evidencia opcionales y MotivoRelacionGiamigli obligatorio si involucra Condominio, persistidos dentro de Solicitud JSON validada. Importes positivos en solicitud, signo determinado por tipo. Ganancias y traspasos internos Giamigli↔chica no crean efectos en cuentas de socio/contacto. Cruces Condominio: aporte/devolución con dos piernas físicas y un efecto de socio.

Misma clave + misma solicitud devuelve operación previa; misma clave con contenido diferente es conflicto. Solo Vigente→Anulada, no edición destructiva. Una operación puede afectar dos cajas. Reintentos de anulación devuelven estado existente, sin duplicar efectos.

## MovimientosCajaEfectivo (existente)
Conservar IdMovimiento, Caja, Fecha, Concepto, Detalle, Importe firmado, Cuenta, FilaPlanilla, IdPagoEfectivo y metadatos existentes. Agregar IdOperacionCaja bigint nullable, Tipo y Anulada con default 0 si no existen. Historia sin operación sigue vigente. FK a operación e índice Caja/Fecha/IdMovimiento; índices filtrados de unicidad donde un pago tenga un solo efecto físico. Saldo=sumatoria de vigentes; orden estable Fecha,IdMovimiento; saldo corrido antes de aplicar paginación y con arrastre anterior al filtro de fechas.

## EfectosOperacionCaja (nueva)
IdEfecto PK; IdOperacion FK; TipoEfecto enumerado (PagoEfectivo, Aplicacion, MovimientoSocio, AsientoParticular, TraspasoTesoreria, GastoCaja, AjusteNoCobrado); IdRegistro; EsCreadoPorOperacion bit; Estado y auditoría. Unicidad de propiedad del efecto creado. Resolver tabla por catálogo fijo en servidor, nunca SQL libre. Referencias preexistentes se enlazan y no se anulan como propias. Cada operación conserva vínculos a todos sus efectos; creación/anulación con bloqueo y transacción común.

## Libros relacionados
Pagos efectivo: único origen contable del pago/cobro a contacto. Adoptar marca de anulación si falta y actualizar todos los consumidores; verificar contrato de signo/IdTipoMovimiento/IdFormaPago/Caja. AplicacionesPago conserva origen efectivo y documentos reales. Validar contacto, moneda, capacidad y saldo bajo la misma transacción. Diferencias de cambio siguen 036 y nunca ajustan el fiscal automáticamente.
MovimientosCuentaSocio: mantener AsignacionGasto/Devolucion, Anulada, Origen/IdOrigen, pesos, USD y kg. Persistir fuente, fechas y cotizaciones utilizadas en metadatos de operación; regla histórica 036 (antes del 16/03/2020 100% US$, después 50% US$/50% kg). Si falta cotización válida no inventar valores.
TraspasosInternosTesoreria: conservar eventos de vinculación/deshacer. Asociar banco y efectivo puente; excluir banco de contactos mientras el vínculo está vigente. No escribir sobre bancos ajenos ni reasignar importes.

## ArqueosCajaEfectivo y ArqueoDenominaciones (nuevas)
Arqueo: IdArqueo PK, Caja, FechaCorte, SecuenciaCorte, Estado Borrador/Confirmado/Invalidado/Desactualizado, SaldoSistema, TotalContado, Diferencia, IdOperacionAjuste nullable UNIQUE, Usuario/fecha de creación y confirmación. Detalle: IdArqueo FK, Denominacion decimal positiva, Cantidad entera >=0, UNIQUE(arqueo,denominación). Total=sum(denominación*cantidad); diferencia=contado-saldo. Una confirmación crea como máximo un ajuste; cero diferencia no crea movimiento. Revalidar corte al confirmar. Correcciones posteriores de períodos arqueados muestran advertencia y no reescriben el recuento original.

## ImportacionesCaja y FilasOrigenCaja (nuevas)
Lote: IdLote, libro lógico, huella archivo, fecha/corte, usuario, estado Preview/Confirmado, versión del parser. Fila: lote, hoja, fila, huella de contenido normalizado, datos originales, estado Nueva/Vinculada/Ambigua/Modificada/Excluida, IdMovimiento nullable, IdOperacion nullable, motivo y resolución auditada. Unicidad de fila dentro del lote y de vínculo de origen confirmado; cambios de posición se reconcilian por identidad explícita o revisión, nunca por coincidencia débil. No imponer unicidad global de contenido: filas legítimas pueden ser iguales.
Comparación al mismo corte: saldo de cada fuente, cobertura, filas faltantes/extras/modificadas/ambiguas. No se almacena otro saldo operativo. La historia ajena/sin vínculo del Condominio queda archivada fuera de lecturas operativas, con snapshot y evidencia en AlcanceHistoricoCaja.

## Concurrencia y reversión
Bloquear cajas afectadas en orden estable y referencias de documentos/banco; revalidar capacidad y advertencias al guardar. Cualquier fallo revierte todos los efectos. Anulación con dependencias posteriores devuelve conflicto con identificadores. Migración reversible mediante respaldo verificado y cambios aditivos; nunca restaurar producción automáticamente ni borrar historia.

## GastoCajaEfectivo y RepartosGastoCaja (nuevas)

Gasto: IdGasto bigint PK; IdOperacion bigint NOT NULL UNIQUE FK; Fecha date NOT NULL; Concepto nvarchar(255) NOT NULL; ImportePesos decimal(19,2) positivo; ImporteUSD decimal(19,4) nullable; TipoCambio decimal(19,6) nullable positivo; FuenteCotizacion nvarchar(255) y FechaCotizacion date nullable; Anulada bit NOT NULL default 0; usuario/fecha y auditoría de anulación. USD requiere fuente/fecha/TC; si falta, mostrar no valuado, nunca cero validado. No insertar Compras/Det_Compras ficticias ni deuda al contacto 97.
Reparto: IdReparto bigint PK, IdGasto FK NOT NULL, IdRubro/IdCentroCostos NOT NULL con referencias válidas, IdDestino/IdCampania/IdLote nullable según naturaleza; ImportePesos decimal(19,2) positivo. Suma igual al gasto; residual de redondeo explícito al último reparto. No reasignar No Aplica ni datos productivos ambiguos.
Integrar origen GastoCaja en backend/src/features/resultado_cultivo/costos.py y lectores de costos inventariados en T001: una vez por reparto vigente, con IdGasto/IdReparto/IdOperacion. Mantener política 012: sin clasificar queda informativo, fuera del margen. Si se necesita adaptar el DTO de origen y el listado sin clasificar, hacerlo en la misma entrega. Anulación marca gasto y operación juntos; lectores excluyen anulados sin borrar repartos. No duplicar costo en compras ni guardar saldo de caja paralelo.

## Condominio y retorno de sueldo

Aporte/devolución de socio 3 admite cajaContraparte: misma operación, fecha e importe, cajas distintas. Aporte: Condominio −X, Giamigli/chica +X y Devolucion socio 3 X; devolución: signos físicos inversos y AsignacionGasto socio 3 X. Pago directo desde Condominio de gasto Giamigli: pago proveedor, salida Condominio y crédito socio, sin caja Giamigli ficticia; no combinar con compra particular. Guardar naturaleza económica y evidencia.
Opción A: IdSalario, referencia bancaria, retorno de caja, evidencia y snapshot versionado de contacto/aplicaciones previas. Efecto AjusteNoCobrado apunta al Ajuste Interno real de 036 verificado en T001; enlazar el existente sin duplicarlo y no anularlo como propio. Exigir monto plenamente documentado. Conservar los pares de socio desde noviembre de 2017.

## Versiones, arqueos y filtros

Operacion/arqueo tienen Version bigint NOT NULL default 0, incrementada en transiciones. Preview incluye huella de solicitud y dependencias: saldo/movimientos/arqueos, cotizaciones, aplicaciones y vínculos; revalidar dentro de transacción.
Arqueo con ajuste anulado pasa a Invalidado con auditoría en la misma transacción, sin reactivar el recuento. Arqueo afectado por retroactividad pasa a Desactualizado. Conservar datos observados; mostrar saldo recalculado/diferencia vigente aparte. Nuevo arqueo correctivo guarda IdArqueoAnterior nullable FK. Solo Confirmado vigente acredita conciliación; último arqueo muestra también su estado.
Saldo corrido sobre todos los movimientos vigentes antes de filtros de tipo/contacto/socio y páginas. Desde/hasta limita ventana visible; saldoAnterior es saldo real previo al inicio. SubtotalFiltrado suma únicamente movimientos vigentes que cumplen filtros; no sustituye saldo real. Anulados visibles no cambian saldo/subtotal.

Implementar la unicidad de IdOperacionAjuste nullable con índice UNIQUE filtrado WHERE IdOperacionAjuste IS NOT NULL para admitir varios arqueos sin ajuste en SQL Server.

## Detalles cerrados antes de implementación (T003)

Importes nuevos decimal(19,2); cotizaciones decimal(19,6), valuación USD decimal(19,4), kg decimal(14,3), redondeo comercial HALF_UP. Concepto 1–255 caracteres, motivo/evidencia máximo 255, usuario máximo 60 tomado de sesión; identificadores positivos. Texto opcional NULL, no cadena vacía. Version bigint NOT NULL default 0. Preview SHA-256 canónico del pedido y dependencias, sin confiar en saldo enviado por navegador.
Corte: fecha operativa America/Argentina/Buenos_Aires y secuencia IdMovimiento dentro del día; lectura estable por Fecha,IdMovimiento. Desde/hasta inclusivos, saldo a fin del día, orden ascendente. Filtros no alteran saldo real. Página >=1, pageSize 1..200. Detalles de operación y arqueo por identificador; listados paginados.
XLSX máximo 10 MiB, 20.000 filas por hoja y 50 MiB de contenido ZIP descomprimido; hojas permitidas Caja Efectivo Pesos y Caja chica campo del libro lógico CajasGiamigli, y hoja de Condominio explícitamente configurada. Rechazar archivo cifrado/macros/enlaces externos; fórmulas sin valor cacheado quedan pendientes, nunca cero por defecto. No abrir Excel ni escribir archivos originales.
BancoOperacionCaja: IdOperacion FK, Medio catálogo bna/galicia/mercado-libre, IdMovimiento bigint; unicidad activa por movimiento se revalida bajo bloqueo común. Vista de efectivo vigente excluye efectos de operaciones anuladas; tabla física permanece auditable. Pagos efectivo.IdContacto pasa a nullable para puente real sin contacto, según metadatos WC. No reutilizar su IdOperacion int para la cabecera 038 bigint.

## Correspondencia con esquema aplicado

DDL reproducible: backend/scripts/migrar_gestion_cajas_038.py. Persistencia Decimal en operaciones.py; coordinación en service.py; recuentos en arqueos.py e importación en importacion.py. Campos lógicos de solicitud se guardan en Solicitud JSON y fuentes/cotizaciones en Contexto JSON, no en columnas duplicadas. EsCreadoPorOperacion distingue efectos generados y preexistentes. Particulares generan nota tipo 2 con IdFormaPago NULL: no es un movimiento físico adicional. Las piernas bancarias se vinculan a IdPagoEfectivo del puente y BancoOperacionCaja; el contacto bancario original permanece intacto y la exclusión es reversible por estado de operación.
Vista vw_PagosEfectivoVigentes y lectores de ajustes excluyen efectos de operaciones anuladas sin borrar filas. Índice UX_Caja038_PagoFisico, filtrado por vínculo de operación/IdPagoEfectivo/vigente, impide dos movimientos físicos vigentes para el mismo pago. IdOperacionAjuste usa índice UNIQUE filtrado para admitir varios NULL.
La ausencia de PK/clave única en Centro de costos se conserva: IdCentroCostos se valida contra el catálogo dentro de la transacción, sin añadir una clave sobre datos heredados. Lecturas de datetime2 se normalizan cuando ODBC las devuelve como texto. Ninguna migración altera movimientos o saldos iniciales.
La previsualización de anulación calcula el saldo corrido real excluyendo los movimientos de esa operación, desde su posición cronológica, y liga advertencias al contexto actual mediante SHA-256. Se conservan observaciones de arqueo; ajustes anulados invalidan el recuento y cambios retroactivos desactualizan los afectados.


## Corrección de alcance aprobada — 23/10/2026
Sergio reemplaza la conservación visible de toda la caja del Condominio por un registro exclusivo de relaciones con Giamigli. Ver [criterios, contrato y plan de corrección](limpieza-condominio-20261023.md). Históricos ajenos/sin vínculo documentado permanecen archivados, fuera de saldos, filtros y comparaciones operativas. El neto parcial no representa tenencia física ni deuda; no admite arqueos físicos. Una sola entrada de Condominio con cuenta de socio y movimientos vinculados, sin sumar ni duplicar sus efectos.
