# Inversiones: plazos fijos y FCI Fima. Conciliación, imputación y resultado

19/11/2026. Hecho por el agente forense (10) con criterio de dirección financiera (07). Base WC, solo lectura: no se escribió nada en la base ni en el código.

## 0. Estado actual (verificado en la base)

- **Flujo de caja** (`flujo_caja/clasificacion.py`): `_es_plazo_fijo` y `_es_interno_galicia` (cualquier texto con "FIMA") marcan el movimiento **entero** como interno: Constitución/Vencimiento Plazo Fijo y Colocación/Rescate FIMA. Con eso el capital queda bien excluido, pero **el interés también**. Hoy los intereses ganados no aparecen en ningún rubro de ingreso: se pierden dentro de "Movimientos entre cuentas propias".
- `flujo_caja/fima_posiciones.json`: tiene 31 saldos de fin de mes del Fima, del 27/03/2024 al 30/09/2026 (saldo, cuotapartes y valor de la cuotaparte), sacados de los extractos oficiales de Galicia. Hoy solo se usan para mostrar el saldo de la cuenta "Galicia Fondo FIMA".
- **Conciliación de Tesorería**: 37 movimientos Fima de Galicia están en `ConciliacionesTesoreriaEstado` como `SinDocumento/Otro`. Los cargó el usuario `conciliacion-masiva-fima` el 29/09/2026 con el detalle "Movimiento interno de fondo comun de inversion". Es un cierre sin documento y además mezcla capital con rendimiento. Los otros ~94 movimientos Fima, los 6 de plazo fijo de Galicia y los 36 de BNA están sin conciliar. Ninguno tiene un traspaso interno (`TraspasosInternosTesoreria` = 0).
- No hay retenciones de Ganancias asociadas a estos movimientos en ninguno de los dos bancos. Los únicos "INTERESES" que aparecen son intereses deudores, que son un gasto.
- No existe un estado de resultados general de la empresa. Solo están el Resultado de cultivo (`resultado_cultivo/`) y el Flujo de caja.

## 1. Emparejamiento

### BNA, plazo fijo: aparea limpio por `[Nro# Comprobante]`
Cada `DEB.P.FIJO CANAL ELECT.` (constitución) tiene un `PLAZO FIJO` (acreditación) con **el mismo número de comprobante**. Hay **17 pares exactos** (2018–2026), de 30 a 60 días cada uno. Ejemplos:

| Comprobante | Constitución | Acreditación | Interés | % período |
|---|---|---|---|---|
| 7664 | 02/08/2018 −150.000,00 | 06/09/2018 155.118,82 | 5.118,82 | 3,41% (35 d) |
| 55714 | 08/09/2023 −2.700.000,00 | 09/10/2023 2.954.539,73 | 254.539,73 | 9,43% (31 d) |
| 80098 | 03/11/2025 −9.000.000,00 | 03/12/2025 9.281.095,89 | 281.095,89 | 3,12% (30 d) |
| 81415 | 18/12/2025 −5.000.000,00 | 19/01/2026 5.107.397,26 | 107.397,26 | 2,15% (32 d) |

**No cierran (2):** los movimientos 12021 (02/06/2016) y 17483 (22/06/2016), los dos con concepto "PLAZO FIJO" por **−200.000**, con el mismo comprobante 40029280 y sin acreditación. Son anteriores a 2015+1 y probablemente sean un duplicado heredado. Están a verificar con el extracto.

### Galicia, plazo fijo: no hay número de comprobante, se aparea por importe, fecha y tasa
- 05/09/2023 −4.000.000 → 05/10/2023 +4.353.983,56. Interés 353.983,56 (8,85% en 30 d). Aparea.
- 11/10/2023 −1.800.000 → 10/11/2023 +1.959.292,60. Interés 159.292,60 (8,85% en 30 d). Aparea.
- **No cierra:** la constitución del 12/09/2023 por −4.500.000 no tiene acreditación en 2023, y la acreditación del 14/08/2024 por +9.257.546,87 no tiene constitución. La hipótesis es una renovación automática con capitalización durante ~11 meses (4,5 M → 9,26 M, coherente con las tasas 2023-24). Si se confirma, el interés total sería 4.757.546,87. Está a verificar con la constancia o el extracto del banco.

