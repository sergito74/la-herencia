---
description: "Tareas de implementación de impuestos particulares a cargo de socios"
---

# Tasks: Impuestos particulares (041)

**Fecha**: 25/10/2026. **Entrada**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md).

**Organización**: tres historias, por prioridad. Todas las tareas pendientes; este documento no autoriza afirmar que el módulo está implementado ni ejecutar ahora la migración. Se conserva el diseño aprobado y el stack existente: FastAPI/Python, SQL Server WC, Next.js/TypeScript y TanStack Query.

**Pruebas**: solicitadas por plan/quickstart; pytest con pyodbc bloqueado, sin datos reales. Escribir primero las pruebas del incremento y comprobar el fallo esperado; después implementar y verificar. Las comprobaciones reales del caso 3206 se ejecutan como migración controlada, nunca como fixture de pytest.

**Formato**: `- [ ] Tnnn [P] [USn] Descripción con ruta`. `[P]` indica archivos independientes, una vez satisfechas las dependencias; no autoriza lanzar agentes sin pedido del usuario.

## Fase 1: Preparación

**Objetivo**: contrastar el diseño con el código actual y dejar explícitas las decisiones necesarias antes de las escrituras.

- [ ] T001 Contrastar esquema WC y consumidores existentes mediante lecturas acotadas de `backend/src/features/impuestos/repository.py`, `backend/src/features/cuentas_socios/repository.py`, `backend/src/features/flujo_caja/atribucion.py` y `backend/src/features/revision_cuentas/datos.py`; registrar identificadores reales, cierre de cuentas, autenticación, orígenes y estado de los asientos manuales del 3206 en `specs/041-impuestos-particulares/research.md`, sin mutar datos.
- [ ] T002 Resolver y documentar antes de implementar en `specs/041-impuestos-particulares/contracts/api.md` y `specs/041-impuestos-particulares/data-model.md` los detalles no fijados: capacidad/reparto de un Haber entre cargas, importe al vincular un Haber mayor que el pendiente, anulación con devoluciones vinculadas, conflicto de titulares de una partida y forma de introducir/consultar una partida sin añadir columnas a Impuestos; precisar también la ventana de «fecha cercana» de FR-011 reutilizando una regla existente si la hay, sin decidirla silenciosamente en código.

## Fase 2: Base compartida

**Bloquea las historias**: esquema, tipos y transacciones verificables. La migración funcional del 3206 permanece diferida a la fase final.

- [ ] T003 Preparar DDL aditivo e idempotente en `backend/scripts/migrar_impuestos_particulares_041.py` para las tres tablas de `data-model.md`, referencias e índices; respetar «IdCarga int IDENTITY PK», «IdImpuesto int NOT NULL», «IdSocio int NOT NULL», «Importe decimal(18,2) NOT NULL», «Motivo nvarchar(255) NOT NULL», «Partida nvarchar(60) NULL», «IdMovimientoSocio int NOT NULL» y «Estado varchar(10) NOT NULL» con «'vigente' / 'anulada'»; no alterar dbo.Impuestos ni el índice único de socios. Separar preparación de esquema de la migración de datos del 3206; cualquier aplicación real exige WC y respaldo verificado.
- [ ] T004 [P] Definir modelos tipados de cargas, avisos, devoluciones, padrón y errores en `backend/src/features/impuestos/schemas.py`, reflejando `contracts/api.md`: «importe | porcentaje», motivo obligatorio, partida opcional, estados vigente/anulada y devuelto/parcial/pendiente; validar exclusión entre importe y porcentaje, magnitudes positivas y longitudes fijadas en el modelo, sin convertir importes monetarios mediante float en la lógica de cálculo.
- [ ] T005 Establecer en `backend/src/features/impuestos/particular.py` las primitivas compartidas de lectura/escritura parametrizada, transacción única, usuario de sesión y auditoría; resolver dentro de la transacción la creación de IdCarga y su Debe enlazado con «Origen 'ImpuestoParticular', IdOrigen = IdCarga» e «IdMovimientoSocio int NOT NULL», sin dejar huérfanos ni estados parciales; usar las conexiones centrales exclusivas de WC.
- [ ] T006 [P] Crear fixtures simuladas y bloqueo explícito de pyodbc en `backend/tests/test_impuestos_particulares_041.py` para impuesto, socios, cierre, Debe/Haber y cotizaciones; incluir un mecanismo para comprobar rollback y escrituras capturadas sin acceder a WC, LaHerencia ni Access.

