# 050 — Estructura de costos por cultivo y tamizado de facturas: 50 preguntas

14/11/2026. Preguntas armadas con los aportes de los especialistas: producción agrícola, hacienda, finanzas, gestión agro integrada, administración de cuentas, producto/pantallas y datos/motor.

La opción recomendada va primero (R). Para responder, alcanza con poner el número y la letra, por ejemplo `1a, 2b…`. Si estás de acuerdo con todas las recomendadas de un grupo, poné "grupo A: todas R".

**Datos medidos en WC** (renglones desde el 01/07/2025):
- 1.869 renglones en 688 facturas; 687 tienen rubro de cultivo.
- 392 de 480 renglones de insumos (82%) no tienen producto del catálogo.
- 18 facturas mezclan renglones de cultivo con otros que no lo son.
- 6 de los 22 proveedores de cultivo también venden otras cosas.
- 59 renglones de cultivo con campaña "No Aplica" y 14 con destino "General".
- Hoy hay solo 9 reglas de clasificación.

## A. Estructura de costos

1. **¿Qué partes tiene la estructura de costos de un cultivo?**
   - a (R) Semilla, Fertilizantes, Agroquímicos, Labores (siembra, pulverización, fertilización), Cosecha, Fletes, Seguro agrícola, Asesoramiento/análisis, Arrendamiento, Comercialización.
   - b La misma, sin arrendamiento ni asesoramiento: esos dos quedan como gasto general.
   - c Usar tal cual los rubros de compras que ya existen.
2. **¿La estructura es la misma para todos los cultivos?**
   - a (R) Una plantilla común; cada cultivo apaga lo que no usa (por ejemplo, el secado solo en maíz).
   - b Una distinta por cultivo.
   - c Una para fina y otra para gruesa.
3. **¿Quién la mantiene?**
   - a (R) Vos, desde una pantalla de configuración.
   - b La armo yo y vos me pedís los cambios.
4. **¿El resultado del cultivo es margen bruto o resultado neto?**
   - a (R) Margen bruto: los gastos generales quedan en "Estructura" de la campaña, aparte.
   - b Neto, con la estructura repartida por hectárea sembrada.
   - c Neto, con la estructura repartida por costo directo.
5. **¿Cómo entra el arrendamiento?**
   - a (R) Al cultivo/campaña de los lotes arrendados, por hectárea sembrada. Si en el año hay fina y gruesa, se reparte entre las dos.
   - b Todo a la gruesa del lote.
   - c Como estructura, sin pasar por el cultivo.
6. **"Seguimiento cultivos" (93 renglones), el asesor agronómico y los análisis, ¿adónde van?**
   - a (R) A Asesoramiento del cultivo/campaña. Si no dicen el cultivo, se reparten por hectárea sembrada.
   - b A estructura.
7. **Comercialización (comisiones, secada, paritarias, Ingresos Brutos de la venta): ¿son costo del cultivo?**
   - a (R) Sí, en la parte Comercialización del cultivo y campaña del grano vendido.
   - b Se restan de la venta, no del costo.

## B. Tamizado de renglones (qué se imputa y qué no)

8. **¿Cómo se decide si un renglón va a cultivo?**
   - a (R) Por su rubro. Cada rubro queda marcado "va", "no va" o "depende"; los "depende" se resuelven por proveedor o producto, y si no, van a la lista.
   - b Por proveedor.
   - c Siempre a mano.
9. **Facturas mixtas (hoy hay 18):**
   - a (R) Cada renglón decide solo, por su rubro.
   - b Gana el rubro con más importe.
   - c Cada renglón decide por su rubro, pero toda factura mixta pasa por la lista.
10. **¿Usamos reglas por proveedor?**
    - a (R) Sí, solo para proveedores que venden una sola cosa. En los otros 6 manda el rubro.
    - b No, nunca.
    - c Sí, para todos.
11. **Si dos reglas chocan, ¿cuál gana?**
    - a (R) De la más fuerte a la más débil: imputación manual del renglón > lo aplicado por la orden (insumos) > regla por producto > regla por proveedor > regla por rubro > lista.
    - b El rubro primero, y las excepciones a mano.
12. **Rubros que hoy están en grupos distintos ("Flete insumos", "Análisis laboratorio" vs "Análisis PG"):**
    - a (R) Armamos juntos, una sola vez, la tabla fija rubro → parte de la estructura.
    - b Se revisan caso por caso.
13. **Un renglón de un rubro que "no va" (Movilidad, Bienes de uso) pero tiene campaña cargada (hay 5):**
    - a (R) Va a la lista para que lo revises.
    - b Se ignora la campaña.
14. **Renglones con texto libre ("servicio varios", "flete"):**
    - a (R) Se imputan solo si el texto o el rubro indican claramente cultivo y labor. Si no, quedan sin imputar, a la vista en la lista.
    - b Se reparten por hectárea.
    - c Siempre a estructura.
