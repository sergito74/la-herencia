# Feature Specification: Descarga de comprobantes de peajes

**Feature Branch**: `037-descarga-peajes`

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Módulo 'Descarga de comprobantes de peajes': integrar en la aplicación La Herencia el script backend/scripts/descargar_peajes.py (commit 663a8ba) para poder disparar la descarga desde un botón en el menú de la app, además de la tarea semanal. Portales: TelepeajePlus, TelePASE, CEAMSE y AUBASA (acceso de solo lectura/descarga autorizado por Sergio el 2026-10-16). Botón 'Descargar ahora' con progreso y resultado por portal; historial de ejecuciones; abrir cada PDF; indicar si cada documento ya está cargado en Compras y ofrecer cargarlo con el archivo precargado; estado de credenciales por portal sin mostrar contraseñas; evitar ejecuciones simultáneas; próxima corrida semanal. Solo usuarios que pueden dar de alta compras. No carga datos automáticamente en WC más allá del registro de ejecuciones."

## Contexto

Hoy existe un proceso de descarga que entra a cuatro portales de peaje (TelepeajePlus, TelePASE, CEAMSE y AUBASA) y guarda en la carpeta de Compras de Dropbox los resúmenes y facturas nuevos, con el nombre estándar `AAAAMMDD_Proveedor.pdf`, en la carpeta del ejercicio (abril a marzo). Lleva una lista de documentos ya descargados para no repetirlos y está pensado para correr una vez por semana como tarea programada de Windows. Su resultado no se ve en la aplicación: hay que abrir la carpeta o un archivo de registro. Este módulo lo lleva a la aplicación, como parte del proceso de Compras, y lo convierte en una sincronización: descargar cada comprobante nuevo y registrarlo automáticamente en Compras.

El acceso a los portales es de solo lectura y descarga, autorizado explícitamente por Sergio el 2026-10-16. El módulo no paga, no modifica datos en los portales y no acepta nada en ellos.

## Clarifications

### Session 2026-10-16

- Q: ¿Los comprobantes descargados se cargan solos en Compras y, si es así, quedan firmes o con marca de revisión? → A: Se cargan automáticamente y quedan firmes, sin revisión; solo se registra en el historial qué se cargó. Condición: solo se carga si lo leído del PDF cierra exacto contra el total impreso y el formato es reconocido; si no, queda pendiente con el motivo para carga manual.
- Q: ¿Dónde se carga la percepción de IVA (RG 3337 / 3 %) que traen AUSOL, CEAMSE, AUSA y AUBASA? (hallazgo de la revisión de dirección financiera) → A: En el campo Percepción IVA de la compra, desde este módulo en adelante (es crédito fiscal); lo cargado históricamente en Ingresos Brutos no se modifica.
- Q: ¿Cómo se entera el usuario de pendientes o errores? → A: Con un número en el menú, en "Descarga de peajes", que cuenta los documentos pendientes de carga manual y los portales con error sin resolver.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Descargar ahora desde la aplicación (Priority: P1)

Un usuario con permiso para dar de alta compras entra a "Compras › Descarga de peajes" y aprieta "Descargar ahora". La aplicación inicia la descarga en segundo plano y muestra, portal por portal, en qué estado está (pendiente, en curso, terminado, con error). Al terminar muestra cuántos documentos nuevos se bajaron, cuántos ya estaban y qué errores hubo, con el nombre y la carpeta de cada archivo nuevo.

**Why this priority**: Es el pedido central: no depender de la tarea semanal ni de correr nada a mano para traer los comprobantes.

**Independent Test**: Con las credenciales configuradas, apretar el botón y verificar que los documentos nuevos aparezcan en la carpeta del ejercicio con el nombre estándar y que el resultado en pantalla coincida con lo bajado.

**Acceptance Scenarios**:

1. **Given** no hay ninguna descarga en curso y las credenciales están configuradas, **When** el usuario aprieta "Descargar ahora", **Then** la descarga empieza, la pantalla muestra el avance por portal y al terminar lista los documentos nuevos (fecha, proveedor, nombre de archivo, carpeta).
2. **Given** los portales no tienen documentos nuevos, **When** termina la descarga, **Then** la pantalla informa "sin documentos nuevos" por portal y no se escribe ningún archivo.
3. **Given** un portal está caído o rechaza el ingreso, **When** se ejecuta la descarga, **Then** ese portal queda marcado con error y un mensaje legible, y los demás portales se procesan igual.
4. **Given** ya hay una descarga en curso (manual o semanal), **When** alguien aprieta "Descargar ahora", **Then** la aplicación no inicia otra, avisa que hay una en curso y muestra su avance.
5. **Given** el usuario tiene rol de solo lectura, **When** entra a la pantalla, **Then** ve el historial y el estado, pero el botón "Descargar ahora" no está disponible.

