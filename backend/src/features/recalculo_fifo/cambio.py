"""TC BNA vendedor divisa para el recálculo FIFO (032, research R2).

Reutiliza la serie `dbo.[Dolar BNA]` de 030 a través de
`flujo_caja.cotizacion`. La serie se carga una vez por ejecución, y el
motor recibe una función `tc(fecha)`. El "día anterior al pago" lo calcula
el motor, que llama con fecha - 1. Para un día sin cotización (feriado) se
usa la anterior, hasta 7 días hacia atrás.
"""

from __future__ import annotations

from datetime import date

from src.features.flujo_caja.cotizacion import cargar_serie, cotizacion_del_dia

INICIO = date(2010, 4, 1)


def funcion_tc(hasta: date | None = None):
    serie = cargar_serie(INICIO, hasta or date.today())

    def tc(fecha: date) -> float | None:
        encontrado = cotizacion_del_dia(serie, fecha)
        return encontrado[0] if encontrado else None

    return tc