15. **Insumos sin producto del catálogo (82%):**
    - a (R) El sistema propone el producto leyendo la descripción. Si está seguro lo asigna; si no, va a la lista.
    - b Los cargás vos a mano.
    - c Cuentan por lo que dice la factura, sin pasar por stock.
16. **Cuando corregís una imputación, ¿el sistema aprende?**
    - a (R) Te pregunta "¿aplicar siempre a este proveedor/producto?".
    - b Aprende solo, sin preguntar.
    - c No aprende.
17. **¿Qué tan seguro tiene que estar el sistema para imputar sin pasar por la lista?**
    - a (R) Sin ninguna duda en proveedor, producto o labor, cultivo y campaña. Cualquier diferencia de cantidad o de hectáreas va a la lista con el motivo.
    - b Acepta hasta un 5% de diferencia en hectáreas.
    - c Imputa lo más probable y marca la confianza.

## C. Campaña y lote

18. **¿A qué campaña va un gasto sin orden (flete, seguro, secada)?**
    - a (R) A la campaña que el gasto atiende: el seguro, a la campaña asegurada; el flete y la secada, a la de la cosecha. Si no se sabe, a la vigente a la fecha de la factura, y va a la lista.
    - b Siempre a la vigente a la fecha de la factura.
19. **Gastos de cultivo con "No Aplica" o "General" (59 y 14):**
    - a (R) El sistema propone la campaña y el cultivo por la fecha y la orden más cercana, y los deja en la lista.
    - b Se reparten por hectárea.
    - c Van a gasto general.
20. **El barbecho (herbicidas de invierno antes de sembrar):**
    - a (R) Al cultivo que se siembra después.
    - b Al cultivo que se cosechó antes.
21. **Cultivos de cobertura (vicia, centeno):**
    - a (R) Su costo se suma al cultivo de verano siguiente.
    - b Son un cultivo propio, con resultado negativo.
22. **¿El costo se lleva por lote?**
    - a (R) Por lote cuando hay orden. El resto (arrendamiento, seguro, fletes) se reparte por hectárea sembrada entre los lotes del cultivo.
    - b Por lote solo lo que tiene orden; el resto, a nivel cultivo.
    - c Todo a nivel cultivo/campaña.
23. **¿Con qué superficie se reparte?**
    - a (R) Hectáreas sembradas según las facturas de siembra (regla del 12/11).
    - b Hectáreas cosechadas.
    - c Superficie del plan agrícola.
24. **Un renglón que va a cultivo pero no dice cuál (flete de granos, análisis de suelo):**
    - a (R) El sistema lo deduce por grano, lote o fecha. Si queda una sola opción lo imputa; si no, va a la lista.
    - b Se reparte por hectárea.
    - c Siempre a la lista.

## D. Insumos y stock

25. **Semillas:**
    - a (R) Todas pasan por stock y las consume la orden de siembra. La semilla propia se valúa al precio del grano cuando se reservó.
    - b La semilla propia no tiene costo.
    - c La semilla va directo por la factura.
26. **Semilla o insumo que pone el contratista y viene dentro de su factura de labor:**
    - a (R) Se trata como el resto de la labor: va al cultivo de la orden, sin pasar por stock.
    - b Se separa y pasa por stock.
27. **Sobrante al cerrar la campaña:**
    - a (R) Sigue en stock, con su costo original, y lo paga el cultivo que lo aplique.
    - b Se reparte entre los cultivos de la campaña que cierra.
28. **Insumo vencido o perdido:**
    - a (R) Lo baja el recuento y se reparte en las órdenes del período (regla vigente). Si no hay órdenes, va a estructura.
    - b Siempre a estructura.
29. **Bolsas de silo, hilo y mallas de rollos:**
    - a (R) Al cultivo que se embolsa o enrolla, en la parte Cosecha.
    - b A estructura.

## E. Frontera con ganadería

30. **Pasturas y verdeos (avena, raigrás, alfalfa):**
    - a (R) Son cultivo forrajero con campaña propia, y su costo pasa después a la hacienda.
    - b Lo mismo, pero la alfalfa se reparte en los años que dura.
    - c Costo directo de ganadería.
31. **Rollos y silos hechos en el campo:**
    - a (R) La labor y los insumos van al cultivo forrajero; cuando la hacienda consume, pasan a ganadería al costo.
    - b Todo directo a ganadería.
    - c Se valúan a precio de mercado.
32. **Facturas sanitarias (vacunas, veterinario, SENASA):**
    - a (R) Nunca van a cultivo: van a ganadería.
    - b A ganadería, repartidas por rodeo o categoría.
33. **Gastos compartidos (gasoil, alambrados, molinos, sueldos de Sierra e Irma):**
    - a (R) No se imputan a cultivo: son estructura. Solo el gasoil con orden de labor va al cultivo.
    - b Se reparten por hectáreas agrícolas contra ganaderas.
    - c Se reparten con un porcentaje que fijás cada campaña.
34. **Pastaje y rastrojo pastoreado:**
    - a (R) No toca al cultivo: queda en ganadería (039).
    - b El pastaje sobre rastrojo es ingreso secundario del cultivo.

