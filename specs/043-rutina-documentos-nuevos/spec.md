# Feature Specification: Rutina automática de documentos nuevos

**Feature Branch**: `043-rutina-documentos-nuevos`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "Rutina programada que sincroniza las cuentas automatizadas de la bóveda (incluida la nueva De Campo a Campo), lee los mails nuevos, carga los documentos faltantes y deja en los menús correspondientes (Compras, Impuestos, Ventas, etc.) un aviso con los documentos nuevos para revisar; al hacer clic lleva al módulo mostrando el documento cargado. Reemplaza el listado de revisión que se había puesto en la pantalla de la bóveda."

## Contexto

- La bóveda de portales (042) ya baja documentos de las cuentas automatizadas y, para algunas (peajes, Allianz, Movistar), los carga solos en Compras.
- El 27/10/2026 se agregó en la pantalla de la bóveda un listado "Cargado solo en Compras — para revisar". Sergio **no lo quiere ahí**: los avisos tienen que estar en el módulo donde vive cada documento. Ese listado se retira con esta funcionalidad.
- Regla de Sergio (27/10/2026): después de cargar documentos nuevos al sistema siempre tiene que quedar un aviso para revisar que hayan quedado bien imputados.
- Decisiones de Sergio (27/10/2026): la rutina es **solo programada** (sin botón); lee **todo mail nuevo** desde la corrida anterior, sin barrer la casilla completa; el aviso es **un número en el menú** de cada módulo; corre **todos los días a las 7:00 y a las 14:00**.
- De Campo a Campo (remates de hacienda) ya está dada de alta en la bóveda con usuario, contraseña cifrada y autorización explícita de solo lectura y descarga (27/10/2026). Falta conocer su portal y automatizarla.

## Clarifications

### Session 2026-10-27