### Galicia, FCI Fima: no se aparea 1 a 1
Son 17 suscripciones y 111 rescates (todos parciales, por importes redondos), con cuotaparte variable: de 42,50 en 03/2024 a 85,37 en 09/2026. Un rescate no "corresponde" a una suscripción en particular, así que aparear movimiento con movimiento no tiene sentido. El método correcto es **por saldo**:

> Rendimiento del período = Saldo final − Saldo inicial + Rescates − Suscripciones

Los saldos salen de `fima_posiciones.json`. El rendimiento mensual dio **positivo los 31 meses**, sin ningún mes negativo, lo que confirma que los extractos y los movimientos son consistentes. Para octubre y noviembre de 2026 todavía faltan las posiciones de fin de mes (hay rescates por $12,6 M y $16,8 M sin cerrar).

## 2. Tratamiento contable: alternativas

| Alternativa | Pros | Contras |
|---|---|---|
| A. Como hoy: todo interno o `SinDocumento/Otro` | Ya está hecho | El interés no entra en el resultado. Son cierres sin documento. Viola "sin cuadres escondidos" |
| B. Interno en el flujo y `SinDocumento/Interes` en el bancario | Cambio mínimo | Para el Fima no hay un movimiento de "interés" que marcar: el rendimiento está dentro de los rescates. No hay activo, así que no se ve cuánto queda invertido |
| **C. Medio nuevo "Inversiones" (subcuentas Plazo fijo BNA, Plazo fijo Galicia, FCI Fima Galicia) + traspaso interno por el capital + documento interno "Rendimiento de inversión"** | El capital es un traspaso banco↔inversión, igual que entre bancos. El interés es un ingreso con respaldo: el comprobante del plazo fijo o el extracto del Fima con su saldo. El saldo del activo se concilia con el extracto oficial. Encaja con `traspasos_internos_tesoreria` | Requiere una tabla de movimientos de inversión, sumar el medio a `MEDIOS_SOPORTADOS` y crear un tipo de documento interno |

**Recomendación: C.** Funcionaría así:
- **Plazo fijo**: al constituirse, el banco baja (−capital) y la inversión sube (+capital), y eso se registra como un traspaso. Al vencer, la inversión baja (−capital) y el banco sube (+capital + interés). El traspaso es por el capital, y la diferencia es un **documento interno de ingreso "Intereses plazo fijo"**, con el comprobante del banco como respaldo. El banco queda conciliado: un tramo por traspaso y otro por documento.
- **Fima**: cada suscripción y cada rescate es un traspaso Galicia↔Fima, al valor nominal. A fin de mes, el sistema genera **un documento de rendimiento mensual** por la diferencia que da la fórmula, y el saldo del Fima en el sistema queda **igual al extracto oficial, al centavo**. Este es el control de cierre.
- Los 37 `SinDocumento/Otro` de la masiva del 29/09 se reemplazan por estos traspasos.

## 3. Cómo entra en los resultados
- **Rubro**: un rubro nuevo de ingreso, "Resultados financieros", con dos subrubros: "Intereses plazo fijo" y "Rendimiento FCI". Va **fuera del neto operativo agropecuario** pero dentro del resultado de la empresa. Los intereses deudores y las comisiones van a ese mismo rubro, como egreso.
- **Centro de costos**: Administración general / Estructura. **No va al Resultado de cultivo**, porque no es un ingreso de ninguna campaña ni de ningún lote.
- **Momento**: el plazo fijo se reconoce al vencimiento (por percibido, y casi todos duran ≤ 35 días, así que el devengado cambia muy poco). Solo los plazos fijos que cruzan el cierre del ejercicio se devengan a la fecha de cierre. El Fima se reconoce mensual, por la diferencia de saldos, que ya es su valuación a mercado.
- **Moneda**: todos los casos son en pesos. Si algún día hay un plazo fijo o un FCI en US$, se lleva en dólares y el interés se convierte al TC del día de la acreditación (la regla del comprobante, que acá es la constancia del banco).
- **Impuestos** (a validar con el Estudio): la sociedad anónima tributa Ganancias sobre los intereses y los rendimientos de FCI. Para personas jurídicas esas rentas no están exentas, se suman al resultado impositivo del ejercicio y el Fima se valúa a la cuotaparte del cierre. En los datos no hay retenciones de Ganancias sobre estas rentas. Los intereses de plazo fijo están exentos de IVA. Ley 25.413: el débito para constituir y el crédito al vencer en la misma cuenta suelen estar exentos, y está a verificar si en las fechas de los plazos fijos hay débitos 25.413.

