# Feature Specification: Lector general de facturas electrónicas

**Feature Branch**: `047-lector-general-facturas`
**Created**: 2026-11-02
**Status**: Cancelada por Sergio (02/11/2026): se sigue con carga manual salvo los lectores ya armados. Simulación: 29 de 347 cargables, 28 coincidentes. Queda sin uso la columna Rutina_Programacion.LectorGeneralActivo.
**Input**: Pedido de Sergio: que las facturas nuevas se carguen solas sin un lector por proveedor, y que todo documento nuevo quede marcado para revisión.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Factura de proveedor conocido se carga sola (Priority: P1)

Llega una factura electrónica de un proveedor con imputación habitual. El sistema la lee, valida y carga en Compras sin intervención, y Sergio solo la revisa.

**Why this priority**: es el objetivo: dejar de cargar a mano lo que se puede deducir con certeza.

**Independent Test**: procesar una factura válida de un proveedor con historial inequívoco y comprobar que queda cargada, con el archivo vinculado y pendiente de revisión.

**Acceptance Scenarios**:

1. **Given** una factura dirigida a Giamigli, de emisor existente, con importes que cierran e imputación habitual, **When** la rutina la procesa, **Then** queda cargada en Compras y aparece en "Nuevos para revisar".
2. **Given** la misma factura llega de nuevo por otra vía, **When** se procesa, **Then** no se duplica la carga.
3. **Given** un proveedor con lector específico probado, **When** llega su factura, **Then** se usa ese lector y no el general.

### User Story 2 - Todo documento nuevo queda para revisión (Priority: P1)

Sergio ve en una sola lista cada documento nuevo, cargado solo o no, y puede controlar contacto, imputación e importes, abrir el archivo, corregir y marcarlo como revisado.

**Why this priority**: requisito clave de Sergio; la carga automática solo es aceptable si todo se revisa.

**Independent Test**: procesar un documento cargado solo y uno no cargado; ambos aparecen pendientes hasta marcarlos revisados.

**Acceptance Scenarios**:

1. **Given** un documento cargado solo, **When** Sergio abre "Nuevos para revisar", **Then** ve proveedor, comprobante, fecha, importes, imputación aplicada y acceso al archivo y a la carga.
2. **Given** un documento revisado, **When** vuelve a correr la rutina, **Then** no reaparece como pendiente.
3. **Given** una carga incorrecta, **When** Sergio la corrige desde la lista, **Then** la corrección queda guardada y el documento puede marcarse revisado.

### User Story 3 - Lo que no es seguro queda para cargar a mano (Priority: P2)

Si falta una condición, el sistema no adivina: guarda el documento, no carga nada y explica el motivo en palabras de negocio.

**Why this priority**: una carga errónea daña las cuentas conciliadas; es peor que una carga manual.

**Independent Test**: procesar facturas con total que no cierra, emisor inexistente e imputación ambigua; ninguna se carga y cada una muestra su motivo.

**Acceptance Scenarios**:

1. **Given** importes que no cierran al centavo, **When** se procesa, **Then** no se carga y el motivo lo indica.
2. **Given** un emisor que no está en Contactos, **When** se procesa, **Then** no se crea el contacto y el motivo pide darlo de alta.
3. **Given** un proveedor con varias imputaciones posibles, **When** se procesa, **Then** queda a mano con el motivo correspondiente.

### Edge Cases

- PDF sin código QR o con QR ilegible: se usa el texto; si los datos no alcanzan, queda a mano.
- QR y texto discrepan en emisor, número, fecha o total: queda a mano.
- Comprobante de Ganadera San Justo: no se registra ni se guarda.
- Comprobante en US$: se lleva en dólares al TC del comprobante; sin TC impreso, queda a mano.
- Nota de crédito o débito sin factura asociada identificable: queda a mano.
- Varios comprobantes en un PDF: queda a mano salvo lector específico.
- Factura escaneada sin texto ni QR legible: queda a mano.
- Cuenta de proveedor cerrada: se carga y la revisión lo advierte.
- Compra a nombre de Sergio: sigue las reglas vigentes; se avisa en la revisión.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE leer facturas, notas de débito y notas de crédito electrónicas llegadas por portal, mail o carpeta, sin programar cada proveedor.
- **FR-002**: El sistema DEBE tomar los datos del código fiscal del comprobante cuando exista y complementarlos con su texto.
- **FR-003**: Los lectores específicos existentes DEBEN tener prioridad sobre el lector general.
- **FR-004**: Solo se DEBE cargar solo si se cumplen todas: emisor existente, dirigido a la empresa según reglas vigentes, importes que cierran al centavo, no duplicado e imputación habitual inequívoca.
- **FR-005**: El sistema NUNCA DEBE crear contactos.
- **FR-006**: Neto, IVA por alícuota, percepciones, conceptos no gravados y total DEBEN sumar exactamente el total impreso.
- **FR-007**: La imputación habitual DEBE deducirse de cargas anteriores del proveedor; es inequívoca solo si las últimas 3 facturas del proveedor tienen la misma imputación (decisión de Sergio, 02/11/2026); con menos de 3 o con alguna distinta, NO se carga.
- **FR-008**: Si el rubro requiere cultivo o campaña, DEBE aplicarse solo cuando el historial lo determine sin ambigüedad.
- **FR-009**: Todo documento nuevo, cargado solo o no, DEBE quedar pendiente en "Nuevos para revisar" hasta que un usuario lo marque revisado.
- **FR-010**: La revisión DEBE mostrar contacto, comprobante, fecha, importes e imputación, y dar acceso al archivo y a la carga para corregirla.
- **FR-011**: Lo que no se cargue DEBE quedar guardado con un motivo en palabras de negocio.
- **FR-012**: Los comprobantes de Ganadera San Justo DEBEN seguir bloqueados.
- **FR-013**: Los comprobantes en dólares DEBEN seguir la regla del TC del comprobante.
- **FR-014**: Las pantallas NO DEBEN mostrar términos internos.
- **FR-015**: El sistema DEBE permitir procesar el historial en modo simulación, sin escribir, para comparar con cargas manuales antes de activar la carga real.

### Key Entities

- **Comprobante leído**: emisor, receptor, tipo, número, fecha, moneda, TC, importes, CAE.
- **Imputación habitual**: rubro y destino repetidos en las cargas del proveedor.
- **Documento nuevo**: archivo, origen, estado, motivo, carga vinculada y marca de revisión.

## Success Criteria *(mandatory)*

- **SC-001**: En la simulación sobre facturas ya cargadas, el 100% de las que el sistema cargaría coincide al centavo y en imputación con la carga manual.
- **SC-002**: Al menos el 70% de las facturas electrónicas de proveedores con historial se cargan sin intervención.
- **SC-003**: El 100% de los documentos nuevos aparece en la lista de revisión.
- **SC-004**: Cero duplicados y cero contactos creados por el lector.
- **SC-005**: Cada documento no cargado explica su motivo sin términos internos.

## Assumptions

- Sigue el filtro de mails vigente desde el 02/11/2026.
- La rutina y sus horarios (043) no cambian.
- Recibos, boletas, resúmenes y liquidaciones quedan fuera de alcance.
- Una carga automática se corrige con la pantalla normal de Compras.
- Los 2 motivos de pendiente existentes se mantienen salvo que el lector cargue el documento.
