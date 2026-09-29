# Research: Conciliación de Tesorería con documentos

## 1. ¿Qué forma real tiene cada uno de los 4 orígenes de documento?

**Decisión**: relevado contra el código real de cada módulo (no asumido):

| Origen | Tabla | Unidad conciliable | Id | Contacto/contraparte | Importe |
|---|---|---|---|---|---|
| Compras | `dbo.Compras` (vía `vw_Compras_ImporteDocumento`) | una factura/NC/ND | `IdDeuda` | `IdContacto` | importe bruto ya usado por Tarjetas (`_IMPORTE_BRUTO`, incluye compra particular) |
| Impuestos | `dbo.Impuestos` | un pago de impuesto/tasa | `IdImpuesto` | `IdOrganismo` (FK a Contactos) | `Importe` |
| Remuneraciones | `dbo.Remuneraciones` | una liquidación de sueldo | `IdSalario` | `IdContacto` (empleado) | suma de columnas de concepto (`_IMPORTE_SQL`, ya resuelto en `remuneraciones/repository.py`) |
| Alquileres | `dbo.[Detalle Cobro Alquiler]` (vía `dbo.Alquileres` para el contacto) | una cuota de alquiler | `IdCobroAlquiler` | `Alquileres.IdContacto` (join por `IdAlquiler`) | `[Importe Cuota]` |

**Alternativas consideradas**: tratar todo el contrato de Alquileres (`IdAlquiler`) como la unidad conciliable — rechazado: el pago real ocurre por cuota (`Detalle Cobro Alquiler`), conciliar el contrato completo perdería la granularidad y no cerraría nunca contra un solo movimiento de Tesorería.

**Nota**: `Detalle Cobro Alquiler.Estado` (`Pendiente`/`Cobrado`) es un campo de gestión ya existente (`set_estado_cuota`, escritura manual del usuario desde el módulo de Arrendamientos) — esta feature NO lo toca ni lo deriva de la conciliación: son dos registros paralelos (la conciliación de Tesorería es la fuente de verdad de "se cobró/pagó con qué movimiento"; `Estado` sigue siendo una marca manual de gestión). Evita un acoplamiento no pedido por el usuario (Principio VII).

## 2. ¿Cómo generalizar `buscar_documentos` a 4 orígenes sin duplicar la lógica que ya tiene Tarjetas para Compras+Impuestos?

**Decisión**: nueva función `conciliacion_tesoreria.repository.buscar_documentos(texto)` con una consulta `UNION ALL` de 4 ramas (una por origen), mismo patrón exacto que `tarjetas_resumenes.repository.buscar_documentos` (que ya hace esto para 2 orígenes desde 025) — cada rama proyecta las mismas columnas (`origen`, `idOrigen`, `fecha`, `tipoDocumento`, `numeroDocumento`, `moneda`, `tipoDeCambio`, `importeOriginal`, `contraparte`, `saldoPendiente`, `vinculosPrevios`). No se llama a la función de Tarjetas (ese buscador es específico de Compras+Impuestos con columnas propias de tarjeta, como `ajustaTipoCambio`); se escribe la propia en `conciliacion_tesoreria`, con las 4 ramas.

**`saldoPendiente`/`vinculosPrevios`** se calculan sumando Tesorería y Tarjetas para Compras/Impuestos, y Tesorería para los otros dos orígenes. El usuario confirmó saldo compartido; las dos pantallas y sus escrituras deben consultar la misma fuente de saldo. Se amplía mínimamente el repository de Tarjetas, manteniendo intacto el motor puro.

**Alternativas consideradas**: una vista SQL `vw_DocumentosConciliables` que unifique los 4 orígenes a nivel de base de datos — rechazada por ahora: es más cambio de esquema del necesario (una vista nueva, no solo columnas), y la consulta en Python ya es suficientemente simple con 4 ramas cortas; se puede migrar a una vista después si se necesita reusar desde más de un lugar (no es el caso hoy).

## 3. ¿Cómo registrar a qué documento corresponde una conciliación, sin romper las filas viejas (solo contacto+importe)?

**Decisión**: 2 columnas nuevas nullable en `ConciliacionesTesoreria`: `TipoOrigenDocumento varchar(20) NULL` (`Compras`|`Impuestos`|`Remuneraciones`|`Alquileres`|`NULL`) e `IdOrigenDocumento bigint NULL`. Una fila con ambas en `NULL` es una conciliación manual simple (FR-009, comportamiento ya vigente de 023) — `calcular_estado`/`esta_resuelto` no cambian, siguen sumando `Importe` por `(Medio, IdMovimiento)` sin mirar estas columnas nuevas. Mismo patrón ya usado por 025 para agregar `IdImpuesto` a `Tarjetas_Resumenes_Lineas_Compras` sin romper las filas viejas (`IdCompra`-only).

