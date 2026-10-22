# Tareas: Gestión de cajas de efectivo (038)

**Entrada**: spec.md aclarada, plan.md, research.md, data-model.md, contracts/api.md y quickstart.md de este directorio.
**Fecha**: 22/10/2026. **Estado**: implementación en curso; ver registro en quickstart.md.
**Formato**: casillas pendientes, identificador secuencial, [USn] por historia y [P] solo para archivos independientes. No autoriza lanzar agentes ni hacer push.
**Verificación**: escenarios de la spec y controles mínimos de la Constitución; datos simulados, sin operaciones de prueba en WC. Registrar resultados reales en quickstart.md. Las rutas nuevas son archivos por crear.

## Fase 1 — Preparación

- [X] T001 Relevar mediante lecturas acotadas de WC columnas, claves, restricciones, tipos y signos de caja, efectivo, aplicaciones, socios y traspasos; registrar consultas y resultados sin datos sensibles en specs/038-gestion-cajas-efectivo/schema-verification.md y ajustar data-model.md a los hallazgos.
- [X] T002 Inventariar todos los consumidores de Pagos efectivo y exclusiones bancarias con sus rutas en specs/038-gestion-cajas-efectivo/schema-verification.md; documentar la estrategia de anulación y de exclusión/restauración de bancos sin alterar importes fiscales.
- [X] T003 Resolver precisión, longitud, nulabilidad y versiones faltantes del diseño, límites de archivo/filas/hojas y comportamiento de corte/orden de caja; sincronizar specs/038-gestion-cajas-efectivo/data-model.md y contracts/api.md antes de programar.

## Fase 2 — Fundamentos compartidos (bloqueantes)

- [X] T004 Crear migración aditiva idempotente en backend/scripts/migrar_gestion_cajas_038.py para operación, efectos, arqueos, denominaciones, importaciones, filas, GastoCajaEfectivo y RepartosGastoCaja; conservar historia y añadir únicamente columnas/índices ausentes; incluir modo de inspección sin escritura y precondiciones de esquema.
- [X] T005 Obtener y verificar respaldo antes del DDL; registrar ruta local y verificación en specs/038-gestion-cajas-efectivo/quickstart.md; aplicar backend/scripts/migrar_gestion_cajas_038.py a WC y comprobar que saldos al corte e identificadores históricos no cambian. No restaurar producción automáticamente.
- [X] T006 Definir modelos base en backend/src/features/cajas_efectivo/schemas.py respetando “ClaveIdempotencia uniqueidentifier UNIQUE”, “HuellaSolicitud char(64)”, “Tipo varchar(40)”, “Concepto nvarchar(255)”, “Cuenta varchar(20) A/B para nuevas operaciones”, “IdContacto/IdSocio opcionales con referencia válida”, “Importes positivos en solicitud” y “MotivoRelacionGiamigli obligatorio si involucra Condominio”; conservar tipos GET existentes y definir contratos monetarios nuevos con Decimal.
- [X] T007 Implementar persistencia de operación y efectos en backend/src/features/cajas_efectivo/repository.py: “IdOperacion bigint PK”, “IdOperacion nullable” en historia, “Anulada con default 0”, “EsCreadoPorOperacion bit”, “TipoEfecto enumerado (PagoEfectivo, Aplicacion, MovimientoSocio, AsientoParticular, TraspasoTesoreria, GastoCaja, AjusteNoCobrado)” y unicidad de propiedad; catálogo fijo sin SQL libre, añadiendo GastoCaja y AjusteNoCobrado según data-model.md.
- [X] T008 Crear coordinador en backend/src/features/cajas_efectivo/service.py usando transacción compartida de backend/src/db/connection.py; bloquear cajas en orden estable y documentos/bancos usados, revalidar capacidad y hacer rollback total; misma clave/contenido devuelve operación y clave reutilizada con otro contenido devuelve 409.
- [X] T009 Implementar previsualización y confirmación de SALDO_NEGATIVO/PERIODO_ARQUEADO en backend/src/features/cajas_efectivo/service.py, incluyendo saldo mínimo posterior afectado por una operación retroactiva; aceptar advertencias solo sobre versión vigente y exigir nueva vista previa si cambió el contexto.
- [X] T010 Exponer previsualización, creación y detalle en backend/src/features/cajas_efectivo/router.py con permisos existentes, usuario de sesión, rutas estáticas sin colisión con slugs, errores 401/403/404/409/422 y sin detalles SQL.
- [X] T011 Implementar mecanismo común de reversión de efectos propios en backend/src/features/cajas_efectivo/service.py y su exclusión en los lectores inventariados en schema-verification.md; conservar registros originales y rechazar dependencias posteriores ajenas con identificadores. Se completará cada adaptador con su historia antes de habilitarla.
- [X] T012 Verificar contrato base de previsualización/creación/detalle, Decimal, idempotencia y errores con FastAPI y SQL simulado en backend/tests/test_cajas_contrato_base_038.py; registrar evidencia en specs/038-gestion-cajas-efectivo/quickstart.md antes del cliente T013.
- [x] T013 Ampliar tipos y llamadas HTTP en frontend/src/services/cajasEfectivoApi.ts con clave idempotente estable por intento, advertencias versionadas, errores de conflicto y compatibilidad de GET existentes.

