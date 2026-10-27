# Quickstart / validación: 042 — Bóveda de portales

## Requisitos previos

- Backend con `.venv` (`cryptography`, `keyring`, `playwright` ya instalados) y frontend levantados con `launcher/LaHerencia.ps1`.
- Respaldo verificado de `WC` antes de `crear_esquema_boveda_042.py`.
- Usuario Administrador (Sergio) y un usuario de otro rol para la prueba negativa.

## 1. Esquema y migración de peajes

```powershell
backend\.venv\Scripts\python backend\scripts\crear_esquema_boveda_042.py --dry-run
backend\.venv\Scripts\python backend\scripts\crear_esquema_boveda_042.py --aplicar
```
Esperado: 4 portales de peaje con autorización 16/10/2026, programación semanal igual a la tarea actual, credenciales copiadas cifradas, historial y documentos de 037 copiados (mismos totales que `DescargaPeajes_*`). Bayá Casal, Cargill y los 7 portales del 27/10 registrados con autorización; los sin conector, "solo bóveda".

## 2. Seguridad (SC-001, SC-002)

- `SELECT` sobre `Boveda_Credenciales`: `ClaveCifrada` ilegible; con la base restaurada en otra instancia y sin la clave maestra, `revelar` falla.
- Buscar cada contraseña conocida en: logs del backend, `git grep`, respuestas de `GET /api/boveda/*` → 0 coincidencias.
- Con usuario no administrador: menú sin "Bóveda" y `GET /api/boveda/portales` → 403.
- `revelar` devuelve el valor y deja fila `revelar` en `Boveda_Auditoria`.

## 3. Alta de portal nuevo (US1, US5, SC-003)

Agregar un portal de prueba con URL y credencial → aparece "solo bóveda", sin programación ni "Correr ahora"; "Abrir portal" abre la URL.

## 4. Autorización (US4)

Revocar la autorización de un peaje → "Correr ahora" responde "Falta autorización" y la programación no lo dispara. Volver a autorizar.

## 5. Programación (US2, SC-004)

Programar un peaje "diaria" a la hora actual + 2 min → corre solo. Cerrar la app pasada la hora, reabrir → corre una sola vez dentro de los 15 min. Dos "Correr ahora" seguidos → el segundo recibe 409.

## 6. Descarga y carga (US3, SC-005, SC-006)

Correr los 4 peajes: mismos resultados que con 037; correr de nuevo → 0 nuevos. Para un conector con `leer_comprobante` (ej. Bayá Casal) verificar compra creada solo si cierra exacto y con rubro/centro; si no, pendiente con motivo.

## 7. Estado de cuenta (SC-007)

Correr Cargill → foto en US$ con saldo portal, saldo sistema y diferencia al centavo; cualquier diferencia ≠ 0,00 suma en el contador del menú.

## 8. Fallas (US6)

Contraseña errónea en un portal de prueba → `credenciales_rechazadas`, sin reintento, programación suspendida; actualizar la clave levanta la suspensión. Los demás portales de la misma tanda terminan igual.

## 9. Pruebas automáticas

`backend\.venv\Scripts\python -m pytest backend/tests/boveda -q` (cifrado ida/vuelta y AAD, cálculo de próxima corrida, permisos 403, contrato de API con repositorio simulado; no escriben en `WC`). `npm run build` en `frontend`.

## 10. Respaldo de la clave maestra (hacerlo una vez, y de nuevo si cambia el equipo)

La clave que descifra las contraseñas de la bóveda vive solo en el Administrador de credenciales de Windows de este equipo (servicio `LaHerencia-Boveda`). Se creó el 27/10/2026 al migrar los peajes. Sin ella (equipo nuevo, Windows reinstalado), las contraseñas de la bóveda hay que volver a cargarlas a mano.

Respaldo (lo corre Sergio en una consola; pide una frase de recuperación de al menos 12 caracteres, que no se muestra):

```powershell
cd C:\dev\LaHerencia\backend
.venv\Scripts\python -m scripts.boveda_clave exportar D:\respaldo\laherencia-boveda.lhkey
```

- El archivo no puede quedar dentro del repositorio ni de Dropbox (el script lo rechaza).
- Guardar el archivo y la frase **por separado** (ej. archivo en un pendrive, frase en papel).
- Restaurar en otro equipo: `python -m scripts.boveda_clave importar <archivo.lhkey>` (no pisa una clave distinta ya instalada).
