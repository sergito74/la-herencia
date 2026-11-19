"""Listados de conciliación bancaria para el Estudio (18/11/2026).

Sergio sube a Dropbox (Giamigli de Bolivar SA/Bancos) un listado por banco para que el Estudio trabaje: cada
movimiento del extracto con su contacto y los documentos que cancela. Estas planillas se regeneran desde el sistema
(nunca a mano) y se guardan en la misma carpeta y con el mismo nombre que ya usa el Estudio. Antes de reemplazar una
planilla se guarda una copia de la anterior en backups/conciliaciones-estudio.

Columnas: las del banco (fecha, descripción, comprobante, débito, crédito) y la conciliación (contacto, estado,
documentos aplicados con su importe, lo que queda sin aplicar, rubro, centro de costos y destino del documento).
"""

from __future__ import annotations

import re
import shutil
from collections import defaultdict
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.db.connection import fetch_all

BANCOS = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Bancos")
DESTINOS = {
    "galicia": BANCOS / "Galicia" / "Conciliacion Galicia.xlsx",
    "bna": BANCOS / "BNA" / "Conciliacion bancaria Banco Nacion.xlsx",
    "mercado-libre": BANCOS / "Mercado Libre" / "Conciliacion Mercado Libre.xlsx",
}
NOMBRE = {"galicia": "Banco Galicia", "bna": "Banco Nación", "mercado-libre": "Mercado Pago"}
COPIAS = Path(r"c:\dev\LaHerencia\backups\conciliaciones-estudio")

ESTADOS = {"conciliado": "Conciliado", "parcialmente_conciliado": "Parcial", "traspaso_interno": "Traspaso entre cuentas",
           "sin_documento": "Sin documento", "inversion": "Inversión", "ya_reconocido": "Reconocido", "sin_conciliar": "Pendiente"}

_PESOS = '#,##0.00;[Red]-#,##0.00'
_VERDE = "1F3D2B"


def _movimientos(medio: str) -> list[dict]:
    if medio == "galicia":
        return fetch_all(
            "SELECT m.IdMovimiento AS id, m.Fecha AS fecha, m.[Descripción] AS descripcion, "
            "CAST(m.[Número de Comprobante] AS varchar(40)) AS comprobante, ISNULL(m.[Débitos], 0) AS debito, ISNULL(m.[Créditos], 0) AS credito, "
            "LTRIM(RTRIM(CONCAT(m.LeyendasAdicionales1, ' ', m.LeyendasAdicionales2))) AS leyenda, c.[Razon Social] AS contacto "
            "FROM dbo.[Movimientos Galicia] m LEFT JOIN dbo.Contactos c ON c.IdContacto = m.IdContacto ORDER BY m.Fecha, m.IdMovimiento")
    if medio == "bna":
        return fetch_all(
            "SELECT m.IdMovimientoBNA AS id, m.[Fecha / Hora Mov#] AS fecha, m.Concepto AS descripcion, "
            "CONVERT(varchar(40), CAST(m.[Nro# Comprobante] AS bigint)) AS comprobante, CASE WHEN m.Importe < 0 THEN -m.Importe ELSE 0 END AS debito, "
            "CASE WHEN m.Importe > 0 THEN m.Importe ELSE 0 END AS credito, NULL AS leyenda, c.[Razon Social] AS contacto "
            "FROM dbo.[Movimientos BNA] m LEFT JOIN dbo.Contactos c ON c.IdContacto = m.IdContacto ORDER BY m.[Fecha / Hora Mov#], m.IdMovimientoBNA")
    return fetch_all(
        "SELECT m.IdMovimiento AS id, m.Fecha AS fecha, m.Descripcion AS descripcion, CAST(m.IdOperacion AS varchar(40)) AS comprobante, "
        "CASE WHEN m.Importe < 0 THEN -m.Importe ELSE 0 END AS debito, CASE WHEN m.Importe > 0 THEN m.Importe ELSE 0 END AS credito, "
        "NULL AS leyenda, c.[Razon Social] AS contacto FROM dbo.[Movimientos Mercado Libre] m "
        "LEFT JOIN dbo.Contactos c ON c.IdContacto = m.IdContacto ORDER BY m.Fecha, m.IdMovimiento")


