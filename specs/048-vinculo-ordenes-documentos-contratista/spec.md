# Feature Specification: Vínculo de órdenes de trabajo con documentos del contratista

**Feature Branch**: `main` (sin rama propia, como las specs 043-047)

**Created**: 2026-11-06 · **Revisada**: 2026-11-06 (simplificación pedida por Sergio)

**Status**: Draft

**Input**: User description: "No funciona el vínculo desde la orden de trabajo con los documentos comerciales (Facturas, Notas de Débito y Crédito) del contratista que ejecutó la orden. El objetivo es no tener que imputar manualmente los documentos comerciales a cada Cultivo / Campaña, sino que el sistema lo haga automáticamente para luego imputar los costos a los Costos / Resultados de los cultivos y al Flujo de Caja." (Sergio, 06/11/2026)

## Contexto y diagnóstico (verificado en WC el 06/11/2026)

- La orden de trabajo pide tipear un número interno de compra para vincular la factura. Es inusable y contradice la premisa "interfaz sin cosas internas".
- Nunca se vinculó ningún documento: 0 vínculos para 152 órdenes ejecutadas. Access tampoco tenía este vínculo.
- Vincular no genera la imputación automática por cultivo/campaña: hay 0 imputaciones de contratista.
- El Resultado por cultivo busca los vínculos en un registro viejo (vacío), distinto del que escribe la orden, y toma el cultivo/campaña cargado a mano en cada renglón.
- Hay 12 contratistas con órdenes desde 2015; 91 facturas de labor y 6 NC (ninguna relacionada con su factura).

## Decisiones tomadas (Sergio, 06/11/2026)

- **D1 El vínculo se hace en Compras**: en el formulario de la factura del contratista se tildan sus órdenes de trabajo. La NC/ND se relaciona con su factura en el panel "Documentos relacionados" que ya existe. La orden de trabajo NO vincula: solo muestra esos vínculos, y el Resultado los usa. (Reemplaza la versión anterior con propuestas, pantalla de revisión y descartes, que Sergio descartó por complicada.)
- **D2 NC/ND siguen a su factura**: se imputan igual (cultivos, campañas y proporción) que la factura que corrigen.
- **D3 Alcance histórico**: aplica a cualquier factura, de cualquier fecha, al vincularla.
- **D4 Flujo de Caja fuera de alcance**: queda como está.

## Clarifications

### Session 2026-11-06

- Q: Cuando la factura trae renglones que no son la labor (flete, traslado, gasoil), ¿qué se reparte? → A: El neto de la factura por la superficie de las órdenes, salvo los renglones de insumos y otros negocios (FR-004).
- Q: ¿Qué pasa con las facturas del contratista sin orden? → A: Suman al costo según su imputación cargada a mano y se ven en un listado propio. En adelante no puede pasar: una factura nueva de labor de un contratista debe tener orden.
- Q: ¿Quién puede vincular? → A: Cualquier usuario con permiso de carga; los de solo lectura solo miran.
- Q: ¿Desde dónde se vincula? → A: Desde el formulario de Compras (D1).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vincular la factura con sus órdenes desde Compras (Priority: P1) 🎯

Al cargar o editar una factura de labor de un contratista, el formulario muestra las órdenes de trabajo ejecutadas de ese contratista (fecha, labor, lotes, hectáreas), de la más nueva a la más vieja, con las que todavía no tienen factura primero. El usuario tilda las que corresponden y guarda la compra.

**Independent Test**: editar la factura 00002-00000735 de Pérez (05/11/2026, 198 ha), tildar la orden del 25/10/2026 (198 ha) y guardar: queda vinculada.

**Acceptance Scenarios**:

1. **Given** una factura de un contratista con órdenes, **When** se abre el formulario, **Then** se ve la lista tildable de sus órdenes, sin números internos.
2. **Given** una factura de labor nueva sin ninguna orden tildada, **When** se guarda, **Then** el formulario avisa "Factura de contratista sin orden de trabajo" y pide confirmar; queda en el listado de facturas sin orden.
3. **Given** una NC/ND del contratista, **Then** no muestra órdenes: se relaciona con su factura en "Documentos relacionados".

---

### User Story 2 - La orden muestra sus documentos y el Resultado los imputa solo (Priority: P1)

La orden de trabajo muestra, en solo lectura, las facturas y las NC/ND vinculadas (número, fecha, neto) con enlace a la compra, y el reparto por lote/cultivo/campaña. El Resultado por cultivo toma ese reparto en lugar de la carga manual de esos documentos.

**Independent Test**: tras US1, abrir la orden del 25/10/2026: muestra la factura 00002-00000735 y su reparto; en el Resultado, el cultivo/campaña muestra el costo desde la orden y la factura no cuenta además por su carga manual.

**Acceptance Scenarios**:

