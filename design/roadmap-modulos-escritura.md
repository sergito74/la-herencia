# Roadmap: módulos de escritura pendientes (006-009)

Continuación de `design/erp-module-architecture.md` tras completar el módulo
fundacional de Contactos (2026-09-17). El usuario confirmó que los 4 módulos
siguientes son igualmente prioritarios ("todos los módulos son prioritarios y
necesarios inminentemente") y no fijó orden — el orden de ejecución real
(006 primero) se definió por dependencia técnica: Pagos de Compras Pendientes
(008) necesita que existan compras con vencimientos dados de alta por el
sistema nuevo para probarse end-to-end, y Compras (006) es el módulo con más
dependientes.

Cada uno sigue el ciclo completo ya usado en 002-005:
`/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` →
`/speckit-analyze` → `/speckit-implement`, con verificación read-only previa
contra los formularios Access reales (constitución principio VI: colaboración
de especialistas antes de tocar un dominio nuevo) y contra `INFORMATION_SCHEMA`
de `WC`/`LaHerencia` antes de clarify.

## 006 — Carga de Compras (alta/edición)

- **Alcance**: alta de una compra completa: cabecera (`Compras`: proveedor,
  fecha, tipo/número documento, tipo de cambio, centro de costos, rubro) +
  líneas (`Det_Compras`) + vencimientos (`Vencimiento Compras` / tabla real a
  confirmar en clarify). Edición de una compra existente. Reutiliza
  `ContactoSelect` para proveedor.
- **Fuente Access**: `Frm Compras`, `SbFrm Det_Compras`, `Sbfrm Vencimiento
  Compras` (ya inspeccionados parcialmente en la sesión de análisis previa).
- **Bloquea**: 008 (Pagos de Compras Pendientes) necesita vencimientos reales
  para calcular saldos pendientes.
- **Riesgo principal**: cálculo de IVA/tipo de cambio y validación de que la
  suma de líneas + vencimientos cuadre con el total de cabecera — replicar la
  lógica real del formulario Access, no inventar una nueva.

## 007 — Ventas de Hacienda (alta) y Ventas de Granos (lectura + alta)

- **Alcance**: (a) agregar alta a Ventas de Hacienda, que hoy solo tiene
  lectura (spec 005); (b) migrar Ventas de Granos desde cero — nunca se leyó
  ni escribió en el sistema nuevo.
- **Fuente Access**: `Frm Venta Hacienda` + `Subformulario Detalle Venta
  Feria Hacienda` (alta ya vista); `Frm Venta Granos` (pendiente de inspección
  read-only completa — hacerla en la fase clarify de este spec).
- **Riesgo principal**: Ventas de Granos es dominio nuevo — no asumir que
  comparte estructura con Hacienda solo porque ambos son "Ventas"; confirmar
  contra el Access real antes de modelar.

## 008 — Cálculo de Pagos de Compras Pendientes

- **Alcance**: vista consolidada de vencimientos de compras pendientes de
  pago (saldo pendiente por vencimiento, considerando pagos parciales ya
  registrados en Tesorería) + acción de "registrar pago" que enlaza un
  vencimiento con un movimiento de tesorería/cuenta corriente.
- **Fuente Access**: `Sbfrm Vencimiento Compras`, `Formulario pagos` / `Frm
  Gestion Operaciones` (ya inspeccionados parcialmente).
- **Depende de**: 006 (necesita vencimientos reales de compras nuevas para
  probarse íntegramente, aunque puede leer también los vencimientos legacy
  migrados).
- **Riesgo principal**: definir la relación real 1-a-muchos o muchos-a-muchos
  entre un vencimiento y sus pagos (¿un vencimiento puede pagarse en varias
  cuotas parciales desde distintos medios?) — confirmar contra datos reales,
  no asumir 1-a-1.

## 009 — Conciliación de Resúmenes de Tarjetas con Compras

- **Alcance**: cargar/leer resúmenes de tarjeta (líneas de consumo) y
  proponer/confirmar el enlace de cada línea con una Compra ya cargada —
  mismo patrón que las tablas `Tarjetas_Conciliacion_Link` /
  `Tarjetas_Conciliacion_Propuesta` ya identificadas en el inventario SQL de
  la sesión de "migración completa".
- **Fuente Access**: `FrmTarjetasResumen`, `sfTarjetasLineas`,
  `sfTarjetasDistrib` — pendientes de inspección detallada (solo se
  identificaron las tablas hasta ahora, no los forms).
- **Riesgo principal**: el más fragmentado de los 4 (múltiples formatos de
  resumen por banco/tarjeta, ya visto parcialmente en tesorería 003) — el
  spec debe acotar explícitamente qué formatos cubre en v1.

## Regla transversal (todos los specs 006-009)

- Todo alta/edición nueva escribe **exclusivamente contra `WC`**, nunca
  `LaHerencia` (regla de oro, `backend/src/db/connection.py`,
  `execute_write`/`execute_insert_returning_id`).
- Selección de contactos (proveedor/comprador/consignatario/banco/tarjeta)
  vía `ContactoSelect`, nunca texto libre.
- Cada spec agrega su propia entrada de navegación (`NavHeader.tsx` + home)
  como parte de su Fase 1 (Setup), no como tarea separada.
- Antes de `/speckit-clarify`, inspección read-only de los formularios Access
  reales listados arriba (COM automation, `acDesign`/`acHidden`) — no
  modelar a partir de solo los nombres de tabla.
- Consulta al agente especialista de dominio correspondiente
  (`07-financial-direction-specialist` para 006/008/009,
  `05-agricultural-production-specialist` para la parte de Ventas de Granos
  en 007) como checkpoint antes de cerrar el plan de cada módulo.