## F. Finanzas e impuestos

35. **Impuestos:**
    - a (R) El IVA y Ganancias nunca se imputan. El inmobiliario y las tasas viales van a estructura. Ingresos Brutos va a Comercialización.
    - b Como la (a), pero el inmobiliario y las tasas se reparten por hectárea.
    - c Ningún impuesto va al cultivo.
36. **Intereses, gastos bancarios y diferencias de cambio (ND/NC por tipo de cambio):**
    - a (R) Resultado financiero de la campaña, aparte del cultivo.
    - b Los intereses de un insumo financiado (canje, plazo) van al cultivo de ese insumo.
    - c Todo al cultivo del insumo que los originó.
37. **Notas de crédito (bonificaciones, devoluciones):**
    - a (R) Copian la imputación de la factura que corrigen, en proporción. Si el insumo pasó por stock, baja el precio de lo aplicado. Si no tienen factura relacionada, van a la lista.
    - b Restan en la campaña en que llegan.
    - c Van a estructura.
38. **Maquinaria, mejoras y alambrados (bienes de uso):**
    - a (R) No son gasto del cultivo. Se amortizan después, a estructura.
    - b Se amortizan por hectárea trabajada a cada cultivo.
    - c Gasto del cultivo por la fecha de la factura.
39. **¿Qué fecha manda?**
    - a (R) La de la aplicación o la labor (orden). Sin orden, la del comprobante; si cae entre dos campañas, va a la lista.
    - b Siempre la fecha de la factura.
40. **Gasoil de la maquinaria propia:**
    - a (R) Va al cultivo cuando hay una orden de labor propia que lo consume. Si no, a estructura.
    - b Se reparte por hectárea trabajada.
    - c Siempre a estructura.

## G. Casos administrativos

41. **Facturas a nombre de la Sucesión o de socios que son gasto del campo; compras particulares:**
    - a (R) Las de Sucesión y socios se imputan por rubro como cualquier otra. Las particulares (Particular L/S) nunca.
    - b Ninguna se imputa sola.
42. **Contacto genérico 97 (compras chicas en efectivo):**
    - a (R) Se imputa si el rubro es de cultivo, y siempre pasa por la lista.
    - b Siempre a estructura.
    - c Nada hasta corregir el proveedor.
43. **Facturas en US$ (250 renglones de cultivo):**
    - a (R) Al TC del comprobante (regla vigente). El informe muestra $/ha y US$/ha.
    - b Solo en pesos.
44. **Cosecha pagada en grano (a porcentaje), sin factura de dinero:**
    - a (R) Se valúa con la liquidación del grano entregado y va a Cosecha del cultivo.
    - b No se imputa hasta que haya factura.

## H. Pantallas y control

45. **¿Dónde revisás lo imputado solo?**
    - a (R) Una pantalla "Para revisar", con los dudosos arriba y el resto agrupado por día de carga.
    - b Un aviso en cada compra.
    - c Las dos cosas.
46. **Al cargar la compra, la sugerencia por renglón:**
    - a (R) Viene ya completa, marcada como "sugerido", y se cambia con un clic.
    - b Hay que pedirla con un botón.
    - c No hay sugerencia; se imputa al guardar.
47. **Renglones que no van a cultivo:**
    - a (R) Etiqueta clara en cada renglón: "Va a stock", "Gasto general", "A cultivo", "Ganadería".
    - b En blanco, con aviso solo si falta algo.
48. **Avisos:**
    - a (R) Un contador en el menú ("3 para revisar"), sin mails.
    - b Además, un resumen semanal en borrador de Outlook.
49. **Informe de costos por cultivo/campaña:**
    - a (R) Por parte de la estructura, con $/ha y US$/ha y apertura hasta la factura o la orden; al pie, lo que sigue en stock sin consumir.
    - b Por lote.
    - c Comparativo entre campañas.
50. **Si cambia una orden, un remito o una regla:**
    - a (R) Se recalcula solo desde 2025/26 y cada cambio queda guardado (fecha, qué cambió, cuánto movió) y en la lista.
    - b Se recalcula solo hasta que cerrás la campaña; después, con tu OK.
    - c Se recalcula sin guardar historial.

## Respuestas de Sergio (14/11/2026)

Eligió la recomendada en todas, salvo en estas:

- **3**: la estructura la mantiene Claude, a pedido (no hay pantalla de configuración).
- **10**: no hay reglas por proveedor; siempre manda el rubro del renglón.
- **21**: el cultivo de cobertura es un cultivo propio, con su resultado.
- **22**: todo se lleva a nivel cultivo/campaña, sin lote.
- **23**: la superficie de reparto es la del plan agrícola.
- **26**: la semilla o el insumo que pone el contratista se separa y pasa por stock.
- **28**: el insumo vencido o perdido va a gasto general, como pérdida de la empresa (no se reparte en órdenes).
- **36**: los intereses de un insumo financiado (canje, plazo) van al cultivo de ese insumo; el resto es resultado financiero.