## 4. Rendimientos reales por año (calculados de la base)

| Año | PF BNA | PF Galicia | FCI Fima | Total |
|---|---|---|---|---|
| 2018 | 18.309,56 | – | – | 18.309,56 |
| 2019 | 187.138,37 | – | – | 187.138,37 |
| 2020 | 45.008,22 | – | – | 45.008,22 |
| 2021 | 50.673,97 | – | – | 50.673,97 |
| 2022 | 0 | – | – | 0 |
| 2023 | 464.375,35 | 513.276,16 | – | 977.651,51 |
| 2024 | 0 | (4.757.546,87 a verificar) | 2.837.065,68 | 2.837.065,68 (+4,76 M) |
| 2025 | 281.095,89 | – | 5.842.119,58 | 6.123.215,47 |
| 2026 (Fima hasta 30/09) | 107.397,26 | – | 6.332.911,62 | 6.440.308,88 |

Suscripciones y rescates del Fima: 2024 52,0 M / 52,0 M; 2025 136,0 M / 132,6 M; 2026 200,5 M / 169,8 M. Saldo al 30/09/2026: $78.512.096,88.

**Casos que no cierran:** (a) los 2 movimientos de BNA de 2016 por −200.000; (b) el plazo fijo de Galicia de 4,5 M (12/09/2023) contra la acreditación de 9.257.546,87 (14/08/2024); (c) el Fima de octubre y noviembre de 2026, que espera la posición de fin de mes; (d) los 37 `SinDocumento/Otro` de la masiva, que hay que reemplazar.

## 5. Automatización (igual que la regla de la Ley 25.413)
Se corre al iniciar, todos los días y después de cada extracto:
1. **BNA**: si hay `DEB.P.FIJO` y `PLAZO FIJO` con el mismo comprobante, la acreditación es mayor que la constitución y pasaron ≤ 400 días, se generan el traspaso y el documento de interés.
2. **Galicia PF**: se aparea la constitución con la primera acreditación de 25 a 400 días después que tenga una tasa implícita razonable (por ejemplo, de 0 a 15% mensual). Si hay ambigüedad o falta un lado, va a excepción.
3. **Fima**: cada suscripción o rescate genera su traspaso de inmediato. Cuando se carga la posición mensual del extracto, se genera el documento de rendimiento del mes. Si el rendimiento da negativo, va a excepción para revisar, sin bloquear nada: un FCI de pesos puede tener un mes negativo.
4. **Excepciones para Sergio**: falta un lado del par, una inversión con más de 400 días abierta, un mes de Fima sin posición o con rendimiento negativo, y el control de que el saldo del sistema y el del extracto difieran aunque sea en un centavo.

Además, la posición mensual del Fima tiene que entrar sola cuando se lee el PDF del extracto de Galicia, y no a mano en el JSON.

## 6. Preguntas para Sergio
1. ¿Aprobás el modelo C (cuenta "Inversiones" con traspasos y un documento interno de rendimiento), y que los 37 `SinDocumento/Otro` del Fima se reemplacen por eso?
2. El plazo fijo de Galicia de $4.500.000 del 12/09/2023 y la acreditación de $9.257.546,87 del 14/08/2024: ¿es el mismo plazo fijo renovado con capitalización? ¿Tenés las constancias?
3. Los dos débitos "PLAZO FIJO" de BNA por −$200.000 de junio de 2016 (mismo comprobante 40029280): ¿los tomamos como un duplicado heredado y quedan fuera del alcance?
4. Para el resultado: ¿reconocemos el Fima mes a mes (por valuación) y el plazo fijo al vencimiento, devengando solo lo que cruza el cierre del ejercicio? ¿En qué mes cierra el ejercicio?
5. ¿El rubro "Resultados financieros" va dentro del resultado de la empresa en Administración general, sin pasar por cultivos?

## 7. Para el diseño de pantalla (requisitos funcionales para los agentes 12 y 08)

Esta sección no diseña la interfaz. Solo dice qué tiene que poder ver y hacer Sergio. Sigue la premisa de la casa: nada interno en pantalla (ni ids, ni conectores, ni códigos).

