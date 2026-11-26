# Tasks: Módulo Ganadero (052): etapa 1

**Input:** [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api-ganaderia.md](contracts/api-ganaderia.md), [quickstart.md](quickstart.md)
**Tests:** las pide la Constitución (V): una verificación puntual por regla, con datos simulados. Ninguna prueba escribe en WC.
**Reglas para todas las tareas:**
- **Base y datos:** respaldo verificado antes de cualquier DDL o escritura masiva. Los scripts simulan y solo escriben con `--aplicar`. El saldo de las cuentas es el mismo antes y después.
- **Pantalla:** nada interno en pantalla. Números con los helpers de `lib/format.ts`.
- **Después de cada cambio:** reiniciar con `launcher/LaHerencia.ps1 -Reiniciar -NoBrowser`.

Etiquetas de historia:
- **[US1]** resultado
- **[US2]** stock
- **[US5]** controles base
- **[USD]** dólar único (FR-016), que es transversal y va primero

## Phase 1: Setup
- [x] T001 Crear el paquete `backend/src/features/ganaderia/__init__.py` y registrar el router `/api/ganaderia` en `backend/src/main.py`, siguiendo el patrón de `resultado_cultivo`.
- [ ] T002 [P] Crear la carpeta `backend/tests/ganaderia/` con un `conftest.py` de datos simulados, igual al de `backend/tests/documentos_nuevos/conftest.py`.
- [x] T003 [P] Crear las rutas vacías `frontend/src/app/ganaderia/{resultado,stock,controles,configuracion}/page.tsx` y el menú "Ganadería" de primer nivel en `frontend/src/components/layout/NavHeader.tsx`, con enlaces a `/ventas/hacienda`, `/ventas/pastaje` y al flujo de caja filtrado. Las pantallas sin implementar muestran "Próximamente".

## Phase 2: Foundational. Dólar único (FR-016), va primero
- [x] T004 [USD] Auditar todos los lugares que pasan a US$: buscar `Comp_Divisa`, `TC_CompDivisa`, `Prom_billete`, `Vend_Divisa`, `[Tipo de Cambio]` y `vw_CnsComprasDolarBNA` en `backend/src` y en las vistas SQL de WC. Clasificar cada uno en costo/resultado (se unifica), cuenta corriente (TC del comprobante, se deja) o proyección del flujo (vendedor, se deja y se documenta). Guardar el resultado en `specs/052-modulo-ganadero/auditoria-dolar-20261125.md`.
- [x] T005 [USD] Crear `backend/src/features/cotizaciones/dolar_gestion.py` con la regla única y un fragmento SQL reutilizable:
  - comprobante en US$ → su `[Tipo de Cambio]`;
  - comprobante en pesos → `[Dolar BNA].Comp_Divisa` de la fecha (último ≤ fecha);
  - "Ajusta TC" → 0.

  Exponer `usd(importe_pesos, fecha, moneda, tc, ajusta)` y `SQL_USD`.
- [x] T006 [USD] Reemplazar `_USD_SQL` en `backend/src/features/resultado_cultivo/costos.py` y las fórmulas equivalentes que la auditoría T004 haya marcado como "costo/resultado" por `dolar_gestion`, sin cambiar el resultado de los casos que ya usan esta regla.
- [x] T007 [P] [USD] Prueba `backend/tests/ganaderia/test_dolar_gestion.py`: comprobante en US$, en pesos con fecha sin cotización (toma la anterior), y "Ajusta TC" = 0.
- [x] T008 [USD] Verificación antes y después en el Resultado de cultivos, campañas 2023/24 a 2025/26: listar en `auditoria-dolar-20261125.md` las diferencias en US$ por cultivo que deje la unificación. Si hay diferencias, mostrárselas a Sergio antes de hacer commit.

