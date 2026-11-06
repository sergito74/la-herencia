# Tasks: Recibos de Proveedores y Órdenes de Pago (046)

**Branch**: `046-recibos-ordenes-pago` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Tareas de Implementación

### Fase 1: Base de Datos y Repositorio de Órdenes de Pago
- [X] **T001**: Tomar respaldo verificado de la base de datos `WC` con `COPY_ONLY` y `CHECKSUM` según constitución.
- [X] **T002**: Crear las tablas `dbo.OrdenesPago`, `dbo.OrdenesPago_Detalle` y `dbo.OrdenesPago_Medios` mediante script de migración SQL.
- [X] **T003**: Implementar `backend/src/features/ordenes_pago/schemas.py` con los modelos Pydantic de solicitud y respuesta de Órdenes de Pago.
- [X] **T004**: Implementar `backend/src/features/ordenes_pago/repository.py` (consulta de facturas pendientes con saldo, creación y edición de OP, emisión y anulación).
- [X] **T005**: Implementar tests unitarios y de contrato para el repositorio en `backend/tests/test_ordenes_pago_repository.py`.

### Fase 2: Ingesta y Clasificación de Recibos de Proveedores
- [X] **T006**: Configurar en `backend/src/features/documentos_nuevos/clasificador.py` el enrutamiento de tipo `recibo` hacia el módulo `pagos` (en vez de `compras`).
- [X] **T007**: Actualizar `backend/src/features/documentos_nuevos/carpetas.py` y `router.py` para admitir el módulo `pagos` con enlaces al nuevo panel.
- [X] **T008**: Validar la ingesta con tests en `backend/tests/documentos_nuevos/test_clasificador.py` y `test_carpetas.py`.

### Fase 3: Endpoints de la API y Vinculación
- [X] **T009**: Crear `backend/src/features/ordenes_pago/router.py` e incluirlo en `backend/src/main.py`.
- [X] **T010**: Implementar endpoint para vincular Recibo Oficial contra OP / débitos bancarios y generar las aplicaciones en `dbo.AplicacionesPago`.
- [X] **T011**: Ejecutar suite de pruebas de API en `backend/tests/test_ordenes_pago_api.py`.

### Fase 4: Frontend y Flujo de Usuario
- [X] **T012**: Crear servicio de cliente API en `frontend/src/services/ordenesPagoApi.ts`.
- [X] **T013**: Crear la vista principal `frontend/src/app/finanzas/ordenes-pago/page.tsx` con listado de Órdenes de Pago y bandeja de Recibos pendientes.
- [X] **T014**: Implementar el modal/formulario interactivo `FormularioOrdenPago.tsx` para confeccionar la OP seleccionando facturas de compra pendientes y medios de pago.
- [X] **T015**: Implementar el componente de vinculación de recibo (`VincularReciboModal.tsx`) con previsualización del PDF original.
- [X] **T016**: Agregar el acceso en el menú principal `frontend/src/components/layout/NavHeader.tsx` bajo Finanzas.
- [X] **T017**: Ejecutar build del frontend y pruebas de integración finales.


