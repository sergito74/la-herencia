# Research — 049 + 050

## R-01 Qué renglones entran al esquema nuevo (alcance)

**Decisión**: hay una tabla `ImputacionAlcance(IdDetalleCompra, Motivo, FechaAlta)` con dos motivos:

- **`Nuevo`**: todo renglón de una compra cargada después del corte. El corte es el `IdDeuda` máximo al activar, guardado en `ImputacionConfig`; no se toma la fecha de la factura. Así, una factura vieja que se carga hoy cuenta como nueva.
- **`StockSinImputar`**: el script de activación marca una sola vez los renglones de insumo ya cargados que cumplen tres condiciones:
  - no tienen imputación manual útil (destino `General`/`No Aplica` o sin campaña);
  - no tienen corrida aprobada;
  - su producto tiene saldo en stock en una capa vinculada a ese renglón.

**Razón**: "lo ya imputado no se toca". Una lista explícita es auditable y reversible: borrar la fila devuelve el renglón al régimen viejo.

**Alternativas descartadas**:
- Por fecha de factura: falla con las facturas viejas cargadas tarde.
- Por campaña ≥ 2025/26: toca renglones ya imputados a mano.

## R-02 Imputación progresiva por renglón

**Decisión**: se reutiliza `motor.calcular_propuesta_insumo`. Ya devuelve, para un renglón de factura, las fracciones de uso (orden → cultivo/campaña) más la fracción "en stock", al costo de la capa FIFO del remito vinculado.

Cada recálculo guarda una corrida nueva en `ImputacionPropuestas`. Las corridas ya existentes son el historial (FR-017).

La corrida de un renglón en alcance se aprueba sola si cumple dos condiciones:
- la suma de los usos más el stock iguala el total del renglón, al centavo;
- no tiene ningún motivo de duda.

Si no las cumple, va a la cola de revisión.

**Razón**: la lógica FIFO por capa ya está probada (010/017). Lo que faltaba era el vínculo remito↔factura y el disparo para los renglones sin corrida previa.

## R-03 Factura de insumo sin remito

**Decisión**: `calcular_stock` agrega una capa virtual `F{IdDetalleCompra}` a la fecha de la factura, solo para renglones en alcance con destino "A cultivo (stock)" que no tengan ningún `tblRemitoCompra`.

Cuando aparece el remito y se vincula, la capa virtual desaparece y su consumo pasa a la capa real. Ese cambio queda registrado como una corrida nueva.

**Riesgo**: que el mismo insumo cuente dos veces en stock (remito sin vincular + capa virtual). Para mitigarlo:
- la pasada diaria lista los remitos sin vincular del mismo proveedor y producto como "posible duplicado";
- esos casos van a revisión y no se aprueban solos.

## R-04 Vínculo automático remito↔factura

**Decisión**: candidato = mismo proveedor, mismo producto (`IdFormulado`) y fecha del remito entre 60 días antes y 30 días después de la factura. Entre los candidatos:

- **Una sola combinación exacta** de cantidades, uno o varios remitos que suman la cantidad facturada en la unidad base (`factor_a_base`): se escribe en `tblRemitoCompra` y queda aprobada.
- **Varias combinaciones, o ninguna exacta**: va a revisión con los candidatos.

Lo que sale de la factura también tiene un límite: la suma de `CantidadRemitida` por renglón nunca supera su cantidad.

**Razón**: la regla de "sin tolerancias" (P17), y además las entregas parciales.

## R-05 Orden de prioridad del tamiz

**Decisión**: manual del renglón > lo aplicado por orden (insumos) > regla por producto > regla por rubro > revisión.

"Manual" quiere decir que la imputación cargada en el renglón tiene cultivo y campaña reales, no `General`/`No Aplica`.

Hay dos casos en que la manual no manda:
- En un **insumo** de stock en alcance, la manual queda solo como referencia y gana lo aplicado (049 FR-002).
- Si la manual contradice el rubro (P13), el renglón va a revisión.

## R-06 Rubros "Depende"

