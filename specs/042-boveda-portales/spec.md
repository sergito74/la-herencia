# Feature Specification: Bóveda de portales y sincronización periódica

**Feature Branch**: `042-boveda-portales`

**Created**: 2026-10-27

**Status**: Draft

**Input**: Pedido de Sergio (27/10/2026): "Quiero que adaptes y amplíes el módulo de sincronización de peajes para que acceda a muchos otros sitios para bajar documentación, estado de la cuenta corriente y datos relevantes, periódicamente. Quiero que sea una sección encriptada que solo pueda accederse desde dentro del sistema. Además tiene que tener una interfaz donde se puedan agregar servicios adicionales eventualmente. Allí deben guardarse los links a los accesos de los sistemas y las credenciales. Tienen que tener también la posibilidad de programar la periodicidad del acceso a cada uno de los portales por parte del sistema." Portales iniciales, además de los peajes: ARCA, Municipalidad de Bolívar, ARBA, Sancor Seguros, Bayá Casal, Cargill, Allianz, Jáuregui y Morales, Lartirigoyen.

## Contexto

El módulo 037 (Descarga de comprobantes de peajes) ya entra a cuatro portales (TelepeajePlus, TelePASE, CEAMSE y AUBASA), baja facturas y resúmenes, los guarda en la carpeta de Compras y los carga en Compras cuando cierran exacto. Sus credenciales se cargan con un instalador fuera de la aplicación y la periodicidad es una única tarea semanal para todos los portales.

Durante la revisión de cuentas (036) se consultaron a mano, con autorización puntual, otros portales (Bayá Casal, Cargill, ARCA, ARBA) para bajar resúmenes de cuenta, certificados y comprobantes. Ese trabajo se repite y hoy depende de que alguien lo haga a mano.

Esta funcionalidad generaliza 037 en una **Bóveda de portales**: un lugar protegido dentro del sistema donde se registra cada portal (enlace de acceso, credenciales, autorización, periodicidad) y desde donde el sistema entra periódicamente a bajar documentación y estado de cuenta. Los peajes pasan a ser los primeros portales de la bóveda sin perder nada de lo que hacen hoy.

Reglas que se mantienen (regla de oro de cuentas externas y Constitución): el acceso es **solo lectura y descarga** (no pagar, no presentar declaraciones, no aceptar, no enviar mensajes ni modificar datos en el portal); el sistema no entra a un portal sin autorización explícita registrada; no se eluden captchas ni segundos factores; las credenciales nunca se guardan en Git, archivos de texto ni registros.

## Clarifications

### Session 2026-10-27

- Q: ¿Se puede ver la contraseña guardada? → A: Sí, con "Revelar/Copiar" para entrar a mano; cada revelado queda en la auditoría.
- Q: ¿El pedido del 27/10/2026 autoriza al sistema a entrar a ARCA, Municipalidad de Bolívar, ARBA, Sancor Seguros, Allianz, Jáuregui y Morales y Lartirigoyen? → A: Sí. Autorización de Sergio del 27/10/2026, alcance solo lectura y descarga; se registra así en la bóveda.
- Q: ¿Quién accede a la bóveda? → A: Solo Sergio (administrador).
- Q: ¿Cómo se usa el umbral de $300? → A: Sergio (27/10/2026): solo para relativizar saldos de cuentas que en total están por debajo de $300; NO justifica diferencias, saldos ni redondeos. La comparación portal↔sistema es al centavo: cualquier diferencia distinta de $0,00 se señala.
- Q: ¿Las corridas programadas deben ocurrir con la aplicación cerrada? → A: No. Corren solo mientras la aplicación La Herencia está abierta; lo atrasado se recupera (una vez por portal) al abrirla.
- Q: ¿La bóveda pide reingresar la contraseña del sistema? → A: No. Alcanza con la sesión iniciada como administrador, también para revelar/copiar contraseñas.
- Q: ¿Dónde se guardan los documentos bajados de todos los portales? → A: Todos (facturas, resúmenes, certificados, boletas, pólizas, liquidaciones) en la carpeta de Compras del ejercicio (abril–marzo), igual que los peajes.
- Q: ¿Las facturas de portales no peaje se cargan solas en Compras? → A: Sí, desde el principio en todos los portales, con la regla de 037: solo si lo leído cierra exacto contra el total impreso, el formato es reconocido y no existe ya la compra (proveedor + número); si no, queda pendiente de carga manual con el motivo. Nunca se crean pagos, asientos ni ajustes automáticos.