**Alternativas consideradas**:
- *Una tabla de vínculo aparte (`ConciliacionesTesoreriaDocumentos`)* — rechazada: el importe conciliado YA vive en `ConciliacionesTesoreria.Importe`; una tabla aparte duplicaría ese importe o forzaría un JOIN 1:1 innecesario para algo que es, conceptualmente, un atributo más de la misma fila (qué documento cubre esta parte del movimiento).
- *Un `CHECK` que exija los dos campos juntos o ninguno* — no se agrega en esta versión: la validación del repository exige ambos `NULL` o ambos con valor, de acuerdo con data-model.md. La regla XOR de Tarjetas se aplica a otra estructura y no corresponde copiarla aquí.

## 4. ¿Cómo modelar "sin documento" y "diferencia aceptada" para Tesorería?

**Decisión**: tabla nueva insert-only `ConciliacionesTesoreriaEstado` con los motivos de Tarjetas y auditoría propia. Incluye `EstadoQuitado`/`Revocacion` para quitar una excepción sin borrar historial. La excepción vigente se obtiene de la última fila por IdEstado. Una diferencia aceptada debe cerrar también una conciliación parcial, por lo que no se consulta únicamente después de descartar toda conciliación. Ver las reglas de estado en data-model.md. Tarjetas usa DELETE físico: se reutiliza su catálogo, no se presenta su persistencia como insert-only.

**Alternativas consideradas**: agregar `Estado`/`Motivo` como columnas de `ConciliacionesTesoreria` — rechazado: "sin documento"/"diferencia aceptada" son estados de un MOVIMIENTO sin importe ni documento vinculado (no una fila de conciliación con importe > 0), mezclar ambos conceptos en la misma tabla obligaría a permitir `Importe NULL`/`0`, complicando la validación `CHECK (Importe > 0)` ya vigente.

## 5. ¿Cómo integrar con 024 (`esta_resuelto`) sin romper el gate simétrico?

**Decisión**: `esta_resuelto` mantiene firma y agrega el sexto estado público `sin_documento`. `calcular_estado` incorpora la excepción vigente antes de devolver parcial/sin conciliar. La vía documental y la manual admiten continuar un parcial; la vía de traspasos solo admite sin_conciliar. Todas las escrituras deben revalidar la exclusión dentro de la misma transacción, no en una lectura anterior al INSERT.

## 6. Identidad del motor y revocación (revisión de implementación)

El motor puro opera sobre claves `idCompra`/`idImpuesto`; no acepta directamente los cuatro orígenes. Un adaptador en `conciliacion_tesoreria/documentos_adapter.py` asigna IDs internos únicos por selección, llama al motor sin modificarlo y restaura `(origen,idOrigen)` en sugerencias e imputados. Las claves internas nunca se persisten ni salen en la API. Los documentos de distintos orígenes con el mismo ID no colisionan.

El estado revocado no elimina conciliaciones ni promete volver siempre a sin_conciliar. El resultado depende de la suma de las filas que siguen existiendo. No se implementa `quitar_vinculo`: la revocación de imputaciones contables no está en el contrato aprobado.

**Alternativas consideradas**: ninguna — es la extensión directa del mecanismo que 024 ya dejó preparado (5 valores, con espacio para sumar más sin romper a los consumidores que hacen `switch`/mapeo por defecto).

## 7. Transacción común y alcance adicional

Un contexto transaccional en db/connection.py reutiliza la misma conexión para lecturas y escrituras y obtiene un único bloqueo de aplicación SQL Server, de nombre fijo, con propietario Transaction y espera limitada. Serializa las confirmaciones de conciliación manual/documental, estados, traspasos y vínculos de Tarjetas, incluso entre procesos. Las funciones anidadas comparten contexto; solo la exterior hace commit/rollback. No se aceptan nombres de bloqueos ni SQL de usuarios; los validadores SQL existentes siguen activos. Se prefiere este bloqueo breve común a una jerarquía compleja de locks por documento en esta app interna. No protege escrituras externas que ignoren el protocolo.

La ampliación incluye db/connection.py, los repositories de Tarjetas y traspasos, documentos.py compartido para saldos, schemas/tipos de Tesorería y el componente de traspasos. Se prueban transacciones con conexiones simuladas, sin insertar datos de prueba en WC.

Candidatos: hasta 60 documentos, ordenados por coincidencia de importe (primero), cercanía de fecha y clave estable; el motor considera 18 y combinaciones de hasta 4, devuelve hasta 5 propuestas. Búsqueda manual de hasta 40 resultados, texto de 2 a 100 caracteres. Selección de 1 a 20 claves únicas. No exigir contacto reconocido. SC-002 se medirá sobre fixtures con coincidencia conocida en los seis medios y cuatro orígenes; separar esta medida reproducible de una futura evaluación sobre corpus etiquetado real, que no está disponible.