**Puerta**: esquema y respaldo documentados, atomicidad e idempotencia disponibles. No habilitar una operación hasta verificar también su reversión.

## Fase 3 — US1: Pagar a proveedores (P1, primer incremento)

**Objetivo**: registrar pago, gasto sin comprobante y compra particular una sola vez.
**Prueba independiente**: una factura pagada baja caja y deuda una vez; parciales/múltiples y compra particular mantienen sus efectos correctos.

- [X] T014 [US1] Implementar pago en backend/src/features/cajas_efectivo/service.py y repository.py: un Pagos efectivo enlazado a una salida de caja, con Caja/IdTipoMovimiento/IdFormaPago verificados, sin incorporar caja a vw_MovimientosCuenta_Base.
- [X] T015 [US1] Integrar aplicaciones explícitas en backend/src/features/aplicaciones_pago/repository.py bajo la transacción común, validando contacto, moneda, disponibilidad, parciales y varios documentos; conservar valuaciones externas y reglas 036 sin crear ND/NC automáticamente.
- [X] T016 [US1] Implementar gasto sin comprobante con rubro y reparto válido en backend/src/features/cajas_efectivo/service.py, persistiendo GastoCajaEfectivo/RepartosGastoCaja según data-model.md, sin factura ni deuda al contacto 97; integrar fuente GastoCaja una sola vez en backend/src/features/resultado_cultivo/costos.py y sus listados sin clasificar, con origen rastreable y exclusión al anular. Verificar suma de repartos, identificadores y costo USD no valuado explícito.
- [X] T017 [US1] Integrar compra particular en backend/src/features/cajas_efectivo/service.py y backend/src/features/cuentas_socios/repository.py: pago al proveedor, asiento Particular y una AsignacionGasto; reutilizar asignación existente cuando corresponda y garantizar reversión conjunta sin duplicarla.
- [X] T018 [US1] Verificar contrato SQL/API de pago total/parcial/múltiple, gasto con costo único, particular, reversión, permisos y errores en backend/tests/test_cajas_contrato_pagos_038.py con FastAPI y acceso SQL simulado; contrastar esquema vivo leído en T001, respuestas y rollback, ejecutar y registrar resultado en specs/038-gestion-cajas-efectivo/quickstart.md. Puerta obligatoria antes de implementar su UI; sin escrituras de prueba en WC.
- [x] T019 [US1] Crear frontend/src/components/cajas-efectivo/OperacionCajaForm.tsx con proveedor/documentos, rubro/reparto, compra particular, MoneyInput, vista previa y aceptación de avisos; integrar en frontend/src/components/cajas-efectivo/CajaEfectivo.tsx con SoloLectura.
- [x] T020 [US1] Verificar pago, gasto, particular, permisos, reintentos, conflicto de capacidad y fallo de cada paso con SQL simulado en backend/tests/test_cajas_efectivo_038.py; confirmar reversión de estos efectos y registrar resultados en specs/038-gestion-cajas-efectivo/quickstart.md.