### Session 2026-10-27 (tarde, después de usarla)

- Pedido de Sergio: "no sé si están corriendo; la interfaz no es clara; quiero barras de avance y mensajes en cada cuenta; no entiendo la columna Descarga; quiero seleccionar manualmente una o más cuentas para sincronizar; falta Movistar". Resolución:
  - Cada cuenta muestra su estado en palabras: "En cola", "Sincronizando…" con barra de avance y paso ("Buscando documentos…", "Descargando 3 de 12…"), o el resultado de la última sincronización (nuevos, ya estaban, cargados, para cargar a mano) o su error.
  - Barra general de la tanda ("Sincronizando: 2 de 4 cuentas terminadas") y mensaje final con los motivos de las cuentas que no se sincronizaron.
  - La columna "Descarga" pasa a "Sincronización automática": "Todavía no disponible — solo guarda el acceso", "Activa · próxima …", "Disponible · solo manual", o lo que falta (autorización, contraseña).
  - Selección con casillas y "Sincronizar seleccionadas"; además "Sincronizar todas las automáticas". Siempre de a una cuenta, sin encolar dos veces la misma.
  - Movistar agregada (contacto 71), solo bóveda hasta tener su sincronización.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar un portal en la bóveda (Priority: P1)

Un usuario autorizado entra a la sección "Bóveda de portales" (protegida), ve la lista de portales registrados y agrega uno nuevo: nombre, organismo o proveedor asociado (contacto del sistema, si corresponde), enlace de acceso, usuario, contraseña y datos adicionales de ingreso (por ejemplo CUIT, número de cliente, PIN), y notas. Puede editar esos datos o reemplazar la contraseña más tarde. La contraseña nunca vuelve a mostrarse completa salvo una acción explícita de "revelar", que queda registrada.

**Why this priority**: Es la base de todo lo demás y por sí sola ya da valor: un lugar único y seguro con los accesos de todos los sistemas.

**Independent Test**: Cargar un portal con credenciales, salir y volver a entrar; verificar que los datos persisten, que la contraseña aparece enmascarada, que no figura en claro en la base, en registros ni en la respuesta de la lista.

**Acceptance Scenarios**:

1. **Given** un usuario con permiso de bóveda, **When** agrega un portal con enlace y credenciales, **Then** el portal aparece en la lista con su enlace, el usuario visible y la contraseña enmascarada.
2. **Given** un portal registrado, **When** el usuario reemplaza la contraseña, **Then** la nueva queda guardada cifrada, la anterior deja de usarse y queda registrado quién y cuándo la cambió (sin el valor).
3. **Given** un usuario sin permiso de bóveda (incluso con otros permisos), **When** intenta entrar a la sección o a sus datos, **Then** no ve la sección en el menú y el sistema le niega el acceso.
4. **Given** un portal registrado, **When** el usuario elige "Abrir portal", **Then** se abre el enlace de acceso en una pestaña nueva.
5. **Given** un portal registrado, **When** el usuario elige "Revelar contraseña", **Then** se muestra la contraseña (y se puede copiar) por un tiempo breve y la acción queda en el registro de auditoría.

---

### User Story 2 - Programar la periodicidad de cada portal (Priority: P1)

Para cada portal con conector, el usuario define cada cuánto el sistema debe entrar (por ejemplo diario, semanal en un día dado, mensual en un día dado, o desactivado) y el horario. La pantalla muestra, por portal, la última corrida, su resultado y la próxima corrida prevista.

**Why this priority**: Es el pedido explícito de periodicidad por portal; reemplaza la tarea semanal única de 037.

**Independent Test**: Programar un portal en una frecuencia corta, esperar la hora prevista y verificar que corrió solo ese portal y que la próxima corrida se recalculó.

**Acceptance Scenarios**:

