# Feature Specification: Recibos de Proveedores y Órdenes de Pago (046)

**Feature Branch**: `046-recibos-ordenes-pago`  
**Created**: 2026-10-30  
**Status**: Implementada (30/10/2026)  
**Scope**: Finanzas / Cuentas Corrientes / Tesorería  

---

## 1. Contexto y Objetivos

### 1.1 El Problema
1. **Recibos de Pago confundidos con Compras:** Los recibos oficiales emitidos por proveedores (como Baya Casal, Sancor, acopios o talleres) acreditan la cobranza/cancelación de pagos y facturas, no una nueva deuda o gasto fiscal. Mezclarlos en Compras distorsiona el resultado económico y las declaraciones juradas.
2. **Falta de planificación de pagos:** Para preparar pagos a proveedores (transferencias bancarias, cheques o efectivo de caja), hoy se requiere revisar manualmente facturas dispersas en `Compras` o en cuentas corrientes sin una herramienta de confección de **Órdenes de Pago** que consolide facturas pendientes, retenciones a practicar y medios de pago previstos.
3. **Desconexión probatoria:** Cuando sale una transferencia bancaria o pago de caja, no existía un circuito ágil para vincular el PDF del recibo emitido por el acreedor ni para imputarlo contra las facturas correspondientes.

### 1.2 La Solución
Implementar el módulo unificado de **Recibos y Órdenes de Pago**:
* **Gestión de Órdenes de Pago (OP):** Selección de facturas pendientes de un proveedor, cálculo de retenciones si correspondiera, selección de medios de pago (cuenta bancaria, cheque, caja) y emisión de la OP en estado borrador / emitida.
* **Procesamiento de Recibos Oficiales (Ingesta automática):** Detección automática de recibos por mail o depósitos en carpetas locales mediante `DocumentosNuevos` (`modulo='pagos'`), extrayendo proveedor, fecha, número y total.
* **Conciliación y Aplicación:** Vinculación del recibo contra la Orden de Pago o directamente contra los movimientos de tesorería y facturas pendientes en `dbo.AplicacionesPago` (Spec 019).

---

## 2. Historias de Usuario

### Historia 1 (P1): Preparación y emisión de Órdenes de Pago
Como usuario financiero, quiero seleccionar una o varias facturas de compra pendientes de un proveedor y confeccionar una Orden de Pago, para organizar los pagos a realizar desde bancos o cajas de efectivo antes de ejecutarlos.

#### Criterios de Aceptación:
1. Permite elegir un proveedor con saldo deudor y listar sus facturas de compra pendientes (saldo neto pendiente > 0).
2. El usuario selecciona qué facturas pagar (total o parcialmente) y define los medios de pago tentativos (Galicia CC, BNA, Caja Giamigli, Cheque diferido).
3. La Orden de Pago se guarda con un número secuencial, fecha de confección, fecha estimada de pago, detalle de facturas aplicadas y total a pagar.
4. Estado de la OP: `Borrador` → `Emitida` → `Pagada` (cuando se concilia con los movimientos reales de tesorería) o `Anulada`.

---

### Historia 2 (P1): Recepción y clasificación de Recibos de Proveedores
Como usuario, quiero que los recibos oficiales que envían los proveedores por mail o que guardo en las carpetas se detecten automáticamente y se ubiquen en el módulo de Pagos (sin ensuciar Compras).

#### Criterios de Aceptación:
1. `documentos_nuevos` clasifica los comprobantes de tipo `recibo` y los asigna al módulo `pagos` (visible en `/finanzas/recibos-pagos`).
2. Extrae CUIT de emisor, número de recibo, fecha e importe total cancelado.
3. El recibo queda pendiente de asignación con visualización de su PDF original.

---

### Historia 3 (P1): Vinculación y Aplicación del Recibo
Como usuario, quiero vincular un recibo oficial contra una Orden de Pago o contra débitos bancarios/caja existentes y facturas, para cerrar la cuenta corriente con respaldo documental.

#### Criterios de Aceptación:
1. Si existe una OP emitida que coincide con el importe o facturas del recibo, el sistema sugiere vincularla con un solo click.
2. Si no hay OP previa, permite aplicar el recibo seleccionando el/los movimientos financieros reales de salida de fondos y las facturas de compra que cancela.
3. Genera o confirma los registros en `dbo.AplicacionesPago` y adjunta la ruta del PDF del recibo para auditoría permanente.
4. El aviso en `DocumentosNuevos` pasa a `revisado`.