## Phase 2b: Foundational. Esquema y forrajes
- [x] T009 Crear el script `backend/scripts/ganaderia_tablas_20261125.py` (simula, y con `--aplicar` hace respaldo y DDL). Debe crear:
  - las tablas `GanCategoria`, `GanCategoriaAlias`, `GanMovimiento`, `GanRecuento`, `GanRecuentoDetalle`, `GanRubroMapa`, `GanForrajeRegla`, `GanCalendarioCultivo`, `GanSuperficieAjuste`, `GanReserva`, `GanReservaConsumo`, `GanReparto` y `GanControlAceptado`, según [data-model.md](data-model.md);
  - en `GanMovimiento.Tipo`, el CHECK con "Nacimiento, Compra, Venta, Muerte, Consumo, CambioCategoria, PastajeEntrada, PastajeSalida, Traslado, AjusteRecuento";
  - `GanMovimiento.IdDetalleVenta` UNIQUE cuando no es NULL;
  - en `GanRecuento.Origen`, el CHECK con "Recuento, Acta, Cierre, Planilla";
  - en `GanForrajeRegla.Tratamiento`, el CHECK con "Consumo, Amortiza".
- [x] T010 En el mismo script, agregar `Map_CultivoResultado.EsGanaderia bit NOT NULL DEFAULT 0` y ponerlo en 1 para Sorgo, Maíz diferido, Avena, Pastura, Rye grass y Verdeos. Cargar los datos iniciales:
  - `GanCategoria` con los coeficientes EV de data-model;
  - los alias de la planilla y de las actas, incluida "Terneras Miguel";
  - `GanForrajeRegla`, con el desfase campaña → ejercicio: Avena del año N → ejercicio abr-N/mar-N+1; Maíz diferido N-1/N → abr-N/mar-N+1; Pastura Amortiza 4;
  - `GanCalendarioCultivo` (R3);
  - `GanReparto`, Personal permanente 70/20/10;
  - `GanRubroMapa` con los rubros de la planilla, con administración, honorarios y movilidad como Estructura.
- [x] T011 Excluir los cultivos con `EsGanaderia=1` en `backend/src/features/resultado_cultivo/resultado.py` (`_cultivos_con_datos`, alrededor de la línea 207) y en la constante VERDEOS de `formularios_access.py`. El silo deja de restarse "al vacío": `_costo_silo` sigue calculando, y su importe se expone para Ganadería.
- [x] T012 [P] Prueba `backend/tests/ganaderia/test_forrajes_traspaso.py` (SC-005): en un escenario simulado, el costo agrícola antes menos el costo agrícola después es igual al costo forrajero más el silo en Ganadería, al centavo.
- [x] T013 Crear la vista `vw_Gan_Costos` en el script T009. Fuentes:
  - las fracciones `VIGENTE_050` de ganadería o de cultivo `EsGanaderia`;
  - el tamiz con destino Ganadería;
  - el centro 2 fuera del alcance de 050.

  Netas de IVA y de `factor_particular`, con US$ calculado con `dolar_gestion`. Se agrega el personal permanente por `GanReparto`.
- [x] T014 Ejecutar T009–T013 con `--aplicar` después del respaldo, y registrar el respaldo y los conteos en `specs/052-modulo-ganadero/registro-aplicacion.md`.

## Phase 3: User Story 1. Resultado ganadero por ejercicio (P1) 🎯 MVP
**Objetivo:** el cuadro con la estructura de la planilla y el estándar del sector (FR-002/003/004/005/012/013/020/021/022).
**Prueba independiente:** quickstart §3 (2018/19 y 2022/23 contra la planilla, en pesos y con la diferencia de TC aparte) y §4 (ha efectivas 26/27).
- [x] T015 [US1] `backend/src/features/ganaderia/superficie.py`: ha efectivas por lote y mes.
  - Fuentes: `PlanAgricola` y las órdenes; siembra y cosecha reales (`Datos Cosecha`), o el calendario si faltan.
  - Pastura viva hasta su baja; rastrojo = ganadero sin costo; lote picado = ganadero desde el picado.
  - Ajuste por `GanSuperficieAjuste`.
