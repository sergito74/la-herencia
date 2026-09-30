# Research: 029 — decisiones y evidencia

## 1. Esquema y estado real

**Decisión:** reutilizar Impuestos y su campo `[Documento Original]`; agregar tablas propias para auditoría y respaldo, sin alterar vista contable.

**Evidencia:** consulta SELECT a INFORMATION_SCHEMA y OBJECT_DEFINITION de `vw_MovimientosCuenta_Base` en WC el 2026-09-30. Impuestos tiene IdImpuesto int, Fecha datetime nullable, IdOrganismo/IdTipoImpuesto int nullable, período/número nvarchar(255), Importe money, Documento Original nvarchar(max), IdOperacion int nullable. Tipo Impuesto tiene IdTipoImpuesto int, IdOrganismo nullable y Nombre Impuesto nvarchar(255) obligatorio. No se realizaron escrituras.

Saldos agregados observados, redondeados solo para lectura: AFIP −12.968.502,77; ARBA −6.367.489,20; Bolívar −5.441.161,44; UATRE −874.637,64; Tapalqué 0,00; Ministerio −6.000,00. No constituyen lista de pagos faltantes. Tapalqué tiene 22 movimientos; investigar su composición en el diagnóstico, sin asumir que todo pago sin Impuestos requiere nueva deuda.

**Alternativa descartada:** forzar cero a partir del saldo neto. Puede ocultar compras, deuda legítima, devoluciones y partidas duplicadas.

## 2. Respaldo y conservación de importes

**Decisión:** distinguir vínculo documental comprobado, respaldo probable, faltante confirmado y pendiente. `ya_reconocido` solo indica contacto: no prueba boleta. Leer vínculos a Impuestos de ConciliacionesTesoreria, Tarjetas_Resumenes_Lineas_Compras y los nuevos de 029. Sumar capacidad consumida sin duplicar la misma evidencia. Reservar capacidad global por boleta en orden determinista fecha/clave; colisiones no se resuelven por elegir el primero. Parciales, importes nulos, otros respaldos y contradicciones quedan pendientes.

**Evidencia:** `conciliacion_tesoreria/repository.py`, `documentos.py`, `tarjetas_resumenes/conciliacion_documentos.py`. Conciliación tolera ARS 0,10 para coincidencia; sobreimputación documental permite solo 0,01. AplicacionesPago usa otro contrato y no admite Impuestos. En 029 usar Decimal y no convertir anticipadamente a float; la capa actual convierte Decimal a float, así que la lectura monetaria 029 debe conservar Decimal mediante cursor de la conexión común.

**Alternativa descartada:** comparar cada pago contra el mismo saldo sin reservarlo, o generar por el total de un pago parcialmente respaldado.

## 3. Identidad y contabilidad

**Decisión:** normalizar `(medio,idMovimiento)` desde adaptadores explícitos para bna, galicia, mercado-libre, efectivo, valores-propios y valores-recibidos. Resolver contacto efectivo incluyendo reasignaciones; las distribuciones entre varios organismos quedan pendientes. Vincular cada pago a sus filas contables concretas, sin sumar dos veces fuente y conciliación. Inventariar además vínculos de tarjeta para no volver a cubrir boletas pagadas por ese medio; consumos de tarjeta sin identidad de organismo fiable quedan informados, no generan boletas automáticas.

**Evidencia:** la vista vigente suma movimientos nativos BNA/Galicia/efectivo y también ConciliacionesTesoreria. La rama nativa ML no está presente y la rama Tarjetas une Compras, no Impuestos. Insertar conciliación documental para pagos ya reconocidos puede duplicar el crédito. No extender esa vista durante 029: los pagos sin reflejo contable fiable quedan pendientes con motivo visible.

**Alternativa descartada:** llamar directamente a vincular_lote de 026 (rechaza reconocidos y además tiene efecto contable). El vínculo propio de 029 no genera asiento y sí resta capacidad documental en todas las lecturas y escrituras de conciliación.

## 4. Archivos reales antes de generación