1. **Given** un portal autorizado y con conector, **When** el usuario programa "semanal, lunes 07:00", **Then** la pantalla muestra la próxima corrida en el próximo lunes 07:00 y el sistema corre ese portal a esa hora.
2. **Given** un portal programado, **When** el usuario lo pasa a "desactivado", **Then** no vuelve a correr automáticamente, pero puede correrse a mano.
3. **Given** la aplicación estaba cerrada a la hora prevista, **When** se abre, **Then** al abrir la aplicación corre una sola vez la corrida atrasada (no una por cada período perdido).
4. **Given** una corrida del mismo portal ya en curso, **When** llega la hora de otra o alguien aprieta "Correr ahora", **Then** no se inicia una segunda y se informa la que está en curso.
5. **Given** los cuatro portales de peajes con la programación semanal actual, **When** se pone en marcha esta funcionalidad, **Then** conservan esa periodicidad sin que nadie la reconfigure.

---

### User Story 3 - Bajar documentación y estado de cuenta (Priority: P1)

En cada corrida (programada o manual), el conector del portal entra con las credenciales de la bóveda, baja los documentos nuevos (facturas, resúmenes, certificados, liquidaciones, boletas, pólizas) y, cuando el portal lo ofrece, el estado de cuenta corriente (saldo y movimientos a la fecha). Los documentos se guardan en la carpeta de Compras del ejercicio con el nombre estándar y quedan listados en la aplicación con su portal, fecha, tipo y si ya están cargados en el sistema. El estado de cuenta queda guardado como "foto" fechada y se compara con el saldo que el sistema tiene para ese contacto.

**Why this priority**: Es el objetivo de negocio: tener la documentación y los saldos de los proveedores y organismos al día sin trabajo manual, como base de las conciliaciones (036).

**Independent Test**: Correr un portal con documentos nuevos y verificar que se guardaron sin duplicarse, que aparecen en la lista y que la foto del estado de cuenta muestra saldo del portal, saldo del sistema y diferencia.

**Acceptance Scenarios**:

1. **Given** un portal con documentos nuevos, **When** termina la corrida, **Then** cada documento nuevo queda guardado una sola vez, con fuente (portal, fecha y hora de descarga) y estado "cargado en el sistema" / "pendiente de carga".
2. **Given** documentos ya bajados antes, **When** corre de nuevo, **Then** no se vuelven a guardar ni a listar como nuevos.
3. **Given** un portal que ofrece estado de cuenta, **When** termina la corrida, **Then** queda una foto con fecha de corte, saldo por moneda y movimientos, y la diferencia contra el saldo del sistema del contacto asociado.
4. **Given** cualquier diferencia de saldo distinta de cero (comparación al centavo, en cada moneda), **When** se guarda la foto, **Then** el portal queda señalado con "diferencia de saldo" para revisar; no se genera ningún asiento ni ajuste.
5. **Given** los portales de peajes, **When** corren, **Then** siguen cargando en Compras automáticamente como hoy (037), y las facturas de los demás portales se cargan con la misma regla de cierre exacto (FR-020); ningún portal genera pagos ni asientos.

---

### User Story 4 - Autorización y control de cada portal (Priority: P1)

Antes de que el sistema entre a un portal, Sergio registra la autorización: alcance (solo lectura/descarga), fecha y quién autorizó. Sin autorización vigente el portal puede tener credenciales guardadas, pero el sistema no entra. La autorización puede revocarse en cualquier momento y el sistema deja de entrar inmediatamente.

**Why this priority**: Es la regla de oro del proyecto para cuentas externas; sin esto la funcionalidad no puede operar.

**Independent Test**: Intentar correr un portal sin autorización y verificar que se rechaza; autorizarlo y verificar que corre; revocar y verificar que deja de correr.

**Acceptance Scenarios**:

1. **Given** un portal sin autorización registrada, **When** se intenta correr (programado o manual), **Then** no se entra al portal y se informa "falta autorización".
2. **Given** un portal autorizado, **When** Sergio revoca la autorización, **Then** las corridas programadas se suspenden y queda registrado quién y cuándo revocó.
3. **Given** los portales ya autorizados antes (peajes 16/10/2026, Bayá Casal 19-20/10/2026, Cargill 20/10/2026), **When** se migran a la bóveda, **Then** su autorización queda registrada con la fecha y alcance originales; los portales ARCA, Municipalidad de Bolívar, ARBA, Sancor Seguros, Allianz, Jáuregui y Morales y Lartirigoyen quedan registrados con la autorización de Sergio del 27/10/2026, alcance solo lectura y descarga.