- [x] T016 [P] [US1] Prueba `test_superficie.py`: lote de soja 1.ª (nov–abr fuera), pastura con baja anticipada y lote sin plan (12 meses).
- [x] T017 [US1] `backend/src/features/ganaderia/categorias.py`: regla R4 de unidad de medida → cabezas y kg, con `KgEstimado`, y pares de anulación/refactura neteados.
- [x] T018 [P] [US1] Prueba `test_categorias.py`: Kilos (0003-00010318 → 2 cabezas y 880 kg), Unidades, Pesos (sin hacienda) y el par 00002-00005483/5484.
- [ ] T019 [US1] `backend/src/features/ganaderia/forrajes.py`:
  - costo forrajero por ejercicio de consumo con el desfase de `GanForrajeRegla`;
  - amortización de la pastura desde el primer pastoreo, por lote, en 4 años, con baja anticipada si aparece un cultivo agrícola;
  - cosecha de un cultivo ganadero: el costo sigue en Ganadería; según el destino en `Datos Cosecha`, el destino propio pasa a reserva o forraje, y la venta es ingreso de Ganadería;
  - reservas (`GanReserva`), cuyo consumo pasa a costo promedio y cuyo saldo al 31/03 es inventario.
- [ ] T020 [P] [US1] Prueba `test_forrajes.py`: avena de marzo en el ejercicio siguiente, pastura rota en el año 2, sorgo cosechado para silo (sigue en Ganadería) y avena cosechada y vendida como semilla (ingreso ganadero), silo con consumo parcial (el saldo queda como inventario) y silo sin consumo (queda en stock y genera aviso).
- [x] T021 [US1] `backend/src/features/ganaderia/resultado.py`: el cuadro por ejercicio (abr–mar) y por campaña (jul–jun, "margen de caja, sin variación de inventario"). Contenido:
  - ventas por categoría A/B/total, comercialización y pastaje (`PastajeLiquidaciones`);
  - directos por `GanRubroMapa` y alimentación (forrajes + silo + reservas consumidas);
  - **ingreso neto** con diferencia de inventario estimada: cabezas del stock × `PesoTipicoKg` × precio de cierre cargado a mano (por ahora "estimada");
  - margen bruto, estructura sin repartir y resultado operativo consolidado;
  - indicadores: kg producidos (vendidos + consumo + final − inicial − comprados; sin terceros), costo directo por kg y por ha, ha efectivas, MB/ha, EV y EV/ha (con terceros);
  - columna "como planilla" para SC-001.
- [x] T022 [US1] `GET /api/ganaderia/resultado`, `/resultado/detalle` y `/superficie` en `backend/src/features/ganaderia/router.py`, con `schemas.py`, según [contracts/api-ganaderia.md](contracts/api-ganaderia.md).
- [ ] T023 [P] [US1] Prueba de contrato `test_api_resultado.py`: forma de la respuesta, `null` cuando no hay dato, período sin stock con su aviso.
- [x] T024 [US1] Pantalla `frontend/src/app/ganaderia/resultado/page.tsx` y `frontend/src/components/ganaderia/CuadroResultado.tsx`:
  - fila 1 con PageHeader y Segmentos; fila 2 con ejercicio/campaña, $/us$, rango y campo;
  - rubros plegables × períodos, con primera columna y encabezado fijos y `CeldaNumerica`;
  - "—" cuando no hay dato;
  - clic en una celda → `SideDrawer` con comprobantes y enlaces (patrón de `DetalleCostosPanel.tsx`);
  - exportar a Excel.
- [x] T025 [US1] Pantalla `frontend/src/app/ganaderia/configuracion/page.tsx`: categorías (EV, peso típico), mapa de rubros, reglas de forraje, calendario, reparto de personal, ajustes de superficie y precio de cierre estimado. Todo por nombre, sin ids. Hecho 26/11/2026: 9 secciones (categorías, nombres, rubros, forrajes, calendario, reparto, superficie, ajustes por lote, precio de cierre); categorías solo se editan; borrar solo en nombres, ajustes y reglas de valuación.
- [x] T026 [US1] Carga de reservas: `POST /api/ganaderia/reservas` y `/reservas/{id}/consumos`, más un bloque "Reservas forrajeras" en la pantalla de Stock. La confección se precarga desde `_costo_silo` del maíz picado. Hecho 26/11/2026: silos de maíz desde las facturas de confección; consumo registrado en % por fecha (Sergio: sin regla fija); sin registro = estimado al ejercicio siguiente, rotulado; último silo 20 % al 26/11/2026.
- [ ] T027 [US1] Verificación SC-001a contra la planilla (2018/19 y 2022/23) y SC-001b (forrajes por valor contra las solapas fuente). Guardar el informe en `specs/052-modulo-ganadero/verificacion-planilla.md`, con cada diferencia y su comprobante.

