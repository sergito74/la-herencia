# Traspaso a Codex — 22/10/2026 por la tarde

Punto de entrada para continuar. Antes de seguir, leer `.specify/memory/agent-guidance.md` y `constitution.md`. Todo lo de abajo está en `main`.

## 1. Nuevo desarrollo: spec 038, gestión de cajas de efectivo

- **Estado:** `specs/038-gestion-cajas-efectivo/spec.md` está **Clarified**: checklist completo y las 2 aclaraciones de Sergio resueltas (sección Clarifications). `.specify/feature.json` apunta a 038; es un archivo local ignorado por git, así que si no existe hay que recrearlo.
- **Siguiente fase:** `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. No regenerar la spec.
- **Decisiones de Sergio:**
  - Caja del Condominio: solo los movimientos relacionados con Giamigli. El Condominio tiene su propio sistema.
  - La planilla Cajas Giamigli.xlsx convive con el sistema hasta que Sergio confíe en él: importar sin duplicar y comparar planilla vs sistema caja por caja.
- **Base existente que hay que reusar:**
  - Backend `backend/src/features/cajas_efectivo/` (027, hoy solo lectura; slugs `giamigli-sa`, `campo-chica`, `condominio-lsc`).
  - Tabla `dbo.MovimientosCajaEfectivo`:
    - Columnas: `Caja`, `Fecha`, `Concepto`, `Detalle`, `Importe` (+ entrada / − salida), `Cuenta` (A/B/White/Blue/W), `FilaPlanilla`, `IdPagoEfectivo`, `Usuario`.
    - CHECK de Caja en ('GiamigliSA','CampoChica','CondominioLSC').
    - **No entra** en `vw_MovimientosCuenta_Base`.
  - Los pagos y cobros a contactos se ven en las cuentas corrientes a través de `dbo.[Pagos efectivo]` (Caja, IdTipoMovimiento, IdFormaPago, Cuenta). Un pago de caja nuevo debe crear **un** registro en `Pagos efectivo` (efecto en la cuenta del contacto) y **un** movimiento de caja vinculado (`IdPagoEfectivo`), nunca dos efectos sobre el contacto.
  - Cuentas de socio: `dbo.MovimientosCuentaSocio` (021; Tipo AsignacionGasto/Devolucion; valuación kg/US$ con `scripts/socios_valuacion_036.cot/cotizaciones` y `cuentas_socios.repository.deuda_actualizada`).
  - Traspasos bancarios: `TraspasosInternosTesoreria` (medios bna, galicia, mercado-libre, efectivo = Pagos efectivo…). Para vincular BNA con la caja se usó IdContacto NULL + `AuditoriaCorrecciones` (regla `traspaso-bna-caja-via-sergio`) + `Detalle` del movimiento de caja: modelar un vínculo formal en el plan.
  - Compras particulares: factura con línea negativa + `Pagos efectivo` Caja 'Particular S/L' negativo + AsignacionGasto del socio.
  - Arqueos: hoja "Recuento Caja Efectivo" de la planilla (80 recuentos por denominación, 2020–2026). Hoy no hay tabla en WC.
- **Reglas vigentes a respetar** (memoria y 036):
  - Retiros iguales de los socios = retiro de ganancias, sin efecto en la cuenta de socio.
  - Contacto 375 = Sergio empleado; 5670 = Sergio socio (alerta `AvisoCuentaContacto`).
  - Sueldo cobrado y devuelto a caja = no cobrado + traspaso (opción A).
  - Formato de números `formatMoneda` / `MoneyInput`; nunca `type=number`.

## 2. Revisión de cuentas (036): estado y pendientes

Detalle en `cajas-y-socios-plan-20261022.md` y `sergio-375-pendientes-resumen-20261022.md`.

### Hecho hoy

**Cuenta 375 de Sergio (empleado):**
- Cerrada con excepción en **−$1.800.000**, que es el sueldo de septiembre de 2026, pagado en octubre.
- Lo que no es sueldo pasó al contacto **5670 "Sergio Giamberardini (socio)"**.
- Sueldos no cobrados 2011–2019 cancelados con un ajuste por período.
- Allianz Taos devuelto a 515 con asientos Particular S.

**Cajas:**

| Caja | Movimientos | Saldo | Nota |
|---|---:|---:|---|
| Giamigli | 2.024 | $381.785,15 | Incluye los ingresos 2011–2015 identificados y un remanente NO identificado de $144.350,52 al 13/07/2015 |
| Caja chica | 100 | $96.907 | — |
| Condominio | 1.226 | $0,23 | 2016–2026 |

**BNA:** 17 aportes del Condominio de 2012–2015 asignados al contacto 549.

### Pendiente, en este orden

1. **Caja Condominio 2011–mar-2016:** desde `Documents\Alquileres urbanos\Condominio LSC\Movimientos LSC.xlsx` (hoja Movs, TIPO CAJA 'EF'). Con la decisión de 038, cargar al menos lo relacionado con Giamigli.
2. **Vincular cajas ↔ bancos ↔ cuentas de socio, de 2015 a 2026:**
   - Aportes y retiros de Sergio, Lucy, Ceci y del Condominio en la caja Giamigli y en la caja Condominio (por ejemplo, "Retiro Giamigli (Préstamo)" del 28/03/2016).
   - Cargas de la caja chica.
   - Retiros y depósitos bancarios.
   - Los egresos que pagó el Condominio y sus aportes en efectivo de 2011–2015 ($65.645,76 + $7.500) son aportes del Condominio a Giamigli: registrarlos en su cuenta de socio (socio 3) sin duplicar con los depósitos bancarios.
3. **Cuentas de socio en conjunto:**
   - Lucy (390, socio 2): **no tiene sueldo**, no se separa.
   - Condominio LSC (549, socio 3) y Virginia (564): pausa levantada.
   - Ceci (socio 4).
4. **13 depósitos BNA sin identificar de 2011–2014** ($211.716,52) y el remanente de caja de $144.350,52. Sergio no recuerda el origen: dejarlos como no identificados salvo que aparezca evidencia.
5. **Pendientes previos de 036:** AFIP (119); criterio C3 de Access; 5 tests con datos reales; 56 PDF de compras sin archivo.

## 3. Avisos técnicos

- Planilla `Cajas Giamigli.xlsx`:
  - Antes de editar por COM, verificar `Workbook.ReadOnly`: si Sergio la tiene abierta, el guardado falla en silencio.
  - Usar `Range("B12").Value2`; no asignar celdas dentro de funciones de PowerShell.
  - Hacer backup en `backups/` antes de editar.
- SQL Server: mínimo de memoria configurado en 1024 MB (autorizado). El listado de saldos de cuentas corrientes ya no usa la ventana de `vw_MovimientosCuenta_Saldo`.
- `execute_write_transaction` no acepta DDL ni listas vacías; para ALTER usar pyodbc con autocommit.
