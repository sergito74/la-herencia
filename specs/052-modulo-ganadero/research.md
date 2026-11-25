# Research: Módulo Ganadero (052)

Decisiones verificadas contra el código y la base WC por los agentes del 25/11/2026 y por Sergio.

## R1. Fuente de los costos ganaderos (FR-003)
- **Decision:** la vista `vw_Gan_Costos` arma los costos ganaderos con tres fuentes:
  - fracciones vigentes de 050 (`VIGENTE_050`, `resultado_cultivo/costos.py:68-73`) marcadas como ganadería o imputadas a un cultivo con `EsGanaderia=1`;
  - el tamiz vigente con destino Ganadería;
  - los renglones con centro 2 fuera del alcance de 050, con las mismas exclusiones `_NO_EN_ALCANCE`/`_PASO_POR_STOCK`.

  Los importes van netos de IVA y de la parte particular (`factor_particular`, `imputacion/progresivo.py:199`).
- **Rationale:** hay 317 renglones con centro 2 imputados a cultivos agrícolas ($6,4 M) y 59 con centro y destino contradictorios. Usar `Det_Compras.IdCentroCostos` daría doble conteo.
- **Alternatives:** centro o destino del renglón (descartada por el doble conteo); un motor de imputación propio (descartado: duplicaría 050).

## R2. Forrajes fuera del Resultado de cultivos (FR-004, FR-005)
- **Decision:** se agrega la columna `EsGanaderia bit` a `Map_CultivoResultado`, en 1 para Avena, Pastura, Maíz diferido, Sorgo, Rye grass y Verdeos. `_cultivos_con_datos` (`resultado.py:207-235`) y la constante VERDEOS de `formularios_access.py` dejan afuera esos cultivos. El costo de producción del forraje pasa entero a Ganadería: verdeos al ejercicio de consumo y pastura amortizada en 4 años por lote, desde `ImputacionPropuestas.IdLote`. El silo o grano propio consumido va a costo de producción (Sergio: no se comercializa fácilmente). `_costo_silo` deja de restarse en cultivos y pasa como costo de alimentación en Ganadería.
- **Rationale:** hoy el resultado agrícola sí incluye los forrajes (2023/24: maíz diferido US$ 9.221, sorgo US$ 12.391).
- **Test:** con una campaña real, el costo agrícola antes menos el costo agrícola después es igual al costo forrajero en Ganadería, al centavo (SC-005).

## R3. Ha ganaderas efectivas (FR-013)
- **Decision:** se replica el método de Sergio (`Estructura/Superficie Campo.xlsx`, "Sup Ganadera 2011/2012"). Por lote y mes del ejercicio, el lote es agrícola si `PlanAgricola` (o una orden) le asigna un cultivo de cosecha y el mes está entre la siembra y la cosecha. En cualquier otro caso es ganadero. Ha efectivas = Σ superficie del lote × meses ganaderos / 12.
- **Fechas:** la siembra sale de la orden de siembra de `Ordenes_Lotes`/`Ordenes_Trabajo` y la cosecha, de `Datos Cosecha`. Si faltan, se usa el calendario típico del cultivo (tabla `GanCalendarioCultivo`, configurable). Valores iniciales tomados de las planillas 2011/12:

  | Cultivo | Fuera del pastoreo |
  |---|---|
  | Soja 1.ª | nov–abr |
  | Soja 2.ª | ene–abr |
  | Maíz | oct–abr |
  | Girasol | oct–mar |
  | Trigo | jun–dic |

- **Rationale:** Sergio (25/11): "los lotes ganaderos están en el plano y en el plan". `PlanAgricola` ya tiene forrajes y agricultura por lote y campaña (2021/22 a 2026/27).
- **Alternative:** el parámetro "415 − agrícolas" que la planilla escribía a mano (descartado: es manual).

## R4. Cabezas y kg de las ventas (FR-009)
- **Decision:** la regla depende de `[Unidad de medida]`:

  | Unidad | Cantidad | Peso Total |
  |---|---|---|
  | Kilos | kg | cabezas |
  | Unidades/Cabezas/toros | cabezas | kg (si > 0) |
  | Pesos | gasto o ajuste, sin hacienda | — |

  Si falta uno de los dos datos, se usa el peso típico de la categoría, con la marca `KgEstimado`. Los pares de anulación y refactura (negativo con su documento par) se netean.
- **Verificado:** PDF de la liquidación 0003-00010318 (2 vacas de 440 kg, una por renglón).

## R5. Conversión a US$ (FR-016): un solo dólar para todos los centros
- **Decision:** una sola regla para Agricultura, Ganadería y Administración. Es la que ya usa `resultado_cultivo/costos.py` (`_USD_SQL`):
  - US$ → su TC;
  - pesos → `[Dolar BNA].Comp_Divisa` (BNA comprador divisa) de la fecha;
  - "Ajusta TC" → 0.

  Se centraliza en `src/features/cotizaciones/dolar_gestion.py`: una función SQL/Python que usan resultado_cultivo, ganaderia y cualquier tablero, en lugar de repetir la fórmula. Las ventas de granos ya usan BNA comprador divisa (día hábil anterior para la LPG sin TC), así que quedan alineadas.
- **Rationale:** Sergio (25/11/2026) pidió unificar para que todos los centros queden alineados.
- **Alternativas:** el Prom_billete de la planilla histórica (descartado: desalinea con Agricultura; la diferencia se muestra como TC en SC-001); vw_CnsComprasDolarBNA (se revisa que use la misma regla, y si no, se alinea o se deja de usar).
- **Auditoría previa:** hay que listar todos los lugares que dolarizan (`grep` de Comp_Divisa / TC_CompDivisa / Prom_billete / Vend_Divisa / [Tipo de Cambio]) y clasificarlos así:
  - **costo o resultado:** se unifican;
  - **cuenta corriente o deuda en US$:** se mantiene la regla del TC del comprobante, que es la misma;
  - **flujo de caja proyectado:** usa vendedor divisa para proyectar y se deja así, documentado.

## R6. Ejercicio abril–marzo vs campañas
- **Decision:** las fracciones se asignan al ejercicio por la fecha de consumo de la orden; si no hay, por la fecha de la factura. La vista por campaña va rotulada "sin variación de inventario".

## R7. Stock histórico (FR-007)
- **Decision:** un script re-corrible importa, con `Fuente`:
  - la solapa "Stock Hacienda" de la planilla (23 recuentos 2016–2023; La Herencia = establecimiento 1, San Pedro = 2) como `GanRecuento` de origen "Planilla";
  - los stocks al 31/03 de 2021 y 2023 de los mails al Estudio, de origen "Cierre";
  - la planilla Req Vacunas Oct 26, de origen "Acta", con las 70 "terneras Miguel" como hacienda de terceros de San Justo.

  Los nombres de categoría pasan por `GanCategoriaAlias`. Se simula y se revisa antes de `--aplicar`.
- **Existencia a una fecha:** último recuento ± movimientos posteriores. Si no hay movimientos de nacimiento o muerte, la diferencia entre dos recuentos se muestra como "sin explicar", sin ajustarla.

## R8. Marca "revisado y aceptado"
- **Decision:** tabla `GanControlAceptado` con la misma forma que `ControlRemitosAceptados`, y un componente UI común `MarcaRevisado` (panel lateral con motivo, sin `window.prompt`).

## R9. Seguros
- **Decision:** fuera del alcance (Sergio, 25/11/2026: no).