---

### User Story 2 - Carga automática en Compras (Priority: P1)

Cada documento nuevo que se baja (manual o semanal) se registra solo en Compras, igual que se carga a mano hoy: proveedor fijo según el portal y el concesionario, Factura A, número de comprobante, fecha, renglones por tipo de pasada (cantidad, precio, IVA), percepción de IIBB, conceptos no gravados y sellos según corresponda, rubro Viáticos, centro de costo y destino habituales, y el PDF como documento original. Solo se carga si la suma de lo leído cierra exacto con el total impreso y no existe ya una compra con ese proveedor y número. Si no, el documento queda "pendiente de carga manual" con el motivo. La carga queda firme, sin paso de revisión.

**Why this priority**: Es una sincronización: el valor está en que los comprobantes de peaje estén en el sistema sin trabajo manual.

**Independent Test**: Con un documento nuevo de cada formato, ejecutar la descarga y verificar que se creó la compra con los mismos datos que tendría una carga manual y con el total igual al impreso.

**Acceptance Scenarios**:

1. **Given** una factura nueva de formato reconocido cuyo detalle cierra con el total impreso, **When** termina la descarga, **Then** existe una compra nueva con proveedor, número, fecha, renglones, impuestos y PDF correctos, y el historial la muestra como "cargada automáticamente".
2. **Given** un documento cuya lectura no cierra con el total impreso (o de formato no reconocido), **When** termina la descarga, **Then** no se crea ninguna compra y el documento figura "pendiente de carga manual" con el motivo.
3. **Given** ya existe una compra del mismo proveedor con el mismo número, **When** se procesa el documento, **Then** no se crea otra y el documento figura "ya cargado" con acceso a esa compra.
4. **Given** un documento pendiente, **When** el usuario elige "Cargar en Compras", **Then** se abre el alta de Compras con el proveedor y el documento original precargados.
5. **Given** cualquier documento de la lista, **When** el usuario elige "Ver PDF", **Then** se abre con el visor de documentos que ya usa Compras; si el archivo no está, se informa sin error técnico.

---

### User Story 3 - Historial de ejecuciones (Priority: P2)

El usuario ve el historial de ejecuciones: fecha y hora, origen (manual, con el usuario que la disparó, o semanal), duración, resultado por portal y los documentos bajados en cada una. Las corridas semanales aparecen igual que las manuales.

**Why this priority**: Permite comprobar que la rutina semanal funciona y rastrear cuándo y cómo llegó cada comprobante (trazabilidad).

**Independent Test**: Ejecutar una descarga manual y una disparada por la tarea semanal, y verificar que las dos aparecen en el historial con su origen y su detalle.

**Acceptance Scenarios**:

1. **Given** hubo ejecuciones manuales y semanales, **When** el usuario abre el historial, **Then** las ve ordenadas de la más reciente a la más vieja, con origen, usuario (si fue manual), duración y resultado por portal.
2. **Given** una ejecución con errores, **When** el usuario la abre, **Then** ve el mensaje de error de cada portal afectado.

---

### User Story 4 - Estado de la configuración (Priority: P3)

En la misma pantalla, el usuario ve por portal si las credenciales están configuradas o faltan, y si la tarea semanal está instalada, con la fecha y hora de la próxima corrida. Si algo falta, la pantalla indica que hay que correr el instalador. Nunca se muestran contraseñas ni usuarios completos.

**Why this priority**: Evita descargas que fallan sin explicación; hoy el instalador todavía no se corrió.

**Independent Test**: Antes de correr el instalador, la pantalla muestra los cuatro portales "sin configurar" y la tarea "no instalada"; después del instalador, todos "configurados" y la próxima corrida.

**Acceptance Scenarios**:

1. **Given** faltan las credenciales de un portal, **When** se abre la pantalla, **Then** ese portal figura "sin configurar" y "Descargar ahora" avisa que ese portal se va a saltear.
2. **Given** la tarea semanal está instalada, **When** se abre la pantalla, **Then** se muestra la fecha y hora de la próxima corrida.
3. **Given** la tarea semanal no está instalada, **When** se abre la pantalla, **Then** se indica "no instalada" con la instrucción para correr el instalador.

---

### Edge Cases

