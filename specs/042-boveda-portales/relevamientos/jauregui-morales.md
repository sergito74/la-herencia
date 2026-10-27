# Relevamiento Jáuregui y Morales (portal de clientes FocaSoftware) — 27/10/2026

Autorización: bóveda portal 12, solo lectura. Credencial: bóveda.

## Ingreso
- `http://45.176.20.244/clientes/` (sin HTTPS): `#txtUsuario`, `#txtPassword`, botón "Ingresar" → `/clientes/main`. Sin captcha. La conexión no está cifrada: la clave viaja en claro (riesgo del proveedor, avisar a Sergio).

## Datos
- Filtro: `#txtDatosDesde`/`#txtDatosHasta` (dd-mm-aaaa, datepicker), casillas remitos/contado/anuladas, opción "Resumen de Cuenta" o "Análisis de Deuda"; el botón "Enviar datos" solo ejecuta la consulta en la misma página.
- Resumen: saldo inicial, una fila por comprobante (fecha-hora, comprobante `A 0009-00115758`, FPA, tipo FT/RC, débito, crédito, saldo, remitos pendientes, observaciones, vencimiento) y "Totales al: …" con el saldo final ("(Deuda: …)").
- No hay PDF de comprobantes: no se bajan documentos.
- 27/10/2026: saldo $ 106.399,99 (factura A 0009-00115758 del mismo día).

## Prohibido (constancia de revisión)
Solo ingreso y consulta del resumen. No usa "Cambiar Password" ni ningún otro formulario.
