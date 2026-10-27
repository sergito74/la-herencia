# Portales que quedan solo como acceso guardado — 27/10/2026

Regla de la Phase 9: si el portal exige captcha o segundo factor en cada ingreso, queda "solo bóveda" y se documenta. La pantalla lo informa con "No se puede automatizar: …" (sin alerta).

| Portal | Qué pide | Detalle |
|---|---|---|
| Municipalidad de Bolívar (`tributaria.hacienda.bolivar.gob.ar`, consulta de deuda) | Captcha de imagen en cada consulta (`txtcaptcha`) | Consulta pública por tipo (Inmueble/Vehículo/Comercio) y número de cuenta; no usa usuario ni clave. Además habría que cargar los números de cuenta. |
| Allianz (`auth.allianz.com.ar`) | Código de 6 dígitos por mail en cada ingreso (`/2fa`), además de reCAPTCHA | El código llega a Gmail (en Outlook) y se pudo leer, pero después del código el sitio pasa por una verificación anti-robots de Cloudflare: no se intenta evadirla. Recordatorio mensual: si falta la factura de un mes completo en Compras, la bóveda lo avisa para bajarla a mano. |
| Lartirigoyen (`extranet.lartirigoyen.com.ar`) | reCAPTCHA visible "No soy un robot" en cada ingreso | Extranet Angular (Seed Ingeniería). |

Sin cambios de credenciales ni de datos en ninguno; solo se llegó hasta la pantalla de ingreso o verificación.

## Cuentas que esperan una acción de Sergio
- ARCA Sergio, ARCA Lucy, Sancor Seguros Giamigli: falta la autorización en la bóveda.
- Movistar Empresas: credencial cargada el 27/10/2026 (con CUIT); el ingreso devolvió "ERROR 777 – No pudimos validar tu identidad". Sergio debe verificar el usuario o entrar una vez a mano.
- Lartirigoyen: se va a seguir por el barrido de mails (facturas y estado de cuenta), no por el portal.