**Control de salida**: esquema revisable, modelos coherentes con contrato y transacciones simulables. No hay datos del 3206 migrados todavía.

## Fase 3: US1 — Cargar un impuesto a un socio (P1, MVP)

**Objetivo**: carga total o parcial, Debe único, trazabilidad y exclusión proporcional del costo empresarial, manteniendo intacta la cuenta del organismo.

**Prueba independiente**: con fixtures del 3206, cargar $8.852,10 al Condominio; un solo Debe al 07/11/2017 y 100% US$ positivo, sin duplicar el manual; boleta, pago y saldo ARBA iguales. Caso parcial $6.000/$10.000: $6.000 a Cuenta de socios y $4.000 a costo de empresa.

- [ ] T007 [US1] Escribir en `backend/tests/test_impuestos_particulares_041.py` pruebas de carga total, importe parcial/porcentaje, varios socios por impuesto, impuesto sin pago vinculado, ausencia de cotización, límites/longitudes, duplicación, rol Lectura, cierre con/sin confirmación, reemplazo manual y rollback; probar «> 0; Σ vigentes por impuesto ≤ Impuestos.Importe», incluida concurrencia que intenta superar el total.
- [ ] T008 [US1] Implementar creación y validaciones en `backend/src/features/impuestos/particular.py`: comprobar impuesto/socio reales, suma vigente bajo bloqueo transaccional, rechazo 409 por exceso, motivo obligatorio y asignación por boleta aunque un pago cubra varias; admitir impuesto sin pago vinculado y «1 Sergio, 2 Lucy, 3 Condominio LSC, 4 Ceci», sin repartir Condominio entre condóminos.
- [ ] T009 [US1] Generar el Debe desde `backend/src/features/impuestos/particular.py` usando `backend/src/features/cuentas_socios/valuacion.py::a_fecha` a la fecha del impuesto: antes del 16/03/2020, 100% US$; desde esa fecha, 50% US$ y 50% kg INMAG; almacenar dólares/kg siempre positivos y dejar el signo al Tipo, preservando excepciones/mutuos existentes; cargar exactamente una representación por IdCarga.
- [ ] T010 [US1] Implementar en `backend/src/features/impuestos/particular.py` detección de Debe manual equivalente, aviso 409 y reemplazo solo del movimiento indicado y validado; exigir confirmación explícita de cuenta cerrada en servidor; anular el manual conservando historial y crear el vinculado en la misma transacción, sin buscar ni sustituir por importe solamente.
- [ ] T011 [US1] Añadir GET `/{id}/particular` y POST `/{id}/particular` en `backend/src/features/impuestos/router.py`, conectando schemas y servicio con ejecución apropiada de SQL síncrono, 409 estructurado/`requiereConfirmacion`, no encontrado y protección 403 de escrituras para Lectura; registrar rutas específicas sin colisión con rutas dinámicas existentes.
- [ ] T012 [P] [US1] Incorporar tipos y llamadas de consulta/carga de `contracts/api.md` en `frontend/src/services/impuestosApi.ts`, conservando el cliente y manejo de errores existentes e incluyendo los avisos y confirmaciones explícitas.
- [ ] T013 [US1] Extender `backend/src/features/cuentas_socios/repository.py` para resolver el origen ImpuestoParticular por IdCarga y mostrar impuesto/boleta de origen en el listado de socios, conservando anulados y magnitudes positivas; no convertir el contacto bancario del socio en una segunda cuenta de deuda.
- [ ] T014 [US1] Implementar atribución proporcional por boleta en `backend/src/features/flujo_caja/atribucion.py::partes_desde_aplicaciones`: parte cargada → rubro «Cuenta de socios», centro «Socios»; resto → rubro original; preservar salida total, moneda y evitar duplicación cuando un pago tiene varias aplicaciones; no tocar conciliación/FIFO ni impuestos en resultado por cultivo, que hoy no los incorpora.
- [ ] T015 [P] [US1] Incorporar en `backend/src/features/revision_cuentas/datos.py` la indicación «cargado a socio» para carga total y el desglose empresarial para carga parcial; conservar la lectura del impuesto completo y el saldo del organismo, sin tratar la parte de socio como costo empresarial pendiente.
- [ ] T016 [US1] Añadir en `backend/tests/test_impuestos_particulares_041.py` verificaciones de atribución/revisión y trazabilidad: suma de partes igual a salida, pago mixto de varias boletas, boleta y cuenta ARBA intactas, ningún cobro o compensación automática, sin doble registro al reintentar o reemplazar.
- [ ] T017 [US1] Crear `frontend/src/components/impuestos/ImpuestoParticularPanel.tsx` y montarlo en la ficha existente de `frontend/src/components/impuestos/ImpuestosListado.tsx`: socio, importe o porcentaje, motivo y partida, remanente, avisos de duplicado/cierre con confirmación explícita y estados vacío/carga/error; ocultar o deshabilitar acciones al rol Lectura; invalidar consultas de impuesto, socios, revisión y flujo tras guardar con TanStack Query.
- [ ] T018 [US1] Validar el recorrido total/parcial y el caso manual equivalente en `specs/041-impuestos-particulares/quickstart.md`, registrando evidencia en `specs/041-impuestos-particulares/validacion.md`; verificar como criterio de aceptación la carga en menos de un minuto y no marcar US1 terminada solo por compilar.