---

### User Story 5 - Agregar servicios nuevos (Priority: P2)

El usuario puede agregar desde la interfaz un portal que el sistema todavía no sabe recorrer. Ese portal queda como "solo bóveda" (guarda enlace y credenciales, se puede abrir a mano) hasta que exista un conector para él. La pantalla distingue claramente los portales con descarga automática de los que son solo bóveda.

**Why this priority**: Es el pedido de crecer en el tiempo, pero los conectores son trabajo de desarrollo por portal; la interfaz debe aceptar el alta desde ya.

**Independent Test**: Dar de alta un portal desconocido y verificar que se guarda, que se puede abrir y que no ofrece programación hasta tener conector.

**Acceptance Scenarios**:

1. **Given** un portal nuevo sin conector, **When** se agrega, **Then** queda como "solo bóveda", sin programación ni botón "Correr ahora".
2. **Given** se incorpora un conector para un portal ya registrado, **When** se vincula, **Then** el portal pasa a ofrecer programación y corrida conservando sus credenciales.

---

### User Story 6 - Seguimiento de corridas y alertas (Priority: P2)

El usuario ve un historial de corridas por portal (inicio, fin, resultado, documentos nuevos, foto de saldo, errores legibles) y un contador en el menú con portales con error, que requieren intervención (captcha, segundo factor, contraseña vencida) o con diferencia de saldo.

**Why this priority**: Las corridas son desatendidas; sin aviso, un portal caído pasa inadvertido.

**Independent Test**: Provocar un error de ingreso y verificar que aparece en el historial y suma en el contador del menú.

**Acceptance Scenarios**:

1. **Given** un portal pide captcha o segundo factor, **When** corre, **Then** el sistema no intenta eludirlo, marca "requiere intervención" y suma en el contador.
2. **Given** la contraseña fue rechazada, **When** corre, **Then** marca "credenciales rechazadas", no reintenta en esa corrida (para no bloquear la cuenta) y suspende las corridas programadas de ese portal hasta que se actualice la contraseña.
3. **Given** un portal falla, **When** termina la corrida general, **Then** los demás portales se procesan igual.

---

### Edge Cases

- La aplicación está cerrada a la hora programada: al abrirla se recupera una sola corrida por portal atrasado.
- Dos portales programados a la misma hora: corren uno por vez, sin perder ninguno.
- Un portal cambia su página y el conector no encuentra lo que busca: error legible "el portal cambió", sin guardar datos parciales como si fueran completos.
- Una foto de estado de cuenta incompleta (paginación cortada): se marca incompleta y no se compara con el sistema.
- Un mismo usuario/contraseña sirve para varios portales (por ejemplo, Clave Fiscal para ARCA y otros servicios del mismo organismo): se permite registrar varios servicios bajo una misma credencial sin duplicarla.
- Clave Fiscal o credenciales personales de un socio: deben poder distinguirse de las de la empresa (titular de la credencial).
- Se pierde la clave maestra de cifrado o se restaura la base en otro equipo: las credenciales no deben poder leerse desde una copia de la base sola; debe existir un procedimiento documentado de recuperación.
- Documento con el mismo número bajado de dos portales distintos: no se duplica en el sistema.
- Peajes: no debe perderse ni duplicarse el historial de ejecuciones y documentos de 037 al pasar a la bóveda.

## Requirements *(mandatory)*

### Functional Requirements

**Bóveda y seguridad**

