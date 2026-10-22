# Investigación y decisiones — 038

## Operación atómica
Decisión: cabecera con clave de idempotencia y efectos tipados. Coordinar validaciones y escrituras con la conexión compartida de src/db/connection.py (atomic_reconciliation/reconciliation_transaction). No encadenar commits independientes. Alternativa descartada: duplicar los libros existentes en caja.

## Pago y cobro
Decisión: un solo Pagos efectivo por pago/cobro, vinculado a caja; aplicar con aplicaciones_pago.repository. Caja no entra en vw_MovimientosCuenta_Base. La compra particular añade el asiento Particular y AsignacionGasto del socio según 036, sin duplicar la asignación existente. Aplicaciones explícitas prevalecen sobre sugerencias FIFO.
Evidencia: cajas_efectivo es GET y suma Importe; tesoreria identifica efectivo con Pagos efectivo. aplicaciones_pago admite parciales y múltiples documentos. sugerencia usa importeImputado negativo para compras y positivo para ventas: verificar la traducción al signo físico de caja antes de escribir.
Hallazgo inicial (resuelto en implementación): documentos.py soportaba compras, ventas de hacienda y granos, sin alquileres. Implementación debe relevar el origen documental de alquileres y extender su adaptador y pruebas; no prometer aplicación a un documento inexistente ni inventar deuda. Bloquear esa variante con mensaje preciso hasta tener un documento compatible.

## Socios
Decisión: aporte usa Devolucion (crédito); retiro a cuenta usa AsignacionGasto (deuda); ganancias no genera cuenta de socio. No introducir nuevos tipos sin actualizar todos los consumidores: hoy cualquier Tipo distinto de AsignacionGasto resta saldo.
Reutilizar fórmula de scripts/socios_valuacion_036.py y extraer función compartida si hace falta. Guardar cotizaciones a fecha e importes kg/US$; no usar registrar_devolucion sin ampliarlo porque solo guarda pesos. deuda_actualizada distingue mutuo y usa cotización actual para exposición, no para reconstruir el ingreso histórico.

## Traspasos
Decisión: Giamigli-caja chica mediante operación y dos movimientos opuestos sin efecto de socio. Cruces con Condominio son aportes/devoluciones con dos piernas y un efecto de socio. Caja-banco mediante efectivo puente sin contacto, TraspasosInternosTesoreria y vínculo explícito a caja. Intermediario personal y evidencia no generan aporte. El módulo 024 registra eventos Vincular/Deshacer y exige movimientos sin conciliar; no crea caja ni elimina por sí solo efectos en cuentas corrientes. FR-008 requiere exclusión central comprobada del banco vinculado, con restauración al anular. Las sugerencias por fecha/importe nunca son prueba automática.

## Anulación
Decisión: guardar auditoría y desactivar los efectos propios de la operación en una transacción. Anular aplicaciones y socio; deshacer vínculos bancarios. Si Pagos efectivo no tiene estado de anulación utilizable, añadir marca y excluirlo de todos los lectores pertinentes, sin borrar ni crear un pago ficticio compensatorio. Dependencias posteriores ajenas se informan como conflicto; nunca se revierten en silencio.

## Convivencia y arqueos
Decisión: vista previa y confirmación; origen identificado por libro lógico, hoja, fila y huella. La fila sola cambia al insertar líneas. Coincidencias ambiguas/manuales requieren enlace explícito o revisión humana; dos filas con misma fecha/importe no se descartan automáticamente. Filas modificadas quedan pendientes. Importación usa el mismo coordinador, con modo de vincular efectos históricos existentes sin recrearlos.
Condominio: conservar historia completa consultable; nuevos movimientos solo Giamigli, con motivo obligatorio. Mostrar cobertura y exclusiones en comparación. Su saldo parcial no prueba el efectivo completo del sistema propio del Condominio.
Arqueo: corte por fecha y secuencia, denominaciones en pesos, diferencia explícita y una sola confirmación. Revalidar saldo al confirmar; avisos por fecha retroactiva y saldo negativo.

## Permisos y límites de evidencia
AuthMiddleware en main.py devuelve 403 para escritura del rol Lectura; usuario de request.state.usuario. Reutilizar SoloLectura/AuthContext.
Investigación sobre código y documentos locales; no se leyó ni modificó WC. La inspección de columnas, restricciones y vistas reales es puerta de implementación. No se investigan versiones externas porque se conserva el stack instalado.

## Resoluciones del análisis autorizadas — 22/10/2026
Las precisiones de spec/modelo/contrato sustituyen las generalizaciones anteriores: solo Giamigli↔chica es traspaso sin socio; Condominio es aporte/devolución con dos piernas o pago directo con crédito al socio. Gasto sin comprobante requiere registro no fiscal y repartos integrados una vez en costos; no hay circuito demostrado que pueda reutilizarse sin adaptación: costos.py hoy lee vistas heredadas/órdenes. Anulación de ajuste invalida arqueo; retroactividad lo desactualiza. GET conserva números existentes; nuevos campos usan Decimal. Saldo real no cambia por ocultar filas. Opción A conserva el mecanismo de Ajuste Interno no cobrado y no reclasifica pares históricos desde noviembre de 2017, según sergio-375-pendientes-resumen-20261022.md, actualización de 15:05. Verificar contrato SQL/API antes de UI. Todo sigue siendo diseño, sin escrituras.

## Resolución aplicada
Implementación 038 completada. Alquileres se aplica por cuota real IdCobroAlquiler y el CHECK de AplicacionesPago fue ampliado con respaldo verificado. Particular parcial conserva asignación completa del gasto personal documentado a fecha de compra (021), evita recrear nota/asignación y protege pagos dependientes. Anulación tiene previsualización propia para negativos/períodos arqueados. El estado unificado de tesorería ignora el contacto histórico solo mientras existe vínculo 038 vigente; no se borra ese contacto. El cierre y evidencias vigentes están en quickstart.md y schema-verification.md; las alternativas y pendientes anteriores corresponden a la fase de investigación.