## Fase 4: US2 — Ver cargas y devoluciones (P1)

**Objetivo**: consultar socio/importe, devolver total o parcialmente, mostrar saldo pendiente y proponer titulares por partida sin cargar automáticamente.

**Prueba independiente**: una carga con Haber vinculado del mismo socio figura devuelta; sin Haber, pendiente; con devolución parcial, parcial y con deuda residual. Un impuesto de partida conocida avisa el titular, pero no crea un Debe hasta que el usuario lo confirme.

- [ ] T019 [US2] Escribir pruebas de devoluciones nuevas/existentes y estados en `backend/tests/test_impuestos_particulares_041.py`: varios Haber, devolución parcial, Haber de otro socio/anulado, vínculo duplicado y capacidad reutilizada, remanente, deuda sin devolución, ausencia de cancelación automática, partida conocida/Oscar y filtro de listado paginado.
- [ ] T020 [US2] Implementar vínculo a Haber existente y creación de Haber nuevo en `backend/src/features/impuestos/particular.py`, según las decisiones de T002: «PK (IdCarga, IdMovimientoSocio)», Haber «del mismo socio», validación transaccional de capacidad y referencia; nuevo Haber con «Origen='DevolucionImpuestoParticular', IdOrigen=IdCarga», magnitudes positivas y valuación vigente de su fecha; no crear un cobro bancario/caja ni duplicar el Haber existente.
- [ ] T021 [US2] Calcular cargas y devoluciones en `backend/src/features/impuestos/particular.py`: «aCargoDeSocios = Σ cargas vigentes», «parteEmpresa = Importe − aCargoDeSocios», «devuelto = Σ devoluciones» y devuelto/parcial/pendiente; conservar deuda no cancelada y reconocer compensaciones únicamente mediante asientos explícitos válidos conforme a FR-007, sin deducir reintegro por coincidencia de importe.
- [ ] T022 [US2] Implementar padrón en `backend/src/features/impuestos/particular.py`: «Partida (PK), IdSocio, IdCargaOrigen, Fecha, Usuario», alimentado solo por cargas con partida, con conflictos resueltos según T002; Oscar siempre a socio3 Condominio, sin titular Oscar separado; proponer titular al abrir/crear con partida conocida, sin carga automática ni importación masiva del padrón.
- [ ] T023 [US2] Incorporar POST `/particular/{idCarga}/devoluciones` y GET `/partidas/{partida}` en `backend/src/features/impuestos/router.py`; ampliar GET `/` y `backend/src/features/impuestos/repository.py` con `aCargoDe`, estado de devolución y filtro `particular=true`, conservando filtros y paginación y evitando consultas por fila; no agregar partida ni marca a dbo.Impuestos.
- [ ] T024 [P] [US2] Extender `frontend/src/services/impuestosApi.ts` con devolución existente/nueva, consulta de partida y parámetros/campos de listado aprobados; reflejar importes devueltos y pendientes sin recomputar reglas financieras en el navegador.
- [ ] T025 [US2] Extender `frontend/src/components/impuestos/ImpuestoParticularPanel.tsx` con detalle de cargas, devoluciones enlazadas, saldo y acciones para vincular Haber o registrar uno nuevo; integrar aviso de partida conocida en `frontend/src/components/impuestos/ImpuestoForm.tsx` conforme a T002, con confirmación humana y tratamiento legible de errores, sin crear automáticamente cobros.
- [ ] T026 [P] [US2] Añadir etiquetas por socio/importe, estado devuelto/parcial/pendiente y filtro «a cargo de socio» en `frontend/src/components/impuestos/ImpuestosListado.tsx`, manteniendo la boleta completa y soportando más de un socio; invalidar las consultas afectadas al registrar una devolución.
- [ ] T027 [US2] Ejecutar las pruebas focalizadas de US2 y verificar lista/ficha con cero, una y varias cargas/devoluciones y padrón conocido en `specs/041-impuestos-particulares/validacion.md`; confirmar que todas las cargas vigentes aparecen y que los importes sin devolver permanecen como deuda del socio.