- **FR-001**: El sistema MUST ofrecer una sección "Bóveda de portales" accesible solo desde la aplicación, únicamente al usuario administrador (Sergio). Ningún otro usuario ni rol accede, aunque tenga otros permisos. No se pide reingresar la contraseña: alcanza con la sesión iniciada.
- **FR-002**: Las contraseñas y demás secretos MUST guardarse cifrados en reposo, de modo que una copia de la base de datos por sí sola no permita leerlos.
- **FR-003**: Los secretos MUST NOT aparecer en claro en listados, respuestas de consulta, registros de la aplicación, historial de corridas, mensajes de error, Git ni archivos del proyecto.
- **FR-004**: Cada portal MUST registrar: nombre, enlace de acceso, tipo (organismo, proveedor, cliente, banco, otro), contacto del sistema asociado (opcional), titular de la credencial (empresa o socio), usuario, contraseña, datos adicionales de ingreso (pares nombre/valor, cada uno marcable como secreto), y notas.
- **FR-005**: El sistema MUST registrar en un historial de auditoría cada alta, modificación, cambio de contraseña, revelado/copia de contraseña, autorización, revocación y corrida, con usuario y fecha, sin los valores secretos.
- **FR-006**: La sección MUST permitir abrir el enlace de acceso de cada portal.
- **FR-007**: El sistema MUST permitir que varios servicios compartan una misma credencial sin duplicarla.

**Autorización y alcance**

- **FR-008**: El sistema MUST NOT entrar a un portal sin autorización vigente registrada (quién autorizó, fecha, alcance); la revocación MUST tener efecto inmediato sobre corridas programadas y manuales, incluida la corrida en curso (se detiene antes de la siguiente descarga).
- **FR-009**: Los conectores MUST limitarse a ingresar, consultar y descargar; MUST NOT pagar, presentar, aceptar, firmar, enviar mensajes ni modificar datos en el portal.
- **FR-010**: Ante captcha, segundo factor o verificación humana, el conector MUST detenerse y marcar el portal como "requiere intervención", sin intentar eludirlo.
- **FR-011**: Ante credenciales rechazadas, el sistema MUST no reintentar en esa corrida y suspender la programación de ese portal hasta que se actualicen.

**Programación y corridas**

- **FR-012**: Cada portal con conector MUST tener su propia programación: desactivado, diaria, semanal (día y hora) o mensual (día y hora).
- **FR-013**: El sistema MUST correr las corridas programadas sin intervención solo mientras la aplicación La Herencia esté abierta; al abrirla, MUST recuperar una sola corrida atrasada por portal. No se usan tareas de Windows para las corridas (la tarea semanal de peajes de 037 se reemplaza por esta programación).
- **FR-014**: El sistema MUST impedir dos corridas simultáneas del mismo portal y procesar los portales de a uno, de modo que un error en uno no impida los demás.
- **FR-015**: Usuarios con permiso MUST poder sincronizar ahora una cuenta, una selección de cuentas o todas las que tienen sincronización automática; se corren de a una, sin duplicar una cuenta ya en cola o en curso, y la respuesta MUST indicar por qué se omitió cada cuenta no sincronizable.
- **FR-015b**: Mientras se sincroniza, cada cuenta MUST mostrar si está en cola o en curso, el paso actual y el avance (n de m documentos), y la tanda MUST mostrar cuántas cuentas terminaron.
- **FR-016**: La pantalla MUST mostrar por portal: autorización, estado de credenciales (configuradas / rechazadas / faltantes), conector (disponible / solo bóveda), última corrida y resultado, próxima corrida.

**Documentación y estado de cuenta**

- **FR-017**: Cada documento descargado, de cualquier portal y tipo, MUST guardarse una sola vez en la carpeta de Compras del ejercicio (abril–marzo) con el nombre estándar `AAAAMMDD_Proveedor.pdf`, registrando portal, fecha de descarga, tipo y clave de identificación en el portal.
- **FR-018**: El sistema MUST indicar por documento si ya está cargado en el sistema y ofrecer abrirlo y cargarlo con el archivo precargado.
- **FR-019**: Cuando el portal ofrezca estado de cuenta, el sistema MUST guardar una foto fechada (fecha de corte, saldo por moneda, movimientos, marca de completa/incompleta) y compararla al centavo con el saldo del sistema del contacto asociado, señalando toda diferencia distinta de $0,00 / US$ 0,00. El umbral de $300 NO se aplica a esta comparación ni sirve para justificar diferencias o redondeos.
- **FR-020**: Para todo portal, cada factura o comprobante de compra descargado MUST cargarse automáticamente en Compras, firme, solo si lo leído cierra exacto contra el total impreso, el formato es reconocido y no existe ya una compra del mismo proveedor y número; si no, queda "pendiente de carga manual" con el motivo. Resúmenes, certificados, estados de cuenta y demás documentos no comprobantes se guardan sin cargar. El sistema MUST NOT crear pagos, asientos ni ajustes automáticamente.