- Un portal cambia su página de ingreso o su formato y la descarga no reconoce los documentos: el portal queda en error con un mensaje que indica que puede haber cambiado, sin afectar a los demás.
- Un portal pide un código adicional o captcha: error claro de "requiere ingreso manual".
- La descarga se corta a mitad de camino (corte de red o cierre de la aplicación): los archivos ya guardados quedan registrados y la próxima ejecución no los repite; la ejecución interrumpida queda marcada como incompleta.
- Ya existe un archivo con el mismo nombre en la carpeta: se guarda con el sufijo " 001", " 002"... como hoy, y nunca se pisa un archivo existente.
- Un documento cuya fecha pertenece a otro ejercicio: se guarda en la carpeta de ese ejercicio, que se crea si no existe.
- La carpeta de Dropbox no está disponible: la ejecución termina con error general antes de entrar a los portales.
- Un documento que no es PDF válido: no se guarda, queda como error y no se marca como descargado, para reintentarlo la próxima vez.
- La tarea semanal arranca mientras hay una descarga manual en curso: no inicia otra y queda registrada como salteada.
- Concesionario nuevo sin nombre estándar: se guarda con el nombre del portal y queda un aviso en el resultado de la ejecución.
- Dos pedidos de "Descargar ahora" casi simultáneos: solo uno inicia la descarga; el otro recibe el aviso de que hay una en curso (nunca dos respuestas de "iniciada").
- La simulación (dry-run) no deja rastro: no crea ejecuciones, documentos, archivos ni compras.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST ofrecer en el menú de Compras una pantalla "Descarga de peajes" con el estado de la configuración, la ejecución en curso (si hay) y el historial.
- **FR-002**: El sistema MUST permitir iniciar una descarga ("Descargar ahora") solo a usuarios con permiso de alta de Compras; los usuarios de solo lectura ven la pantalla sin el botón, y el servidor rechaza el pedido si igual llega.
- **FR-003**: La descarga MUST ejecutarse en segundo plano sin bloquear la aplicación, procesando TelepeajePlus, TelePASE, CEAMSE y AUBASA de forma independiente: el error de un portal no impide procesar los demás.
- **FR-004**: La pantalla MUST mostrar el avance de la ejecución en curso por portal (pendiente, en curso, terminado, error) y actualizarlo sin que el usuario recargue la página.
- **FR-005**: El sistema MUST impedir dos ejecuciones simultáneas, sean manuales o semanales; un pedido mientras hay otra en curso se informa y no inicia nada nuevo.
- **FR-006**: La descarga MUST conservar las reglas actuales: solo lectura en los portales, nombre `AAAAMMDD_Proveedor.pdf` con sufijo " 001"... si el nombre existe, carpeta del ejercicio abril-marzo, nunca pisar un archivo, solo guardar PDF válidos y no repetir documentos ya descargados (incluidos los 98 marcados al 2026-10-16).
- **FR-007**: El sistema MUST registrar cada ejecución con fecha/hora de inicio y fin, origen (manual o semanal), usuario si fue manual, estado final (completa, con errores, incompleta, salteada) y, por portal, cantidad de documentos nuevos, ya existentes y mensaje de error.
- **FR-008**: El sistema MUST registrar cada documento bajado con su portal, proveedor, fecha del documento, identificador en el portal, nombre de archivo, ruta completa y ejecución que lo bajó.
- **FR-009**: La ejecución semanal MUST usar el mismo proceso y el mismo registro que la manual, para que ambas aparezcan igual en el historial.
- **FR-010**: Para cada documento bajado, el sistema MUST indicar su estado de carga: "cargado automáticamente", "ya cargado" (una compra existente lo tiene como documento original o coincide proveedor y número) o "pendiente de carga manual" con el motivo, y dar acceso a la compra cuando exista.
- **FR-011**: Para cada documento pendiente, el sistema MUST ofrecer "Cargar en Compras", que abre el alta de Compras con el documento original y el proveedor precargados.
- **FR-017**: El sistema MUST cargar automáticamente en Compras cada documento nuevo de formato reconocido, con los mismos criterios que la carga manual actual de ese proveedor (contacto fijo, tipo y número de comprobante, fecha, renglones por concepto con cantidad, precio e IVA, percepción de IIBB, conceptos no gravados, sellos, rubro, centro de costo, destino y documento original), usando las mismas validaciones que el alta de Compras.
- **FR-018**: La carga automática MUST hacerse solo si el total calculado con lo leído coincide con el total impreso del comprobante (diferencia máxima $0,05: redondeo por renglón de los proveedores; verificado 2026-10-16 en AUSOL $0,01 y AUBASA $0,02 contra cargas manuales idénticas) y no existe una compra del mismo proveedor con el mismo número; en cualquier otro caso no crea nada y deja el documento pendiente con el motivo.
- **FR-020**: El menú MUST mostrar junto a "Descarga de peajes" un contador con la cantidad de documentos pendientes de carga manual más los portales con error en la última ejecución; el contador baja cuando el documento queda cargado (por cualquier vía) o una ejecución posterior del portal termina bien, y no se muestra si es cero.
- **FR-019**: Las compras cargadas automáticamente quedan firmes (sin estado de revisión) y el registro de la ejecución MUST guardar qué compra creó cada documento.
- **FR-012**: El sistema MUST permitir abrir cada PDF bajado con el visor de documentos locales que ya usa Compras, e informar claramente si el archivo no se encuentra.
- **FR-013**: El sistema MUST mostrar por portal si las credenciales están configuradas, sin mostrar nunca contraseñas, y MUST NOT permitir cargarlas ni verlas desde la aplicación (se cargan con el instalador).
- **FR-014**: El sistema MUST mostrar si la tarea semanal está instalada y la fecha y hora de su próxima corrida.
- **FR-015**: Las credenciales, contraseñas y datos de sesión de los portales MUST NOT guardarse en la base, en archivos del repositorio ni en los registros de ejecución.
- **FR-016**: El módulo MUST NOT crear en la base otros datos de negocio además de las compras de FR-017 (no pagos, no conciliaciones, no contactos nuevos) y el registro de ejecuciones y documentos bajados.