def _aplicaciones(medio: str) -> dict[int, list[dict]]:
    """Documentos cancelados por cada movimiento: aplicaciones de pago (cuentas corrientes) y conciliaciones de Tesorería."""
    out: dict[int, list[dict]] = defaultdict(list)
    for a in fetch_all(
            "SELECT a.IdMovimientoOrigen AS mov, a.TipoDocumento AS tipo, a.IdDocumentoAplicado AS doc, a.ImporteAplicado AS imp "
            "FROM dbo.AplicacionesPago a WHERE a.Anulada = 0 AND a.OrigenMovimiento = ?", (medio,)):
        out[int(a["mov"])].append({"tipo": a["tipo"], "doc": a["doc"], "imp": float(a["imp"] or 0)})
    for c in fetch_all(
            "SELECT IdMovimiento AS mov, TipoOrigenDocumento AS tipo, IdOrigenDocumento AS doc, Importe AS imp "
            "FROM dbo.ConciliacionesTesoreria WHERE Medio = ? AND IdOrigenDocumento IS NOT NULL", (medio,)):
        tipo = {"Compras": "CompraDeuda"}.get(c["tipo"], c["tipo"])
        if not any(x["tipo"] == tipo and x["doc"] == c["doc"] for x in out[int(c["mov"])]):
            out[int(c["mov"])].append({"tipo": tipo, "doc": c["doc"], "imp": float(c["imp"] or 0)})
    return out


# Débitos y créditos propios del banco: no tienen documento y no quedan "pendientes".
_BANCARIO = re.compile(r"25413|25\.413|GRAVAMEN|IMP\.? ?DEB|IMP\.? ?CRED|COMISI|IVA|PERCEP|SELLOS|MANT(ENIMIENTO)?|INTERES|"
                       r"SERVICIO DE CUENTA|CARGO|IMPUESTO", re.I)


_INVERSION = re.compile(r"FIMA|PLAZO FIJO|P\.FIJO|PLAZO FIJ|RESCATE|SUSCRIPCION|SUSCRIPCI", re.I)


def _otros_pagos(medio: str) -> dict[int, list[dict]]:
    """Sueldos y trabajos eventuales pagados con este movimiento (vínculos del 18/11/2026)."""
    out: dict[int, list[dict]] = defaultdict(list)
    if medio not in ("galicia", "bna"):
        return out
    for f in fetch_all(
            "SELECT p.IdMovimientoBanco AS mov, r.[Periodo liquidado] AS periodo, p.Importe AS imp FROM dbo.RemuneracionesPagos p "
            "JOIN dbo.Remuneraciones r ON r.IdSalario = p.IdSalario WHERE p.Medio = ? AND p.IdMovimientoBanco IS NOT NULL", (medio,)):
        out[int(f["mov"])].append({"tipo": "Sueldo", "doc": str(f["periodo"]).strip(), "imp": float(f["imp"])})
    for f in fetch_all(
            "SELECT p.IdMovimientoBanco AS mov, t.Fecha AS fecha, t.Descripcion AS d, p.Importe AS imp FROM dbo.TrabajosEventualesPagos p "
            "JOIN dbo.TrabajosEventuales t ON t.IdTrabajo = p.IdTrabajo WHERE p.Medio = ? AND p.IdMovimientoBanco IS NOT NULL", (medio,)):
        out[int(f["mov"])].append({"tipo": "Trabajo eventual", "doc": f"{f['fecha']:%d/%m/%Y} {f['d']}", "imp": float(f["imp"])})
    return out


