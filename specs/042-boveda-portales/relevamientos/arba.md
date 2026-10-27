# Relevamiento ARBA Autogestión — 27/10/2026

Autorizaciones: bóveda portal 8 (Giamigli) y portal 20 (Oscar Giamberardini, autorizado por Sergio el 27/10/2026), solo lectura. Credenciales: bóveda.

## Ingreso
- `sso.arba.gov.ar/Login/login?service=…PanelAutogestion.asp`: tres modos (CUIT, usuario, dominio). Se usa CUIT (`#CUIT`, `#clave_Cuit`). Sin captcha al 27/10/2026.
- Panel "Gestionar": `DatosContactoRedirect.asp?destino=https://app.arba.gov.ar/Gestionar/dist/gestionar` (no se confirma ni modifica nada de los datos de contacto).

## Datos que se leen (API de la página)
- `GET app.arba.gov.ar/Gestionar/services/padron/objetos/GESTIONAR`: objetos del contribuyente (`cod_impuesto` 0 inmobiliario, 1 automotor, 2 IIBB, 10 inmobiliario), `claveh` por objeto.
- `GET …/services/objeto/deuda?impuesto=<131|551|211|135>&objeto=…&cuit=…&claveh=…`: `deuda_total`, `deuda_judicial`, `total_excedente` (saldo a favor), plan de pagos.
- Giamigli: IIBB y automotor. Oscar: solo la partida 011-007957-5 (pedido de Sergio); las demás se ignoran.

## Documentos
Boletas (`LiqPredet`) y cuenta corriente impresa piden captcha en cada consulta: no se bajan. La foto de deuda por objeto queda como estado de cuenta informativo.

## Prohibido (constancia de revisión)
Solo GET de consulta. No genera boletas, no paga, no presenta DDJJ, no adhiere débitos, no agrega objetos de terceros ni cambia datos de contacto.