**Extensibilidad y continuidad**

- **FR-021**: Los usuarios con permiso MUST poder agregar portales nuevos desde la interfaz; sin conector quedan como "solo bóveda".
- **FR-022**: Los cuatro portales de peajes MUST migrarse a la bóveda conservando credenciales, autorización, periodicidad, historial de ejecuciones, documentos y la carga automática en Compras; la pantalla de 037 MUST seguir disponible con su permiso actual (usuarios que dan de alta compras), mostrando corridas, documentos y "Descargar ahora" de los peajes, sin acceso a credenciales ni a la bóveda.
- **FR-023**: Conectores iniciales a implementar, en orden de prioridad propuesto: peajes (existentes), Bayá Casal y Cargill (relevamientos ya autorizados), ARCA, ARBA, Municipalidad de Bolívar, Sancor Seguros, Allianz, Jáuregui y Morales, Lartirigoyen. Cada conector se habilita solo con su autorización registrada (FR-008).

### Key Entities

- **Portal / Servicio**: sistema externo registrado; enlace, tipo, contacto asociado, conector (o "solo bóveda"), estado.
- **Credencial**: usuario, secreto cifrado, datos adicionales, titular (empresa o socio); puede compartirse entre servicios.
- **Autorización**: portal, alcance, autorizado por, fecha, revocación.
- **Programación**: portal, frecuencia, día/hora, próxima corrida, suspendida (motivo).
- **Corrida**: portal, origen (programada/manual), inicio, fin, resultado, mensaje legible, documentos nuevos.
- **Documento descargado**: portal, clave en el portal, tipo, fecha, archivo, estado de carga en el sistema.
- **Foto de estado de cuenta**: portal, contacto, fecha de corte, saldo por moneda, movimientos, completa/incompleta, diferencia contra el sistema.
- **Registro de auditoría de bóveda**: acción, usuario, fecha, portal, sin valores secretos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las credenciales de portales usadas por el sistema están en la bóveda; ninguna aparece en claro en la base, los registros, Git o archivos del proyecto (verificado con búsqueda de los valores).
- **SC-002**: Un usuario sin permiso de bóveda no puede ver ni obtener ningún dato de la bóveda por ninguna vía de la aplicación.
- **SC-003**: Registrar un portal nuevo con enlace y credenciales lleva menos de 2 minutos.
- **SC-004**: Cada portal con conector corre en su horario programado al menos el 95 % de las veces en que la aplicación está abierta, y una corrida perdida se recupera dentro de los 15 minutos de abrir la aplicación.
- **SC-005**: Ningún documento se guarda dos veces en 10 corridas consecutivas sobre el mismo portal.
- **SC-006**: Los peajes siguen bajando y cargando en Compras con los mismos resultados que antes de la migración.
- **SC-007**: Para los portales con estado de cuenta, la diferencia entre el saldo del portal y el del sistema se ve sin abrir el portal a mano.
- **SC-008**: Cero acciones de escritura (pago, presentación, aceptación, mensaje) realizadas en portales externos.

## Assumptions

- La aplicación corre en el equipo local de Sergio (como 037); las corridas programadas ocurren solo con la aplicación abierta.
- La clave de cifrado se custodia fuera de la base de datos, en el almacén protegido del sistema operativo del equipo, y existe un procedimiento documentado de respaldo/recuperación de esa clave.
- Los conectores se desarrollan uno por uno como trabajo de código; esta funcionalidad entrega la bóveda, la programación, el historial y los conectores iniciales en el orden de FR-023, pudiendo liberar en etapas.
- Portales que exigen segundo factor en cada ingreso pueden no ser automatizables; en ese caso quedan como "requiere intervención" o "solo bóveda".
- Todos los documentos bajados van a la carpeta de Compras del ejercicio (abril–marzo), la misma que usa 037.
- No hay tolerancia en la comparación de saldos: las cuentas se concilian al centavo. El umbral de $300 solo relativiza cuentas cuyo saldo total es menor a ese monto, y no se usa en este módulo.
- Ninguna escritura fuera de la base WC.