def _documentos(ids_compra: set) -> dict[int, dict]:
    """Descripción de cada compra aplicada y la imputación de su renglón principal."""
    if not ids_compra:
        return {}
    out = {}
    ids = sorted(ids_compra)
    for i in range(0, len(ids), 800):
        lote = ids[i:i + 800]
        for f in fetch_all(
                f"""SELECT c.IdDeuda AS id, c.[Tipo documento] AS td, c.[Nro Documento] AS nro, c.Fecha AS fecha, co.[Razon Social] AS prov,
                       r.Rubro AS rubro, cc.[Centro de costos] AS cc, de.Destino AS destino
                FROM dbo.Compras c LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
                OUTER APPLY (SELECT TOP 1 d.IdRubro, d.IdCentroCostos, d.IdDestino FROM dbo.Det_Compras d WHERE d.IdCompra = c.IdDeuda
                             ORDER BY ABS(ISNULL(d.Cantidad, 0) * ISNULL(d.[Precio Unitario], 0)) DESC) p
                LEFT JOIN dbo.Rubros r ON r.IdRubro = p.IdRubro LEFT JOIN dbo.[Centro de costos] cc ON cc.IdCentro = p.IdCentroCostos
                LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = p.IdDestino
                WHERE c.IdDeuda IN ({','.join('?' * len(lote))})""", tuple(lote)):
            out[int(f["id"])] = f
    return out


def _texto_doc(a: dict, docs: dict) -> str:
    if a["tipo"] == "CompraDeuda" and a["doc"] in docs:
        d = docs[a["doc"]]
        return f"{d['td'] or 'Factura'} {d['nro'] or ''} ({d['prov'] or ''})".replace("  ", " ")
    if a["tipo"] in ("Sueldo", "Trabajo eventual"):
        return f"{a['tipo']} {a['doc']}"
    return {"VentaHacienda": "Venta de hacienda", "VentaGranos": "Venta de granos", "Pastaje": "Pastaje"}.get(a["tipo"], a["tipo"] or "Documento") + f" #{a['doc']}"