## Fase 5: US3 — Anular una carga a socio (P2)

**Objetivo**: revertir una carga conservando historial y recuperar costos empresariales; bloquear la baja de boleta con cargas vigentes.

**Prueba independiente**: anular una carga con motivo deja el Debe anulado/auditado y devuelve su parte a costos; mientras haya cargas vigentes, DELETE de la boleta responde 409. Las devoluciones existentes se conservan conforme a T002.

- [ ] T028 [US3] Escribir en `backend/tests/test_impuestos_particulares_041.py` pruebas de anulación, motivo obligatorio, repetición, rollback, rol Lectura, carga ya anulada, carga con devoluciones y rechazo de baja de boleta con al menos una carga vigente; verificar que anular una de varias cargas solo devuelve su parte a costos.
- [ ] T029 [US3] Implementar anulación transaccional en `backend/src/features/impuestos/particular.py`: «Estado varchar(10) NOT NULL» pasa a «'anulada'», con MotivoAnulacion/AnuladoPor/AnuladoEn, y Debe anulado con usuario/fecha/motivo; preservar cargas, referencias y Haber/devoluciones conforme al comportamiento resuelto en T002, sin borrar ni cancelar un Haber ajeno automáticamente.
- [ ] T030 [US3] Incorporar POST `/particular/{idCarga}/anular` en `backend/src/features/impuestos/router.py` y bloquear la baja con 409 tanto en ruta como en la operación efectiva de `backend/src/features/impuestos/repository.py` mientras existan cargas vigentes; proteger contra carrera entre baja y nueva carga con la misma transacción/bloqueo y conservar 403 para Lectura.
- [ ] T031 [P] [US3] Añadir llamada de anulación y manejo de 409 en `frontend/src/services/impuestosApi.ts`, conservando motivo y errores estructurados del contrato.
- [ ] T032 [US3] Añadir acción de anular con motivo e historial visible en `frontend/src/components/impuestos/ImpuestoParticularPanel.tsx`, y explicación del bloqueo de baja en `frontend/src/components/impuestos/ImpuestosListado.tsx`; invalidar impuesto, cuenta de socio, flujo, revisión y avisos de partida afectados, sin ocultar los registros anulados.
- [ ] T033 [US3] Verificar devolución proporcional a costos en `backend/src/features/flujo_caja/atribucion.py` y `backend/src/features/revision_cuentas/datos.py` al anular, junto con los casos de baja y anulación en `specs/041-impuestos-particulares/validacion.md`; confirmar que no cambia el saldo del organismo ni se pierden referencias del historial.

