# Research: Flujo de caja por Rubro

## 1. Reparto de un pago entre rubros (aclaración: según lo aplicado)

**Estado actual**: `atribucion.atribuir_desde_aplicaciones` suma pesos por rubro y devuelve solo el de mayor peso: el pago entero va a un rubro. Además, una compra con líneas de varios rubros cae en "Compra con varios rubros".

**Decisión**: devolver una lista de **partes** `{rubro, centroCosto, importe}`:
- Cada aplicación aporta su `ImporteAplicado`.
- Si la compra aplicada tiene líneas de rubros distintos, ese importe se reparte en proporción al importe de cada línea de la compra, y la última parte absorbe el redondeo para que la suma sea exacta.
- Si lo aplicado es menor que el movimiento, la diferencia es una parte "Pendiente de aplicar". Si el movimiento es anterior al 01-09-2015, esa parte es "Histórico sin aplicar".
- Si lo aplicado supera el movimiento, algo que no debería pasar, se escala proporcionalmente al importe del movimiento. El banco manda: el importe siempre es el del movimiento real.

**Rationale**: es lo que Sergio eligió, y garantiza que la suma de las partes sea igual al movimiento. Por eso el detalle de cada celda coincide exactamente (FR-006).

**Alternativas**: mantener "ganador único" (rechazada por la aclaración) y repartir por total de documento (rechazada, opción B).

**Fallback sin aplicaciones**: se mantiene la lógica existente (matching exacto de 018 v2, Ley 25.413, recaudación ARBA y luego Pendiente/Histórico), que produce una sola parte.

## 2. Traspasos entre cuentas propias (aclaración: filas propias)

**Estado actual**: `clasificacion.es_interno` marca como internos:
- en Galicia, el grupo de conceptos "Inversiones" (FIMA);
- en BNA, las transferencias entre titulares con el CUIT de la empresa.

Hoy `agregar_por_rubro` los descarta.

**Decisión**: agregar `tipo_interno(movimiento)`:
- Galicia "Inversiones" con importe negativo → **Colocación FIMA**.
- Galicia "Inversiones" con importe positivo → **Rescate FIMA**.
- BNA titular propio → **Traspaso entre bancos**.

Van en la sección "Movimientos entre cuentas propias", fuera de ingresos y egresos operativos. La regla de detección de internos no cambia.

**Traspasos entre bancos**: un traspaso BNA → Galicia deja dos movimientos. La regla de 018 solo reconoce el lado BNA. Para no inflar el ingreso operativo, `emparejar_traspasos` busca el lado Galicia: signo opuesto, mismo importe y dentro de los 3 días. Si lo encuentra, lo marca también como "Traspaso entre bancos"; si no, el traspaso queda señalado "sin contraparte". La regla `es_interno` de 018 no se modifica: esto es un paso adicional del flujo por rubro.

## 3. Saldo inicial por cuenta

**Estado actual**: `saldo_inicial_al` devuelve un único total (apertura + todos los movimientos BNA y Galicia antes de la fecha).

**Decisión**: devolver el saldo por cuenta:
- **Nación**: las 3 cuentas BNA de `CuentasBancarias` sumadas. Las 2 dadas de baja ya tienen saldo 0 al cierre.
- **Galicia cuenta corriente**: la cuenta 4.
- **Galicia Fondo FIMA**: no es una cuenta registrada. Se reconstruye como capital neto colocado: −(suma de los movimientos Galicia "Inversiones" hasta la fecha), porque colocar resta de la cuenta corriente y suma al fondo.
- **Total**: la suma de las tres.

**Limitación documentada**: el saldo FIMA reconstruido no incluye el rendimiento del fondo (no hay datos de cotización del FCI en los extractos). Coincide con el saldo real del FIMA solo si el rendimiento se rescata o se ignora; se muestra con una aclaración en pantalla.

**Mercado Libre** (cuenta 1002): no forma parte de `get_movimientos_normalizados` (018), así que queda fuera del flujo, igual que en 018. Se registra como posible extensión.

## 4. Conversión a dólares (aclaración: cotización del día de cada movimiento)

**Fuente**: tabla `dbo.[Dolar BNA]` (5.230 días). Columnas: `Comp_billete`, `Vend_billete`, `Comp_Divisa`, `Vend_Divisa` y promedios.

La tabla `cotizacion_bna` existe pero está vacía y no se usa.

**Decisión**: usar **`Vend_Divisa`** (BNA vendedor divisa), la cotización de transferencias, que corresponde a movimientos bancarios. Se usa la de la fecha del movimiento; si no hay, la última anterior dentro de los 7 días. Si no hay ninguna, la parte queda **sin tipo de cambio**: se excluye de la suma en USD y la celda muestra el aviso con la cantidad y el importe en ARS no convertido.

**Hallazgo**: la serie termina el **2026-04-23**. Los movimientos posteriores van a salir sin tipo de cambio hasta que se actualice la tabla, que hoy se carga a mano desde `Parametros financieros.xlsx`. Actualizar la serie queda fuera de esta feature; la pantalla lo avisa.

**Implementación**: la serie se carga una vez por consulta, dentro del rango más 7 días, en un dict fecha → cotización. Así se evitan consultas por movimiento.

## 5. Exportación a Excel

**Decisión**: generarla en el backend con openpyxl, mismo patrón que `cuentas_corrientes/exportacion.py` y `_xlsx_response`. Reproduce la vista (rango, granularidad, moneda) con importes numéricos, formato de moneda y encabezado con rango, moneda y fecha de generación.

**Alternativa rechazada**: armarlo en el navegador, porque agregaría una dependencia nueva al frontend (Principio VIII).

## 6. Performance

El cálculo ya se hace en memoria sobre los movimientos del rango. La única consulta nueva por movimiento sería la de aplicaciones: **se cambia a una carga única de todas las aplicaciones vigentes del rango**, en vez de una consulta por movimiento, para cumplir SC-004 con rangos de 12 a 24 meses.
