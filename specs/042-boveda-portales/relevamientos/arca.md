# Relevamiento ARCA (Sistema de Cuentas Tributarias) — 27/10/2026

Autorización: bóveda portal 7 "ARCA Giamigli", solo lectura. Ingresa con la clave fiscal de Sergio como representante. Credencial: bóveda. "ARCA Sergio" y "ARCA Lucy" no tienen autorización: no se programan.

## Ingreso
- `auth.afip.gob.ar/contribuyente_/login.xhtml`: CUIT → "Siguiente" → clave → "Ingresar". El campo de captcha existe oculto; al 27/10/2026 no se mostró. Si aparece, la corrida queda en "requiere intervención".
- Portal `portalcf.cloud.afip.gob.ar`. Su API de deuda (`/portal/api/deuda/{cuit}/exigible`) solo responde para la persona que ingresa, no para los representados.
- "Mis Comprobantes" no está habilitado en esta clave fiscal (no figura en sus servicios).

## Cuentas Tributarias
- Se abre desde Mis servicios (ventana nueva, `ctacte.cloud.afip.gob.ar/contribuyente/externo`, Tapestry). El selector de contribuyente lista los CUIT representados; al cambiarlo, la página se recarga.
- "Estado de Cumplimiento" → botón "Siguiente" (ejecuta la consulta con todos los impuestos del año en curso) → carga asíncrona ("CARGANDO…"). Por impuesto: subtotal de Deuda, Saldo de libre disponibilidad, Saldo técnico, Otros créditos y Multas no firmes.
- Foto informativa: saldo = deuda + multas del año; los saldos a favor van en el detalle.

## Prohibido (constancia de revisión)
Solo navega a Cuentas Tributarias, cambia el contribuyente consultado y ejecuta la consulta de Estado de Cumplimiento. No usa Presentación DJ/Pagos, Compensación, Transferencias, Solicitud de Devoluciones, Billetera, Reimputación, Reducción de anticipos ni los avisos del portal (DFE, datos de contacto).
