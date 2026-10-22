# Cuenta de Sergio: pendientes y resumen

## Actualización 22/10/2026, 14:40

- **P18 aplicado** (`sergio_p18_retiro_20230905_036.py`): retiro adicional por compensación de pagos de Giamigli. Galicia 1390 pasa al 5670 y se agrega AsignacionGasto $30.000 del 05/09/2023 en la cuenta de socio.
- **Planilla** (Excel cerrado; backup `backups/Cajas Giamigli-20261022-antes-p18-p31.xlsx`): filas en Cuenta Sergio del 05/09/2023 ($30.000) y del 10/09/2025 ($485.400). Saldos acumulados encadenados, sin cortes.
- **375 = −$2.135.297,52** = −$1.800.000 (sueldo de septiembre de 2026, se paga en octubre) − $335.300 (historia 2011–2019).
- **Historia 2011–2019, NO implementada** (solo diagnóstico):
  - 2011–2012: Empleados.xlsx "Pagos Sergio G" cierra en 03/2013 con un saldo a favor de Sergio de $68.500. Sus pagos de 2011–2012 están en el 375 (BNA, Pagos efectivo Condominio y La Herencia).
  - 2013–2016: los sueldos de $8.000–$12.434 por mes no tienen ningún pago en el 375 ni en "Pagos Sergio G".
  - 2017–2019: hay pagos BNA con atraso que coinciden con sueldos de meses anteriores (por ejemplo, 14/05/2018 $31.500 = dic-2017; 30/05/2018 $24.400 = ene-2018; 30/01/2018 $21.000 = oct-2017; 08/10/2018, 27/12/2018 y 15/01/2019 $21.000 = feb/mar-2018). Los retornos de 2016–2018 (Codex) cubren parte.
  - Falta la decisión de Sergio: ¿los sueldos de 2013–2016 se cobraron (en efectivo, por el Condominio o con retornos) o quedaron sin cobrar? Si quedaron sin cobrar, pasan a su cuenta de socio como crédito y el 375 se cierra.


## Actualización 22/10/2026, 14:35 — cuenta separada en EMPLEADO y SOCIO (APLICADO)

**Decisiones de Sergio:**
- (1) Separar las cuentas, con una alerta operativa en pantalla.
- (2) Regla de compras particulares: **SIEMPRE** para este tipo de gastos.
- (3) El excedente de febrero de 2024 es deuda del socio.
- (4) P31 es una compensación.
- (5) Sobre P18 preguntó si hay $30.000 de más.

**Aplicado en WC (scripts con backup):**
- `allianz_taos_particular_036.py`: los 20 débitos de Allianz de la Taos (Galicia 02/2025–09/2026, $2.487.318,43) vuelven a Allianz (515) con reasignación 375→515, más un asiento "Particular S" (Pagos efectivo, negativo) por débito. Allianz sigue en $0. La deuda de socio ya existía, una por débito; mayo de 2026 es factura − NC $105.
- `sergio_cuenta_socio_contacto_036.py`:
  - Contacto nuevo **5670 "Sergio Giamberardini (socio)"**.
  - Se le reasignan 41 movimientos 2020–2026 del 375 que no pagan sueldo y tienen contraparte en la cuenta de socio o en Cuenta Cond LSC (lista en el script).
  - Ajustes internos: 267 (−$70.000 en el 375 / +$70.000 en el 390); 683 (−$200.000 en el socio 5670 / +$200.000 en el 390); retención de febrero de 2024 (−$9.248,64 en el 375; la deuda ya estaba en la cuenta de socio, mov. 2131: no se duplicó).
  - P31: AsignacionGasto $485.400 del 10/09/2025 en la cuenta de socio + reasignación de Galicia 2782.
- Frontend: `components/ui/AvisoCuentaContacto.tsx` (alerta en Cuentas corrientes, Revisión de cuentas y Cuentas de socios → Sergio) para los contactos 375 y 5670.

**Saldos:**
- **375 (empleado): −$2.105.297,52**, que se explica así:
  - Sueldo de septiembre de 2026, $1.800.000: se paga en octubre y el extracto llega hasta el 30/09.
  - Historia 2011–2019: sueldos sin pago identificado $672.700 − pagos sin sueldo $337.400 = −$335.300.
  - P18: +$30.000.
- 5670 (socio): $7.804.060. No se concilia, es el lado bancario de la cuenta de socio.
- 390 (Lucy): +$270.000 por las partes de Lucy.