## Fase 4 — US2: Aportes y retiros de socios (P1)

**Objetivo**: aporte a favor, retiro a cuenta como deuda y ganancias sin cuenta de socio.
**Prueba independiente**: aporte de Sergio de $100.000 aumenta caja y crédito del socio valuado a fecha; ganancias no cambia saldo de socio.

- [x] T021 [US2] Extraer fórmula histórica de backend/scripts/socios_valuacion_036.py a backend/src/features/cuentas_socios/valuacion.py y reutilizarla sin cambiar resultados existentes; guardar fuente/fecha/cotizaciones e importes, regla anterior al 16/03/2020 100% US$ y posterior 50% US$/50% kg; bloquear cotización faltante.
- [X] T022 [US2] Implementar aporte como Devolucion y retiro a cuenta como AsignacionGasto en backend/src/features/cajas_efectivo/service.py y backend/src/features/cuentas_socios/repository.py con valuación histórica; preservar signo y separación del mutuo en todos los cálculos.
- [X] T023 [US2] Implementar retiro de ganancias sin cuenta de socio y aporte/devolución Condominio con cajaContraparte y dos piernas físicas, crédito/débito de socio único; pago directo de gasto Giamigli desde Condominio agrega crédito socio sin caja Giamigli ficticia ni pago al 549; validación de relación Condominio/Giamigli en backend/src/features/cajas_efectivo/service.py; empleado 375 no sustituye socio 5670; devolución de sueldo mediante traspaso no es aporte.
- [X] T024 [US2] Verificar contrato SQL/API de aporte/retiro, dos piernas Condominio con un efecto de socio, pago directo, ganancias y cotizaciones en backend/tests/test_cajas_contrato_socios_038.py con FastAPI y acceso SQL simulado; contrastar esquema vivo leído en T001, respuestas y rollback, ejecutar y registrar resultado en specs/038-gestion-cajas-efectivo/quickstart.md. Puerta obligatoria antes de implementar su UI; sin escrituras de prueba en WC.
- [x] T025 [US2] Ampliar frontend/src/components/cajas-efectivo/OperacionCajaForm.tsx para socio, aporte, retiro a cuenta y ganancias, mostrando efecto y valuación antes de guardar.
- [x] T026 [US2] Verificar signo, corte histórico de fórmula, cotización faltante, ganancias, Condominio, reintento y reversión en backend/tests/test_cajas_socios_038.py y registrar evidencia en specs/038-gestion-cajas-efectivo/quickstart.md.

## Fase 5 — US3: Traspasos entre cajas y bancos (P2)

**Objetivo**: mover efectivo sin crear gasto, aporte ni cuenta de contacto.
**Prueba independiente**: $100.000 de Giamigli a chica produce salida/entrada iguales; banco queda enlazado y fuera de contacto.

