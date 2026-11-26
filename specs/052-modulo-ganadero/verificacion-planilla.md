# Verificación contra la planilla histórica (T027): 26/11/2026

- **Planilla:** "Historico Negocio Ganadero (ver 2).xlsx" (Documents\La Herencia\Ganaderia).
  - Solapas por comprobante: "Ventas Hacienda", "Gastos Comercializacion Liq." y "Compras".
  - Valores manuales: "Cultivos y forrajes" y "Amort Pasturas".
  - Último comprobante: 16/03/2024. En 2023/24 se compara solo hasta esa fecha.
- **Sistema:** el resultado ganadero en vista campaña (julio–junio), 2016/17 a 2023/24.
  - Ventas y liquidaciones: solo La Herencia, como la planilla.
  - Compras: todos los campos, porque la planilla no separaba los costos por campo.
  - Los traslados internos a San Pedro no se comparan: la planilla no los tenía.
- **Script (solo lectura):** `backend/scripts/ganaderia_verificacion_planilla_20261126.py`.
- **Detalle completo:** [verificacion-planilla-detalle-20261126.xlsx](verificacion-planilla-detalle-20261126.xlsx).
  - Solapa "Resumen": campaña × bloque, en pesos y US$.
  - Solapa "Diferencias por comprobante": las 107 diferencias de $ 1 o más, con fecha, proveedor, rubro del sistema y dónde quedó cada comprobante.
  - Solapa "Forrajes".
- **Primera pasada (25/11):** cubría solo 2018/19 y 2022/23 en US$. Esta la reemplaza. Sus correcciones (ha ganaderas, filtro por campo) ya están en el sistema.

## SC-001a: ventas, comercialización, sanidad e inseminación, gastos generales

### Ventas: coinciden al peso las 8 campañas

| Campaña | Planilla $ | Sistema $ | Planilla US$ | Sistema US$ | Dif. US$ (TC) |
|---|---|---|---|---|---|
| 2016/17 | 928.389 | 928.389 | 58.416 | 58.917 | 501 |
| 2017/18 | 1.786.359 | 1.786.359 | 90.007 | 90.484 | 477 |
| 2018/19 | 1.533.533 | 1.533.533 | 37.677 | 37.711 | 34 |
| 2019/20 | 4.529.117 | 4.529.117 | 73.575 | 74.223 | 648 |
| 2020/21 | 4.741.990 | 4.741.990 | 54.424 | 56.092 | 1.669 |
| 2021/22 | 12.849.782 | 12.849.782 | 115.300 | 117.834 | 2.533 |
| 2022/23 | 17.551.860 | 17.551.861 | 91.191 | 92.837 | 1.646 |
| 2023/24 (al 16/03/2024) | 42.851.078 | 42.851.078 | 58.409 | — | — |

- **Pesos:** coinciden al peso. En 2022/23 hay $ 1 de redondeo.
- **US$:** toda la diferencia es de tipo de cambio. La planilla usaba dólar billete y el sistema usa el dólar de gestión (FR-016), como fija la spec. No se ajusta.
- **2023/24:** los US$ del sistema no se pueden cortar al 16/03, por eso quedan sin comparar.

### Costos: diferencias en pesos (sistema − planilla)

| Campaña | Comercialización | Sanidad | Gastos generales |
|---|---|---|---|
| 2016/17 | 230 | 271 | 1.500 |
| 2017/18 | 791 | 0 | −4.166 |
| 2018/19 | 602 | 4.519 | 10.745 |
| 2019/20 | 4.217 | 556 | 6.727 |
| 2020/21 | 29.358 | 4.502 | 29.931 |
| 2021/22 | 22.311 | 2.640 | 22.650 |
| 2022/23 | 155.474 | 51.727 | 41.247 |
| 2023/24 (al 16/03) | 192.842 | 501.000 | 59.462 |

Alimentación comprada (feed lot, alimento general) coincide; solo hay $ 1 de redondeo en 2019/20.

### Las 107 diferencias por comprobante, por causa

1. **80 comprobantes están en el sistema y no en la planilla.** Son cargas posteriores a la planilla, la misma causa que había encontrado el forense. Por concepto:
   - **Guías, tasas y aranceles:**
     - SENASA: 40 guías y DTe, 2019/20 a 2023/24.
     - Municipalidad de Bolívar: tasa de guías 2022/23 $ 77.289 y 2023/24 $ 138.932; otras 5 tasas en 2020/21 y 2021/22, unos $ 20.660.
     - Municipalidad de Tapalqué: 5 tasas, 2020/21 a 2022/23.
     - FUNDEBO: aranceles de vacunación 22/03/2023, $ 31.545.
     - Sociedad Rural de Tapalqué: 3 aranceles y movilidad.
   - **Fletes de hacienda:** Luis $ 5.000, Cestona $ 10.380, Santos $ 13.700 y Gutiérrez $ 31.100.
   - **Administración:**
     - Vanina Silva (honorarios de administración): una factura por año, 2020/21 a 2023/24.
     - Asociación Argentina de Angus (cuotas): 7 facturas.
     - Ministerio de Desarrollo Agrario: $ 6.000.
   - **Sanidad:** Agrovet 0003-00051555 del 15/03/2024, $ 501.000 (productos veterinarios y vacunas). Explica toda la diferencia de sanidad de 2023/24.
   - **Insumos productivos de Cargill:**
     - 2018/19: un par de factura y su anulación de $ 13.048, más $ 10.450.
     - 2022/23: 5850-00005539 por $ 110.853 y 5848-00002356 por $ 6.651.

