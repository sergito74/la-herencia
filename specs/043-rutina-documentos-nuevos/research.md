# Research: 043 — Rutina automática de documentos nuevos

Relevamiento del 27/10/2026 sobre el código actual (`backend/src/features/boveda`, `frontend/src/components/layout/NavHeader.tsx`, `backend/scripts/`) y el portal de De Campo a Campo (solo lectura, autorización de Sergio del 27/10/2026).

## R1. Programación de la rutina

- **Decisión**: reusar el hilo del planificador de la bóveda (`boveda/planificador.py`, corre dentro del backend). Se agrega un horario propio de la rutina: todos los días 07:00 y 14:00. La próxima corrida se calcula desde ahora; si el backend estuvo apagado se corre **una sola vez** al volver (recuperación única, mismo criterio que 042). Mientras la rutina corre no se lanza otra (candado propio + el candado por portal de 042).
- **Razón**: ya existe, ya resolvió la recuperación única y la serialización de navegadores (Clarification 042: no hay tareas de Windows).
- **Alternativas**: Programador de tareas de Windows (descartado en 042); programación por cuenta (ya existe, pero Sergio pidió una rutina única).
- La programación por cuenta de 042 queda: la rutina corre todas las cuentas sincronizables; las que además tengan programación propia siguen con ella.

## R2. Lectura de mails

- **Decisión**: Outlook por COM, solo lectura (`boveda/mails.py` ya lo usa para los códigos de Allianz). Se recorren las bandejas de entrada de todos los almacenes (Outlook, La Herencia, Alquileres, Sucesion, Varios, …) y se toman solo los mails con `ReceivedTime` **posterior a la marca de la última corrida completada** de cada almacén. Cada adjunto procesado se registra por `EntryID` del mail + SHA-256 del adjunto, así no se vuelve a procesar. La primera corrida fija la marca en el momento de activación (no barre historia).
- **Filtro de adjuntos**: PDF (y XML de comprobante si aparece). Se descarta lo que no sea comprobante (Clarification 1): factura, nota de crédito/débito, boleta, liquidación, recibo, resumen de cuenta, contrato de venta de granos.
- **Receptor**: se carga solo lo dirigido a Giamigli de Bolívar SA (CUIT 30-71211460-2, cuando el comprobante lo indica) o a la Sucesión (etapa previa de Giamigli). Los almacenes Alquileres/Sucesion y comprobantes a nombre de otras sociedades o personas no se cargan en el sistema: ver *Pendiente P1*.
- **Razón**: Sergio pidió "todo mail, pero que sea nuevo"; la marca por almacén evita la barrida completa. Ningún mail se marca, mueve ni borra (regla de oro).
- **Alternativas**: IMAP/Gmail API (requiere credenciales y alta nueva, descartado); marcar mails como leídos (prohibido).

## R3. Clasificación y destino

- **Decisión**: un clasificador por texto del PDF (pdfplumber, ya usado) decide **tipo** (factura A/B/C, NC, ND, boleta, liquidación, recibo, resumen bancario/tarjeta, resumen de proveedor, contrato de granos) y **emisor** (CUIT → `Contactos`). Destino:

