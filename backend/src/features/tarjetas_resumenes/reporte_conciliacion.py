"""Reporte de conciliaciones de resúmenes de tarjeta en planilla (.xlsx) para el
Estudio Contable.

Hojas: "Resúmenes" (cabecera con cargos e impuestos, total, pago y estado de cada
resumen), "Conciliación" (una fila por consumo y documento vinculado, con CUIT,
neto, IVA, tipo de cambio e importe imputado), "Pagos" y "Ayuda". Los importes
van como números con formato de celda (`$`/`us$`), así que Excel los muestra con
la configuración regional de quien abre el archivo (miles "." y decimales ","
en Argentina) y se pueden sumar y filtrar.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.db.connection import fetch_all
from src.db.params import as_sql_datetime
from src.features.tarjetas_resumenes.conciliacion_documentos import importe_pesos
from src.features.tarjetas_resumenes.repository import (
    _APLICA_PARTICULAR,
    TOLERANCIA_CONCILIACION,
    _f,
)

CARGOS: list[tuple[str, str, str]] = [
    # (columna SQL, clave, título)
    ("ImpuestoSellos", "impuestoSellos", "Impuesto de sellos"),
    ("GastosAdmin", "gastosAdmin", "Gastos de administración"),
    ("MantCuenta", "mantCuenta", "Mantenimiento de cuenta"),
    ("RenovAnual", "renovAnual", "Renovación anual"),
    ("PromocionBNA", "promocionBNA", "Promoción BNA"),
    ("CreditoContingente", "creditoContingente", "Crédito contingente"),
    ("IntFinanc", "intFinanc", "Interés de financiación"),
    ("IntCompens", "intCompens", "Interés compensatorio"),
    ("IVA105", "iva105", "IVA 10,5%"),
    ("PercepIVA105", "percepIVA105", "Percepción IVA 10,5%"),
    ("IVA21", "iva21", "IVA 21%"),
    ("PercepIVA21", "percepIVA21", "Percepción IVA 21%"),
    ("PercepIIBB", "percepIIBB", "Percepción IIBB"),
    ("AjusteResAnterior", "ajusteResAnterior", "Ajuste de resumen anterior"),
]

ESTADO_CONCILIADA = "Conciliada"
ESTADO_DIFERENCIA = "Conciliada con diferencia aceptada"
ESTADO_SIN_DOC = "Sin documento / no aplica"
ESTADO_PENDIENTE = "Pendiente"

MOTIVOS = {
    "AjusteTipoCambioSinNota": "Ajuste de tipo de cambio sin nota",
    "Redondeo": "Redondeo",
    "Impuesto": "Impuesto",
    "Interes": "Interés",
    "CompraNoCargada": "Compra no cargada en el sistema",
    "Otro": "Otro",
}

_FMT_PESOS = '"$" #,##0.00;[Red]-"$" #,##0.00'
_FMT_USD = '"us$" #,##0.00;[Red]-"us$" #,##0.00'
_FMT_FECHA = "dd/mm/yyyy"
_FMT_TC = "#,##0.00##"


def _m(valor) -> float:
    """Importe a centavos: los totales de Compras se arman multiplicando cantidades,
    precios e IVA y arrastran decimales de más."""
    return round(_f(valor), 2)


def _d(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    return valor


def _where(id_tarjeta, desde, hasta) -> tuple[str, list]:
    condiciones, params = ["1 = 1"], []
    if id_tarjeta is not None:
        condiciones.append("r.IdTarjeta = ?")
        params.append(id_tarjeta)
    if desde is not None:
        condiciones.append("r.FechaCierre >= ?")
        params.append(as_sql_datetime(desde))
    if hasta is not None:
        condiciones.append("r.FechaCierre <= ?")
        params.append(as_sql_datetime(hasta))
    return " AND ".join(condiciones), params


def obtener_datos(id_tarjeta: int | None = None, desde=None, hasta=None) -> dict:
    """Todo lo que necesita el reporte, con pocas consultas (no una por línea)."""
    where, params = _where(id_tarjeta, desde, hasta)
    cargos_sql = ", ".join(f"r.{col} AS {clave}" for col, clave, _ in CARGOS)
    resumenes = fetch_all(
        f"""
        SELECT r.IdResumen AS idResumen, t.TarjetaNombre AS tarjeta, r.ResumenCodigo AS codigo,
               r.FechaCierre AS fechaCierre, r.FechaVencimiento AS fechaVencimiento, {cargos_sql}
        FROM dbo.Tarjetas_Resumenes r
        LEFT JOIN dbo.Tarjetas t ON t.IdTarjeta = r.IdTarjeta
        WHERE {where}
        ORDER BY r.FechaCierre, r.IdResumen
        """,
        tuple(params),
    )
    lineas = fetch_all(
        f"""
        SELECT l.IdLineaConsumo AS idLinea, l.IdResumen AS idResumen, l.FechaCompra AS fecha, l.Detalle AS detalle,
               l.Importe AS importe, c.[Razon Social] AS proveedor, c.[CUIT/CUIL] AS cuit,
               e.Estado AS estado, e.Motivo AS motivo, e.Detalle AS detalleMotivo, e.ImporteDiferencia AS importeDiferencia
        FROM dbo.Tarjetas_Resumenes_Lineas l
        JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen
        LEFT JOIN dbo.Contactos c ON c.IdContacto = l.IdContacto
        LEFT JOIN dbo.Tarjetas_Resumenes_Lineas_Estado e ON e.IdLineaConsumo = l.IdLineaConsumo
        WHERE {where}
        ORDER BY r.FechaCierre, l.IdResumen, l.IdLineaConsumo
        """,
        tuple(params),
    )
    vinculos = fetch_all(
        f"""
        SELECT v.IdLineaConsumo AS idLinea, v.IdCompra AS idCompra, v.ImporteImputado AS imputado,
               w.Fecha AS fecha, w.[Tipo documento] AS tipo, w.[Nro Documento] AS numero, w.Moneda AS moneda,
               w.[Tipo de Cambio] AS tipoDeCambio, (w.ImporteDocumento - pa.cp) AS importeOriginal,
               pa.cp AS compraParticular, cm.[Ajusta Tipo Cambio] AS ajustaTipoCambio,
               ISNULL(d.neto, 0) AS neto, ISNULL(d.iva, 0) AS iva,
               ISNULL(cm.[Ingresos Brutos], 0) + ISNULL(cm.[Conceptos no gravados], 0) + ISNULL(cm.Guias, 0)
                 + ISNULL(cm.Comision, 0) + ISNULL(cm.Financiacion, 0) + ISNULL(cm.[Gastos Varios], 0)
                 + ISNULL(cm.[Ley de Sellos], 0) + ISNULL(cm.[Res gral 4169/96], 0) AS otros,
               ct.[Razon Social] AS proveedor, ct.[CUIT/CUIL] AS cuit
        FROM dbo.Tarjetas_Resumenes_Lineas_Compras v
        JOIN dbo.Tarjetas_Resumenes_Lineas l ON l.IdLineaConsumo = v.IdLineaConsumo
        JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen
        JOIN dbo.vw_Compras_ImporteDocumento w ON w.IdDeuda = v.IdCompra
        JOIN dbo.Compras cm ON cm.IdDeuda = v.IdCompra
        {_APLICA_PARTICULAR}
        OUTER APPLY (
            SELECT SUM(dc.Cantidad * dc.[Precio Unitario]) AS neto,
                   SUM(dc.Cantidad * dc.[Precio Unitario] * ISNULL(dc.IVA, 0) / 100.0) AS iva
            FROM dbo.Det_Compras dc
            WHERE dc.IdCompra = v.IdCompra
              AND NOT (dc.[Precio Unitario] < 0 AND dc.[Producto/Servicio] LIKE '%particular%')
        ) d
        LEFT JOIN dbo.Contactos ct ON ct.IdContacto = w.IdContacto
        WHERE {where}
        ORDER BY v.IdVinculo
        """,
        tuple(params),
    )
    pagos = fetch_all(
        f"""
        SELECT p.IdResumen AS idResumen, p.Fecha AS fecha, p.Importe AS importe, p.Origen AS origen
        FROM dbo.Tarjetas_Resumenes_Pagos p
        JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = p.IdResumen
        WHERE {where}
        ORDER BY p.Fecha, p.IdPago
        """,
        tuple(params),
    )
    tarjeta = None
    if id_tarjeta is not None:
        fila = fetch_all("SELECT TarjetaNombre AS n FROM dbo.Tarjetas WHERE IdTarjeta = ?", (id_tarjeta,))
        tarjeta = fila[0]["n"] if fila else None
    return {"resumenes": resumenes, "lineas": lineas, "vinculos": vinculos, "pagos": pagos, "tarjeta": tarjeta}


def _estado_linea(linea: dict, vinculos: list[dict]) -> str:
    if linea.get("estado") == "SinDocumento":
        return ESTADO_SIN_DOC
    if linea.get("estado") == "DiferenciaAceptada":
        return ESTADO_DIFERENCIA
    return ESTADO_CONCILIADA if vinculos else ESTADO_PENDIENTE


def _estilo_encabezado(ws, fila: int, columnas: int) -> None:
    relleno = PatternFill("solid", fgColor="1F3D2B")
    for c in range(1, columnas + 1):
        celda = ws.cell(row=fila, column=c)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = relleno
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[fila].height = 32


def _anchos(ws, anchos: list[float]) -> None:
    for i, a in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = a


def construir_libro(datos: dict, filtros: dict) -> Workbook:
    lineas_por_resumen: dict[int, list[dict]] = defaultdict(list)
    for l in datos["lineas"]:
        lineas_por_resumen[l["idResumen"]].append(l)
    vinculos_por_linea: dict[int, list[dict]] = defaultdict(list)
    for v in datos["vinculos"]:
        vinculos_por_linea[v["idLinea"]].append(v)
    pagos_por_resumen: dict[int, list[dict]] = defaultdict(list)
    for p in datos["pagos"]:
        pagos_por_resumen[p["idResumen"]].append(p)
    resumen_por_id = {r["idResumen"]: r for r in datos["resumenes"]}

    wb = Workbook()

    # ------------------------- Resúmenes -------------------------
    ws = wb.active
    ws.title = "Resúmenes"
    titulos = (
        ["Tarjeta", "Resumen", "Fecha de cierre", "Vencimiento", "Total consumos"]
        + [t for _, _, t in CARGOS]
        + ["Total del resumen", "Pagado", "Diferencia de pago", "Pago", "Consumos", "Conciliados",
           "Con diferencia aceptada", "Sin documento", "Pendientes", "Estado"]
    )
    ws.append(titulos)
    _estilo_encabezado(ws, 1, len(titulos))
    fila_desde = 2
    for r in datos["resumenes"]:
        lineas = lineas_por_resumen.get(r["idResumen"], [])
        estados = [_estado_linea(l, vinculos_por_linea.get(l["idLinea"], [])) for l in lineas]
        consumos = round(sum(_f(l["importe"]) for l in lineas), 2)
        cargos = [_f(r[clave]) for _, clave, _ in CARGOS]
        total = round(consumos + sum(cargos), 2)
        pagado = round(sum(_f(p["importe"]) for p in pagos_por_resumen.get(r["idResumen"], [])), 2)
        diferencia = round(total - pagado, 2)
        pago_ok = diferencia <= TOLERANCIA_CONCILIACION
        pendientes = estados.count(ESTADO_PENDIENTE)
        ws.append(
            [r["tarjeta"], r["codigo"], _d(r["fechaCierre"]), _d(r["fechaVencimiento"]), consumos, *cargos, total,
             pagado, diferencia, "Conciliado" if pago_ok else "Pendiente", len(lineas),
             estados.count(ESTADO_CONCILIADA), estados.count(ESTADO_DIFERENCIA), estados.count(ESTADO_SIN_DOC),
             pendientes, "Conciliado" if pago_ok and pendientes == 0 else "Pendiente de conciliar"]
        )
    ultima = ws.max_row
    n_cargos = len(CARGOS)
    for fila in ws.iter_rows(min_row=2, max_row=ultima):
        fila[2].number_format = _FMT_FECHA
        fila[3].number_format = _FMT_FECHA
        for c in range(4, 6 + n_cargos + 3):  # consumos, cargos, total, pagado, diferencia
            fila[c].number_format = _FMT_PESOS
    if ultima >= 2:
        ws.append(["Totales"] + [None] * 3 + [
            f"=SUM({get_column_letter(c)}{fila_desde}:{get_column_letter(c)}{ultima})" for c in range(5, 6 + n_cargos + 3)
        ])
        for c in range(1, len(titulos) + 1):
            ws.cell(row=ws.max_row, column=c).font = Font(bold=True)
        for c in range(5, 6 + n_cargos + 3):
            ws.cell(row=ws.max_row, column=c).number_format = _FMT_PESOS
    ws.freeze_panes = "C2"
    if ultima >= 2:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(titulos))}{ultima}"
    _anchos(ws, [18, 24, 13, 13, 16] + [15] * n_cargos + [17, 16, 15, 12, 10, 12, 13, 12, 11, 22])

    # ------------------------- Conciliación (detalle) -------------------------
    wd = wb.create_sheet("Conciliación")
    titulos_d = [
        "Tarjeta", "Resumen", "Fecha de cierre", "N° línea", "Fecha del consumo", "Detalle del consumo",
        "Importe del consumo", "Estado", "Motivo", "Detalle del motivo", "Diferencia",
        "Proveedor", "CUIT", "Tipo de documento", "N° de documento", "Fecha del documento", "Moneda",
        "Tipo de cambio", "Neto gravado", "IVA", "Otros conceptos", "Importe del documento",
        "Importe del documento en $", "Importe imputado", "Observaciones",
    ]
    wd.append(titulos_d)
    _estilo_encabezado(wd, 1, len(titulos_d))
    for l in datos["lineas"]:
        r = resumen_por_id[l["idResumen"]]
        vs = vinculos_por_linea.get(l["idLinea"], [])
        estado = _estado_linea(l, vs)
        importe = _f(l["importe"])
        imputado_total = round(sum(_f(v["imputado"]) for v in vs), 2)
        diferencia = None
        if l.get("estado") == "DiferenciaAceptada" and l.get("importeDiferencia") is not None:
            diferencia = _f(l["importeDiferencia"])
        elif vs:
            dif = round(importe - imputado_total, 2)
            diferencia = dif if abs(dif) > 0.005 else None
        base = [r["tarjeta"], r["codigo"], _d(r["fechaCierre"]), l["idLinea"], _d(l["fecha"]), l["detalle"]]
        estado_cols = [
            estado,
            MOTIVOS.get(l.get("motivo"), l.get("motivo")),
            l.get("detalleMotivo"),
        ]
        if not vs:
            wd.append(
                base + [importe] + estado_cols + [diferencia, l["proveedor"], l["cuit"]] + [None] * 12
            )
            continue
        for i, v in enumerate(vs):
            moneda = "Dólares" if v["moneda"] == "Dolares" else "Pesos"
            doc = {"moneda": v["moneda"], "tipoDeCambio": _f(v["tipoDeCambio"]), "importeOriginal": _f(v["importeOriginal"])}
            marcas = []
            if v["ajustaTipoCambio"]:
                marcas.append("Nota de ajuste de tipo de cambio")
            if _f(v["compraParticular"]) < 0:
                marcas.append("Compra particular (importe bruto)")
            wd.append(
                base
                + [importe if i == 0 else None]
                + estado_cols
                + [diferencia if i == 0 else None, v["proveedor"], v["cuit"], v["tipo"], v["numero"], _d(v["fecha"]),
                   moneda, _f(v["tipoDeCambio"]) if v["moneda"] == "Dolares" else None,
                   _m(v["neto"]), _m(v["iva"]), _m(v["otros"]), _m(v["importeOriginal"]), importe_pesos(doc),
                   _m(v["imputado"]), "; ".join(marcas) or None]
            )
    ultima_d = wd.max_row
    for fila in wd.iter_rows(min_row=2, max_row=ultima_d):
        fila[2].number_format = _FMT_FECHA
        fila[4].number_format = _FMT_FECHA
        fila[6].number_format = _FMT_PESOS
        fila[10].number_format = _FMT_PESOS
        fila[15].number_format = _FMT_FECHA
        fila[17].number_format = _FMT_TC
        formato_doc = _FMT_USD if fila[16].value == "Dólares" else _FMT_PESOS
        for c in (18, 19, 20, 21):
            fila[c].number_format = formato_doc
        fila[22].number_format = _FMT_PESOS
        fila[23].number_format = _FMT_PESOS
    wd.freeze_panes = "G2"
    if ultima_d >= 2:
        wd.auto_filter.ref = f"A1:{get_column_letter(len(titulos_d))}{ultima_d}"
    _anchos(wd, [16, 22, 13, 9, 13, 34, 16, 30, 26, 24, 14, 28, 15, 16, 18, 13, 10, 12, 15, 13, 14, 16, 17, 16, 34])

    # ------------------------- Pagos -------------------------
    wp = wb.create_sheet("Pagos")
    titulos_p = ["Tarjeta", "Resumen", "Fecha de cierre", "Fecha de pago", "Importe pagado", "Origen"]
    wp.append(titulos_p)
    _estilo_encabezado(wp, 1, len(titulos_p))
    for p in datos["pagos"]:
        r = resumen_por_id[p["idResumen"]]
        wp.append([r["tarjeta"], r["codigo"], _d(r["fechaCierre"]), _d(p["fecha"]), _f(p["importe"]),
                   {"BNA": "Banco Nación", "Galicia": "Banco Galicia"}.get(p["origen"], p["origen"] or "Carga manual")])
    for fila in wp.iter_rows(min_row=2, max_row=wp.max_row):
        fila[2].number_format = _FMT_FECHA
        fila[3].number_format = _FMT_FECHA
        fila[4].number_format = _FMT_PESOS
    wp.freeze_panes = "A2"
    if wp.max_row >= 2:
        wp.auto_filter.ref = f"A1:F{wp.max_row}"
    _anchos(wp, [18, 24, 14, 14, 17, 18])

    # ------------------------- Proveedores sin CUIT -------------------------
    sin_cuit: dict[str, int] = defaultdict(int)
    for v in datos["vinculos"]:
        if not (v["cuit"] or "").strip():
            sin_cuit[v["proveedor"] or "(sin proveedor)"] += 1
    if sin_cuit:
        wc = wb.create_sheet("Proveedores sin CUIT")
        wc.append(["Proveedor", "Documentos en este reporte"])
        _estilo_encabezado(wc, 1, 2)
        for nombre, cantidad in sorted(sin_cuit.items(), key=lambda x: (-x[1], x[0])):
            wc.append([nombre, cantidad])
        wc.freeze_panes = "A2"
        _anchos(wc, [44, 26])

    # ------------------------- Ayuda -------------------------
    wa = wb.create_sheet("Ayuda")
    wa.column_dimensions["A"].width = 34
    wa.column_dimensions["B"].width = 110
    filas = [
        ("Reporte de conciliación de resúmenes de tarjeta", None),
        ("Generado", datetime.now().strftime("%d/%m/%Y %H:%M")),
        ("Tarjeta", filtros.get("tarjeta") or "Todas"),
        ("Cierre desde", filtros["desde"].strftime("%d/%m/%Y") if filtros.get("desde") else "Sin límite"),
        ("Cierre hasta", filtros["hasta"].strftime("%d/%m/%Y") if filtros.get("hasta") else "Sin límite"),
        (None, None),
        ("Hoja «Resúmenes»", "Una fila por resumen: consumos, los cargos e impuestos de cabecera, total, pago registrado y cuántos consumos están conciliados."),
        ("Hoja «Conciliación»", "Una fila por consumo y documento vinculado (si un consumo cubre varios documentos, ocupa varias filas). Las filas de un mismo consumo comparten N° línea; «Importe del consumo» y «Diferencia» figuran solo en la primera fila para que las sumas no se dupliquen."),
        ("Hoja «Pagos»", "Pagos registrados de cada resumen y el banco de origen."),
        (None, None),
        ("Estado «Conciliada»", "El consumo está vinculado a uno o más documentos (Factura / Nota de Crédito / Nota de Débito) cuya suma cierra con el importe."),
        ("Estado «Conciliada con diferencia aceptada»", "Vinculada, pero la suma no cierra: la columna «Diferencia» indica cuánto y «Motivo» por qué se aceptó."),
        ("Estado «Sin documento / no aplica»", "Consumo sin comprobante (impuestos, intereses, compra no cargada): «Motivo» indica la causa."),
        ("Estado «Pendiente»", "Todavía no se concilió."),
        (None, None),
        ("CUIT", "Se toma de Contactos. " + (
            f"{len(sin_cuit)} proveedor(es) de este reporte no tienen CUIT cargado (ver hoja «Proveedores sin CUIT»)."
            if sin_cuit else "Todos los proveedores de este reporte tienen CUIT cargado.")),
        ("Importes", "Los importes del consumo, del documento en $ y el imputado están en pesos. «Importe del documento» está en la moneda del documento; los documentos en dólares se pesifican con su propio tipo de cambio."),
        ("Diferencia", "Importe del consumo menos lo imputado a documentos (positivo: falta imputar; negativo: se imputó de más)."),
        ("Compra particular", "Factura con una línea negativa de compra particular: se informa el importe bruto (lo que cobró la tarjeta) y el neto/IVA sin esa línea."),
        ("Nota de ajuste de tipo de cambio", "Nota de crédito/débito que ajusta la diferencia entre la cotización de la tarjeta y la del documento."),
    ]
    for a, b in filas:
        wa.append([a, b])
    wa["A1"].font = Font(bold=True, size=14)
    for fila in wa.iter_rows(min_row=2, max_row=wa.max_row):
        fila[0].font = Font(bold=True)
        fila[1].alignment = Alignment(wrap_text=True, vertical="top")
        fila[0].alignment = Alignment(vertical="top", wrap_text=True)
    return wb


def generar_xlsx(id_tarjeta: int | None = None, desde=None, hasta=None) -> bytes:
    datos = obtener_datos(id_tarjeta, desde, hasta)
    wb = construir_libro(datos, {"tarjeta": datos["tarjeta"], "desde": desde, "hasta": hasta})
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