**Pendientes:**
- **Planilla:** agregar en Cuenta Sergio la fila del 10/09/2025, "Devolución por aporte pagos varios" $485.400. No se pudo: Excel estaba abierto.
- **P18:** Giamigli te transfirió $30.000 el 05/09/2023 aparte del sueldo de agosto ($300.000, pagado el 31/08). No figura en Cuenta Sergio ni en la caja. Sigue en el 375. Propuesta: tratarla como retiro o compensación de socio (pasarla al 5670 + AsignacionGasto).
- **Historia 2011–2019 del 375** (etapa de Codex): 2018 enero, febrero, marzo y julio sin pago; sueldos 2011–2017 pagados por Condominio, caja o retornos.
- **Lucy (390):** revisar con el mismo criterio de separación cuando se retome.


## Actualización 22/10/2026, 14:20 (respuestas de Sergio y cambios aplicados)

**Respuestas de Sergio:**
- **P18:** la planilla "Sueldo Sergio" ($330.000 en agosto de 2023) es un error de tipeo; manda el recibo PDF del Estudio ($300.000). Por lo tanto, los **$30.000 del 05/09/2023 no son sueldo** y siguen sin explicación.
- **P31:** Sergio supone que es una compensación por gastos de Giamigli pagados desde su cuenta personal. **Evidencia:**
  - Banco receptor: "REEMBOLSO GASTOS 485.400".
  - Desde la última compensación (01/08/2025, $200.000), en Cuenta Sergio figuran pagos suyos por gastos de Giamigli: Irma agosto $194.621, Sancor $32.707, autónomos de Sergio $112.913,56 y de Lucy $47.635,83 (01/09), Torrontegui $55.500 (03/09). Suman $443.377,39; con los autónomos de julio ($111.113,52) llegan a $554.490,91.
  - Ninguna combinación da exactamente $485.400; la más cercana difiere en $936.
  - **No hay fila de compensación** en Cuenta Sergio para el 10/09/2025, a diferencia de las de 01/08/2025 y 11/11/2025.
  - Conclusión: la suposición es coherente, pero la composición exacta no está respaldada.
- **Puntos 3, 5 y 6:** aprobados. **Punto 4:** aprobado en principio, pero Sergio pidió que se le explique el mecanismo. **Puntos 1 y 2:** pidió más detalle.

**Aplicado en WC (con backup):**
- `scripts/sergio_lucy_galicia_20241104_036.py`: Mov. Galicia 2198 ($250.000) del 375 al 390, y 2199 ($90.000) del 390 al 375, con log en ReasignacionesContacto. El 375 bajó $160.000.
- `scripts/sergio_sueldos_2024_ganancias_036.py`: en la liquidación de julio de 2024 se cargó la devolución de Ganancias $63.326,76 (como Ajuste No Remunerativo) y el redondeo $0,24; en febrero, el redondeo $0,64. Saldo 375: **$8.465.329,55** (antes $8.688.657,19).

**Correcciones de hipótesis anteriores:**
- **Diciembre de 2024 NO falta:** la liquidación está fechada 01/01/2025 ($1.425.000) y coincide con el pago del 30/12/2024.
- **P36 / Allianz:** el Mov. 3200 tiene IdContacto 515, pero en la vista aparece en el 375 por la reasignación 2079 (01/10/2026, "Seguro TAOS gasto particular de Sergio"). En total hay **20 débitos de Allianz** (02/2025–09/2026, $2.487.318,43) reasignados al 375. La ficha de Allianz (515) está **cerrada**. Devolverlos exige reabrirla y aplicar la regla de compras particulares (pago en el proveedor + asiento Particular S + deuda de socio, que ya existe). **Sin aplicar:** se consulta a Sergio.
- **Febrero de 2024:** el recibo da un neto de $690.752 (Ganancias $9.248,64); se pagaron $700.000. La retención también se devolvió en julio. Sergio cobró **$9.248 de más** en febrero. **Sin aplicar:** propuesta, deuda en su cuenta de socio.

**Mecanismo propuesto para el punto 4 (pendiente de aprobación):**
- Contacto **375 = Sergio empleado**: solo recibos de sueldo (debe) y sus pagos y retenciones (haber). Cierra en 0.
- **Cuenta de socio** (MovimientosCuentaSocio, valuada en kg/US$): aportes, retiros, gastos particulares, compensaciones y retornos a caja.
- Las transferencias bancarias que no son sueldo se reasignan a un contacto nuevo, **"Sergio Giamberardini (socio)"**, igual que el Condominio tiene el 549. Ese contacto no lleva saldo propio: es el lado bancario de la cuenta de socio, que ya registra esos movimientos desde la planilla. No se duplica nada.
- Alternativa: dejarlas en el 375 con un documento interno de compensación por cada una.

Estado vigente al cierre de la retoma de Claude, 22/10/2026 por la tarde. Continúa la versión de Codex del mismo día. Los identificadores P/S están en [sergio-375-pagos-para-revisar-20261022.md](sergio-375-pagos-para-revisar-20261022.md).