### Key Entities

- **Ejecución de descarga**: una corrida del proceso. Fecha/hora de inicio y fin, origen (manual/semanal), usuario que la disparó, estado final, resultado por portal (nuevos, existentes, error).
- **Documento descargado**: un PDF bajado por una ejecución. Portal, proveedor (nombre estándar), fecha del documento, identificador en el portal, nombre de archivo, ruta, ejecución de origen, total impreso, estado de carga (cargado automáticamente / ya cargado / pendiente), motivo si quedó pendiente y compra asociada.
- **Portal**: TelepeajePlus, TelePASE, CEAMSE, AUBASA. Estado de credenciales (configuradas/faltantes) y mapeo de concesionarios a nombres de proveedor estándar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Desde la pantalla, una descarga completa de los cuatro portales se inicia con un clic y termina en menos de 5 minutos en condiciones normales.
- **SC-002**: El 100 % de los documentos nuevos de los cuatro portales queda en la carpeta del ejercicio correcta con el nombre estándar, sin duplicar documentos ya existentes.
- **SC-003**: Al menos el 95 % de los documentos nuevos de formato reconocido queda cargado en Compras sin intervención, y el 100 % de las compras cargadas solas tiene un total igual al impreso.
- **SC-007**: El usuario puede saber en menos de 30 segundos qué documentos quedaron pendientes de carga manual y por qué.
- **SC-004**: El 100 % de las ejecuciones, manuales y semanales, quedan en el historial con su origen y resultado.
- **SC-005**: En ningún caso aparece una contraseña en pantalla, en la base o en los registros.
- **SC-006**: Nunca corren dos descargas al mismo tiempo, aunque se aprieten varios botones o coincida con la tarea semanal.

## Assumptions

- La aplicación (backend) corre en la misma PC donde están la carpeta de Dropbox, el navegador usado para la descarga y las credenciales de Windows; es la configuración actual del lanzador de escritorio.
- Las credenciales siguen cargándose con el instalador PowerShell existente; la aplicación solo consulta si existen.
- La tarea semanal la instala el mismo instalador, ajustado para que ejecute el proceso con origen "semanal" y su resultado quede en el mismo registro.
- El registro de ejecuciones y documentos bajados se guarda en tablas nuevas de `WC` (con nombres propios del módulo, sin reusar nombres existentes), creadas con respaldo previo.
- La lista de documentos ya descargados actual (98 claves) se migra al nuevo registro sin volver a bajarlos. El archivo `_descargas_portales.log` deja de escribirse: el registro pasa a la base.
- "Permiso de alta de Compras" es el mismo criterio de roles que hoy oculta los botones de alta a los usuarios de solo lectura.
- El proveedor sugerido para "Cargar en Compras" sale de un mapeo nombre estándar → contacto; si no hay un contacto claro, el alta se abre sin proveedor.
- Los formatos a reconocer son los de los proveedores actuales: resumen de Telepeaje (se carga en $0 con sellos, como hoy), Autopistas del Sol, GCO, AUSA, Corredores Viales, Corresur, CV5/Pentavia, CEAMSE y AUBASA; todos traen texto legible (no son escaneos).
- Un concesionario nuevo sin proveedor asignado queda pendiente de carga manual; no se crean contactos solos.
- Fuera de alcance: otros portales, pagos y conciliación de los débitos, y edición de credenciales desde la aplicación.
