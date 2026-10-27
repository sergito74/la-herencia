# Cooperativa Eléctrica de Bolívar (CEBOL) — relevamiento 27/10/2026

Autorización: pedido de Sergio en el chat del 27/10/2026 ("Otro portal que debemos automatizar es el de la
Cooperativa Electrica … Adelante"), solo lectura. Bóveda: portal 22, credencial 21, contacto 23.

- Oficina virtual: https://ofv2.cebol.com.ar (enlace desde www.cebol.com.ar). Usuario/correo y contraseña, sin captcha.
- API de la página (token del ingreso): `nservicioasociado/index` (suministros; hoy 1: socio 23541, conexión 1,
  RUTA 205 187), `getDeuda/{socio}&{conexion}` (comprobantes impagos y pagos, `comprobanteFormat` "FCA 0003-000000233850"),
  `getDeudaResumida` (deuda vencida/a vencer y dinero a favor), `getPdfDeuda/{comprobante}&{sistema}?periodo=…` (PDF).
- Número en Compras: `0003-00233850` (8 dígitos). Primera corrida: 18 de 20 coincidieron con cargas a mano.
- No se usa: Pagar, medios de pago, alta/baja de suministros, perfil, notificaciones.
- Pendiente: lector para carga automática (por ahora las facturas quedan "para cargar a mano").
