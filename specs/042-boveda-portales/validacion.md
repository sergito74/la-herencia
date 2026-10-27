# Validación: 042 — Bóveda de portales

Registro de verificaciones ejecutadas (no de propuestas). Las contraseñas nunca se imprimieron: se compararon dentro del proceso.

## 27/10/2026 — Claude

### Esquema y migración (WC)

- `crear_esquema_boveda_042.py`: respaldo verificado `WC_esquema-boveda-042_20261027_100719_991001.bak`; 10 tablas creadas, 0 filas.
- `--migrar-037`: respaldo verificado `WC_boveda-migrar-037_20261027_101558_412994.bak`. Control de totales dentro de la transacción:

| Portal | Documentos 037 | Documentos bóveda | Corridas 037 | Corridas bóveda |
|---|---:|---:|---:|---:|
| TelepeajePlus | 43 | 43 | 7 | 7 |
| TelePASE | 51 | 51 | 7 | 7 |
| CEAMSE | 6 | 6 | 7 | 7 |
| AUBASA | 1 | 1 | 7 | 7 |

- Credenciales de peajes copiadas cifradas desde el keyring `LaHerencia-Peajes` (no se borraron del keyring): las 4 se descifran y coinciden con el keyring.
- `--registrar-portales`: 9 portales con autorización y contacto verificado en `Contactos` (Bayá Casal 226, Cargill 258, ARCA→AFIP 119, ARBA 12, Municipalidad de Bolívar 72, Sancor 171, Allianz 515, Jáuregui y Morales 48, Lartirigoyen 61). Sin credenciales ni conector (solo bóveda). Los enlaces de ARBA, Municipalidad, Sancor, Allianz y Lartirigoyen son generales y **sin verificar**; Jáuregui y Morales tiene un marcador `https://sin-enlace.invalid/` hasta que Sergio cargue el enlace.

### Corrida real por la bóveda (T035)

`servicio.correr_portal` manual de los 4 peajes: los 4 `ok`, ingreso con las credenciales de la bóveda; 0 nuevos, 96 ya registrados (AUBASA 1, CEAMSE 5, TelePASE 50, TelepeajePlus 40); sin descargas ni compras duplicadas. No hubo documentos nuevos, así que la carga automática al centavo no se ejercitó con un PDF real en esta corrida (sí con pruebas automáticas). Tarea de Windows de 037 **deshabilitada** (no eliminada).

### Búsqueda de secretos (T049, quickstart §2)

| Lugar | Revisado | Con contraseña |
|---|---|---:|
| Repositorio (versionado y sin versionar) | `git grep --untracked` de las 4 claves | 0 como valor aislado |
| Logs locales (`launcher`, `backend`, `%LOCALAPPDATA%\LaHerencia*`) | 14 archivos | 0 |
| Respuestas de la API (`/api/boveda/*`, `/api/descarga-peajes/*`, 13 portales) | 22 respuestas | 0 |
| Columnas de texto (`Boveda_Auditoria`, `Portales_Corridas`, `Boveda_Credenciales`) | 70 filas | 0 |

Las claves de CEAMSE y AUBASA (iguales entre sí, 6 dígitos) aparecen 41 veces en el repositorio **solo como parte de un número más largo** (un CUIT); nunca como número aislado: no es filtración. Observación para Sergio: son contraseñas débiles y repetidas; conviene cambiarlas en los portales y actualizar la bóveda.

### Pruebas automáticas

`pytest tests/boveda -q`: 40 pasan (cifrado y AAD, permisos 403 en todas las rutas para roles no administradores y 401 sin sesión, contrato de portales/credenciales sin secretos, revelar con `no-store` y auditoría, cálculo de próxima corrida, recuperación única, rechazo de credenciales con suspensión, intervención, revocación durante la corrida, documentos no PDF, carga al centavo con diferencias de $0,01 y $0,05). Ninguna escribe en `WC`.

Frontend: `tsc --noEmit` y `eslint` sin errores sobre los archivos tocados.

### Revisión de checkpoint (T052): ingeniería Python/seguridad, 27/10/2026

La hizo un agente con el rol `.github/agents/03-python-engineer.agent.md`, solo lectura. Encontró 9 defectos; quedaron todos corregidos y verificados:

1. **Clave maestra creada en silencio** si faltaba en el keyring (por otro usuario de Windows, por ejemplo), lo que dejaba ilegibles los secretos anteriores. Ahora nunca se crea en tiempo de ejecución si ya hay secretos guardados (`repository.clave_para_escribir`). Hay pruebas que lo cubren.
2. **Login fallido de peajes**: se mapeaba como "portal cambió" y se reintentaba en cada corrida. Ahora 037 levanta `ErrorIngreso`, que se trata como `CredencialesRechazadas`: suspende la programación y no reintenta. Hay prueba.
3. **Applock retenido por el pooling ODBC**: ahora se libera con `sp_releaseapplock` explícito. Verificado con prueba real contra WC y con dos corridas reales seguidas de CEAMSE (ambas `ok`).
4. **`tomar_lock`**: ahora usa `SET NOCOUNT ON` y recorre `nextset()`, igual que `connection.py`.
5. **Dato pasado a secreto sin valor**: quedaba en texto plano. Ahora se exige el valor (devuelve 400).
6. **`editar_credencial`**: daba 500 si faltaba la clave maestra. Ahora devuelve 503, y la clave se pide solo si se cifra algo.
7. **Alta de portal fallida**: dejaba una credencial huérfana. Ahora se deshace.
8. **Autorizar**: la autorización nueva y la revocación de la anterior ahora van en una sola transacción.
9. **`PATCH /portales`**: un `null` en nombre, url o tipo daba 500. Ahora devuelve 422.

Sugerencias aplicadas:
- La sesión del conector ya no guarda la clave en claro (`repr=False`).
- Los mensajes de corrida y los registros enmascaran usuario y clave.
- El redondeo ahora es `ROUND_HALF_UP`.
- Una corrida programada "salteada" ya no se reprograma: se reintenta en el siguiente tick.
- En la exportación de la clave, scrypt pasa a N=2^17 (el valor queda guardado en el archivo) y la exportación no pisa un archivo existente.

No aplicada: el GET de documentos y de resumen sigue revalidando los pendientes por fila. Es el criterio de 037 y con este volumen es aceptable.

Pruebas: `pytest tests/boveda` dio 44 pasan y 1 omitida (la prueba real del lock, que pasa con `LA_HERENCIA_TEST_WC=1`). Las pruebas de 037 (`test_descarga_peajes_*`) dieron 29 pasan. `npm run build` del frontend pasó.

Pendiente: la revisión de dirección financiera (agente 07) de la comparación de saldos y de la carga automática. Se hace con el primer conector que traiga estado de cuenta (Cargill o Bayá Casal).
