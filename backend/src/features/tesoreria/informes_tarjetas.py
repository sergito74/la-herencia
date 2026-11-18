"""Informes de tarjetas de crédito para el Estudio y actualización automática de todos los informes (18/11/2026).

Mismos archivos que el Estudio ya conoce (misma carpeta y nombre en Dropbox), con dos hojas: "Resumen" (un renglón
por resumen, con los cargos que tiene cada tarjeta) y "Detalle Resumen" (cada consumo con su conciliación). Las hojas
históricas de AgroNación (compras en cuotas, intereses, pagos, saldo de capital) se dejaron de generar (Sergio).

El sistema mantiene todos los informes (bancos y tarjetas) solo: mientras está abierto, cada 3 horas compara una
huella de los datos de cada informe y regenera los que cambiaron. No depende de nadie.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.db.connection import execute_write, fetch_all
from src.features.tesoreria import listado_estudio as L

TARJETAS = {
    1: L.BANCOS / "BNA" / "AgroNacion" / "Listado Resumenes.xlsx",
    2: L.BANCOS / "BNA" / "Corporativa Nacion" / "Detalle Consumos Tarjeta Coroporativa Nacion.xlsx",
    3: L.BANCOS / "BNA" / "Mastercard" / "Resumenes Mastercard BNA.xlsx",
    4: L.BANCOS / "Galicia" / "Tarjetas" / "Visa" / "Detalle Consumos Tarjeta Visa Galicia.xlsx",
    5: L.BANCOS / "Galicia" / "Tarjetas" / "Galicia Rural" / "Detalle Consumos Tarjeta Galicia Rural.xlsx",
}
CARGOS = [("ImpuestoSellos", "Impuesto Sellos"), ("GastosAdmin", "Gastos Adm. / Emisión"), ("MantCuenta", "Com. Mant. Cuenta"),
          ("RenovAnual", "Com. Renov. Anual"), ("PromocionBNA", "Promoción Banco Nación"), ("CreditoContingente", "Crédito Contingente"),
          ("IntFinanc", "Intereses Financiación"), ("IntCompens", "Intereses Compensatorios"), ("IVA21", "IVA 21%"),
          ("PercepIVA21", "Percep. IVA 21%"), ("IVA105", "IVA 10,5%"), ("PercepIVA105", "Percep. IVA 10,5%"),
          ("PercepIIBB", "Percep. IIBB"), ("AjusteResAnterior", "Ajuste Res. Anterior")]


def _nombres() -> dict[int, str]:
    return {int(r["i"]): r["n"] for r in fetch_all("SELECT IdTarjeta AS i, TarjetaNombre AS n FROM dbo.Tarjetas")}


def _encabezar(ws, columnas: list[tuple[str, float]], titulo: str) -> None:
    ws.append([titulo])
    ws["A1"].font = Font(bold=True, size=12, color=L._VERDE)
    ws.append([c for c, _ in columnas])
    for i, (_, ancho) in enumerate(columnas, start=1):
        celda = ws.cell(row=2, column=i)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=L._VERDE)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.freeze_panes = "A3"


def _pesos(v: float) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def estado_linea(estado_guardado: str | None, vinculado: float, importe: float, tiene_vinculos: bool, contacto, detalle: str) -> str:
    """Pura: estado de conciliación de un consumo de tarjeta."""
    if estado_guardado == "DiferenciaAceptada":
        return "Conciliado con diferencia"
    if estado_guardado:
        return "Sin documento"
    if tiene_vinculos and abs(abs(vinculado) - abs(importe)) <= 1:
        return "Conciliado"
    if tiene_vinculos:
        return "Parcial"
    if not contacto and L._BANCARIO.search(detalle or ""):
        return "Cargo de la tarjeta"
    return "Pendiente"


def planilla_tarjeta(id_tarjeta: int) -> bytes:
    nombre = _nombres().get(id_tarjeta, str(id_tarjeta))
    resumenes = fetch_all(
        "SELECT r.*, (SELECT SUM(l.Importe) FROM dbo.Tarjetas_Resumenes_Lineas l WHERE l.IdResumen = r.IdResumen) AS TotalConsumos "
        "FROM dbo.Tarjetas_Resumenes r WHERE r.IdTarjeta = ? ORDER BY r.FechaCierre, r.IdResumen", (id_tarjeta,))
    cargos = [(k, t) for k, t in CARGOS if any(abs(float(r.get(k) or 0)) > 0.005 for r in resumenes)]
    titulo = f"Tarjeta {nombre} — Giamigli de Bolívar S.A. — generado el {datetime.now():%d/%m/%Y %H:%M} desde el sistema"
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    _encabezar(ws, [("Nro. Resumen", 22), ("Fecha Cierre", 12), ("Fecha Vencimiento", 13), ("Total Consumos", 16)]
               + [(t, 14) for _, t in cargos] + [("Total a pagar", 16)], titulo)
    for r in resumenes:
        valores = [float(r.get(k) or 0) for k, _ in cargos]
        consumos = float(r["TotalConsumos"] or 0)
        ws.append([r["ResumenCodigo"], r["FechaCierre"], r["FechaVencimiento"], round(consumos, 2)] + [v or None for v in valores]
                  + [round(consumos + sum(valores), 2)])
    for fila in ws.iter_rows(min_row=3):
        fila[1].number_format = fila[2].number_format = "dd/mm/yyyy"
        for c in fila[3:]:
            c.number_format = L._PESOS

    lineas = fetch_all(
        """SELECT l.IdLineaConsumo AS id, r.ResumenCodigo AS resumen, r.FechaCierre AS cierre, l.FechaCompra AS fecha, l.Detalle AS detalle,
                  l.Importe AS importe, co.[Razon Social] AS contacto, e.Estado AS estado, e.Detalle AS motivo
           FROM dbo.Tarjetas_Resumenes_Lineas l JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen
           LEFT JOIN dbo.Contactos co ON co.IdContacto = l.IdContacto
           LEFT JOIN dbo.Tarjetas_Resumenes_Lineas_Estado e ON e.IdLineaConsumo = l.IdLineaConsumo
           WHERE r.IdTarjeta = ? ORDER BY r.FechaCierre, l.FechaCompra, l.IdLineaConsumo""", (id_tarjeta,))
    vinculos: dict[int, list[dict]] = defaultdict(list)
    for v in fetch_all(
            """SELECT v.IdLineaConsumo AS linea, v.IdCompra AS compra, v.IdImpuesto AS imp, v.ImporteImputado AS monto
               FROM dbo.Tarjetas_Resumenes_Lineas_Compras v JOIN dbo.Tarjetas_Resumenes_Lineas l ON l.IdLineaConsumo = v.IdLineaConsumo
               JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen WHERE r.IdTarjeta = ?""", (id_tarjeta,)):
        vinculos[int(v["linea"])].append(v)
    docs = L._documentos({int(v["compra"]) for vs in vinculos.values() for v in vs if v["compra"]})
    dw = wb.create_sheet("Detalle Resumen")
    _encabezar(dw, [("Nro. Resumen", 22), ("Fecha Cierre", 12), ("Fecha Compra", 12), ("Detalle", 40), ("Importe", 15),
                    ("Proveedor", 30), ("Estado", 22), ("Documentos vinculados", 55), ("Importe vinculado", 15), ("Rubro", 22),
                    ("Observación", 45)], titulo)
    for l in lineas:
        vs = vinculos.get(int(l["id"]), [])
        vinculado = round(sum(float(v["monto"] or 0) for v in vs), 2)
        textos = [(L._texto_doc({"tipo": "CompraDeuda", "doc": int(v["compra"])}, docs) if v["compra"] else f"Impuesto #{v['imp']}")
                  + f": {_pesos(float(v['monto'] or 0))}" for v in vs]
        principal = next((docs[int(v["compra"])] for v in vs if v["compra"] and int(v["compra"]) in docs), None)
        dw.append([l["resumen"], l["cierre"], l["fecha"], (l["detalle"] or "").strip(), float(l["importe"] or 0), l["contacto"],
                   estado_linea(l["estado"], vinculado, float(l["importe"] or 0), bool(vs), l["contacto"], l["detalle"]),
                   "; ".join(textos) or None, vinculado or None, (principal or {}).get("rubro"), l["motivo"]])
    for fila in dw.iter_rows(min_row=3):
        fila[1].number_format = fila[2].number_format = "dd/mm/yyyy"
        fila[4].number_format = fila[8].number_format = L._PESOS
    if dw.max_row > 2:
        dw.auto_filter.ref = f"A2:K{dw.max_row}"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def actualizar_tarjetas(ids: tuple[int, ...] = tuple(TARJETAS)) -> list[dict]:
    nombres = _nombres()
    return [L._guardar(TARJETAS[i], planilla_tarjeta(i), f"Tarjeta {nombres.get(i, i)}") for i in ids]


def estado() -> list[dict]:
    from datetime import datetime as dt

    nombres = _nombres()
    out = L.estado()
    for i, destino in TARJETAS.items():
        m = dt.fromtimestamp(destino.stat().st_mtime).isoformat(timespec="minutes") if destino.exists() else None
        out.append({"banco": f"Tarjeta {nombres.get(i, i)}", "archivo": destino.name, "carpeta": destino.parent.name, "actualizada": m})
    return out


def actualizar_todo() -> list[dict]:
    return L.actualizar_dropbox() + actualizar_tarjetas()


# ------------------------------------------------------------------ actualización automática por cambios

def _uno(sql: str, params: tuple = ()) -> str:
    return str(list(fetch_all(sql, params)[0].values()))


def huellas() -> dict[str, str]:
    """Una huella barata por informe: si cambia, hay algo nuevo (movimientos, resúmenes, vínculos o estados)."""
    out = {}
    for medio, tabla, idc in (("galicia", "Movimientos Galicia", "IdMovimiento"), ("bna", "Movimientos BNA", "IdMovimientoBNA"),
                              ("mercado-libre", "Movimientos Mercado Libre", "IdMovimiento")):
        out[medio] = _uno(
            f"SELECT COUNT(*) AS a, MAX({idc}) AS b, "
            "(SELECT COUNT(*) FROM dbo.AplicacionesPago WHERE OrigenMovimiento = ? AND Anulada = 0) AS c, "
            "(SELECT COUNT(*) FROM dbo.ConciliacionesTesoreria WHERE Medio = ?) AS d, "
            "(SELECT COUNT(*) FROM dbo.ConciliacionesTesoreriaEstado WHERE Medio = ?) AS e, "
            f"(SELECT COUNT(*) FROM dbo.ConciliacionesTesoreriaEstado) AS f FROM dbo.[{tabla}]", (medio, medio, medio))
    for i in TARJETAS:
        out[f"tarjeta-{i}"] = _uno(
            "SELECT COUNT(*) AS a, MAX(l.IdLineaConsumo) AS b, SUM(l.Importe) AS c, "
            "(SELECT COUNT(*) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v JOIN dbo.Tarjetas_Resumenes_Lineas x ON x.IdLineaConsumo = v.IdLineaConsumo "
            " JOIN dbo.Tarjetas_Resumenes y ON y.IdResumen = x.IdResumen WHERE y.IdTarjeta = ?) AS d, "
            "(SELECT COUNT(*) FROM dbo.Tarjetas_Resumenes WHERE IdTarjeta = ?) AS e, "
            "(SELECT COUNT(*) FROM dbo.Tarjetas_Resumenes_Lineas_Estado) AS f "
            "FROM dbo.Tarjetas_Resumenes_Lineas l JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen WHERE r.IdTarjeta = ?", (i, i, i))
    return out


def _destino(clave: str):
    return L.DESTINOS[clave] if clave in L.DESTINOS else TARJETAS[int(clave.split("-")[1])]


def actualizar_si_cambio() -> list[dict]:
    """Regenera solo los informes cuyos datos cambiaron desde la última vez (dbo.ListadosEstudioHuellas)."""
    previas = {f["Clave"]: f["Huella"] for f in fetch_all("SELECT Clave, Huella FROM dbo.ListadosEstudioHuellas")}
    hechos = []
    for clave, h in huellas().items():
        if previas.get(clave) == h and _destino(clave).exists():
            continue
        r = L.actualizar_dropbox((clave,)) if clave in L.DESTINOS else actualizar_tarjetas((int(clave.split("-")[1]),))
        hechos += r
        if all(x["ok"] for x in r):
            if clave in previas:
                execute_write("UPDATE dbo.ListadosEstudioHuellas SET Huella = ?, Fecha = SYSDATETIME() WHERE Clave = ?", (h, clave))
            else:
                execute_write("INSERT INTO dbo.ListadosEstudioHuellas (Clave, Huella) VALUES (?, ?)", (clave, h))
    return hechos


def arrancar() -> None:
    """Mientras el sistema está abierto, cada 3 horas regenera los informes del Estudio que cambiaron."""
    import logging
    import os
    import sys
    import threading
    import time

    if "pytest" in sys.modules or os.environ.get("LA_HERENCIA_SIN_PLANIFICADOR") == "1":
        return

    def bucle():
        while True:
            try:
                actualizar_si_cambio()
            except Exception:  # noqa: BLE001
                logging.getLogger(__name__).exception("Informes del Estudio")
            time.sleep(3 * 3600)

    threading.Thread(target=bucle, name="informes-estudio", daemon=True).start()