## Fase 6: Migración y validación transversal

**Objetivo**: sustituir el caso manual 3206 y entregar el módulo comprobado, con evidencia compartida para Claude y Codex.

- [ ] T034 Probar la migración y una segunda ejecución sin escrituras en `backend/tests/test_impuestos_particulares_041.py`, con fixtures del3206: saldo nominal y valuado del Condominio idéntico, magnitudes positivas, Debe único, Haber conservado, estado devuelto, ARBA/boleta/pagos/aplicaciones intactos y total de flujo conservado; si el Debe manual no coincide con la fecha/valuación requeridas, detener la aplicación y documentar la diferencia en `specs/041-impuestos-particulares/validacion.md`, sin inventar un ajuste.
- [ ] T035 Completar la migración de datos idempotente del 3206 en `backend/scripts/migrar_impuestos_particulares_041.py`, con inspección por defecto y `--aplicar`: identificar por claves/datos reales el Debe manual y Haber existentes, rechazar ambigüedades, crear cargaCond8852,10 a fecha07/11/2017, anular/reemplazar solo el Debe manual del25/10/2026 y vincular el Haber13/11/2017 sin duplicarlo ni reclasificar el banco18537; fotografiar saldos/cotizaciones, registrar auditoría y asegurar rollback completo ante cualquier fallo.
- [ ] T036 Aplicar el esquema/migración3206 mediante `backend/scripts/migrar_impuestos_particulares_041.py` solo tras inspección satisfactoria y respaldoWC verificado; registrar ruta de respaldo, snapshot de controles, resultado y repetición idempotente en `specs/041-impuestos-particulares/validacion.md`; no escribir en LaHerencia ni Access ni alterar Impuestos para almacenar las cargas.
- [ ] T037 Ejecutar pytest focalizado041 con pyodbc bloqueado sobre `backend/tests/test_impuestos_particulares_041.py`, TypeScript sin emisión y ESLint de `frontend/src/components/impuestos/ImpuestoParticularPanel.tsx`, `frontend/src/components/impuestos/ImpuestosListado.tsx`, `frontend/src/components/impuestos/ImpuestoForm.tsx` y `frontend/src/services/impuestosApi.ts`; registrar resultados reales en `specs/041-impuestos-particulares/validacion.md` y corregir fallos del alcance.
- [ ] T038 Abrir y verificar en navegador el flujo real desde `frontend/src/app/finanzas/impuestos/page.tsx`: caso3206 devuelto, Debe enlazado e historial, rol Lectura, permisos, confirmaciones, errores/vacíos, lista/filtro, propuesta de partida y lectura de flujo/revisión; usar datos simulados o inspección del caso migrado para evitar crear cargas financieras reales de prueba; completar los10 escenarios de `specs/041-impuestos-particulares/quickstart.md` con evidencia en `specs/041-impuestos-particulares/validacion.md`.
- [ ] T039 Actualizar `specs/041-impuestos-particulares/quickstart.md`, `specs/041-impuestos-particulares/tasks.md` y `specs/041-impuestos-particulares/validacion.md` con decisiones finales, controlesSC001–SC004, limitaciones y continuidad compartida; revisar diff para excluir respaldos/credenciales/artefactos, y marcar tareas terminadas solo con evidencia del comportamiento requerido.