| Rubro | Cómo se resuelve |
|---|---|
| Analisis laboratorio | Busca "suelo" en la descripción → Asesoramiento del cultivo (cultivo por la imputación manual o la deducción); "hacienda"/"sangre"/"brucelosis" → Ganadería; si no aparece ninguna, revisión. |
| Combustible | Si el renglón pasó por stock y lo consume una orden de labor propia → cultivo de esa orden (Labores); si no → Estructura. |
| Financiamiento | Si hay `CompraDocumentosRelacionados` con una factura de insumo → mismo reparto que esa factura, en proporción; si no → Financiero. |
| Insumos productivos (silobolsa, hilo, malla) | Entra a stock y lo resuelve la orden que lo usa: si el cultivo de la orden es forrajero → ese cultivo; si es de grano → Comercialización de ese cultivo; si la orden es de centro Ganadería → Ganadería; si la orden no tiene cultivo ni centro → revisión. |

## R-06b Flete de insumos

**Decisión**: el flete de insumos es costo de adquisición. Al calcular el costo unitario de una capa, `costos_de_renglones` le suma el flete atribuido:

- **Flete en la misma factura**: se reparte entre sus renglones de insumo en proporción al importe.
- **Flete en factura aparte**: se reparte entre los renglones de insumo de la factura o el remito relacionados (`CompraDocumentosRelacionados` / `VinculoRemitoPendiente`, tipo `flete`), también en proporción al importe.

El renglón de flete no tiene fracciones propias. Su importe se reparte entre las fracciones de los insumos, y el listado del Estudio lo muestra como filas por uso.

**Alternativas descartadas**:
- Imputar el flete de una vez: no hay campaña cierta mientras el insumo está en stock.
- Repartirlo por cantidad: las unidades son mixtas.

## R-07 Doble conteo en el resultado del cultivo

**Decisión**:
- Para los renglones en alcance:
  - `costos_heredados` (la vista) los **excluye**;
  - su costo sale de las fracciones aprobadas (Origen `Insumo` o `Directo`).
- En `costo_ordenes_trabajo`, el consumo de capas de renglones en alcance se descuenta: ya lo cuentan las fracciones.
- El resto del cálculo heredado no cambia.

**Consecuencia aceptada**: el doble conteo de insumos en renglones viejos ya imputados queda como está, porque Sergio pidió que lo ya hecho no se toque. El informe de impacto (049 FR-012) lo muestra. Corregirlo en el pasado sería otra decisión.

## R-08 Reparto por superficie del plan agrícola

**Decisión**: los costos "a cultivo" sin cultivo determinado y con una sola campaña posible se reparten según la superficie del plan agrícola de esa campaña (módulo `planificacion`). Si el plan no tiene superficie para esa campaña, el renglón va a revisión.

El reparto es por cultivo/campaña, sin lote, salvo las labores de contratista, que siguen con el reparto de 048.

## R-09 Producto sugerido

**Decisión**: se normaliza la descripción (mayúsculas, sin acentos ni unidades ni números de concentración) y se compara contra el nombre y los sinónimos de los formulados del catálogo SENASA/INASE que ya tiene WC.

- **Coincidencia única** (un solo formulado contiene todos los tokens significativos): se asigna `IdFormulado` en el renglón, que tiene que estar en alcance.
- **Varias o ninguna**: va a revisión con las opciones.

Cuando Sergio corrige, se ofrece guardar una regla `TamizReglaProducto` (texto normalizado → producto).

## R-10 Disparadores y pasada diaria

**Decisión**:
- Al guardar o editar una compra → `tamiz.tamizar_compra(id)`.
- Al ejecutar, editar o anular una orden → `_recalcular_imputacion_por_productos`, ampliado a los renglones en alcance aunque todavía no tengan corrida.
- Al vincular o desvincular un remito → recálculo, como hoy.
- Pasada diaria `imputacion_diaria_050.py`, registrada en el Programador de tareas de Windows igual que la rutina de peajes:
  - vínculos remito↔factura pendientes;
  - recálculo de todos los renglones en alcance con saldo en stock;
  - control de cierre.

## R-11 Aviso y pantalla de revisión

**Decisión**:
- El endpoint `GET /imputacion/revisar/contador` alimenta el contador del menú (TanStack Query, refetch cada 5 min).
- La pantalla lista primero los dudosos y después lo aprobado solo, agrupado por día de carga.
- No se mandan mails.