1. **Given** una factura vinculada a varias órdenes, **Then** se reparte por la superficie de todas ellas y la suma cierra al centavo.
2. **Given** una NC relacionada con una factura vinculada, **Then** se imputa en los mismos cultivos/campañas y proporción, con su signo, y se ve en la orden.
3. **Given** una factura en dólares, **Then** se usa el tipo de cambio del comprobante.
4. **Given** que se destilda la orden en la factura, **Then** la imputación se retira y vuelve a contar la carga manual.

---

### User Story 3 - Listado de facturas de labor sin orden (Priority: P2)

Un listado (con exportación a Excel) de las facturas de labor de contratistas sin orden vinculada, con sus renglones y el cultivo/campaña cargado a mano, con enlace a la compra para vincularla.

**Independent Test**: el listado muestra las facturas de labor sin vínculo (hoy 91) y no incluye la factura de hacienda de Yanquelen.

### Edge Cases

- Una factura que cubre varias órdenes, y una orden con varias facturas (anticipo + saldo).
- Orden anulada después del vínculo: el vínculo se retira y la imputación se recalcula.
- Corrección de hectáreas en la orden: el reparto se recalcula.
- Orden de un rubro sin cultivo: va al centro de costo de la orden (imputación 017).
- Contratista "Giamigli de Bolívar" (maquinaria propia, sin documentos): nada que vincular.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El formulario de Compras MUST mostrar, para una factura de labor de un contratista, la lista tildable de sus órdenes de trabajo ejecutadas (fecha, labor, lotes, hectáreas; las que no tienen factura primero), sin identificadores internos, y guardar los vínculos tildados junto con la compra.
- **FR-002**: Son "documentos de labor" los que tienen al menos un renglón de un rubro de labor: Fumigación, Siembra, Cosecha, Fertilización, Disqueado, Embolsado de grano. Solo a ellos se les ofrecen órdenes.
- **FR-003**: Las NC/ND MUST relacionarse con su factura en el panel "Documentos relacionados" existente; no se vinculan a órdenes.
- **FR-004**: Al guardar los vínculos, el sistema MUST imputar de inmediato el documento por lote/cultivo/campaña según la superficie de las órdenes vinculadas. Se reparte el neto de los renglones que no son de los rubros Semillas, Fertilizantes, Agroquímicos, Hacienda, Trabajos Maq. Propia ni Gastos de Comercialización (esos siguen con su imputación propia). Cierra al centavo.
- **FR-005**: Las NC/ND relacionadas con una factura vinculada MUST imputarse con las mismas proporciones y su signo (D2).
- **FR-006**: La orden de trabajo MUST mostrar en solo lectura sus documentos vinculados (y las NC/ND relacionadas) con enlace a la compra y su reparto; no permite vincular ni desvincular.
- **FR-007**: El Resultado por cultivo MUST tomar el costo de contratista del reparto, y MUST excluir para esos documentos exactamente los renglones repartidos de la carga manual (sin doble conteo). Los documentos no vinculados siguen contando como hoy.
- **FR-008**: MUST existir un listado (y exportación a Excel) de facturas de labor de contratistas sin orden, con renglones, cultivo/campaña cargado a mano y enlace a la compra.
- **FR-009**: Guardar una factura de labor de un contratista sin órdenes MUST mostrar un aviso que hay que confirmar. El aviso no bloquea (la deuda se tiene que poder registrar); la factura queda en el listado "sin orden" (FR-008) hasta vincularla. Así se cumple "en adelante no puede pasar" sin impedir la carga.
- **FR-010**: Los saldos de cuentas corrientes MUST quedar iguales al centavo.
- **FR-011**: El vínculo MUST registrar quién y cuándo lo guardó.
- **FR-012**: Solo los usuarios con permiso de carga pueden vincular (el formulario de Compras ya lo respeta).

### Key Entities

- **Orden de trabajo**: labor ejecutada por un contratista, con distribución por lote/cultivo/campaña y superficie.
- **Documento del contratista**: factura, NC o ND, con renglones, moneda y tipo de cambio.
- **Vínculo factura–orden**: muchos a muchos, guardado desde Compras.
- **Documento relacionado**: NC/ND ↔ factura (existente).
- **Reparto (imputación)**: porción del neto repartible asignada a cada lote/cultivo/campaña.

## Success Criteria *(mandatory)*

- **SC-001**: Vincular una factura con sus órdenes toma menos de 30 segundos desde el formulario de Compras, sin conocer ningún número interno.
- **SC-002**: El 100% de los documentos vinculados queda imputado sin carga manual, y el reparto suma el neto repartible al centavo.
- **SC-003**: El costo de contratista de una campaña no cambia por doble conteo (total antes = después, salvo repartos entre cultivos, que se listan).
- **SC-004**: Ningún saldo de cuenta corriente cambia.

## Assumptions

- Se reutiliza la imputación 017 para el reparto y el centro de costo.
- La tabla vieja de vínculos (vacía) se deja de usar.
- El panel "Documentos relacionados" de Compras ya existe y se reutiliza para NC/ND.
- Todo se escribe en la base WC.
