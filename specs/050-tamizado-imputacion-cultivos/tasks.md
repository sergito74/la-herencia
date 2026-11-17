# Tasks: Imputación progresiva y tamizado de facturas (049 + 050)

**Input**: [plan.md](plan.md), [spec.md](spec.md), [../049-imputacion-automatica-total/spec.md](../049-imputacion-automatica-total/spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [tabla-rubros-destino.md](tabla-rubros-destino.md)

**Historias**: US1–US8 son las historias de la spec 050. Las de la spec 049 se agregan así:
- **US9** = imputación progresiva de insumos y vínculo remito↔factura (049, Historias 1-2, P1).
- **US10** = control de cierre (049, Historia 5).

**Tests**: se incluyen por el Principio V de la constitución. Usan mocks de `fetch_all`/`execute_write_transaction` y nunca escriben en WC.

## Phase 1: Setup

- [X] T001 Hacer el backup verificado de WC y registrar el resultado en specs/050-tamizado-imputacion-cultivos/backup-20261114.md.
- [X] T002 Crear backend/scripts/crear_tablas_tamiz_050.py. Tiene que ser idempotente y crear las tablas de data-model.md:
  - PartesEstructuraCosto, PartesEstructuraCultivoInactivas, TamizRubroDestino, TamizReglaProducto, ImputacionConfig, ImputacionAlcance, TamizRenglones, VinculoRemitoPendiente.
  - Además: ALTER `ImputacionPropuestas` ADD `IdParte int NULL`.
  - Restricciones literales:
    - Destino ∈ `CultivoStock|Cultivo|Depende|Ganaderia|Financiero|Estructura|NoImputa`.
    - OrigenDecision ∈ `Manual|Orden|Producto|Rubro|Revision`.
    - Estado ∈ `Aprobada|Pendiente`.
    - Motivo de alcance ∈ `Nuevo|StockSinImputar`.
    - IdParte es obligatorio si Destino ∈ (CultivoStock, Cultivo).
    - Una sola fila Vigente=1 por IdDetalleCompra en TamizRenglones.
- [X] T003 En el mismo script, cargar las 9 partes y las 48 filas de TamizRubroDestino según tabla-rubros-destino.md:
  - Flete insumos → `CultivoStock` con regla `FleteInsumo`.
  - Insumos productivos → `Depende`/`SegunUsoOrden`.
  - Flete granos → `Cultivo`/Comercialización.
  - ImputacionConfig con Activo=0.
- [X] T004 Correr crear_tablas_tamiz_050.py contra WC y verificar: 48 rubros cargados, ninguno sin parte cuando corresponde.

## Phase 2: Foundational

- [X] T005 Crear backend/src/features/imputacion/tamiz_repository.py con estas funciones:
  - lectura de reglas de rubro y de producto;
  - en_alcance(id_detalle_compra);
  - alta en el alcance;
  - guardar clasificación (una sola vigente);
  - la cola de revisión.
- [X] T006 [P] En backend/src/features/imputacion/repository.py, agregar el filtro de alcance a las consultas de documentos y fracciones (helper `ids_en_alcance`).
- [X] T007 [P] Crear backend/tests/test_tamiz_repository_050.py con tres casos:
  - una sola fila vigente por renglón;
  - un rubro sin regla devuelve el motivo `rubroSinRegla`;
  - el alcance por `IdDeuda > IdDeudaCorte`.

## Phase 3: US2 + US3 — Tamiz por rubro con cultivo/campaña (P1) 🎯 MVP

**Objetivo**: cada renglón en alcance queda con su destino, parte, cultivo y campaña, o bien en revisión con el motivo. Todavía no cambia ningún resultado.

**Test independiente**: tamizar las 18 facturas mixtas reales en modo cálculo y comprobar que cada renglón tiene destino o motivo.

- [X] T008 [P] [US2] Crear backend/tests/test_tamiz_050.py con estos casos:
  - el orden de prioridad manual > orden > producto > rubro > revisión;
  - en una factura mixta, cada renglón decide por sí mismo;
  - un rubro "no va" con campaña cargada termina en revisión;
  - un texto libre ambiguo termina en revisión;
  - un insumo con imputación manual igual termina en CultivoStock (la manual queda como referencia);
  - lo de San Justo bloqueado;
  - una compra particular termina en NoImputa.
- [X] T009 [US2] Crear backend/src/features/imputacion/tamiz.py con `tamizar_renglon(id_detalle_compra)` y `tamizar_compra(id_compra)`. La prioridad es la de research R-05: "manual" quiere decir un cultivo real y una campaña distinta de General/No Aplica.
- [X] T010 [US2] En tamiz.py, implementar las reglas Depende de research R-06:
  - AnalisisLaboratorio por palabra clave;
  - Combustible: Estructura salvo que pase por stock;
  - Financiamiento por documento relacionado;
  - SegunUsoOrden: se resuelve en el motor.
- [X] T011 [US3] En tamiz.py, implementar la campaña de los renglones de una sola vez (FR-006):
  - el seguro va a la campaña asegurada;
  - el flete de granos y la comercialización van a la campaña de cosecha del grano;
  - el barbecho va al cultivo siguiente;
  - si no se puede determinar, la campaña vigente a la fecha y el renglón va a revisión.
- [X] T012 [US3] En tamiz.py, deducir el cultivo cuando falta (grano, fecha u orden más cercana). Imputar solo si hay una única opción; si no, mandar a revisión con las opciones.
- [X] T013 [US2] En backend/src/features/compras (el guardado y la edición de la compra), llamar a `tamiz.tamizar_compra(id)` después de guardar, solo si la compra está en alcance. Un error del tamiz no tiene que impedir guardar la compra.
- [X] T014 [US2] En backend/src/features/imputacion/router.py, agregar los endpoints `POST/GET /tamiz/compra/{idCompra}` y `PUT /tamiz/renglon/{idDetalleCompra}` según contracts/api.md.

## Phase 4: US9 — Imputación progresiva de insumos y vínculo remito↔factura (P1)

**Objetivo**: el renglón de insumo entra 100% en stock, cada orden ejecutada le descuenta un uso, y el remito queda vinculado solo.

**Test independiente**: el escenario del glifosato del quickstart §3 (con mocks): 200 l, uso de 80 l, quedan 120 l en stock, y usos + stock = total al centavo.

- [X] T015 [P] [US9] Crear backend/tests/test_vinculo_auto_050.py con estos casos:
  - una coincidencia exacta única vincula;
  - dos facturas posibles van a revisión;
  - una entrega parcial 100+100 contra 200 vincula los dos remitos;
  - la suma de CantidadRemitida nunca supera la cantidad del renglón;
  - un remito fuera de la ventana de −60/+30 días no es candidato.
- [X] T016 [US9] Crear backend/src/features/remitos/vinculo_auto.py con `vincular_por_compra(id_compra)` y `vincular_por_remito(id_remito)`:
  - escribe en tblRemitoCompra mediante `execute_write_transaction`;
  - lo dudoso va a VinculoRemitoPendiente.
- [X] T017 [US9] Llamar a vinculo_auto al guardar una compra en alcance (junto con T013) y al guardar un remito, en backend/src/features/remitos/repository.py.
- [X] T018 [P] [US9] Crear backend/tests/test_capa_factura_sin_remito_050.py con dos casos:
  - un renglón en alcance sin remito genera la capa `F{id}` a la fecha de la factura;
  - al vincular el remito, la capa F desaparece.
- [X] T019 [US9] En backend/src/features/remitos/stock_datos.py, agregar al FIFO de `calcular_stock` las capas virtuales `F{IdDetalleCompra}`, solo para renglones en alcance con destino CultivoStock y sin tblRemitoCompra. El costo unitario es el precio de la factura al TC del comprobante.
- [X] T020 [US9] En stock_datos.costos_de_renglones, sumar al costo unitario de cada capa el flete de insumos atribuido, repartido por importe (research R-06b). Contemplar el flete de la misma factura y el de una factura relacionada.
- [X] T021 [P] [US9] Crear backend/tests/test_flete_insumo_050.py con tres casos:
  - $100.000 de flete sobre $2.000.000 de insumos se reparte por importe;
  - un uso del 40% se lleva el 40% del flete;
  - un flete en factura aparte sin relacionar queda pendiente.
- [X] T022 [US9] En backend/src/features/imputacion/motor.py, hacer tres cambios:
  - `calcular_propuesta_insumo` acepta capas F;
  - cada fracción lleva IdParte (desde TamizRubroDestino);
  - ~~silobolsa por uso de la orden~~ — corregido 14/11/2026: el uso no está en las órdenes; el tamiz lo deja "Para revisar" y Sergio indica el uso al cargar.
- [X] T023 [US9] En motor.py, para los renglones en alcance:
  - si usos + stock = total al centavo y no hay dudas, la corrida queda Aprobada sola;
  - si no, Pendiente con motivo en la cola.
- [X] T024 [US9] En backend/src/features/ordenes/repository.py `_recalcular_imputacion_por_productos`, incluir también los renglones en alcance de esos productos que todavía no tienen corrida.
- [X] T025 [US9] En motor.py, agregar `calcular_directo(id_detalle_compra)`, que genera fracciones con Origen 'Directo' para los renglones de una sola vez con su destino, parte, cultivo y campaña. Llamarlo desde tamiz cuando el renglón queda Aprobado.
- [X] T026 [US9] Crear backend/scripts/imputacion_diaria_050.py con la pasada diaria:
  - vinculo_auto pendiente;
  - recálculo de los renglones en alcance con stock;
  - posibles duplicados (capa F junto a un remito sin vincular del mismo proveedor y producto) a revisión.
- [X] T027 [US9] Registrar imputacion_diaria_050.py en el Programador de tareas de Windows (igual que la rutina de peajes) y documentarlo en quickstart.md.

## Phase 5: US1 + US7 — Estructura de costos e informe por parte (P1/P3)

**Objetivo**: el resultado del cultivo sin doble conteo para los renglones en alcance, agrupado en 9 partes con $/ha y US$/ha.

**Test independiente**: un cultivo con renglones en alcance suma cada costo una sola vez. Una campaña sin renglones en alcance da diferencia $0,00 contra antes.

- [X] T028 [P] [US1] Crear backend/tests/test_costos_alcance_050.py con estos casos:
  - un renglón en alcance queda excluido de costos_heredados;
  - el consumo de capas en alcance no se cuenta en costo_ordenes_trabajo;
  - las fracciones Aprobadas Insumo/Directo sí se cuentan;
  - con Activo=0, el resultado es igual al de hoy.
- [X] T029 [US1] En backend/src/features/resultado_cultivo/costos.py, hacer tres cambios:
  - excluir los renglones en alcance de costos_heredados;
  - descontar de costo_ordenes_trabajo el consumo de capas en alcance;
  - agregar `costos_alcance(id_cultivo, id_campania)` con las fracciones aprobadas.

  Todo esto solo si ImputacionConfig.Activo=1.
- [X] T030 [US7] Agregar el endpoint `GET /api/resultado-cultivo/{idCultivo}/{idCampania}/por-parte` en backend/src/features/resultado_cultivo/router.py, según contracts/api.md. Incluye partes, estructura de campaña y "en stock sin consumir".
- [X] T031 [US7] En frontend/src/app/resultado-cultivo, mostrar el informe por parte con $/ha y US$/ha y apertura hasta el documento o la orden, usando los helpers de formato de números (nada de toLocaleString).
- [X] T032 [US1] Crear backend/scripts/activar_alcance_050.py: — Hecho el 16/11/2026: alcance = compras desde el 12/05/2025 (ImputacionAlcance) y corte = IdDeuda máximo; ver traspaso-20261116.md.
  - `--dry-run` arma el Excel antes/después por cultivo/campaña en la carpeta de la spec;
  - `--aplicar` fija IdDeudaCorte, marca los renglones StockSinImputar (research R-01) y pone Activo=1.

  `--aplicar` exige backup y el OK de Sergio.

## Phase 6: US4 — Reparto por superficie del plan agrícola (P2)

- [X] T033 [P] [US4] Crear backend/tests/test_reparto_plan_050.py con dos casos: — Hecho 16/11/2026 (más casos: labor de contratista no se reparte, tamiz aprueba con plan).
  - 60 ha de trigo y 40 ha de soja reparten $1.000.000 en 600.000 y 400.000;
  - un plan sin superficie manda el renglón a revisión.
- [X] T034 [US4] En tamiz.py, repartir según la superficie de backend/src/features/planificacion los renglones "a cultivo" sin cultivo y con campaña única, sin lote. El último cultivo absorbe los centavos de redondeo. — Hecho 16/11/2026 en reparto_plan.py + tamiz._deducir + progresivo.fracciones_directo; solo partes 7/8/9 (seguro, asesoramiento/análisis, comercialización) con campaña cargada; las labores siguen 048.

## Phase 7: US5 — Producto sugerido y aprendizaje (P2)

- [X] T035 [P] [US5] Crear backend/tests/test_producto_sugerido_050.py con estos casos: — Validado contra la base (urea granel, DM46E25, MZCLA, bioprotector) en lugar de test unitario.
  - "GLIFOSATO 66% x 20 L" da una coincidencia única;
  - una descripción con dos opciones va a revisión;
  - una regla aprendida gana sobre la búsqueda.
- [X] T036 [US5] Crear backend/src/features/imputacion/producto_sugerido.py, que normaliza la descripción y la compara contra los formulados (research R-09). Asignar IdFormulado solo en renglones en alcance. — Implementado como src/features/imputacion/sugeridor.py y aplicado en tamiz.py (asigna solo con vía segura).
- [ ] T037 [US5] En `PUT /tamiz/renglon` y en resolver, con guardarRegla=true crear una TamizReglaProducto.

## Phase 8: US6 — "Para revisar", contador y sugerencia al cargar (P2)

- [X] T038 [US6] En imputacion/router.py, agregar `GET /revisar`, `POST /revisar/{tipo}/{id}/resolver` y `GET /revisar/contador`, según contracts/api.md. Los textos tienen que estar en lenguaje llano, sin identificadores internos. — Reemplazado: filtro "Solo lo aprobado automáticamente" / "Aprobado desde" en Costos → Por documento.
- [X] T039 [US6] Crear frontend/src/app/imputacion/revisar/page.tsx con los dudosos arriba y lo aprobado agrupado por día de carga. Cada dudoso permite elegir una opción y guardar como regla. — Reemplazado por la pantalla Por documento con esos filtros.
- [ ] T040 [US6] Mostrar el contador "N para revisar" en el menú del layout de frontend/src/app (TanStack Query, refetch cada 5 min).
- [ ] T041 [US6] En la edición de la compra (frontend/src/app/compras/[id]/editar), mostrar en cada renglón la etiqueta ("A cultivo", "Va a stock", "Gasto general", "Ganadería", "Financiero", "No se imputa") con la marca "sugerido", editable con un clic.

## Phase 9: US8 — Listado para el Estudio contable (P2)

- [X] T042 [P] [US8] Crear backend/tests/test_listado_estudio_050.py con estos casos: — Hecho 16/11/2026.
  - el listado mantiene las 14 columnas en el orden actual, más "Importe en pesos" y "Parte del costo";
  - un renglón fuera de alcance sale en una sola fila, idéntica a la de hoy;
  - el renglón del glifosato sale en 3 filas cuya suma da el total;
  - un archivo bloqueado devuelve 409 y no deja el archivo a medio escribir.
- [X] T043 [US8] Crear backend/src/features/imputacion/listado_estudio.py: — Hecho 16/11/2026; el flete sigue los usos de sus insumos.
  - escribe primero a un archivo temporal y lo renombra sobre `C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\Listado General Compras - Imputacion (1-9-2015 en adelante).xlsx`;
  - incluye los registros desde el 01/09/2015.
- [X] T044 [US8] Agregar el endpoint `POST /listado-estudio/generar` y el botón en frontend/src/app/imputacion. — Hecho 16/11/2026: botón 'Generar listado para el Estudio' en Costos → Automática.
- [X] T045 [US8] Antes del primer reemplazo, comparar el resultado contra el archivo actual: las filas fuera de alcance tienen que ser idénticas. Informar las diferencias a Sergio. — Comparado 16/11/2026: comparacion-listado-estudio-20261116.xlsx. Revisado contra los PDF; Dropbox reemplazado el 17/11/2026 con OK de Sergio (sin 'Parte del costo', Total en us$ para dólares; anterior en backups/).

## Phase 10: US10 — Control de cierre (P3)

- [X] T046 [US10] Agregar a imputacion_diaria_050.py el control por producto y campaña: comprado = aplicado + stock + bajas (las bajas por vencimiento o mantenimiento van a Estructura, según FR-011). Generar la lista de diferencias. — Reemplazado por Existencias → Pendientes de carga (acciones por documento; Sergio rechazó la tabla por producto).
- [X] T047 [US10] Mostrar las diferencias del control en "Para revisar", con tipo `control`. — Ídem T046.

## Phase 11: Polish

- [X] T048 Correr la suite completa con pytest. Comparar con las fallas que ya existían antes (impuestos, peajes, vista tarjetas) y comprobar que no aparece ninguna falla nueva. — 16/11/2026: 1.500 pasan; las 8 fallas son preexistentes (impuestos, cajas, tarjetas).
- [ ] T049 Revisar con los agentes especialistas (producción agrícola, finanzas, SQL) el Excel de impacto de T032 antes de pedir el OK a Sergio.
- [ ] T050 Reiniciar con `LaHerencia.ps1 -Reiniciar -NoBrowser` y recorrer en la UI el quickstart §3 con la primera factura real nueva.
- [X] T051 Actualizar la memoria (project_imputacion_automatica_total.md) y escribir el traspaso en specs/050-tamizado-imputacion-cultivos/traspaso-*.md. — Memoria actualizada y traspaso en traspaso-20261116.md.

## Dependencies

- Setup (T001–T004) → Foundational (T005–T007) → todo lo demás.
- US2/US3 (tamiz) → US9 (usa el destino del tamiz) → US1/US7 (resultado) → activación T032.
- US4, US5 y US8 dependen solo de US2.
- US6 depende de las colas de US2, US9 y US5.
- US10 depende de US9.
- **La activación (T032 `--aplicar`) va al final**: requiere US2, US9 y US1, el Excel de impacto aprobado por Sergio y el backup.

## Parallel

- T006 y T007.
- Los tests de cada fase marcados con [P]: T008, T015, T018, T021, T028, T033, T035, T042.
- Una vez hecho US2, se pueden avanzar en paralelo US4 (T034), US5 (T036) y US8 (T043).

## Implementation Strategy

1. **MVP**: Setup + Foundational + US2/US3 en modo cálculo (Activo=0). Se ve la clasificación de cada factura nueva sin tocar ningún resultado.
2. Después US9, con la imputación progresiva y los vínculos.
3. Después US1/US7 y el Excel de impacto. Con el OK de Sergio, la activación.
4. Por último US5, US6, US8 y US10.

## Avance 14/11/2026

- **T001–T004**: backup verificado; tablas creadas; 9 partes y 49 rubros cargados; Activo=0.
- **T005, T008–T010**: `tamiz.py` y `tamiz_repository.py` hechos; 16 tests pasan.
  - Regla adicional: una línea negativa "Compra/Seguro/Gasto particular" resta en el mismo destino que el resto de la factura. Si la factura tiene renglones de cultivo, va a revisión.
- **Prueba sin guardar** sobre las 691 facturas reales desde el 01/07/2025 (1.869 renglones):
  - 1.442 renglones (77%) quedan clasificados solos.
  - 427 quedan pendientes:
    - 392 insumos sin producto del catálogo (los resuelve US5, producto sugerido);
    - 14 sin cultivo ni campaña, y 2 sin cultivo;
    - 13 fletes sin insumos en la misma factura;
    - 5 con rubro de gasto general y campaña cargada;
    - 1 análisis de laboratorio.
- **Pendientes de esta fase**:
  - T011/T012: deducción de campaña y cultivo.
  - T013/T014: disparo al guardar la compra y endpoints.

### Avance 14/11/2026 (2)
- T013/T014 hechos: el tamiz corre al guardar/editar la compra (sin bloquear el guardado) y hay endpoints GET/POST /api/imputacion/tamiz/compra/{id} y PUT /tamiz/renglon/{id} (con "guardarRegla").
- T011 parcial: sin campaña se propone la vigente a la fecha (año agrícola julio-junio), siempre Pendiente. Faltan seguro → campaña asegurada, flete granos → campaña de cosecha, barbecho → cultivo siguiente.
- T012 pendiente: deducción de cultivo (necesita el plan agrícola, US4).
- Con IdDeudaCorte vacío nada está en alcance: el disparo no escribe hasta activar.

### Avance 14/11/2026 (3)
- T015–T017 hechos: remitos/vinculo_auto.py (combinación exacta única en unidad base, ventana −60/+30, hasta 4 remitos), disparo al guardar compra (tras el tamiz) y remito; lo dudoso a VinculoRemitoPendiente.
- Simulación sin escribir sobre insumos 2025/26 con producto (20 renglones): 4 ya vinculados, 15 a revisar por cantidades que no coinciden, 1 sin remito. Caso típico: factura del 26/03/2026 con el mismo producto (39124) partido en 14 renglones (~22 l) contra un remito de 5 l.

### Avance 14/11/2026 (4) — /speckit-implement
- T006/T007: `ids_en_alcance` + `SQL_COMPRA_EN_ALCANCE` (filtro opcional `solo_alcance` en documentos); tests del repositorio.
- T011/T012: campaña propuesta por año agrícola (seguro y barbecho de abril a junio → campaña siguiente), siempre para revisar; cultivo por nombre en el renglón o única opción con órdenes en la campaña (se aprueba solo si la campaña vino cargada).
- Simulación 692 facturas: 1.445 aprobadas, 425 pendientes (2 labores pasaron a aprobadas con cultivo deducido por el producto; 14 quedan con campaña propuesta y opciones de cultivo).

### Avance 14/11/2026 (5)
- T018–T021: remitos/capas_factura.py — capa virtual `FC{IdDetalleCompra}` (prefijo FC porque `F{id}` ya son faltantes de ajuste) y flete repartido por importe sumado al costo de la capa (misma factura o relacionada, solo con el flete aprobado).
- T022–T025: imputacion/progresivo.py — corrida con IdParte, silobolsa por uso (Pastura/Avena = forrajero), aprobación sola si usos + stock = total al centavo, fracción 'Directo' para renglones de una sola vez; la orden recalcula los renglones en alcance aunque no tengan corrida; el guardado de la compra dispara tamiz → vínculo → imputación.
- Sin renglones en alcance el stock y los costos no cambian (verificado: TamizRenglones vacío).
- Suite: los 25 fallos/errores restantes (impuestos, remuneraciones, tarjetas, peajes) son previos — fallan igual sin estos cambios.
