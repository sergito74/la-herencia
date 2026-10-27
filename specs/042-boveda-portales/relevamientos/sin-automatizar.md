# Portales que quedan solo como acceso guardado — 27/10/2026

Regla de la Phase 9: si el portal exige captcha o segundo factor en cada ingreso, queda "solo bóveda" y se documenta. La pantalla lo informa con "No se puede automatizar: …" (sin alerta).

| Portal | Qué pide | Detalle |
|---|---|---|
| Municipalidad de Bolívar (`tributaria.hacienda.bolivar.gob.ar`, consulta de deuda) | Captcha de imagen en cada consulta (`txtcaptcha`) | Consulta pública por tipo (Inmueble/Vehículo/Comercio) y número de cuenta; no usa usuario ni clave. Además habría que cargar los números de cuenta. |
| Allianz (`auth.allianz.com.ar`) | Código de 6 dígitos por mail en cada ingreso (`/2fa`), además de reCAPTCHA | El código llega a Gmail (en Outlook) y se pudo leer, pero después del código el sitio pasa por una verificación anti-robots de Cloudflare: no se intenta evadirla. Recordatorio mensual: si falta la factura de un mes completo en Compras, la bóveda lo avisa para bajarla a mano. |
| Lartirigoyen (`extranet.lartirigoyen.com.ar`) | reCAPTCHA visible "No soy un robot" en cada ingreso | Extranet Angular (Seed Ingeniería). |

## Ingreso asistido (pedido de Sergio, 27/10/2026)
Botón "Entrar con ayuda" (`POST /api/boveda/portales/{id}/asistido`, `features/boveda/asistido.py`): abre Chrome visible en esta computadora. Allianz: completa usuario, clave y el código del mail (leído de Outlook, solo lectura); la verificación anti-robots la pasa Sergio. Movistar Empresas: rechaza con "ERROR 777" cualquier ingreso tipeado por el sistema (probado 4 veces, también con Chrome visible), así que la ventana se abre sin completar y Sergio escribe usuario y clave. Lo que se descarga en la ventana se guarda en Compras del ejercicio (`AAAAMMDD_Allianz.pdf` / `AAAAMMDD_Movistar.pdf`) y se registra en la cuenta sin duplicar. Recordatorio mensual de factura faltante para ambas.

Sin cambios de credenciales ni de datos en ninguno; solo se llegó hasta la pantalla de ingreso o verificación.

## Cuentas que esperan una acción de Sergio
- ARCA Sergio, ARCA Lucy, Sancor Seguros Giamigli: falta la autorización en la bóveda.
- Lartirigoyen: se va a seguir por el barrido de mails (facturas y estado de cuenta), no por el portal.
