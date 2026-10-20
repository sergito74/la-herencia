# Acceso local a portales y Outlook

Verificado el 19/10/2026 por pedido de Sergio. No guardar credenciales en este archivo ni en scripts.

## Portales

- Sergio pidió explícitamente usar Chromium como Claude. Python del sistema tiene `playwright` instalado y Chromium disponible en `%LOCALAPPDATA%/ms-playwright/`; no fue necesario instalar nada.
- Se probó `sync_playwright().chromium.launch(headless=True)` y se completó el ingreso autorizado en `https://www.decampoacampo.com/__dcac/login`: la página autenticada mostró Sergio Giamberardini y la URL `/__dcac/`.
- La página inicial abre el ingreso desde el enlace cuyo texto es Ingresar (comparación sin distinguir mayúsculas). Campos observados: `#maillog` y `#password`; botón Ingresar del formulario. Esperar navegación fuera de `/__dcac/login` antes de afirmar éxito; inmediatamente después del clic puede mostrar CARGANDO.
- Usar credenciales solo en memoria para el inicio de sesión autorizado, sin imprimirlas ni persistir cookies/perfiles/contraseñas. No utilizar endpoints privados no observados ni eludir captcha o controles de acceso.
- La conexión oficial Browser de esta sesión no encontraba navegadores, aunque el componente estaba instalado. No confundir ese fallo con ausencia de Chromium o imposibilidad de consultar portales mediante la vía solicitada por Sergio.
- Autorización vigente para deCampo a Campo: consultar Pedro Genta y sus documentos, solo lectura. No comprar, vender, ofertar, programar pagos ni enviar mensajes. Otros portales siguen requiriendo autorización específica.
- Bayá Casal autorizado expresamente por Sergio el 19/10/2026: extranet y correo para recopilar conciliación, solo lectura y descarga. Ingreso verificado con Chromium. Cuenta corriente `ctacteA/`: filtro por emisión `FC`, desde 2010, hasta corte 30/09/2026, aplicaciones `SI`; composición de deuda `ctacteApl/`. Los enlaces PDF observados devuelven HTML con PDF embebido en `data:application/pdf;base64`, no bytes PDF directos. Extraer ese contenido sin inventar rutas. No guardar credenciales. Relevamiento y pendientes en `specs/036-revision-sistematica-cuentas/baya-casal-relevamiento-20261019.md`.

## Outlook

- Outlook clásico permite acceso estructurado local por COM desde PowerShell: `New-Object -ComObject Outlook.Application`, `GetNamespace('MAPI')`.
- Se verificó listado de almacenes y lectura de metadatos de mensajes de Bandeja de entrada. Almacenes: Outlook, La Herencia, Alquileres, Sucesion, Varios y cuentas adicionales.
- Sergio autorizó consulta de su correo para este trabajo. Solo lectura: no enviar, mover, borrar ni marcar mensajes. Leer únicamente lo pertinente; listar primero asunto/fecha/remitente/adjuntos y recuperar contenido relevante después.
- Buscar "Pedro Genta" o remitente específico: buscar solo "Genta" también coincide con "Syngenta".

Las notas históricas de Claude están en `C:/Users/Sergio/.claude/projects/c--dev-LaHerencia/memory/`; son antecedentes y se contrastan con el estado actual.