### Dónde vive
- **Tesorería**: un medio o pestaña nueva, **"Inversiones"**, al mismo nivel que BNA, Galicia y Mercado Libre. Adentro tiene tres subcuentas: Plazo fijo BNA, Plazo fijo Galicia y FCI Fima.
- **Inicio**: una tarjeta resumen con el total invertido hoy, el próximo vencimiento y la cantidad de excepciones pendientes, con enlace a Tesorería › Inversiones.
- **Flujo de caja / resultados**: una fila "Resultados financieros", con sus subrubros "Intereses plazo fijo" y "Rendimiento FCI", que abre el detalle.
- En el movimiento bancario (BNA o Galicia), el estado tiene que mostrar "Inversión: plazo fijo / Fima" y su par, sin mostrar "Conciliado" a secas.

### Qué tiene que poder ver
1. **Cartera vigente**:
   - Cada plazo fijo abierto, con banco, fecha de constitución, fecha de vencimiento, capital, tasa (TNA y del período) e interés esperado.
   - El saldo del FCI Fima: el último saldo oficial con su fecha, las cuotapartes, el valor de la cuotaparte y los movimientos posteriores todavía no valuados.
   - El total invertido.
2. **Historial**: los plazos fijos cerrados, cada uno con su constitución, su acreditación, el interés y la tasa efectiva, y el Fima mes por mes (saldo inicial, suscripciones, rescates, saldo final y rendimiento).
3. **Rendimiento por año** (2018–2026), separado por plazo fijo BNA, plazo fijo Galicia y Fima, con el total. Debe coincidir con la tabla de la §4.
4. **Pendientes / excepciones**, cada una con el dato completo y en lenguaje simple:
   - una constitución sin acreditación;
   - una acreditación sin constitución;
   - una inversión con más de 400 días abierta;
   - un mes de Fima sin la posición del extracto;
   - un rendimiento negativo;
   - una diferencia entre el saldo del sistema y el del extracto (al centavo).
5. **Control de cierre** por subcuenta: el saldo del sistema contra el saldo del extracto oficial, con la diferencia a la vista.

### Acciones manuales (las únicas)
- **Emparejar a mano** una excepción: elegir la constitución y la acreditación que van juntas (por ejemplo, el plazo fijo de Galicia de 4,5 M con la acreditación de 9,26 M), con una vista previa del interés resultante, y confirmar.
- **Confirmar o rechazar** las propuestas ambiguas de la regla automática.
- **Marcar fuera de alcance** un movimiento heredado (por ejemplo, los −200.000 de BNA de 2016), con un motivo obligatorio. Queda visible y no se oculta.
- **Cargar o adjuntar el extracto** del Fima cuando no entró solo. La posición mensual se lee del PDF, no se tipea.
- **Deshacer** un emparejamiento.
- Todo lo demás lo hace el sistema solo: al iniciar, todos los días y después de cada extracto, más un botón "Revisar ahora".

### Datos y endpoints de lectura que harían falta (propuesta)
- `GET /tesoreria/inversiones/cartera`: las posiciones vigentes (plazos fijos abiertos y saldo del Fima) y el total.
- `GET /tesoreria/inversiones/historial?tipo=pf|fci&desde&hasta`: los plazos fijos cerrados y el Fima mensual.
- `GET /tesoreria/inversiones/rendimientos?agrupar=anio|mes`: el rendimiento por instrumento y por período.
- `GET /tesoreria/inversiones/excepciones`: los pendientes, con su tipo, sus movimientos candidatos y la propuesta.
- `GET /tesoreria/inversiones/control-saldos`: el saldo del sistema contra el del extracto, por subcuenta y por mes.
- Escritura (para la etapa de implementación, no ahora): `POST .../emparejar`, `POST .../confirmar`, `POST .../fuera-de-alcance`, `DELETE .../emparejar/{par}`, `POST .../revisar-ahora`.
- Formato de números y moneda: la regla global de la casa ($, miles con punto, decimales con coma).

---

## Adenda 19/11/2026: plazo fijo Galicia de $ 4.500.000, resuelto con documentos

Sergio aprobó el modelo C ("1. Sí").

**Es el mismo plazo fijo, renovado en forma automática.** Las pruebas:
- **Constancia de constitución** (`Dropbox/.../Bancos/Galicia/Plazos Fijos/PlazoFijo_Comprobante_170601523.pdf`):
  - Fecha 12/09/2023, $ 4.500.000, 30 días, TNA 111 %.
  - Certificado **809259034553**.
  - Acción al vencimiento: **"Renovación automática"**.