| Tipo | Carpeta | Aviso en |
|---|---|---|
| Factura/NC/ND de proveedor | `Dropbox\Giamigli de Bolivar SA\Compras\<ejercicio>\AAAAMMDD_Proveedor.pdf` (042) | Compras |
| Boleta / retención / percepción de organismo | carpeta actual de Impuestos (la que usan los scripts de 036) | Impuestos y retenciones |
| Liquidación de venta (hacienda, granos) | carpetas actuales de Ventas | Ventas |
| Contrato / fijación de granos | `Documents\La Herencia\Agricultura\Contratos\Contrato <Comprador> <nro>.pdf` | Ventas |
| Resumen de banco / tarjeta | `Dropbox\…\Bancos\<Banco>\<Producto>\<Año>\` (nombre del banco) | Tesorería |
| Resumen de proveedor / consignatario | `Documents\…\Resumenes de Cuenta\<Proveedor>\` | Cuentas corrientes |
| No se pudo decidir | se guarda en Compras del ejercicio | "Sin clasificar" (ver R6) |

- Galicia manda Visa y Galicia Rural con el mismo nombre de archivo: el producto se lee del contenido.
- Emisor no registrado → "para cargar a mano" con "emisor nuevo" (Clarification 2); nunca se crean contactos.

## R4. Carga automática (lectores)

- **Decisión**: registro de lectores por (tipo, emisor). En la primera entrega se cargan solos los que ya tienen lector probado: peajes (037), Allianz y Movistar (043/042, commit d521fa0). Los lectores que hoy viven en scripts sueltos (`cargar_retenciones_certificados.py`, `cargill_liquidaciones_pdf_036.py`, `cargar_resumen_visa_galicia_pdf.py`, `cargar_resumenes_mercado_libre_pdf.py`, `importar_extractos.py`) se incorporan **uno por uno** como tareas separadas, cada uno contra documentos reales ya cargados a mano (la carga tiene que coincidir al centavo). Todo lo demás: "para cargar a mano".
- **Razón**: imputación igual a la manual (spec, restricciones) y cierre al centavo (regla de la bóveda). Incorporar sin prueba arriesga cargas mal imputadas.
- Resúmenes bancarios y de tarjetas: en esta entrega **se guardan y se avisan** en Tesorería con acceso a la importación existente; no se importan solos (la importación tiene sus propias reglas de deduplicación, ver memoria "Importar extractos").

## R5. Registro de documentos nuevos

- **Decisión**: tabla nueva `DocumentosNuevos` (WC) que unifica lo que entra por portal o por mail: origen, módulo, estado, vínculo al registro creado y revisión. `Portales_Documentos` (042) sigue siendo el historial de la bóveda; cada documento de portal genera además su fila en `DocumentosNuevos`. La columna `Portales_Documentos.Revisado` (agregada el 27/10 para el listado que se retira) queda sin uso y se elimina en la migración, con respaldo previo.
- **Razón**: un solo lugar para los avisos de todos los módulos y orígenes; evita sumar columnas de revisión en Compras, Impuestos, Ventas, etc.

## R6. Avisos en el menú y vista "Nuevos para revisar"

- **Decisión**: un endpoint de resumen devuelve la cantidad pendiente por módulo; `NavHeader` muestra el número junto al menú (Compras, Ventas, Finanzas) y junto a la opción del submenú (Tesorería, Cuentas corrientes, Impuestos y retenciones), igual que el contador de peajes existente. El clic abre la pantalla del módulo con `?nuevos=1`: lista de nuevos + el primero abierto (datos, renglones con rubro y centro de costo, archivo). "Revisado" y "Cargar a mano" desde ahí. Lo "sin clasificar" se muestra en Compras con su propio filtro, con la opción de indicar el módulo correcto.
- Se retira `RevisionCargas` de la bóveda (FR-011) y el contador de la bóveda deja de sumar pendientes de carga.
- **Alternativas**: campana de notificaciones global (descartada por Sergio: número en el menú).

## R7. De Campo a Campo

- Ingreso: `https://www.decampoacampo.com/__dcac/login` → botón `#btn_login` abre el modal → `#maillog`, `#password`, `#ingresar_login`; la sesión queda en `/__dcac/`. Ingreso verificado el 27/10/2026 con Chromium sin cabeza (no pide captcha).
- La cuenta de Sergio administra **dos sociedades**: Giamigli De Bolivar SA (30-71211460-2) y Ganadera San Justo Sociedad Si (30-71594327-8).
- Documentos: *Operaciones › Ventas / Compras* (aplicación en `react.alb.decampoacampo.com/operacion/invernada/{venta|compra}`, pestañas con saldo / cerradas / no concretadas). Cada operación ofrece Liquidación, Confirmación de venta, Informe de tropa, Ticket de pesada; datos de liquidación (precio, kg, neto, IVA 10,5 %, IIBB, retención de Ganancias, factura `11-82152`). *Perfil › Mi Historial de Retenciones* (certificados → Impuestos). *Resúmenes* (`/__dcac/misPublicaciones/Resultados_i`).
- Las 6 operaciones de venta vistas el 27/10 (1 con saldo, 5 cerradas) son de **Ganadera San Justo**, no de Giamigli: quedan excluidas (decisión de Sergio).
- **Decisión**: conector `decampoacampo` con Chromium sin cabeza; baja solo Liquidaciones (y certificados de retención) de las operaciones cuya sociedad sea Giamigli (CUIT 30-71211460-2). **Nada de Ganadera San Justo** (Sergio, 27/10/2026): ni operaciones, ni retenciones, ni resúmenes; nunca usa Programar pago, Ofertar, Comprar, Cotizar ni Consultas.

## Pendientes para Sergio (no bloquean el plan; se resuelven antes de la tarea correspondiente)

- **P1**: comprobantes a nombre de la **Sucesión** son gastos de Giamigli (etapa previa, decisión ya cerrada de Sergio): se tratan como dirigidos a Giamigli. Los de otras sociedades o personas (Ganadera San Justo, socios, Alquileres) se ignoran (no se cargan en el sistema de Giamigli).
- ~~P2~~ **Resuelto por Sergio (27/10/2026): no se baja ninguna información de Ganadera San Justo.** El conector filtra por sociedad Giamigli antes de abrir o bajar nada; las operaciones de San Justo ni se listan.