- [X] T027 [US3] Implementar traspaso caja-caja en backend/src/features/cajas_efectivo/service.py: solo Giamigli↔chica, cajas distintas, mismo importe/fecha y operación, signos opuestos y cero efectos de contacto/socio; rechazar cruce Condominio en este tipo y derivar a aporte/devolución; validar ambas cajas y anulaciones.
- [X] T028 [US3] Implementar extracción/depósito con efectivo puente sin contacto en backend/src/features/cajas_efectivo/service.py y backend/src/features/traspasos_internos_tesoreria/repository.py; vincular extracto importado una vez, revalidar estado y guardar intermediario/evidencia sin convertirlo en aporte. Implementar retorno_sueldo_opcion_a con IdSalario, evidencia, ajuste interno no cobrado de 036, snapshot versionado y reversión; no transformar pares históricos compensados desde noviembre de 2017 ni cancelar montos sin respaldo.
- [X] T029 [US3] Aplicar exclusión bancaria de FR-008 y restauración al anular en los lectores concretos inventariados en specs/038-gestion-cajas-efectivo/schema-verification.md, incluyendo backend/src/features/cuentas_corrientes/repository.py y el origen SQL real si corresponde; no asumir que un evento 024 elimina el contacto.
- [X] T030 [US3] Verificar contrato SQL/API de traspasos, rechazo de cruce Condominio, exclusión bancaria y opción A completa sin duplicación en backend/tests/test_cajas_contrato_traspasos_038.py con FastAPI y acceso SQL simulado; contrastar esquema vivo leído en T001, respuestas y rollback, ejecutar y registrar resultado en specs/038-gestion-cajas-efectivo/quickstart.md. Puerta obligatoria antes de implementar su UI; sin escrituras de prueba en WC.
- [x] T031 [US3] Ampliar frontend/src/components/cajas-efectivo/OperacionCajaForm.tsx con caja destino, banco/movimiento importado, intermediario, evidencia y navegación al origen.
- [x] T032 [US3] Verificar concurrencia por banco, igualdad de piernas, cuenta personal intermedia, cero efectos de contacto/socio, exclusión/restauración, opción A por $10.000 con liquidación cancelada por ajuste interno y cero aporte, conservación de pares históricos, diferencia parcial bloqueada y rollback en backend/tests/test_cajas_traspasos_038.py; registrar evidencia en specs/038-gestion-cajas-efectivo/quickstart.md.

## Fase 6 — US4: Cobros en efectivo (P2)

**Objetivo**: entrada de caja y cobro único aplicado al documento real.
**Prueba independiente**: cobro total/parcial de una venta sube caja y reduce pendiente una sola vez.

- [X] T033 [US4] Relevar origen de documentos de alquiler y su saldo en backend/src/features/aplicaciones_pago/documentos.py y specs/038-gestion-cajas-efectivo/schema-verification.md; definir adaptador real en contracts/api.md. Si no existe documento compatible, documentar impedimento concreto y mantener esa variante bloqueada con 422 sin declarar completa la historia.
- [X] T034 [US4] Implementar cobro en backend/src/features/cajas_efectivo/service.py y adaptar backend/src/features/aplicaciones_pago/documentos.py para tipos documentales verificados, incluida la resolución de T033; un efectivo, una entrada, aplicaciones y reversión conjunta.
- [X] T035 [US4] Verificar contrato SQL/API de cobros y documentos compatibles incluida resolución de alquiler en backend/tests/test_cajas_contrato_cobros_038.py con FastAPI y acceso SQL simulado; contrastar esquema vivo leído en T001, respuestas y rollback, ejecutar y registrar resultado en specs/038-gestion-cajas-efectivo/quickstart.md. Puerta obligatoria antes de implementar su UI; sin escrituras de prueba en WC.
- [x] T036 [US4] Ampliar frontend/src/components/cajas-efectivo/OperacionCajaForm.tsx para cliente/documentos pendientes y cobro parcial o múltiple, mostrando limitaciones de tipos aún no disponibles.
- [x] T037 [US4] Verificar signo, documentos de distinto contacto, capacidad, aplicaciones, alquiler resuelto y anulación en backend/tests/test_cajas_cobros_038.py; registrar resultados y cualquier bloqueo real en specs/038-gestion-cajas-efectivo/quickstart.md.

## Fase 7 — US5: Arqueos (P2)