"Conciliado documentalmente" significa que el pago y su comprobante o su registro en la planilla coinciden. **No significa que el sistema esté corregido**: en esta retoma no hubo escrituras en WC, Access ni las planillas. La cuenta 375 no está cerrada.

## Retoma de Claude: nuevos respaldos (solo documentales, sin cambios en el sistema)

| Línea | Débito Giamigli | Resultado | Evidencia |
|---|---:|---|---|
| P16 · 29/10/2021 | $140.000 | **Pago en lote**: $70.000 a Sergio (sueldo de octubre) + $70.000 a Lucy ("Honorarios de profesionales"). | Extracto Galicia de Lucy, 29-10 $70.000 "GIAMIGLI DE BOLIVAR" (`DDJJ Fisicas 2022\Lucy\Galicia\Extractos\...17-12-2021 - Galicia Lucy.pdf` y RAR Galicia Lucy 2021). Cuenta Lucy 29/10/2021 "Honorarios Directores" $70.000. |
| P17 · 01/08/2022 | $400.000 | **Pago en lote**: $200.000 a Sergio + $200.000 a Lucy, ambos "Devolución por aporte pagos varios". | Extracto Galicia de Lucy 01-08 $200.000 (`...19-08-2022 - Galicia Lucy.pdf`). Cuenta Sergio y Cuenta Lucy, 01/08/2022, $200.000 cada uno. Banco Giamigli: rubro "Retiro Directores". |
| P30 · 04/11/2024 | $250.000 (375) y $90.000 (390) | **Contactos cruzados**: el débito de $250.000 (Mov. Galicia 2198, asignado al 375) fue a Lucy; el de $90.000 (Mov. 2199, asignado al 390) fue a Sergio. | Extracto Galicia de Lucy 04/11/24 "REEMBOLSO GASTOS 250.000" (`DDJJ Fisicas 2024\Lucy\Galicia\CA Pesos\...19-12-2024.pdf`). Cuenta Sergio $90.000 y Cuenta Lucy $250.000 el 04/11/2024. |
| P15 · 27/09/2021 | $50.000 | Cobro y devolución: ese día la caja recibe "Aporte Efectivo Sergio" $50.000. | Hoja Caja Efectivo Pesos, 27/09/2021. |
| P18 · 05/09/2023 | $30.000 | Ajuste del sueldo de agosto de 2023: el recibo formal dice $300.000 y la hoja "Sueldo Sergio" toma $330.000 para agosto, como septiembre. | Recibos 2023-08 (neto $300.000) y 2023-09 (neto $330.000); hoja Sueldo Sergio, fila 31/08/2023 = 330.000. **Falta que Sergio lo confirme.** |
| P29 · 16/09/2024 | $270.360 | Retiro de Sergio por el aporte del Condominio para el pago del balance: $811.100 / 3 = $270.366,67. Diferencia de $6,67. | Cuenta Cond LSC, 14/09/2024 "Retiro por aporte pago balance" $270.366,67 (Sergio, Lucy y Ceci). |
| P32 · 11/11/2025 | $650.000 | $350.000 "Devolución por aporte pagos varios" (Cuenta Sergio) + $300.000 "Retiro por aportes varios" de Sergio en el Condominio. | Cuenta Sergio y Cuenta Cond LSC, 11/11/2025. |
| P33 · 11/12/2025 | $400.000 | Retiro de Sergio por aportes del Condominio. | Cuenta Cond LSC, 11/12/2025 (Sergio, Lucy y Ceci, $400.000 cada uno). |
| P34 · 10/02/2026 | $300.000 | Retiro de Sergio por aportes del Condominio; el mismo día la caja recibe un aporte en efectivo del Condominio por $300.000. | Cuenta Cond LSC y Caja Efectivo Pesos, 10/02/2026. Banco: "REINTEGRO VIATICOS". |
| P35 · 11/03/2026 | $330.000 | $130.000 "Devolución por aporte pagos varios" (Cuenta Sergio) + $200.000 "Devolución" a Sergio en el Condominio. | Cuenta Sergio y Cuenta Cond LSC, 11/03/2026. Banco: "REEMBOLSO GASTOS". |
| P36 · 07/05/2026 | $134.619,39 | Débito de Allianz (seguro de la Taos, mayo de 2026: factura $134.724,39 − NC endoso 4 $105). No es un pago a Sergio. | Ya registrado en la cuenta de socio (Allianz mayo, 22/10). Corresponde a la cuenta Allianz, no al 375 (pendiente 4 del avance). |
| P37 · 31/08/2026 | $700.000 | Cobro y devolución: ese día la caja recibe "Aporte Efectivo Sergio" $700.000. | Caja Efectivo Pesos, 31/08/2026. |