## Dependencias y orden

```text
T001 → T002 → base T003–T006
  → US1 T007–T018 (MVP)
    → US2 T019–T027
    → US3 T028–T033 (tras US2 para probar cargas con devoluciones)
      → migración T034–T036
        → comprobaciones y documentación T037–T039
```

- T003 y T004 pueden prepararse por separado después de T002; T005 depende del esquema/modelos; T006 puede avanzar en archivo independiente.
- US2 y US3 necesitan una carga válida de US1, pero cada una se verifica con fixtures propias. US3 espera a US2 para resolver y probar las devoluciones vinculadas, sin compartir implementaciones a medio hacer.
- T012 sigue a T004/contrato y puede avanzar mientras T008–T011 se implementan. T014 y T015 tienen archivos distintos; completar T016 después de ambas.
- T024 requiere T019 y contrato estable; T026 espera T023/T024 y no se ejecuta simultáneamente con T017/T032 porque comparten listado.
- T031 puede avanzar después de T028 con contrato estable mientras se implementan T029–T030; T032 espera T030/T031.
- Las tareas del mismo archivo se serializan: `particular.py`, `schemas.py`, `router.py`, pruebas, panel, listado y serviciofrontend. Las validaciones reales y escriturasWC nunca se paralelizan.

## Ejemplos de trabajo paralelo por historia

- **US1**: T014 (`flujo_caja/atribucion.py`) y T015 (`revision_cuentas/datos.py`), tras disponer del servicio de cargas; T012 (`impuestosApi.ts`) en paralelo con backend, con contrato/modelos ya definidos.
- **US2**: T024 (`impuestosApi.ts`) junto a T020–T023 del backend; después T025 (panel/formulario) y T026 (listado) en archivos distintos cuando tipos y endpoints estén estables.
- **US3**: T031 (`impuestosApi.ts`) junto a T029–T030 del backend; T032 y T033 pueden verificarse en frentes diferentes una vez integradas las APIs, sin editar simultáneamente los mismos archivos.

## Estrategia incremental y cobertura

1. Preparar base y validar contrato/esquema sin migrar el3206.
2. **MVP: US1**, incluyendo costo proporcional y trazabilidad; no posponer esos efectos para después de crear deudas.
3. Completar US2 (devoluciones/padrón) y US3 (anulación/baja protegida).
4. Migrar3206 una sola vez con controles nominales/valuados y verificar ARBA, salidaBNA y vínculo de devolución. No declarar el caso devuelto antes de que exista el vínculo al Haber.
5. Completar validación de navegador y documentación compartida. No ejecutar tareas de conciliación036 ni refactors ajenos como parte de041.

| Requisitos / criterios | Tareas principales |
|---|---|
| FR001–FR003, FR010–FR011 | T004–T011, T017–T018 |
| FR004, FR015 | T008, T019, T022–T026 |
| FR005–FR006, SC002 | T014–T016, T033–T038 |
| FR007, SC004 | T019–T027 |
| FR008–FR009 | T028–T033 |
| FR012–FR013 | T003–T007, T011, T019, T028–T030, T034–T038 |
| FR014, SC001 | T010, T034–T038 |
| SC003 | T017–T018, T038 |

## Puntos a resolver antes de implementar

T002 no reabre las decisiones de diseño aprobadas: completa reglas que el modelo/contrato aún no expresan. En particular, el contrato de vínculo de devolución solo recibe `idMovimientoSocio`, el padrón admite un titular por partida aunque un impuesto admite varios socios, y la tabla heredada no tiene partida para disparar el aviso. Dejar explícitas esas reglas evita elegirlas durante una escritura real. Cualquier cambio de alcance se registra en los artefactos antes de implementarlo.