**Objetivo**: contar denominaciones y confirmar explícitamente una diferencia.
**Prueba independiente**: diferencia de $249,10 visible y ajuste único tras confirmación; arqueo coincidente no genera ajuste.

- [X] T038 [US5] Definir modelos y persistencia en backend/src/features/cajas_efectivo/schemas.py y repository.py con “Estado Borrador/Confirmado/Invalidado/Desactualizado”, “IdOperacionAjuste nullable UNIQUE”, “Denominacion decimal positiva”, “Cantidad entera >=0”, “UNIQUE(arqueo,denominación)”; total=sum(valor*cantidad) y diferencia=contado-saldo al corte estable.
- [X] T039 [US5] Implementar crear/editar borrador, listar y confirmar arqueo en backend/src/features/cajas_efectivo/service.py y router.py; control de versión, revalidación de corte, ajuste solo por confirmación, una vez, sin modificación del confirmado. Anular ajuste invalida arqueo atómicamente; nuevo recuento enlaza IdArqueoAnterior. Retroactividad aceptada marca posteriores afectados Desactualizado; preservar observaciones y mostrar diferencia vigente aparte.
- [X] T040 [US5] Verificar contrato SQL/API de arqueos, confirmación, invalidación, desactualización y recuento correctivo en backend/tests/test_cajas_contrato_arqueos_038.py con FastAPI y acceso SQL simulado; contrastar esquema vivo leído en T001, respuestas y rollback, ejecutar y registrar resultado en specs/038-gestion-cajas-efectivo/quickstart.md. Puerta obligatoria antes de implementar su UI; sin escrituras de prueba en WC.
- [x] T041 [US5] Crear frontend/src/components/cajas-efectivo/ArqueoCajaPanel.tsx con denominaciones en pesos, contado/sistema/diferencia, borrador, confirmación, estados Invalidado/Desactualizado, recuento correctivo enlazado, diferencia original/vigente separadas y aviso de cobertura parcial Condominio; integrar en CajaEfectivo.tsx.
- [x] T042 [US5] Verificar diferencia $249,10, cero, reintento, cambio concurrente, corte, denominación inválida, anulación de ajuste con arqueo Invalidado y nuevo recuento enlazado, retroactividad con arqueo Desactualizado y ajuste reversible auditado en backend/tests/test_cajas_arqueos_038.py; registrar evidencia en specs/038-gestion-cajas-efectivo/quickstart.md.

## Fase 8 — US6: Consulta y corrección (P3)

**Objetivo**: filtrar, rastrear y anular sin borrar con efectos coherentes.
**Prueba independiente**: anular pago restaura caja, proveedor y socio, preservando registros y motivo; historial paginado mantiene saldo corrido.

- [X] T043 [US6] Ampliar consultas en backend/src/features/cajas_efectivo/repository.py y schemas.py con saldo vigente, último arqueo, filtros por fecha/tipo/contacto/socio, anulados opcionales y saldo corrido antes de paginar ordenado por Fecha,IdMovimiento; arrastre anterior al rango y páginas vacías correctos. Filtros tipo/contacto/socio restringen filas pero no el saldo real; subtotalFiltradoDecimal separado, anulados sin efecto. Preservar saldo/importe numéricos GET y agregar campos Decimal de contrato sin cambiar tipos.
- [X] T044 [US6] Completar endpoint de anulación en backend/src/features/cajas_efectivo/router.py y servicio: “Solo Vigente→Anulada”, motivo/usuario/fecha, versión esperada, reintento idempotente y reversión de todos los adaptadores; historia sin operación requiere revisión de vínculos antes de habilitar anulación compuesta.
- [X] T045 [US6] Verificar contrato SQL/API de consulta, saldo real/subtotal, compatibilidad GET y anulación versionada en backend/tests/test_cajas_contrato_consulta_038.py con FastAPI y acceso SQL simulado; contrastar esquema vivo leído en T001, respuestas y rollback, ejecutar y registrar resultado en specs/038-gestion-cajas-efectivo/quickstart.md. Puerta obligatoria antes de implementar su UI; sin escrituras de prueba en WC.
- [x] T046 [US6] Ampliar frontend/src/components/cajas-efectivo/CajaEfectivo.tsx y crear DetalleOperacionCaja.tsx con filtros, saldo corrido, estado, auditoría, origen y anulación con motivo; invalidar consultas de caja, contacto, socio, banco y arqueo pertinentes mediante TanStack Query.
- [x] T047 [US6] Verificar reversión integral, dependencia ajena, doble anulación, historial sin operación, saldo real con movimientos ocultos y subtotal separado, compatibilidad numérica GET, filtros/paginación y permisos en backend/tests/test_cajas_consulta_anulacion_038.py; registrar evidencia en specs/038-gestion-cajas-efectivo/quickstart.md.