## Phase 4: User Story 2. Stock de hacienda (P1)
**Objetivo:** existencia por categoría, dueño y campo, armada por eventos (FR-006/007/009).
**Prueba independiente:** quickstart §5 y §6.
- [x] T028 [US2] `backend/src/features/ganaderia/stock.py`: existencia a una fecha = último recuento ≤ fecha ± movimientos posteriores no anulados, por establecimiento y dueño. La diferencia entre recuentos va como "sin explicar". El 409 si un movimiento dejaría la existencia negativa sin `confirmar`; el 422 si un AjusteRecuento no trae motivo.
- [x] T029 [US2] Endpoints `GET /stock`, `GET` y `POST /movimientos`, `POST /movimientos/{id}/anular`, `GET` y `POST /recuentos` en `router.py`.
- [x] T030 [US2] Hook en `backend/src/features/ventas_hacienda/repository.py`: el alta, la edición y la baja de una venta crean, actualizan o anulan un movimiento "Venta" por renglón (regla R4, uno por `IdDetalleVenta`).
- [x] T031 [P] [US2] Prueba `test_stock.py`: recuento + venta + nacimiento, existencia negativa (409), ajuste sin motivo (422), terceros separados de la propia, y venta editada que actualiza su movimiento sin duplicarlo.
- [x] T032 [US2] Script `backend/scripts/ganaderia_stock_historico_20261125.py` (simula / `--aplicar` con respaldo). Importa:
  - la solapa "Stock Hacienda" de la planilla, 23 recuentos con origen Planilla;
  - los stocks al 31/03 de 2021 y 2023 de los mails al Estudio, con origen Cierre;
  - la planilla Req Vacunas Oct 26, con origen Acta, y las 70 "Terneras Miguel" como terceros de San Justo (contacto 5671);
  - los movimientos de Venta de todas las ventas históricas.

  Lista los alias sin resolver antes de aplicar. Abre los Excel en solo lectura.
- [x] T033 [US2] Ejecutar T032 `--aplicar` después de revisar la simulación. Verificar quickstart §5 (26/10/2023 = 248 vacas, 20 toros, 7 toritos, 133 terneros, 96 terneras) y registrar el resultado en `registro-aplicacion.md`.
- [x] T034 [US2] Pantalla `frontend/src/app/ganaderia/stock/page.tsx` con:
  - la existencia a una fecha (categoría × cabezas, kg, dueño Propia/De terceros con su nombre, campo);
  - los movimientos en `DataTable`;
  - "Registrar movimiento" en `SideDrawer`;
  - el recuento rápido apto para celular (`/ganaderia/stock/recuento`, con `NumberInput` y `inputMode="decimal"` y motivo obligatorio cuando hay diferencia).