---

### Historia 4 (P1): Retención de Ganancias RG 830 en la Orden de Pago (agregada 30/10/2026)
Como usuario financiero, quiero que la OP proponga la retención de Ganancias que corresponde y prepare el pedido al estudio contable, para no depender de calcularla a mano.

#### Criterios de Aceptación (decisiones de Sergio del 30/10/2026; detalle en [retenciones-rg830.md](retenciones-rg830.md)):
1. El sistema **solo calcula**. El certificado lo emite el Estudio Criado, y el sistema arma el borrador del mail a administracion@estudiocriado.com, con copia a rcriado@, con el formato de siempre y las facturas adjuntas. No envía nada.
2. Se aplica el criterio de AFIP: la base es neta de IVA, se suman los pagos del mes del pago al mismo proveedor y del mismo régimen, y el no sujeto se descuenta una sola vez por mes. Alícuotas, no sujeto y mínimo se toman del simulador público de ARCA. Salvedad: solo se suman los pagos del mes hechos por OP; la pantalla avisa que los pagos hechos por fuera no se incluyen.
3. La inscripción del proveedor sale del padrón público de ARCA: monotributista y exento (EX) no retienen; "no corresponde" (NC) se calcula como inscripto y se avisa.
4. El concepto sale del rubro de cada renglón de la factura. La tabla rubro → régimen es un borrador del sistema, que valida el contador y ratifica el estudio.
5. Granos, hacienda y consignatarios quedan excluidos. Los certificados de exclusión se cargan a mano, con su vigencia. Para US$ se usa el TC del comprobante (aplicará cuando la OP admita documentos en dólares; hoy solo admite pesos). Gastos de comercialización de granos, excluidos; fletes de granos, a revisión del contador.
6. Rige de acá en adelante: los pagos ya hechos con tarjeta o débito quedan como están.
7. La retención es una propuesta que confirma el usuario. Los medios de pago suman el neto (facturas menos retención).

### Historia 5 (P2): Recibos con retención o anticipo (agregada 30/10/2026)
Como usuario, quiero vincular recibos que incluyen retenciones o anticipos sin factura, sin forzar una cancelación que no corresponde.

#### Criterios de Aceptación:
1. Total del recibo = pagos aplicados + retención + anticipo.
2. Si el recibo corresponde a una OP con retención, los pagos reales cubren el neto y la retención tiene que ser la de la OP. El número de certificado es opcional (puede llegar después) y la factura se termina de cancelar con la retención cargada en Retenciones (circuito existente).
3. Un anticipo sin factura queda registrado en el recibo, sin aplicaciones. El FIFO de cuentas corrientes lo imputa después.

---

## 3. Modelo de Datos
Detalle completo en [data-model.md](data-model.md); resumen:

* `dbo.OrdenesPago`: Cabecera de OP (IdOrdenPago, Numero, IdContacto, Fecha, ImporteTotal, Estado, Observaciones, Creado, CreadoPor).
* `dbo.OrdenesPago_Detalle`: Renglones de facturas a cancelar (IdOrdenPago, IdCompra, ImporteAplicado).
* `dbo.OrdenesPago_Medios`: Medios de pago previstos (IdOrdenPago, Medio, Cuenta, Importe).
* `dbo.RecibosProveedores`: Registro del recibo oficial (IdRecibo, IdContacto, Numero, Fecha, Total, RutaPdf, Sha256, IdOrdenPago, Retencion, Anticipo, CertificadoRetencion).
* `dbo.RecibosProveedores_Aplicaciones` y `dbo.OrdenesPago_Auditoria`: vínculo recibo↔aplicación y auditoría.
* `dbo.OrdenesPago_Retenciones` y `OrdenesPago.RetencionGanancias`: retención confirmada por régimen.
* `dbo.RetencionesGanancias_Padron`, `_Conceptos` (rubro → régimen) y `_Exclusiones`.

---

## 4. Pruebas y Validación
* Creación y edición de una Orden de Pago con múltiples facturas de compra.
* Detección automática de un PDF de recibo real (ej. Baya Casal o Sancor) y verificación de que **no** ingresa a Compras.
* Vinculación completa y comprobación de que el saldo de las facturas en cuenta corriente queda saldado.

