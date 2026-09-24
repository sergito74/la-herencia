# Auditoría de lentitud — 24/09/2026

Auditoría local alrededor de las 11:30 (Argentina), sobre `fc486e7`, con árbol Git inicialmente limpio. No se cambiaron datos, configuración ni procesos del usuario. Las consultas se abrieron contra WC; no se ejecutaron cálculos que persistan propuestas.

## Contexto actual

Se revisaron la guía compartida, Constitución, memoria histórica, diseños de navegación ERP/Tierra & Cultivo, plan/tareas de 017 y cambios recientes. El sistema actual es Next.js + FastAPI + SQL Server WC. Los últimos cambios incorporan calendario agrícola, informe de imputación por documento y Excel, filtros, consultas por lote, aprobación masiva/en línea y usuario aprobador. El motor 017 propone clasificaciones en paralelo al costeo heredado 012. La memoria de septiembre 15 y los estados pendientes del diseño son históricos: no describen fielmente todo lo ya implementado.

## Hallazgos y evidencia

1. **No hay un servidor web colgado en la muestra.** No había procesos Python/Node ni escuchas 3000/8000. El último registro de API termina con `POST /api/sesion/cierre` exitoso y sondeos de estado exitosos. Es compatible con el apagado automático del launcher; no prueba por sí solo la causa del cierre. No hay traceback en backend.err.log ni error de aplicación en frontend.err.log.

2. **Poco margen de memoria.** Windows informó 12.356.816 KB de RAM utilizable y alrededor de 1.100–1.200 MB libres. Sumas de conjuntos de trabajo: VS Code ~2.871 MB (20 procesos), Chrome ~1.454 MB (11), WebView2 ~1.286 MB (20). Estas sumas pueden contar memoria compartida más de una vez. CPU total 16%, disco sin cola y lecturas de paginación 0 en una muestra posterior: no demuestran saturación sostenida ni una fuga. No corresponde cerrar procesos del usuario indiscriminadamente.

3. **Demora real por compilación durante el uso.** `launcher/LaHerencia.ps1` inicia `npm run dev`. El log registra arranque de Next.js en 12,4 s y compilación de `/produccion/planificacion` en 16,4 s; otras pantallas tardan entre 435 y 999 ms y la inicial 2,3 s. Es una fuente comprobada de espera. Para uso cotidiano conviene un arranque con build validado y `next start`, conservando un modo desarrollo explícito.

4. **Imputación puede bloquear toda la API.** `backend/src/features/imputacion/router.py` declara handlers async pero ejecuta directamente consultas ODBC, FIFO y exportaciones síncronas. El lock asyncio de `_asegurar_corrida` serializa accesos pero no libera el bucle que atiende las demás peticiones. Reproducción aislada sin SQL: sustituir el trabajo de `trazabilidad_insumo` por una espera de 0,5 s demoró una tarea concurrente prevista para 0,01 s hasta 0,501 s. Confirma el defecto de concurrencia, no la duración real de las consultas ni que haya causado el episodio informado. Planificación y Remitos ya usan `run_in_threadpool` como patrón local.

5. **El vigilante puede agravar un cálculo lento.** El launcher sondea sesión con timeout de 5 s; tras tres fallos posteriores a haber visto el backend disponible ejecuta `Stop-All`, que fuerza el cierre del árbol de procesos. Si imputación impide atender esos sondeos, puede provocar un apagado durante trabajo legítimo. Es un riesgo derivado del código; no se observó esa secuencia en el log de esta sesión. Faltan registros con motivo y hora del apagado.

6. **Trabajo repetido y esperas sin límite explícito.** La lista de pendientes de intervención vuelve a evaluar cada fila (hasta 200); el cálculo masivo acepta hasta 2.000 candidatos de cada origen y evalúa cada uno. Para insumos se reconstruye stock por producto, pudiendo repetirlo entre renglones del mismo producto. La capa central ODBC no configura timeout explícito de conexión/consulta. No se ejecutó la corrida masiva ni se cuantificó su duración.

7. **SQL sin bloqueo de usuarios en la muestra.** Consultas de diagnóstico: ~8–9 ms; conteo de 10.553 propuestas en WC: ~9 ms. No había peticiones de usuario bloqueadas; la única sesión de usuario ajena era SQLServerCEIP, dormida y con cero transacciones abiertas. Las tareas internas PARALLEL REDO estaban esperando, sin bloqueador y con CPU 0: su antigüedad no prueba un cuelgue. Un SELECT rápido no acredita el rendimiento de todas las consultas funcionales.

## Prioridad de corrección

1. Sacar SQL/cálculos síncronos del bucle de atención de imputación, preservando la exclusión de corridas y validando dos peticiones concurrentes junto a los latidos de sesión.
2. Evitar que un sondeo fallido mate una operación en curso; registrar motivo de cierre y diferenciar inactividad, cierre de pestañas e indisponibilidad.
3. Separar arranque de uso cotidiano del modo desarrollo para no compilar al navegar.
4. Medir rutas reales con tiempos por consulta/cálculo; después reutilizar cálculos por producto dentro de cada corrida y definir límites de espera. Revisar memoria con la aplicación abierta antes de atribuir una fuga.

## Alcance y límites

Diagnóstico de procesos/recursos, lectura de código y logs, SELECT de diagnóstico SQL y reproducción de concurrencia con trabajo simulado. No se reinició la aplicación ni se reprodujo navegación autenticada; no se alteraron Access, base oficial, WC o aplicaciones abiertas. La auditoría identifica causas de demora y un defecto reproducible, pero no permite adjudicar con certeza un episodio pasado a una sola causa.

## Correcciones aplicadas para pruebas de usuario

- Router de imputación: ODBC/FIFO/Excel en threadpool, conservando lock de creación de corridas. 25 pruebas focalizadas pasaron, incluidas atención concurrente y no duplicación.
- Launcher: versión compilada por defecto, `-Dev` opcional; validación de build antes de iniciar; sondeos fallidos no matan procesos y registran advertencia.
- Compilación completa de Next.js exitosa (incluye lint y TypeScript). Se corrigieron comillas JSX en CargaExcel que impedían el build.
- Backend escucha en ambas direcciones de localhost (127.0.0.1 y ::1). Medición previa: health por localhost 2,054 s y por IPv4 0,004 s. Después: localhost 0,066 s, IPv4 0,016 s, IPv6 0,014 s.
- Next start listo en 828 ms. Entrega HTTP de Planificación: 139 ms; página de documentos: 29 ms. Son tiempos de entrega HTML, no de carga completa autenticada. Handler de documentos con lectura real de 20 documentos WC: 1,042 s.
- Procesos Node/Python del sistema sumaron ~195 MB de conjuntos de trabajo en la muestra posterior. No se cerraron aplicaciones ajenas. Se reiniciaron únicamente backend/vigilante creados en esta intervención.
- Sistema iniciado en localhost:3000. No se realizaron escrituras de negocio ni cambios de esquema. El launcher conserva su cierre por inactividad y su plazo de 120 s si nunca se abre una pestaña.