### Fase 5 y 6: Retenciones y recibos con retención/anticipo (Historias 4 y 5)
- [X] **T018**: Cálculo de retenciones de Ganancias al preparar la OP con el simulador público RG 830 de ARCA (https://servicioscf.afip.gob.ar/calc-rg830/, sin login; Sergio 30/10/2026). Endpoints JSON `default.aspx/conceptosalcliente` y `default.aspx/CalcularRetencion` (sesión con GET previo). Base: pagos del mes al proveedor + pago actual, neto de IVA, menos retenciones ya practicadas en el mes; Inscripción (Sergio 30/10): padrón público de ARCA `apellidoNombreDenominacion.zip` (Ganancias AC/NI/EX/NC, monotributo), sin captcha; la constancia web tiene captcha y no se automatiza. Concepto (bienes 78 / servicios 94 / otros): según la descripción de los renglones de cada factura.
  Implementado 30/10/2026: `backend/src/features/retenciones_ganancias/` (simulador, padrón, borrador rubro→régimen, exclusiones, propuesta acumulada por mes, mail .eml al estudio), pestaña Retenciones en la pantalla. Tablas con respaldo (`scripts/retenciones_046.py`). 34 CUIT completados desde las facturas (`scripts/cuit_desde_facturas_046.py`). Validado contra Detalle de Pagos.xlsx: coincide al centavo una vez aplicada la acumulación mensual.
- [X] **T019** (Historia 5): Recibos con anticipos sin factura y con retenciones (vistos en Bayá Casal): hoy quedan pendientes en la bandeja; definir su aplicación. Incluye vincular una OP con retención: el banco cubre el neto y la retención (certificado del estudio, tabla Retenciones) cubre el resto de la factura.
- [X] **T020**: Contactos sin CUIT que quedaron sin resolver (SENASA, ACA Bolívar, YPF, Edecan, El Luchador, etc.): cargar a mano; la pantalla avisa "El proveedor no tiene CUIT cargado". Hecho 30/10: 37 completados en total (34 desde los PDF y 3 por nombre único en el padrón: PC Electro Tigre, Edecan, YPF Debenedetti/OPESSA). Quedan 17 sin CUIT: organismos del Estado (SENASA, Ministerio de Trabajo, Dirección de Personas Jurídicas), a los que no se retiene, y compras ocasionales (Vanina Silva, El Luchador, Berre, YPF Acceso Oeste/Pilar, ACA Bolívar, Rolyns TV, Arlas, Martínez, Katat, Piccirilli, Agroveterinaria Central, Palacios, Gutiérrez).
- [X] **T021**: DDL de las columnas de recibo con retención/anticipo, con respaldo verificado.
- [X] **T022**: `VincularInput` y `vincular` con retención y anticipo, más sus tests.
- [X] **T023**: Pantalla de vinculación: retención precargada desde la OP, certificado y anticipo; build.

## Phase 7: Convergence

- [X] T024 Pasar la OP emitida a `Pagada` cuando los débitos reales que la cubren llegan a Tesorería (Galicia, BNA o efectivo, mismo proveedor, neto de la OP), sin esperar el recibo. Sin duplicar aplicaciones si después se vincula el recibo, por plan: Fase 3.1 (partial)
- [X] T025 Preseleccionar en `VincularReciboModal.tsx` la OP emitida del proveedor cuyo neto o total coincide con el recibo, y precargar sus facturas e importes para confirmar con un click, por US3/AC1 (partial)
- [X] T026 Prueba de punta a punta con un recibo real (Bayá Casal o Sancor): ingesta a Pagos sin entrar a Compras, vinculación con la OP o el débito, y factura saldada en Cuentas Corrientes al centavo, por spec §4 / T017 (missing) — Hecho 30/10: la rutina ingresó 8 documentos a Pagos y ninguno a Compras; 4 eran cupones de Sancor (avisos), el clasificador se corrigió y salieron de la bandeja; recibo Bayá 0006-00074244 (retención 0000-2026-000013) vinculado en WC, PDF verificado por hash, saldo de la cuenta 226 sin cambios.
- [X] T027 Admitir facturas en US$ en OP y vinculación de recibos (las de Bayá Casal): saldo en pesos al TC del comprobante (regla usd-tc-comprobante), moneda visible en pantalla, retención con base proporcional por neto, por spec H4/AC5 y T026 (missing)

## Phase 8: Facturas a pagar reales (Sergio 05/11/2026)

- [X] T028 Pagos hechos que esperan el extracto: se leen los comprobantes de transferencias (Office Banking Galicia) y eCheqs emitidos de `Documents/La Herencia/Administracion y gestion/Cuentas a pagar/{Transferencias,Cheques electronicos}` (tabla `dbo.PagosEmitidosComprobantes`, DDL con respaldo `scripts/pagos_emitidos_046.py`; lector `backend/src/features/ordenes_pago/comprobantes_emitidos.py`). Se confirman solos contra el débito de Galicia (mismo importe, desde la fecha de envío/pago hasta 7 días; si hay más de un débito, desempata el proveedor). Los sin confirmar posteriores al extracto cargado (−10 días) se descuentan de lo que se debe y se muestran aparte ("Pagados, esperando el resumen del banco", endpoint `/api/ordenes-pago/en-camino`). Primera lectura 05/11: 47 comprobantes reconocidos (43 confirmados), 4 en camino (Jáuregui, Arlas, Basterrechea 545, eCheq 126 Pérez). ~1.400 PDF de formatos viejos no se reconocen (históricos, ya cubiertos por extractos).
- [X] T029 Sin portal: lo que debe la cuenta (menos pagos en camino) son sus documentos más nuevos hasta completar el saldo (lo pagado cubre lo más viejo; regla pago-vencidas-primero confirmada por Sergio 05/11). Se listan facturas, impuestos/tasas, sueldos, alquileres y pastaje; cargos de tarjeta, movimientos bancarios y ajustes cuentan para el saldo pero no se listan. Cuentas con saldo < $300 fuera (umbral de Sergio 27/10). Con portal: lo impago del portal menos los pagos en camino (cubren lo más viejo). Tarjeta: proveedores que se pagan con tarjeta quedan marcados y fuera de "a pagar".
- [ ] T030 Pendiente: el comprobante de transferencia a Ricardo Criado del 10/09/2026 ($1.150.754) no tiene débito igual en Galicia; revisar con Sergio.
- [X] T031 Canje de granos (Sergio 05/11): columna `Compras.CanjeGrano` (DDL con respaldo `scripts/compras_canje_046.py`), casilla "Canje de granos" + grano en el formulario de compras; en Facturas a pagar quedan como "canje" (fuera de lo que se paga en plata, visibles con "Ver también…"). Guazzaroni 0037-3310 y 3313 vencen 30/01/2027 (grano sin definir); 0023-13569 Soja, vence 31/05/2027.
- [X] T032 Contratos de canje (Sergio 05/11): tabla `dbo.ContratosCanje` + `Compras.IdContratoCanje` (DDL con respaldo `scripts/contratos_canje_046.py`); en el formulario de compras, al tildar "Canje de granos" se elige el contrato del proveedor (fija el grano); el listado de facturas a pagar muestra grano, campaña y contrato. Cargados los 2 de Guazzaroni desde Documents/La Herencia/Agricultura/Contratos: 0001-00001365 Trigo 26/27 30 t (facturas 0037-3310 y 3313) y 0001-00001735 Soja 26/27 30 t (factura 0023-13569). Vigentes agregados 05/11 (Sergio "adelante"): Cargill 901549469 Trigo 26/27 30 t (entrega dic-2026) y 901549401 Trigo 26/27 30 t (entrega ene-2027). El resto de la carpeta tiene entrega vencida (hasta Cargill 25/26: soja may-2026, girasol 901482705 mar-2026); GDM5426026770 es una licencia de semilla, no un contrato de granos.
- [X] T033 Tipo de contrato (Sergio 05/11): `ContratosCanje.Tipo` canje|venta (DDL con respaldo `scripts/contratos_tipo_046.py`). Solo los de canje se ofrecen para cancelar una factura; los de venta fijan precio por fuera. Guazzaroni 1365 y 1735 = canje ("Venta a fijar por insumos"); Cargill 901549469 y 901549401 = venta (el contrato no menciona canje ni insumos).
- [X] T034 La orden de pago ofrece las mismas facturas que el listado (`facturas_a_pagar`: documentos más nuevos hasta el saldo de la cuenta menos pagos en camino, sin canjes; con portal sigue el saldo por factura). Importes de la orden en formato moneda (Sergio 05/11: Agrovet mostraba 3 facturas, solo la 0003-69294 está impaga).
- [X] T035 Adelanto financiero contra canje (Sergio 05/11): contratos bajados en solo lectura del portal de Cargill (GET api.cglcloud.com/api/dxo/gps/v1/contracts, customerId 35192801; copia en el scratchpad de la sesión). El AF de US$ 60.000 del 03/06/2026 (Galicia mov. 3261, $83.940.000) se cancela con 901517036A Girasol 26/27 114,286 t (entrega mar-2027) y 901517055A Soja 26/27 183,674 t (entrega jun-2027), firmados el 01/06/2026. Columnas `ContratosCanje.MedioAdelanto/IdMovimientoAdelanto/Fuente` (DDL con respaldo `scripts/contratos_adelanto_046.py`). En facturas a pagar aparece como "canje" (fuera de lo que se paga en plata). Los trigo 901549469A/901549401A quedan como venta.