## Fase 9 — Convivencia transversal (FR-013, FR-014, FR-015)

**Objetivo**: incorporar filas nuevas y comparar sin recrear efectos históricos o manuales.

- [X] T048 Implementar parser sin escritura en backend/src/features/cajas_efectivo/importacion.py reutilizando lectura XLSX existente; límites T003, sin macros, libro lógico/hoja/fila/huella/datos originales y estados “Nueva/Vinculada/Ambigua/Modificada/Excluida”; no imponer unicidad global de contenido ni usar fila sola como identidad.
- [X] T049 Implementar persistencia de lote/filas y vista previa en backend/src/features/cajas_efectivo/repository.py y router.py con “estado Preview/Confirmado”, versión del parser, claves por lote y vínculos confirmados; resolver fila desplazada/modificada sin importar automáticamente ambiguas.
- [X] T050 Implementar confirmación transaccional e idempotente de lote en backend/src/features/cajas_efectivo/importacion.py usando service.py para efectos nuevos, enlace explícito para existentes y exclusiones con motivo; pendientes no generan efectos, fallo revierte lote resuelto completo y vincular no recrea pagos.
- [X] T051 Implementar comparación caja por caja al mismo corte en backend/src/features/cajas_efectivo/importacion.py con saldos, faltantes/extras/modificadas/ambiguas y cobertura Condominio; conservar historia 027/036 y permitir nuevos movimientos Condominio solo relacionados con Giamigli.
- [X] T052 Verificar contrato SQL/API de vista previa/confirmación de importación, vínculos, comparación e idempotencia en backend/tests/test_cajas_contrato_importacion_038.py con FastAPI y acceso SQL simulado; contrastar esquema vivo leído en T001, respuestas y rollback, ejecutar y registrar resultado en specs/038-gestion-cajas-efectivo/quickstart.md. Puerta obligatoria antes de implementar su UI; sin escrituras de prueba en WC.
- [x] T053 Crear frontend/src/components/cajas-efectivo/ImportacionCajaPanel.tsx y ampliar frontend/src/services/cajasEfectivoApi.ts para archivo/vista previa, resolver coincidencias, vincular/importar/excluir/dejar pendiente y comparar; integrar en CajaEfectivo.tsx sin modificar la planilla.
- [x] T054 Verificar doble importación, fila desplazada/modificada, filas idénticas legítimas, coincidencia manual, efectos históricos enlazados, rollback, límites y cobertura en backend/tests/test_cajas_importacion_038.py; registrar resultados en specs/038-gestion-cajas-efectivo/quickstart.md.

## Fase 10 — Validación y continuidad