Resultado: de los $430.000 de diferencia entre emisor y receptor en P16/P17/P30, **todo está identificado**: $70.000 y $200.000 fueron a Lucy, y en P30 los dos contactos están cruzados ($160.000).

## Corrección efectiva pendiente en el sistema (propuesta, sin aplicar)

1. **P16 (Mov. Galicia 267, $140.000):** dividir en $70.000 al 375 (sueldo de octubre de 2021) y $70.000 al 390 (Lucy).
2. **P17 (Mov. Galicia 683, $400.000):** dividir en $200.000 Sergio y $200.000 Lucy. Son retiros de socio, no sueldo: se descuentan del 375 cuando se separen sueldos de socio (punto 4).
3. **P30:** reasignar Mov. Galicia 2198 ($250.000) al 390 y Mov. Galicia 2199 ($90.000) al 375. Antes, revisar que la ficha de Lucy (390) no esté cerrada (regla "reasignar sin reabrir").
4. **Separar sueldos de socio:** los pagos que la planilla registra como "Devolución por aporte pagos varios", los retiros y las devoluciones del Condominio (P17, P29, P32–P35) y los cobros devueltos a caja (P12, P15, P37, 19 retornos de 2016-2018) tienen que dejar de figurar como pago de sueldo en el 375. Definir el mecanismo (vínculo socio o traspaso) sin duplicar la cuenta de socio. Los movimientos del Condominio dependen de su revisión, que está en pausa.
5. **P36:** devolver el débito de Allianz a la cuenta Allianz.
6. Lo que Codex ya había dejado: febrero de 2024 (pago $700.000 / neto $690.752), liquidaciones 2024 (devolución de Ganancias $63.326,76) y la **remuneración de diciembre de 2024 que falta** en la vista ($1.425.000).

## Pendiente de confirmar por Sergio

| Línea | Fecha | Importe | Qué falta |
|---|---|---:|---|
| P10–P11 | 30/06/2016 | $10.000 + $10.000 | Confirmar si los dos ingresos de caja de ese día eran sueldo cobrado y devuelto. |
| P13 | 30/03/2017 | $21.000 | Hay una devolución de $17.735 el 01/04/2017; explicar los $3.265 de diferencia. |
| P14 | 14/06/2017 | $30.000 | La caja recibió $20.000; falta el destino de los otros $10.000. |
| P18 | 05/09/2023 | $30.000 | Confirmar que es el ajuste del sueldo de agosto (planilla: $330.000). |
| P31 | 10/09/2025 | $485.400 | Banco: "ACRED.HABERES" / "Reembolso gastos". No aparece en Cuenta Sergio, Cuenta Cond LSC ni en la caja (agosto a septiembre de 2025). Identificar el motivo. |

## Pendiente de investigación (de la etapa de Codex, sin cambios)

- Febrero de 2024, liquidaciones 2024 y diciembre de 2024: ver el punto 6 de arriba.
- Historia salarial 2011-2019: diferencias diciembre-2011/enero-2012 y el pago de $8.000 del 13/08/2012.
- Cierre de la cuenta 375: después de aplicar las correcciones aprobadas.

## Conciliado documentalmente (Codex, se mantiene)

P01–P02 (sueldos, Empleados.xlsx); P12 (retorno a caja 28/07/2016); P20, P21, P23 y P25 (netos de recibos de marzo a junio de 2024); P27 + P28 (neto de julio de 2024 con devolución de Ganancias); P19, P22, P24 y P26 (retenciones de Ganancias de los recibos); S01–S03 (acreditaciones salariales ICBC); 19 retornos de sueldo a caja de 2016-2018 ($328.503).

## Fuentes de la retoma de Claude

- Extractos Galicia de Lucy: `C:\Users\Sergio\Documents\Estudio Contable\DDJJ Fisicas 2021\Resumenes Galicia Lucy 2021.rar`, `...\DDJJ Fisicas 2022\Lucy\Galicia\Extractos\`, `...\DDJJ Fisicas 2024\Lucy\Galicia\CA Pesos\`.
- Banco Giamigli: WC `dbo.[Movimientos Galicia]` (IdMovimiento 267, 683, 2198, 2199; leyendas "ACRED.HABERES", "REEMBOLSO GASTOS", etc.).
- `Cajas Giamigli.xlsx`: hojas Cuenta Sergio, Cuenta Lucy, Cuenta Cond LSC, Caja Efectivo Pesos y Sueldo Sergio.
- Recibos `Personal\Recibos\2023\2023 07/08/09_SergioGiamberardini.pdf`.