- **Extractos de Galicia de octubre 2023 a julio 2024:** ningún movimiento de ese plazo fijo. Las renovaciones no pasan por la cuenta.
- **Extracto de agosto 2024:** "ACREDITACIÓN VENCIMIENTO PLAZO FIJO **809259034553**" por $ 9.257.546,87 el 14/08/2024.

Rendimiento total: **$ 4.757.546,87**, entre el 12/09/2023 y el 14/08/2024, capitalizado unas 11 veces.

**Corrección a la §8 ("no hay retenciones de Ganancias"):** cada constancia de plazo fijo de Galicia informa una retención del impuesto a las ganancias, que el banco descuenta del interés antes de acreditarlo:

| Plazo fijo | Retención de Ganancias |
|---|---|
| $ 4.000.000 | $ 10.947,95 |
| $ 4.500.000 (primer tramo) | $ 12.316,44 |
| $ 1.800.000 | $ 4.926,58 |

En los extractos no aparecen como movimiento propio. Son pago a cuenta de Ganancias de la sociedad y hay que registrarlas: el rendimiento bruto es el acreditado más la retención. Falta revisar si las constancias del Nación (`Dropbox/.../Bancos/BNA/Inversiones/`) también la informan, y conseguir las retenciones de las renovaciones del plazo fijo de $ 4.500.000, que no tienen constancia en la carpeta.

## Adenda 2 (19/11/2026): los dos débitos de −$ 200.000 de 2016, investigados

Decisiones de Sergio:
- Rubro "Resultados financieros" en Adm. General: **sí**.
- Ejercicio económico: del **01/04 al 31/03**. Los intereses que cruzan el 31/03 se devengan al cierre.

**No son un duplicado: son dos plazos fijos reales.** El extracto del Nación de junio de 2016 muestra las dos constituciones, el 02/06/16 y el 22/06/16, ambas con comprobante 40029280 por $ 200.000.

**Plazo fijo 1 (02/06/2016): cierra con documentos**, en `Comprobantes/Giamigli/2016/` y `.../Plazos Fijos/`.

| Fecha | Movimiento | Importe |
|---|---|---|
| 02/06/2016 | Constitución, certificado 5983, renovable | $ 200.000 |
| 11/07/2016 | Vencimiento | $ 205.992,67 |
| 21/09/2016 | Renovación | $ 215.247,15 |
| 03/11/2016 | Liquidación cobrada **por caja** | $ 219.179,20 |
| 03/11/2016 | Retención SICORE de Ganancias | −$ 117,95 |
| 03/11/2016 | Depósito en efectivo en la cuenta (`DEP.EFECTIVO`, comprobante 3585) | $ 219.061,24 |

Rendimiento bruto: $ 19.179,20.

**Plazo fijo 2 (22/06/2016): hay un candidato, sin documento.** No hay constancia ni acreditación "PLAZO FIJO".
- El candidato más probable es `DEP.EFECTIVO` del 31/01/2017 por $ 224.498,97: el mismo patrón del primero (cobrado por caja y depositado) y un rendimiento razonable para unos 7 meses.
- Otro crédito posible es una transferencia del 07/12/2016 por $ 221.703,21 desde la misma CUIT, pero ya está reconocida y asignada a J y M de la Serna.
- Queda como excepción para que Sergio confirme.


## Adenda 3 (19/11/2026): los plazos fijos BNA de 2016, cerrados

**Mecanismo.** El Nación pagaba los certificados en papel por caja y acreditaba el cobro en la cuenta corriente con el concepto **"DEP.EFECTIVO"**. No hubo efectivo de por medio. Lo confirman la liquidación sellada del certificado 5983 y la correspondencia de Sergio de octubre de 2016 y enero de 2017.

| Plazo fijo | Constitución | Cobro | Rendimiento |
|---|---|---|---|
| N° 5983 | 02/06/2016, $ 200.000 | 03/11/2016, DEP.EFECTIVO $ 219.061,24 | $ 19.179,20 bruto (retención de $ 117,95) |
| N° 6280 | 22/06/2016, $ 200.000 (en enero de 2017 se pidió quitar la renovación automática) | 31/01/2017, DEP.EFECTIVO $ 224.498,97 | $ 24.498,97 neto (falta la constancia con la retención) |

**Regla para la conciliación automática:** en el BNA, un "DEP.EFECTIVO" puede ser el cobro de un certificado de plazo fijo en papel. Se aparea con el plazo fijo abierto cuando el importe es razonable (capital más interés a tasa de mercado).
