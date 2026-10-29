"""036 — planilla para que Sergio revise el recálculo FIFO (por vencimiento; `--regla029` para la regla apagada) (solo lectura).

Una hoja por cuenta, solo con las facturas cuyo pago cambia: cómo está hoy y cómo quedaría.
Uso (desde backend/): python -m scripts.revision_imputaciones_029_036 <salida.xlsx> 115 48 97 [--regla029] [--todas: todas las facturas, no solo las que cambian]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from src.db.connection import fetch_all
from src.features.recalculo_fifo import cambio, entrada, motor
from src.features.recalculo_fifo.ejecuciones import MOV_A_APLICACION

NOMBRE = {"Banco Nacion": "BNA", "Galicia": "Galicia", "Pagos efectivo": "Efectivo", "Compras": "NC",
          "Tarjetas": "Tarjeta", "Venta Granos": "Liq. granos", "Pagos Valores Recibidos": "Cheque",
          "Cobros Valores Recibidos": "Cheque", "Retenciones": "Retención"}
MEDIO_A_ORIGEN = {v: k for k, v in MOV_A_APLICACION.items()} | {"tarjetas": "Tarjetas"}


def _pesos(x: float) -> str:
    return f"$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pago(origen: str, item: dict | None, importe: float) -> str:
    if not item:
        return f"{NOMBRE.get(origen, origen)} {_pesos(importe)}"
    return f"{NOMBRE.get(origen, origen)} {item['fecha']:%d/%m/%Y} {_pesos(importe)}"


if __name__ == "__main__":
    salida, ids = sys.argv[1], [int(x) for x in sys.argv[2:] if x.isdigit()]
    hoy = date.today()
    tc = cambio.funcion_tc(hoy)
    libro = Workbook()
    libro.remove(libro.active)
    for id_contacto, e in entrada.armar(ids).items():
        items = {(i["clave"][0], i["clave"][1]): i for i in e["items"]}
        nuevo = motor.recalcular(e["items"], e["fijos"], tc, hoy, regla_029="--regla029" in sys.argv)["aplicaciones"]
        ahora = defaultdict(list)
        for a in nuevo:
            d, c = tuple(a["debito"])[:2], tuple(a["credito"])[:2]
            if d[0] == "Compras":
                ahora[d[1]].append(_pago(c[0], items.get(c), a["importeArs"]))
        antes = defaultdict(list)
        for a in fetch_all(
                "SELECT a.OrigenMovimiento AS m, a.IdMovimientoOrigen AS i, a.IdDocumentoAplicado AS d, a.ImporteAplicado AS x "
                "FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
                "WHERE c.IdContacto = ? AND a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0", (id_contacto,)):
            origen = MEDIO_A_ORIGEN.get(a["m"], a["m"])
            antes[a["d"]].append(_pago(origen, items.get((origen, a["i"])), float(a["x"])))
        hoja = libro.create_sheet((e["nombre"] or str(id_contacto))[:28].replace("/", "-"))
        hoja.append(["Factura", "Emisión", "Vencimiento", "Importe", "Hoy la pagan", "Quedaría pagada por", "¿Cambia?"])
        for celda in hoja[1]:
            celda.font = Font(bold=True)
        cambios = 0
        for (origen, ident), d in sorted(items.items(), key=lambda kv: kv[1]["vencimiento"]):
            if origen != "Compras" or d["lado"] != "D" or d["clase"] != "doc":
                continue
            a, n = sorted(antes.get(ident, [])), sorted(ahora.get(ident, []))
            if a == n:
                continue
            cambios += 1
            hoja.append([d["nro"] or d["documento"], d["fecha"], d["vencimiento"], _pesos(float(d["importe"])),
                         "\n".join(a) or "(sin pagar)", "\n".join(n) or "(sin pagar)"])
        for col, ancho in zip("ABCDEFG", (18, 12, 12, 16, 42, 42, 9)):
            hoja.column_dimensions[col].width = ancho
        for fila in hoja.iter_rows(min_row=2):
            for celda in fila:
                celda.alignment = Alignment(wrap_text=True, vertical="top")
            fila[1].number_format = fila[2].number_format = "DD/MM/YYYY"
        print(e["nombre"], "facturas que cambian:", cambios)
    libro.save(salida)
