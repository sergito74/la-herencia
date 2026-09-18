# Research: Ventas de Hacienda (alta) y Ventas de Granos (lectura + alta)

Todas las decisiones de esta fase están confirmadas contra la base SQL Server real (`INFORMATION_SCHEMA`, `sys.foreign_keys`, muestras de datos) y contra la inspección read-only real de `Frm Venta Hacienda`/`Frm Venta Granos` y sus subformularios (COM automation, sin escrituras). No se asume ningún nombre de columna ni fórmula sin haberla visto en el sistema real.

## 1. Esquema real confirmado — Ventas de Hacienda

**Decision**: Usar las tablas reales tal cual están, sin renombrar columnas.

- `dbo.[Venta Hacienda]` (cabecera, 20 columnas): `IdVenta` PK, `Fecha`, `IdConsignatario`, `IdEstableciemiento` (**sic**, typo real de la DB — no corregir el nombre de columna, solo el label en la UI), `IdTipoDocumento`, `[Nro documento]` nvarchar(50), `[Porc Comision]` real, `[Vis Municipal]`/`Balanza`/`[Gs Vs No Gravados]`/`AlicuotaIVA`/`[Retencion Ganancias]`/`[Retencion IVA]`/`[Ingresos Brutos]`/`[Ley de Sellos]`/`Flete`/`[Gastos Varios]`/`Complemento` money, `IdOperacion` int, `[Documento Original]` nvarchar(max).
- `dbo.[Det_Ventas Hacienda]` (detalle, 9 columnas): `IdDetalleVenta` PK, `IdVenta` (FK real declarada: `FK_DetVentasHacLB_VentaHacLB`), `IdComprador`, `IdTipoProducto`, `Cantidad` real, `[Unidad de medida]` nvarchar(255), `[Peso Total]` real, `[Precio unitario (A)]`/`[Precio unitario (B)]` money.
- `dbo.[Vencimientos Ventas]` (4 columnas): `IdVencimientoVenta` PK, `IdVenta`, `Fecha`, `Importe` money — **sin FK declarada** a `Venta Hacienda`, validar en aplicación igual que el resto de la app.
- `dbo.[Tipo Hacienda]` (catálogo, ya usado en spec 005): `IdTipoHacienda`, `[Tipo de Hacienda]`.
- `dbo.Establecimientos`: `Id`, `Establecimiento` — catálogo real, confirma que `IdEstableciemiento` es una FK válida aunque no esté declarada.
- `dbo.[Tipo Documento]` (catálogo real, **compartido** — no es un `Literal` fijo como en Compras): `IdTipoDocumento` 1-6 = Factura, Nota de Credito, Nota de Debito, Certificado de deposito, Ticket, Liquidacion. Venta Hacienda usa históricamente 1, 2, 3, 6 (Factura/NC/ND/Liquidación).
- `dbo.[Retenciones Ventas Hacienda]`: `Id`, `Fecha`, `IdContacto`, `Documento`, `[Nro Documento]`, `Importe`, `Imagen` — sin FK a la venta (ya documentado en spec 005), fuera del alcance de escritura de este spec.

**Rationale**: Confirmado contra `INFORMATION_SCHEMA.COLUMNS`/`sys.foreign_keys` reales (no solo el spec 005, que documentaba un subconjunto). El único cambio real respecto a 005 es que ahora se conocen las 16 columnas adicionales de cabecera necesarias para el alta.

**Alternatives considered**: Renombrar `IdEstableciemiento` a `IdEstablecimiento` en la base — rechazado (constitución principio VII: cambio no relacionado, y cambiar nombres de columna reales requiere autorización explícita y afecta el histórico).

## 2. Tipo de contacto real de Consignatario/Comprador — Ventas de Hacienda

**Decision**: El combo de Consignatario (cabecera) filtra por tipos `Comprador`, `Consignatario`, `Multiple`. El combo de Comprador (línea) filtra por tipos `Comprador`, `Multiple`.

**Rationale**: Verificado con `JOIN` real contra `Contactos.[Tipo Contacto]` sobre todas las ventas históricas — `IdConsignatario` de cabecera usa los 3 tipos (82 Consignatario, 45 Multiple, 16 Comprador); `IdComprador` de detalle usa 2 (237 Comprador, 6 Multiple). Ningún otro tipo aparece. Restringir a un solo tipo (como advirtió el riesgo del roadmap para Compras) dejaría fuera contactos reales.

**Alternatives considered**: Un único tipo "Consignatario"/"Comprador" — rechazado, los datos reales lo contradicen.

## 3. Esquema real confirmado — Ventas de Granos

**Decision**: Cabecera única sin tabla de líneas (confirmado, no hay tabla de detalle de producto separada), con dos subformularios de ajustes/deducciones.

- `dbo.[Venta Granos]` (31 columnas): ver lista completa en `data-model.md`. `IdVenta` PK, sin FK declarada hacia `Contactos`/`Granos`, pero el join real funciona (`IdProducto` → `Granos.IdGrano` confirmado con muestra: `IdProducto=1` → `Grano='Soja'`).
- `dbo.[Venta Granos_Ajustes]` (5 columnas): `IdAjuste` PK, `IdVenta` (FK real declarada), `Concepto` nvarchar(50), `Importe` money, `AlicuotaIVA` real.
- `dbo.[Venta Granos_Deducciones]` (7 columnas): `IdDeduccion` PK, `IdVenta` (FK real), `IdConcepto` (FK real a `Venta Granos_ConceptosDeducciones`), `Detalle` nvarchar(50), `Porc` real, `[Base Calculo]` money, `Alicuota` real.
- `dbo.[Venta Granos_ConceptosDeducciones]` (catálogo): `IdConcepto`, `Concepto`.
- `dbo.Granos` (catálogo): `IdGrano`, `Grano`, `[Tipo de Cultivo]`.