- Q: ¿Qué hace la rutina con un PDF de mail que no es un comprobante? → A: Solo comprobantes (factura, nota de crédito/débito, boleta, liquidación, recibo, resumen de cuenta) se guardan y avisan; lo demás se ignora sin guardarse.
- Q: ¿Qué hace la rutina con un comprobante de un emisor que no está en el sistema? → A: Lo guarda y lo deja "para cargar a mano" avisando que el emisor es nuevo; el contacto lo da de alta Sergio (la rutina nunca crea contactos).
- Q: ¿Dónde se guardan y en qué menú se avisan los resúmenes de cuenta? → A: Bancos y tarjetas → carpeta `Dropbox\Giamigli de Bolivar SA\Bancos\<Banco>\<Producto>\<Año>\` (Extractos, Tarjetas\<tarjeta> o AgroNacion/Mastercard en BNA, Inversiones, Plazos Fijos, Préstamos, Corporativa; Mercado Libre en `Mercado Libre\Resumenes\<Año>`), conservando el nombre del banco y, si no es descriptivo, `Extracto AAAA MM` / `AAAA MM`; aviso en Tesorería. Proveedores, consignatarios y similares → `Documents\La Herencia\Administracion y gestion\Resumenes de Cuenta\<Proveedor>\` (sin año, nombre original); aviso en Cuentas corrientes, sobre la cuenta de ese contacto.
- Q: ¿Dónde van los contratos de venta de granos? → A: En `Documents\La Herencia\Agricultura\Contratos\` (carpeta única, sin años), con el nombre que se usa a mano: `Contrato <Comprador> <número>.pdf`, y la variante entre paréntesis cuando corresponde (`(AF Soja)`, `(Carta Fijacion)`, `(CF)`); las fijaciones sueltas como `Fijacion cto. <número>.pdf`. Aviso en Ventas. Hoy no hay un módulo de contratos: el aviso muestra el documento guardado para revisarlo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver en cada módulo los documentos nuevos y revisarlos (Priority: P1)

Sergio abre el sistema y ve, junto a "Compras", "Impuestos", "Ventas" u otro menú, un número con los documentos que el sistema incorporó solo y todavía nadie revisó. Hace clic, entra al módulo con la vista "Nuevos para revisar", ve cada documento cargado (proveedor o cliente, fecha, número, renglones con rubro y centro de costo, importes, archivo original) y, si está bien, lo marca como revisado; si está mal, lo corrige ahí mismo como cualquier otro documento del módulo. El número baja.

**Why this priority**: Es la regla de Sergio y lo que hace confiable la carga automática: sin revisión visible, lo cargado solo no se controla.

**Independent Test**: Con documentos ya cargados por las cuentas automatizadas (por ejemplo, la factura de octubre de Allianz), verificar que aparece el número en Compras, que el clic lleva al documento y que al marcarlo revisado el número baja.

**Acceptance Scenarios**:

1. **Given** hay 2 compras cargadas solas sin revisar, **When** Sergio mira el menú, **Then** ve "Compras" con el número 2.
2. **Given** el aviso de Compras, **When** hace clic, **Then** entra a Compras viendo solo los documentos nuevos para revisar, con el primero abierto.
3. **Given** un documento nuevo abierto, **When** lo marca como revisado, **Then** sale de la vista y el número del menú baja en uno.
4. **Given** un documento nuevo mal imputado, **When** lo corrige y guarda, **Then** queda corregido y sigue disponible para marcarlo como revisado.
5. **Given** un documento que el sistema no supo cargar, **When** Sergio entra a la vista de nuevos, **Then** lo ve como "para cargar a mano", con el archivo y un acceso directo para cargarlo.

---

### User Story 2 - Rutina programada que trae y carga lo nuevo (Priority: P1)

Sin que nadie apriete nada, a la hora programada el sistema sincroniza todas las cuentas automatizadas de la bóveda, lee los mails que llegaron desde la corrida anterior, guarda los documentos adjuntos en la carpeta que corresponda, carga en el sistema los que sabe leer y deja los demás marcados para cargar a mano. Todo lo nuevo queda en los avisos del menú.

**Why this priority**: Es el motor; sin él los avisos no tienen contenido. Comparte prioridad con la historia 1 porque Sergio pidió las dos partes juntas.

**Independent Test**: Forzar una corrida en el horario programado (o adelantarlo) y verificar que cada cuenta automatizada tiene una corrida nueva, que los mails nuevos con adjuntos fueron procesados una sola vez y que los documentos aparecen en los avisos.

**Acceptance Scenarios**:

1. **Given** llega la hora programada, **When** corre la rutina, **Then** sincroniza una por una todas las cuentas automatizadas con autorización vigente y contraseña cargada.
2. **Given** llegaron 5 mails desde la corrida anterior, 3 con adjuntos, **When** corre la rutina, **Then** procesa esos 3 adjuntos y no vuelve a mirar mails anteriores.
3. **Given** un documento que ya estaba en el sistema (cargado a mano o por otra vía), **When** la rutina lo encuentra de nuevo, **Then** no lo duplica ni genera aviso.
4. **Given** una cuenta que pide una verificación humana o rechaza la contraseña, **When** corre la rutina, **Then** esa cuenta queda informada en la bóveda en palabras simples y la rutina sigue con las demás.
5. **Given** la rutina terminó, **Then** en la bóveda queda registrado qué hizo cada cuenta y en los menús quedan los avisos de lo nuevo.

---

### User Story 3 - De Campo a Campo automatizada (Priority: P2)

La cuenta de De Campo a Campo baja sola sus documentos (liquidaciones de remates de hacienda u otros que ofrezca el portal) y, cuando el sistema sabe leerlos, los carga en el módulo que corresponda con la imputación que se usa al cargarlos a mano.

**Why this priority**: Amplía la cobertura; la rutina y los avisos funcionan sin ella.

**Independent Test**: Correr la cuenta y verificar que los documentos que ofrece el portal quedan guardados, sin duplicar los ya cargados, y avisados en el módulo correspondiente.

**Acceptance Scenarios**:

1. **Given** la cuenta con autorización vigente, **When** se sincroniza, **Then** ingresa, lista y baja solo lo que falta, sin operar nada en el portal.
2. **Given** un documento de De Campo a Campo ya cargado a mano, **When** se sincroniza, **Then** se vincula con el existente sin duplicar.

---

### Edge Cases

- La computadora está apagada a la hora programada: la rutina corre en cuanto vuelve a estar disponible, una sola vez, y lee los mails desde la última corrida completada.
- Outlook no está abierto o no responde: las cuentas se sincronizan igual y los mails quedan para la próxima corrida, sin perderse.
- Un mail trae varios adjuntos o el mismo documento llega por mail y por portal: se guarda y se avisa una sola vez.
- Adjuntos que no son comprobantes (logos, firmas, publicidad, presupuestos, catálogos, informes): se ignoran, no se guardan ni generan avisos.
- No se sabe a qué módulo va un documento: queda en un aviso "sin clasificar" visible para que Sergio indique dónde va.
- El comprobante es de un emisor que no está en el sistema: queda "para cargar a mano" con el aviso "emisor nuevo".
- Una corrida anterior sigue en curso: no se lanza otra encima.
- El documento se carga solo pero no cierra al centavo contra el total impreso: no se carga; queda "para cargar a mano" con el motivo en palabras simples.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST ejecutar la rutina automáticamente según una programación, sin botón manual para dispararla.
- **FR-002**: La rutina MUST sincronizar todas las cuentas automatizadas de la bóveda que tengan autorización vigente y contraseña cargada, de a una.
- **FR-003**: La rutina MUST leer solo los mails recibidos desde la última corrida completada, de cualquier remitente, sin marcarlos, moverlos, responderlos ni borrarlos.
- **FR-003b**: De los mails, la rutina MUST tomar solo los adjuntos que sean comprobantes (factura, nota de crédito o débito, boleta, liquidación, recibo, resumen de cuenta); los demás PDF se ignoran sin guardarse ni avisarse.
- **FR-004**: La rutina MUST guardar cada documento nuevo (de portal o de mail) en la carpeta que corresponde a su tipo y ejercicio, sin duplicar archivos ya guardados.
- **FR-004b**: Los resúmenes de bancos y tarjetas MUST guardarse en la carpeta de Bancos según banco, producto y año, y avisarse en Tesorería; los resúmenes de proveedores y consignatarios MUST guardarse en la carpeta de Resúmenes de Cuenta del proveedor y avisarse en Cuentas corrientes sobre la cuenta de ese contacto (ver Clarifications).
- **FR-004c**: Los contratos de venta de granos (contratos, ampliaciones, cartas de fijación) MUST guardarse en la carpeta de Contratos de Agricultura con el nombre usado a mano y avisarse en Ventas (ver Clarifications).
- **FR-005**: La rutina MUST cargar en el módulo correspondiente los documentos que el sistema sabe leer, con la misma imputación que su carga manual habitual, y solo si cierran al centavo contra el total impreso.
- **FR-006**: Los documentos que el sistema no sabe leer o que no cierran MUST quedar registrados como "para cargar a mano", con el archivo y el motivo en palabras simples.
- **FR-006b**: Si el emisor de un comprobante no está registrado en el sistema, la rutina MUST dejarlo "para cargar a mano" indicando que el emisor es nuevo; la rutina nunca da de alta contactos.
- **FR-007**: El sistema MUST mostrar en cada menú (Compras, Impuestos, Ventas y los que correspondan) la cantidad de documentos nuevos sin revisar de ese módulo.
- **FR-008**: Al hacer clic en el aviso, el sistema MUST llevar al módulo con la vista "Nuevos para revisar", mostrando el documento cargado (datos, renglones, imputación y archivo original).
- **FR-009**: Los usuarios MUST poder marcar un documento como revisado; al hacerlo deja de contarse en el aviso. Queda registrado quién y cuándo lo revisó.
- **FR-010**: Los usuarios MUST poder corregir un documento nuevo desde la vista de revisión con las mismas herramientas del módulo.
- **FR-011**: El sistema MUST retirar el listado de revisión de la pantalla de la bóveda; lo pendiente de revisar se ve solo en los módulos.
- **FR-012**: El sistema MUST automatizar la cuenta de De Campo a Campo: ingreso, listado y descarga de sus documentos, solo lectura.
- **FR-012b**: De De Campo a Campo MUST bajarse solo lo de Giamigli de Bolívar SA; no se baja ninguna información de Ganadera San Justo (Sergio, 27/10/2026).
- **FR-013**: La rutina MUST registrar, por corrida, qué hizo cada cuenta y cuántos mails y documentos procesó, visible en la bóveda en palabras simples.
- **FR-014**: Si una cuenta falla o pide verificación humana, la rutina MUST continuar con las demás e informar la cuenta afectada.
- **FR-015**: La rutina MUST correr todos los días dos veces, a las 7:00 y a las 14:00 (decisión de Sergio, 27/10/2026).
- **FR-016**: Las pantallas MUST hablar en palabras de negocio, sin términos internos del sistema.

### Key Entities *(include if feature involves data)*

- **Corrida de la rutina**: una ejecución programada; inicio, fin, resultado por cuenta, mails procesados y documentos nuevos.
- **Documento nuevo**: lo que entró por portal o mail en una corrida; origen (cuenta o mail), archivo, módulo destino, estado (cargado solo, para cargar a mano, sin clasificar), documento cargado vinculado, y revisión (quién y cuándo).
- **Mail procesado**: marca de cada mail ya leído por la rutina para no procesarlo dos veces.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sergio no necesita apretar ningún botón para que lleguen los documentos: el 100% de las corridas programadas se ejecutan solas.
- **SC-002**: Cada documento nuevo aparece en el aviso de su módulo dentro de la misma corrida en que llegó.
- **SC-003**: Desde el aviso, Sergio llega al documento cargado en un solo clic.
- **SC-004**: Ningún documento se carga dos veces ni genera dos avisos, aunque llegue por portal y por mail.
- **SC-005**: El 100% de lo que el sistema carga solo queda pendiente de revisión hasta que Sergio lo marca como revisado.
- **SC-006**: Ningún mail anterior a la última corrida completada se vuelve a procesar.

## Assumptions

- La rutina corre en la computadora de la oficina, donde están Outlook y Chrome (los portales con Chrome común y la lectura de mails lo requieren).
- "Leer mails" es solo lectura de la bandeja de entrada por Outlook; los adjuntos que se consideran documentos son PDF (y XML de comprobantes si aparecen).
- La primera corrida toma como punto de partida el momento en que se activa la rutina: no procesa mails anteriores.
- El módulo destino se decide por el tipo de documento y el contacto (factura de proveedor → Compras, boleta de impuestos → Impuestos, liquidación de venta → Ventas, resumen de banco o tarjeta → Tesorería, resumen de proveedor → Cuentas corrientes, contrato de venta de granos → Ventas); lo que no se puede decidir queda "sin clasificar".
- La revisión la hace el Administrador; los usuarios de solo lectura ven los avisos pero no marcan revisado.
- El botón "Sincronizar" existente en la bóveda se mantiene para correr una cuenta puntual; lo nuevo es que la rutina completa no tiene botón.
- Depende de la bóveda (042) y de los módulos de Compras, Impuestos y Ventas existentes.