- [X] T055 Ejecutar muestra simulada de 50 operaciones variadas con reintentos, concurrencia y anulaciones en backend/tests/test_cajas_efectivo_038.py, verificando exactamente un efecto por libro y cero huérfanos; registrar SC-002 y SC-005 en specs/038-gestion-cajas-efectivo/quickstart.md.
- [x] T056 Ejecutar pruebas acotadas 038, compilación TypeScript y recorrido UI de las seis historias, incluyendo vacío/error/Lectura, pago menor a un minuto y comparación de saldos iniciales al corte mediante lecturas; registrar comandos, resultados y límites en specs/038-gestion-cajas-efectivo/quickstart.md. Para imputaciones productivas aplicar specs/036-revision-sistematica-cuentas/auditoria-campanias.md sin reasignaciones automáticas.
- [x] T057 Revisar diff, secretos, binarios y respaldo fuera de Git; actualizar specs/038-gestion-cajas-efectivo/spec.md, plan.md, contracts/api.md, quickstart.md y tasks.md con comportamiento aplicado, autorizaciones, evidencias y pendientes reales para continuidad Claude/Codex; no marcar tareas por mera existencia de archivos.

## Dependencias y orden

T001→T002→T003→T004→T005. T006→T007→T008→T009→T010→T011; T013 requiere contrato base verificado mediante pruebas de API antes de programar el cliente; no basta redactar el contrato. Toda historia requiere fundamentos terminados. T017 utiliza valuación histórica: completar T021 antes de cerrar compra particular, aunque US2 se entregue después.

US1→US2→US3→US4→US5→US6 es el orden recomendado por prioridad y archivos compartidos. US2, US3, US4 y US5 no requieren datos creados por otra historia: sus pruebas preparan fixtures propias. US6 integra los adaptadores ya verificados. Importación requiere los tipos que pretenda cargar; final requiere todas las historias y convivencia. Una brecha T033 no se convierte en aceptación tácita de menor alcance.

Cada historia sigue modelos/persistencia→servicio→endpoint→verificación SQL/API→UI→verificación integral. Las pruebas de contrato insertadas antes de cada tarea UI son dependencias bloqueantes, no trabajo paralelo. No habilitar operación sin reversión probada, aunque la pantalla de auditoría completa sea US6.

## Oportunidades de trabajo en paralelo

Estas son posibilidades de distribución futura; no implican invocar agentes. Evitar edición simultánea de service.py, schemas.py, repository.py, router.py y OperacionCajaForm.tsx.

No paralelizar backend o verificación del contrato con la implementación de su UI. En US1, US2, US3, US4, US5 y US6 primero completar y ejecutar su tarea de contrato correspondiente; luego puede implementarse UI en paralelo con documentación de evidencias en quickstart.md, sin compartir archivos. La importación sigue la misma puerta. T013 solo después de la puerta base indicada abajo.

## Estrategia de entrega

Primer incremento: preparación/fundamentos + US1, incluyendo valuación T021 para compra particular y reversión de los efectos habilitados. Validarlo antes de ampliar operaciones. Incorporar luego cada historia y convivencia sin publicar ni finalizar Excel automáticamente. La convivencia termina únicamente por decisión explícita de Sergio.

## Registro de generación

22/10/2026: Sergio autorizó el próximo paso tras el plan. Se ejecutó setup-tasks.ps1 y se generaron estas 49 tareas iniciales desde los artefactos existentes, sin regenerar spec ni tocar datos. No hay extensions.yml y por tanto no hay hooks antes/después. Todas las tareas están pendientes; no se ejecutaron pruebas de implementación en esta fase.

## Correcciones autorizadas — 22/10/2026
Sergio aprobó corregir todos los hallazgos de analyze. Se precisaron siete temas en spec/modelo/contrato y se agregaron ocho puertas de verificación de contrato previas al cliente/UI. Hay 57 tareas pendientes, renumeradas en orden documental; la dependencia explícita de valuación para particular sigue indicada arriba. No se aplicó DDL ni se ejecutó implementación.

Registro de implementación: fundamentos y contratos backend completados según pruebas y lecturas de quickstart.md. Los adaptadores nuevos se separaron en operaciones.py, arqueos.py e importacion.py para mantener archivos acotados. UI y validaciones finales siguen pendientes.