2. **11 comprobantes están en la planilla y no en Ganadería del sistema:**
   - **9 los reimputó la imputación 050 a un cultivo.** No es un faltante:
     - Pastura: Bayá Casal 0020-00314873 (semilla de lotus, $ 92.920), Cargill 1125-00001135 (flete) y Francomano Picardi 0003-00009269 (análisis de forrajeras, $ 9.408).
     - Avena: Sudol 00005-00000380 (flete de la semilla, $ 18.000).
     - Maíz, sorgo, girasol o soja: fletes de fertilizante de Cargill y Lartirigoyen, y las bolsas de Gonzalo.
   - **2 son el mismo comprobante cargado con otro número:**
     - Agrovet: la planilla dice 0003-00006197 y el sistema 0003-00006917, por $ 161 el 26/10/2016. Son los mismos dígitos en otro orden.
     - SENASA: la planilla dice 18450835-4 y el sistema 42569097, por $ 1.885 el 07/05/2020.
   - **1 no está cargado en el sistema:** Municipalidad de Bolívar 3616 del 29/06/2020, $ 2.689. Hay que buscar el comprobante. Puede ser una tasa que se cargó junto con la del 08/05/2020 (esa difiere en −$ 203).

3. **16 tienen el mismo número pero distinto importe.** El sistema da más en casi todos.
   - **Liquidaciones de J y M de la Serna (comercialización):** 3-25 +$ 230, 3-1762 +$ 791, 3-3456 +$ 602 y 3-5302 +$ 834. El sistema toma todos los gastos de la liquidación y la planilla tomaba solo una parte.
   - **Inseminación, Cabaña Las Lilas:** 19-3915 +$ 4.519 y 19-5299 +$ 11.957.
   - **Productos veterinarios, Agrovet:**
     - 3-23292 +$ 556, 3-28368 +$ 1.952 y 3-43890 +$ 15.059.
     - Esta última es la diferencia de productos veterinarios de 2022/23 que había marcado el forense.
   - **Administración:**
     - Vanina Silva: +$ 295 y +$ 6.720.
     - Compra genérica "XXXXXXXXX" del 06/04/2017: +$ 1.500.
   - **Asoc. Cooperadora Laboratorio 2-2932:** +$ 270. El sistema tiene el doble que la planilla.
   - **Redondeos de $ 1:** EDP Agro y Agrovet 3-33372. El signo se lee en el Excel.

   Todo esto se ve renglón por renglón en el Excel. Para decir cuál de los dos tiene razón hay que mirar cada PDF, y eso no está hecho.

## SC-001b: forrajes (US$), por valor contra las solapas fuente

La comparación se hace por valor y no por el nombre de la fila (decisión de Sergio del 25/11). En la solapa principal los nombres de fila están corridos respecto de las solapas fuente:
- "Avena" = la amortización de pasturas ("Amort Pasturas").
- "Pastura" = el "Maiz" de "Cultivos y forrajes".
- "Maiz" = el "Maiz silo" de la fuente.
- "Maiz silo" = la "Avena" de la fuente.

| Campaña | Fuente (sin la implantación de pastura) | Sistema | Diferencia |
|---|---|---|---|
| 2016/17 | 20.456 | 22.096 | 1.641 |
| 2017/18 | 24.219 | 17.466 | −6.753 |
| 2018/19 | 17.683 | 21.050 | 3.367 |
| 2019/20 | 20.233 | 21.599 | 1.366 |
| 2020/21 | 23.698 | 18.892 | −4.807 |
| 2021/22 | 34.252 | 39.801 | 5.549 |
| 2022/23 | 47.657 | 44.297 | −3.361 |
| 2023/24 | 26.974 | 37.876 | 10.902 |

**Por concepto (detalle en la solapa "Forrajes"):**
- **Amortización de pasturas:** coincide (por ejemplo 8.483 / 8.481 y 7.782 / 7.759), salvo 2023/24 (5.681 / 5.036) y 2021/22 (6.795 / 6.933).
- **Avena y sorgo:** cerca, salvo sorgo 2020/21 (3.047 / 4.367) y 2023/24 (6.670 / 12.394).
- **Maíz diferido:** las diferencias grandes están acá.
  - Por año: 2017/18 (4.318 / 1.322), 2020/21 (7.707 / 1.818), 2022/23 (10.184 / 7.295) y 2023/24 (7.004 / 12.496).
  - La planilla carga a mano el costo de un año. El sistema toma el costo real del cultivo de la campaña anterior (regla de consumo en el ejercicio siguiente).
- **Maíz silo:** el sistema da más (por ejemplo 2022/23: 13.971 / 7.960).
  - El sistema suma la implantación de las ha picadas más la confección.
  - La planilla separaba "Confección silo" (de Compras) y un valor manual.
  - La forma de imputarlo cambió el 26/11: cada consumo registrado va a su período. Los silos viejos sin registro quedan estimados en el ejercicio siguiente.
- **"Maiz" de la fuente** (2017/18 3.860, 2019/20 4.004, 2022/23 6.744): el sistema no tiene un concepto igual. Puede ser grano propio dado a la hacienda; eso hay que confirmarlo.

Por SC-001b no se ajusta nada: las diferencias quedan en la lista.

## Qué queda para Sergio
1. Municipalidad de Bolívar 3616 (29/06/2020, $ 2.689), que no está cargada: buscar el comprobante.
2. Los 16 importes distintos: confirmar con los PDF de cuáles es el bueno. Los de mayor monto son Agrovet 3-43890 (+$ 15.059) y Cabaña Las Lilas 19-5299 (+$ 11.957).
3. El "Maiz" de la solapa "Cultivos y forrajes": qué representaba.
