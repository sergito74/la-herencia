# Relevamiento Sancor Seguros (Autogestión) — 27/10/2026

Autorización: bóveda portal 10 "Sancor Seguros", solo lectura (pólizas de personas del personal: Accidentes Personales, Salud, Vida Colectivo). "Sancor Seguros Giamigli" (portal 16) no tiene autorización: no se programa.

## Ingreso
- `www.sancorseguros.com.ar/autogestion/ingresar` → login de Grupo Sancor (usuario → Continuar → clave → Continuar). La URL guardada en la bóveda trae un `state` que vence; el conector entra siempre por esta página. Sin segundo factor al 27/10/2026.
- La API (`autogestion.sancorseguros.com.ar/api/v1/…`) responde 500 hasta que se abre la pantalla "Descargar documentación"; se llama con `X-Requested-With: XMLHttpRequest` y `Authorization: Bearer` (vacío, igual que la página).

## Documentos
- Pólizas vigentes: `POST MyPolicies/PostCardsList` `{"policy":{"client":{"bupId":0},"isVigent":true}}`.
- Movimientos: `GET PolicyPayment/GetCertificateMovementsDetails?certificateId=…` (recibos, cobros, `printDate` de cada refacturación).
- Factura: `POST DocumentationDownload/PostDownloadDocument` con `did_gss: "INVOICE"` y la fecha de impresión; devuelve el PDF en base64. El PDF trae juntas las facturas de las tres pólizas del mes: un documento por fecha. Las anteriores a julio/2026 no tienen PDF (se descartan al listar).
- Número (`00038-00229895`) y fecha de emisión se leen del PDF para reconocer la compra ya cargada. Archivos `AAAAMMDD_SancorSeguros.pdf` en Compras.
- No se llama a `SaveDownloadDocumentInfo` (registro de la página, no hace falta).

## Estado de cuenta
Recibos con estado "Pendiente" en los movimientos (lo mismo que "Pólizas a pagar"). Foto informativa.

## Prohibido (constancia de revisión)
No usa "Pagar ahora", "Pago presencial", débito automático, póliza electrónica, denuncia de siniestros, asistencia ni adjuntar documentación.
