# Relevamiento Cargill (portal GPS) — 27/10/2026

Autorización: bóveda, portal 6, solo lectura (Sergio, 20/10/2026). Credencial: bóveda (nunca en archivos).

## Ingreso
- `https://www.mycargill.com/cascsa/v2/login`, formulario Okta (usuario + clave, `#okta-signin-submit`). Sin captcha ni segundo factor al 27/10/2026.
- La página llama a `api.cglcloud.com` con `authorization: Bearer …` (token de la sesión, ~1 h). El conector lo toma de la primera llamada.

## Documentos
- Lista: `GET /api/dxo/gps/v1/invoices?source=JDEAR&role=DXP_GPS_Role_Client&invoiceFromDate=MM/DD/AAAA&invoiceToDate=…&offset&limit` (hasta ~3 meses por consulta). Cada fila trae `documentIds` (sin ids = sin PDF, ej. A/R drafts), `invoiceTypeCode`, `externalDocumentReference` (número fiscal PV+número, o COE en liquidaciones).
- PDF: `POST /api/dxo/gps/v1/userDocuments/download` con `{"documentIds": [...]}` y `Accept: application/octet-stream` (con `application/pdf` responde 406). Es una descarga; no envía nada.
- Tipos: RI factura (insumos que nos vende Cargill), RM nota de crédito, RT nota de débito, L# liquidación de granos, H7 ajuste de liquidación, $I/$B retenciones.
- Carpetas: facturas/NC/ND → Compras del ejercicio; liquidaciones y ajustes → Ventas del ejercicio; retenciones → Ventas/Retenciones del ejercicio (donde Sergio ya los guardaba). Un archivo idéntico ya guardado se reusa.
- Número para Compras: el fiscal (`7050-00077233`), no el interno del portal (`51240-RT-…`).

## Estado de cuenta
- `POST /api/dxo/gps/v1/accountbalance/currency?…&customerId=35192801&fromDate&toDate&isBlnCmpReq=false` con body `{}`; máx. ~3 meses. Un trimestre sin movimientos vuelve vacío (sin saldo inicial): se retrocede hasta el último con movimientos.
- Está en pesos; la cuenta se lleva en US$ al TC de cada comprobante, así que la foto queda informativa (no se compara saldo).
- Signo: negativo en el portal = le debemos a Cargill.

## Prohibido (constancia de revisión)
El conector solo hace GET de consulta, POST de descarga/consulta del libro. No usa `sendAccountBalance`/email, firma de contratos (el portal avisa "contratos sin firmar"), cobros ni ninguna acción que envíe o acepte.

## Primera corrida (27/10/2026)
36 documentos del ejercicio: 12 comprobantes ya estaban cargados en Compras (quedaron vinculados), 24 de venta/retención ya estaban en Ventas. Segunda corrida: 0 nuevos.