**Decisión:** recorrer solamente raíces configuradas de Impuestos y Compras, todas las carpetas de ejercicio, sin fecha de corte. No reutilizar el buscador genérico que devuelve la primera coincidencia. Normalizar alias por organismo y fechas válidas del nombre; ventana propuesta de ±7 días, registrada como política técnica versionada. Coincidencia única en ambos sentidos (pago↔archivo), no prueba fiscal: usuario debe abrir y confirmar el documento. No extraer importes del PDF. Si los datos del documento contradicen el pago, dejar pendiente para tratamiento manual.

Deduplicar por ruta canónica y SHA-256, excluir adjuntos ya usados en Impuestos/Compras o lotes vigentes. No seguir enlaces fuera de raíces. Archivos ilegibles, raíz inexistente, acceso denegado o recorrido incompleto se informan y bloquean la conclusión «sin comprobante». Un caso ambiguo no pasa automáticamente a generado. La selección manual de candidato puede resolver la ambigüedad documental con confirmacionDocumento y revalidación de unicidad global; nunca levanta una ambigüedad financiera. Límite propuesto 20.000 archivos y 30 segundos por recorrido; al alcanzarlo informar incompleto, permitir repetir acotado a organismo/ejercicio sin perder cobertura histórica.

**Alternativa descartada:** OCR o búsqueda abierta por todo el disco; no están en el alcance. La inspección de carpetas reales queda para el diagnóstico, no se afirma haberla repetido en este plan.

## 5. Revisión, backup y concurrencia

**Decisión:** diagnóstico/propuesta no escriben WC. Revisión en navegador; servidor produce huella de datos fuente, selección y correcciones; al confirmar recalcula y compara. La huella no concede autorización: autenticación, rol y validación server-side son obligatorias. Idempotencia por UUID de solicitud con hash del payload, unicidad de pago activo y bloqueo `reconciliation_transaction` compartido con Tesorería/Tarjetas. Máximo 200 pagos por transacción; más pagos requieren lotes revisados por separado.

Backup: registro confiable emitido por herramienta local tras BACKUP WC WITH CHECKSUM y RESTORE VERIFYONLY WITH CHECKSUM, guardado fuera de Git. La API no acepta un booleano «verificado» ni SQL/ruta arbitrarios del navegador; valida identificador de evidencia, base WC, archivo existente y verificación satisfactoria y comienzo del backup posterior a la preparación firmada del lote. El contrato API define token de preparación, modo local --backup-only y GET /respaldo para consultar evidencia firmada sin rutas libres; corregir la selección invalida preparación y respaldo para esa selección. Antes de DDL o reversión se exige igual disciplina. No hacer backup dentro de la transacción contable.

**Alternativa descartada:** escrituras durante vista previa, confirmación con datos obsoletos o backup indicado por el cliente sin comprobación.

## 6. Procedencia y reversión

**Decisión:** origenCreacion inmutable; estado actual de respaldo cambia al adjuntar comprobante. Permitir cambiar tipo/adjunto solo a boletas creadas por 029; conservar evento, autor, antes/después y versión. Tipo genérico creado por organismo, nunca inferir el más frecuente.

Reversión atómica selectiva solo si las boletas y vínculos permanecen sin modificaciones ni dependencias posteriores; eliminar exclusivamente vínculos/boletas propios, guardar snapshot de auditoría y lote revertido. Catálogo genérico se conserva. No restituir un backup completo como reversión habitual. Una solicitud repetida devuelve el lote existente; nuevo diagnóstico tras revertir puede proponer otra vez el pago.

**Alternativa descartada:** borrar por lote sin revisar dependencias. La documentación antigua de 026 dice insert-only pero el código actual permite quitar vínculos: se revalida el estado real al confirmar y revertir.

## 7. Autorización y experiencia

**Decisión:** usar middleware actual (Lectura no puede POST/PATCH/DELETE). GET diagnóstico/propuesta disponibles autenticados; revisión editable en UI solo para roles con escritura. Vacío/error/pendiente explícitos; mostrar causa y saldo proyectado sin prometer saldo cero. Actualizar metadatos de cuenta corriente por clave Impuestos/IdImpuesto, sin concatenar marcas en el número de documento ni cambiar importes.

**Evidencia:** `backend/src/main.py`, módulos Impuestos y frontend de cuentas corrientes existentes. Revisión especializada de investigación de respaldo/tolerancias/reversión incorporada en secciones 2, 3 y 6.