**Rationale**: Confirmado con `INFORMATION_SCHEMA` + muestra real de datos — el join `IdProducto`→`Granos` funciona aunque no haya constraint, así que se usa con confianza (a diferencia de otros joins sin FK en la app que resultaron no confiables).

**Tipo de contacto real de Consignatario — Ventas de Granos**: en la muestra completa, **todas** las 219 filas con `IdConsignatario` son tipo `Multiple` — ningún `Consignatario`/`Comprador` puro. Se filtra el combo por `Multiple` como tipo principal, pero se deja abierto a `Consignatario`/`Comprador` también (mismo criterio que Hacienda) por si el histórico no cubre todos los casos futuros.

**Alternatives considered**: Modelar líneas de producto para Granos como en Hacienda — rechazado, el formulario Access real es "una fila = una venta", no hay tabla de líneas; forzar una no reflejaría el proceso real (constitución principio III).

## 4. Columnas de significado ambiguo en Venta de Granos — decisión Q2

**Decision**: Capturar `Grado Operacion` (nvarchar(5)) y `Grado Mercaderia` (nvarchar(5)) como dos campos de texto corto independientes; capturar `Cantidad entregada` y `Cantidad vendida` (ambas `real`) como dos campos numéricos independientes. Ninguno se fusiona ni se descarta.

**Rationale**: Decisión explícita del usuario (Q2 de `/speckit-clarify`) — preservar toda la información del histórico tal cual, sin forzar una interpretación de negocio no confirmada.

**Alternatives considered**: Investigar más a fondo el significado exacto antes de implementar — descartado por decisión explícita del usuario, se prioriza no perder datos por sobre tener certeza total de la semántica.

## 5. Mecanismo de bloqueo de edición y transacción multi-tabla

**Decision**: Reutilizar el mismo patrón de `006-carga-compras` (`execute_write_transaction`, `repository_locks.py`) generalizándolo — una tabla de lock por dominio (`VentaHaciendaEditLocks`, `VentaGranosEditLocks`) o una tabla única parametrizada por tipo+id. TTL de 5 minutos (no 15), con opción de "forzar", incorporando la lección aprendida en 006 (un solo usuario real se auto-bloqueaba con pestañas viejas).

**Rationale**: Mecanismo ya construido, probado en producción y corregido tras feedback real de uso (TTL, botón forzar, `pagehide`+`keepalive` para liberar al cerrar la pestaña). No hay motivo de negocio para un mecanismo distinto en Ventas.

**Alternatives considered**: Un único mecanismo de lock genérico multi-entidad (`EditLocks` con columna `Entidad`+`IdEntidad`) en vez de tablas separadas por dominio — más elegante a largo plazo, pero se descarta para este spec por simplicidad (principio VII): implementar 2 tablas más siguiendo el patrón exacto ya probado es más simple y reversible que refactorizar el mecanismo existente de Compras al mismo tiempo que se construye Ventas. Se puede evaluar la generalización en un spec de infraestructura futuro si el patrón se repite una tercera vez.

## 6. CORS y verificación de escritura — lección de 006

**Decision**: Verificar explícitamente con `curl -X OPTIONS` el preflight de `POST`/`PUT`/`DELETE` de los nuevos endpoints de Ventas antes de dar por probado el flujo desde el navegador, y reiniciar el backend sin `--reload` antes de cualquier verificación manual.

**Rationale**: Bug real encontrado en 006 — `main.py` no incluía `PUT`/`DELETE` en `allow_methods`, causando fallos silenciosos (error genérico sin detalle) en edición/eliminación desde el navegador. Como este spec ya agrega `PUT`/`DELETE` a los nuevos endpoints de Ventas, el `main.py` actual (ya corregido en 006) ya los cubre — solo hay que **confirmarlo**, no volver a implementarlo.

**Alternatives considered**: N/A — es una verificación, no una decisión de diseño nueva.

## 7. Política de duplicados — decisión Q3

**Decision**: Advertencia no bloqueante (toast informativo) al detectar el mismo número de documento del mismo comprador/consignatario en otra venta — nunca un bloqueo duro (400) como en Compras.

**Rationale**: Decisión explícita del usuario tras el análisis del especialista financiero — una liquidación de feria/acopio puede pagarse en varios parciales legítimos del mismo comprador con distinto número de documento.

**Alternatives considered**: Bloqueo duro igual que Compras — rechazado explícitamente por el usuario (Q3: A).

## 8. Navegación

**Decision**: `NavHeader.tsx` — ítem "Ventas" pasa a tener `submenu: [{ href: "/ventas/hacienda", label: "Hacienda" }, { href: "/ventas/granos", label: "Granos" }]`, mismo patrón que "Finanzas". Botones de alta específicos: "+ Nueva venta de hacienda" en `/ventas/hacienda`, "+ Nueva venta de granos" en `/ventas/granos`.

**Rationale**: Recomendación del arquitecto de producto y del especialista de nomenclatura (consultados en `/speckit-specify`), consistente con el patrón ya usado para Finanzas.

**Alternatives considered**: Dos ítems de primer nivel separados ("Hacienda", "Granos") — rechazado, rompe la jerarquía por proceso de negocio ya adoptada (Ventas es un proceso, Hacienda/Granos son sus dos líneas).