def filas(medio: str) -> list[list]:
    from src.features.conciliacion_tesoreria import repository as conc
    from src.features.tesoreria import estado_resolucion

    movs, apls = _movimientos(medio), _aplicaciones(medio)
    for k, v in _otros_pagos(medio).items():
        apls[k] += v
    docs = _documentos({a["doc"] for l in apls.values() for a in l if a["tipo"] == "CompraDeuda"})
    motivos = {int(e["m"]): e["d"] for e in fetch_all(
        "SELECT e.IdMovimiento AS m, e.Detalle AS d FROM dbo.ConciliacionesTesoreriaEstado e WHERE e.Medio = ? AND e.IdEstado = "
        "(SELECT MAX(x.IdEstado) FROM dbo.ConciliacionesTesoreriaEstado x WHERE x.Medio = e.Medio AND x.IdMovimiento = e.IdMovimiento)", (medio,))}
    out = []
    for m in movs:
        importe = float(m["debito"] or 0) or float(m["credito"] or 0)
        lista = apls.get(int(m["id"]), [])
        aplicado = round(sum(a["imp"] for a in lista), 2)
        if lista and abs(aplicado - importe) <= 1:
            estado = "Conciliado"
        elif lista:
            estado = "Parcial"
        else:
            try:
                clave = estado_resolucion.esta_resuelto(medio, int(m["id"])) if medio in conc.MEDIOS_SOPORTADOS else "sin_conciliar"
            except Exception:  # noqa: BLE001
                clave = "sin_conciliar"
            estado = ESTADOS.get(clave, clave)
            if clave in ("ya_reconocido", "sin_conciliar") and _INVERSION.search(m["descripcion"] or ""):
                estado = "Inversión (FIMA / plazo fijo)"
            elif clave in ("ya_reconocido", "sin_conciliar") and not m["contacto"] and _BANCARIO.search(m["descripcion"] or ""):
                estado = "Impuesto o gasto bancario"
            elif clave == "ya_reconocido":
                estado = "Reconocido (sin documento aplicado)" if m["contacto"] else "Impuesto o gasto bancario"
        principal = next((docs[a["doc"]] for a in sorted(lista, key=lambda a: -a["imp"]) if a["tipo"] == "CompraDeuda" and a["doc"] in docs), None)
        fecha = m["fecha"].date() if isinstance(m["fecha"], datetime) else             date.fromisoformat(str(m["fecha"])[:10]) if m["fecha"] else None
        out.append([fecha, (m["descripcion"] or "").strip(), m["comprobante"], float(m["debito"] or 0) or None, float(m["credito"] or 0) or None,
                    m["contacto"] or (m["leyenda"] or None), estado,
                    "; ".join(f"{_texto_doc(a, docs)}: {a['imp']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for a in lista) or None,
                    aplicado or None, round(importe - aplicado, 2) if lista and abs(importe - aplicado) > 1 else None,
                    (principal or {}).get("rubro"), (principal or {}).get("cc"), (principal or {}).get("destino"),
                    motivos.get(int(m["id"]))])
    return out


COLUMNAS = [("Fecha", 11), ("Descripción", 38), ("Comprobante", 14), ("Débito", 15), ("Crédito", 15), ("Contacto", 32),
            ("Estado", 24), ("Documentos aplicados", 60), ("Importe aplicado", 15), ("Sin aplicar", 13), ("Rubro", 22),
            ("Centro de costos", 18), ("Destino", 18), ("Observación", 50)]


def planilla(medio: str) -> bytes:
    datos = filas(medio)
    wb = Workbook()
    ws = wb.active
    ws.title = "Movimientos"
    ws.append([f"Conciliación {NOMBRE[medio]} — Giamigli de Bolívar S.A. — generada el {datetime.now():%d/%m/%Y %H:%M} desde el sistema"])
    ws["A1"].font = Font(bold=True, size=12, color=_VERDE)
    ws.append([c for c, _ in COLUMNAS])
    for i, (_, ancho) in enumerate(COLUMNAS, start=1):
        celda = ws.cell(row=2, column=i)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=_VERDE)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = ancho
    for f in datos:
        ws.append(f)
    for fila in ws.iter_rows(min_row=3, max_row=ws.max_row):
        fila[0].number_format = "dd/mm/yyyy"
        for k in (3, 4, 8, 9):
            fila[k].number_format = _PESOS
    ws.freeze_panes = "B3"
    ws.auto_filter.ref = f"A2:{get_column_letter(len(COLUMNAS))}{ws.max_row}"
    # Resumen por estado y por año
    rs = wb.create_sheet("Resumen")
    rs.append(["Estado", "Movimientos", "Débitos", "Créditos"])
    tot: dict[str, list] = defaultdict(lambda: [0, 0.0, 0.0])
    for f in datos:
        t = tot[f[6]]
        t[0] += 1; t[1] += f[3] or 0; t[2] += f[4] or 0
    for k, (n, d, c) in sorted(tot.items(), key=lambda x: -x[1][0]):
        rs.append([k, n, round(d, 2), round(c, 2)])
    for c in rs[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor=_VERDE)
    for fila in rs.iter_rows(min_row=2):
        fila[2].number_format = fila[3].number_format = _PESOS
    rs.column_dimensions["A"].width = 36
    for col in "BCD":
        rs.column_dimensions[col].width = 16
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _guardar(destino: Path, contenido: bytes, nombre: str) -> dict:
    """Guarda la planilla en Dropbox; la anterior queda copiada en backups (una copia por día)."""
    COPIAS.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        copia = COPIAS / f"{destino.stem}_{date.today():%Y%m%d}{destino.suffix}"
        if not copia.exists():
            shutil.copy2(destino, copia)
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        destino.write_bytes(contenido)
        return {"banco": nombre, "archivo": str(destino), "ok": True}
    except PermissionError:
        return {"banco": nombre, "archivo": str(destino), "ok": False, "detalle": "la planilla está abierta; cerrala y volvé a actualizar"}


def actualizar_dropbox(medios: tuple[str, ...] = ("galicia", "bna", "mercado-libre")) -> list[dict]:
    """Regenera las planillas de bancos del Estudio en Dropbox."""
    return [_guardar(DESTINOS[m], planilla(m), NOMBRE[m]) for m in medios]


def estado() -> list[dict]:
    """Cuándo se actualizó por última vez cada planilla del Estudio."""
    out = []
    for medio, destino in DESTINOS.items():
        m = datetime.fromtimestamp(destino.stat().st_mtime).isoformat(timespec="minutes") if destino.exists() else None
        out.append({"banco": NOMBRE[medio], "archivo": destino.name, "carpeta": destino.parent.name, "actualizada": m})
    return out