## Phase 5: User Story 5. Controles base (P2, entra en la etapa 1)
**Objetivo:** FR-011 en los grupos Ventas, Consignatarios, Stock, Pastaje, Imputación y Forrajes.
- [x] T035 Extraer `frontend/src/components/ui/MarcaRevisado.tsx` de `components/stock/ControlCierre.tsx`, con `SideDrawer` y motivo (sin `window.prompt`), y que ControlCierre lo use.
- [x] T036 [US5] `backend/src/features/ganaderia/controles.py`, con estos controles:
  - **Ventas:**
    - venta sin cabezas o sin kg;
    - kg por cabeza fuera de rango;
    - renglones idénticos en un mismo documento (solo aviso: "verificar con el PDF de la liquidación");
    - negativo sin su par.
  - **Consignatario:**
    - saldo ≠ 0 a 30 días de la venta;
    - Complemento sin cobro.
  - **Stock:**
    - existencia negativa;
    - teórica vs recuento.
  - **Pastaje:** facturado vs cabezas × días, meses sin liquidar.
  - **Imputación:**
    - Σ fracciones = renglón;
    - **Σ centros = total de compras** (SC-008);
    - centro y destino contradictorios;
    - compra de Ganadería sin imputar.
  - **Forrajes:**
    - reserva sin consumo registrado;
    - cosecha de un cultivo ganadero sin destino registrado;
    - pastura sin primer pastoreo.

  Las aceptaciones se guardan en `GanControlAceptado`.
  Hecho 26/11/2026. Sin dato en el sistema (no implementados): cosecha de cultivo ganadero sin destino y pastura sin primer pastoreo. "Complemento sin cobro" va dentro del saldo del consignatario. "Compra de Ganadería sin imputar" desde 01/04/2025. Corrida: al abrir la pantalla si pasaron 6 h, al guardar ventas/movimientos/recuentos/consumos de reservas, o con el botón.
- [x] T037 [US5] Endpoints `GET /controles`, `POST /controles/correr`, `POST /controles/aceptar` y `POST /controles/aceptados/{id}/quitar`. Corrida automática al guardar ventas, movimientos y reservas, y corrida diaria en la rutina existente.
- [x] T038 [P] [US5] Prueba `test_controles.py`: cada control con un caso positivo y uno negativo, y que la aceptación oculte el caso.
- [x] T039 [US5] Pantalla `frontend/src/app/ganaderia/controles/page.tsx`: grupos con contador, "Correr controles ahora", hora del último control y lista de aceptados con "Quitar la marca".

## Phase 6: Polish
- [ ] T040 [P] `GET /api/flujo-caja/por-rubro` con `centroCosto` opcional en `backend/src/features/flujo_caja/router.py` y en la exportación, y el enlace desde el menú Ganadería. Rotular "reparto aproximado".
- [ ] T041 [P] `NuevosParaRevisar` con un módulo "ganaderia" en Resultado, más el aviso de documentos nuevos del veterinario.
- [ ] T042 Correr `pytest backend/tests/ganaderia backend/tests/resultado_cultivo` y `npm run build` en `frontend/`, recorrer quickstart §1–§8, reiniciar con el launcher y actualizar `tasks.md` y la memoria.

## Fases posteriores (sin detallar)
- **Etapa 2:**
  - Valuación confirmada al cierre (NRV con % de gastos de las ventas reales; producción/tenencia en US$; informe para el Estudio en pesos).
  - Sanidad: plan, frascos y series, aplicación con baja de stock, carencia, trabajos veterinarios, observados, actas.
  - Conciliación resultado ↔ flujo (FR-023).
  - Reparto de estructura.
- **Etapa 3:**
  - Indicadores de cría.
  - Amortización de toros y mejoras.
  - Interés al capital y renta de la tierra (resultado económico).
  - Apertura cría/recría/invernada.
  - EV por peso.

## Dependencies
- T004–T008 (dólar único) → todo lo demás.
- T009–T014 (esquema) → US1, US2 y US5.
- US1 usa el stock de US2 para la diferencia de inventario y los kg producidos. Se pueden hacer en paralelo, pero T021 se cierra después de T033.
- US5 va después de US1 y US2.

## Parallel examples
- Pruebas T007, T012, T016, T018, T020, T023, T031 y T038 (archivos distintos).
- T003 (frontend) en paralelo con T004–T006 (backend).

## Implementation strategy
1. Dólar único y verificación con Sergio (T004–T008).
2. Esquema y forrajes fuera del Resultado de cultivos (T009–T014).
3. US1 (MVP visible: el cuadro de resultado).
4. US2 (stock e histórico).
5. US5 (controles).
6. Polish.

Hay un commit y un push por cada bloque verificado.
