"""Carga un resumen de Visa Galicia desde su PDF (los que todavía no están en WC).

Primer uso (2026-10-09): resumen VI00000000007822346, cierre 01/10/2026, con el cargo de Pintería España
(MERPAGO*PINTESPANA $404.306 del 27/08) y otros 8 consumos. Idempotente: si el código del resumen ya existe,
no hace nada. El contacto de cada línea sale de una tabla explícita (mismo comercio que en resúmenes previos);
las líneas ambiguas quedan SIN contacto para vincular a mano, nunca se adivinan.

Uso (desde backend/):  python -m scripts.cargar_resumen_visa_galicia_pdf [--aplicar]
"""

from __future__ import annotations

import re
import sys
from datetime import datetime

import pdfplumber

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all

PDF = r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Bancos\Galicia\Tarjetas\Visa\2026\Resumen_Tarjetas_Galicia_2026_10_01.pdf"
ID_TARJETA = 4  # Visa Galicia

# Fragmento del texto de la línea -> contacto (confirmado contra líneas de resúmenes ya cargados y facturas pendientes).
CONTACTOS = [
    ("PINTESPANA", 3654),
    ("WAGEN", 636),
    ("Starlink", 567),
    ("CAMINO PQUE", 314),
    ("AUTOPISTA DEL OE", 306),
    ("RUTAS SUR", 2657),
    ("TELEPEAJE", 328),
    ("MARGENES", 346),
]
# "AUTOPISTAS DEL S" por importe: sólo hay una factura pendiente que cierra con el primero; el segundo no tiene
# factura candidata y en resúmenes previos aparece tanto con Autopistas del Sol como con YPF Acceso Oeste -> queda sin contacto.
CONTACTO_POR_IMPORTE = {("AUTOPISTAS DEL S", 14263.23): 276}

LINEA = re.compile(r"^(\d\d-\d\d-\d\d) [*K] (.+?)\s+([\d.]+,\d\d)$")
CUOTA_COMPROBANTE = re.compile(r"\s+(\d{2}/\d{2})?\s*\d{6}$")


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def leer_pdf() -> dict:
    with pdfplumber.open(PDF) as d:
        paginas = [(p.extract_text() or "") for p in d.pages]
    t = "\n".join(paginas)
    codigo = re.search(r"Resumen N\S+\s+(VI\d+)", t).group(1)
    fechas = re.search(r"(\d\d-\w{3}-\d\d) (\d\d-\w{3}-\d\d) (\d\d-\w{3}-\d\d) (\d\d-\w{3}-\d\d)", t)
    meses = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}

    def f(s):
        dd, mm, yy = s.split("-")
        return datetime(2000 + int(yy), meses[mm], int(dd))

    cierre, vencimiento = f(fechas.group(3)), f(fechas.group(4))
    lineas = []
    for linea in t.splitlines():
        m = LINEA.match(linea.strip())
        if not m or "TARJETA" in linea:
            continue
        fecha = datetime.strptime(m.group(1), "%d-%m-%y")
        resto = m.group(2)
        # sacamos cuota/comprobante del final del texto, igual que el Excel del banco (que sólo trae el comercio y su referencia)
        cuota = re.search(r"\s(\d{2}/\d{2})\s+\d{6}$", resto)
        detalle = CUOTA_COMPROBANTE.sub("", resto).strip()
        detalle = re.sub(r"\s+\d{6}$", "", detalle)
        lineas.append({"fechaCompra": fecha, "detalle": detalle[:255], "importe": _num(m.group(3)), "cuota": cuota.group(1) if cuota else None})

    def tomar(patron):
        m = re.search(patron, t)
        return _num(m.group(1)) if m else 0.0

    cargos = {
        "ImpuestoSellos": tomar(r"IMPUESTO DE SELLOS \$ ([\d.]+,\d\d)"),
        "MantCuenta": tomar(r"COMISI\S+ MANT DE CTA\. ([\d.]+,\d\d)"),
        "IVA21": tomar(r"DB IVA \$ RESP INSC\. 21% [\d.]+,\d\d ([\d.]+,\d\d)"),
        "PercepIVA21": tomar(r"PERCEP\.IVA RG2408 [\d,.%]+ B\. [\d.,]+ ([\d.]+,\d\d)"),
    }
    total_pagar = tomar(r"TOTAL A PAGAR ([\d.]+,\d\d)")
    return {"codigo": codigo, "cierre": cierre, "vencimiento": vencimiento, "lineas": lineas, "cargos": cargos, "totalPagar": total_pagar}


def contacto_de(l: dict) -> int | None:
    for frag, c in CONTACTOS:
        if frag.lower() in l["detalle"].lower():
            return c
    for (frag, imp), c in CONTACTO_POR_IMPORTE.items():
        if frag.lower() in l["detalle"].lower() and abs(l["importe"] - imp) < .005:
            return c
    return None


def main(aplicar: bool) -> None:
    _assert_target_is_wc()
    r = leer_pdf()
    ya = fetch_all("SELECT IdResumen FROM dbo.Tarjetas_Resumenes WHERE IdTarjeta = ? AND ResumenCodigo = ?", (ID_TARJETA, r["codigo"]))
    consumos = round(sum(l["importe"] for l in r["lineas"]), 2)
    total = round(consumos + sum(r["cargos"].values()), 2)
    print(f"Resumen {r['codigo']} · cierre {r['cierre']:%d/%m/%Y} · vence {r['vencimiento']:%d/%m/%Y} · {len(r['lineas'])} líneas")
    for l in r["lineas"]:
        print(f"  {l['fechaCompra']:%d/%m/%Y} {l['importe']:>12,.2f}  {l['detalle'][:42]:42} {l['cuota'] or '':5} -> contacto {contacto_de(l)}")
    print(f"Consumos {consumos:,.2f} · cargos {r['cargos']} · total {total:,.2f} · el PDF dice {r['totalPagar']:,.2f}")
    if abs(total - r["totalPagar"]) > .05:
        raise SystemExit("El total calculado no coincide con el del PDF: no se carga.")
    if ya:
        print("Ese resumen ya está cargado: nada que hacer.")
        return
    if not aplicar:
        print("Simulación: no se escribió nada. Usar --aplicar para grabar (con respaldo).")
        return
    from src.features.vinculos.backup import backup_verificado
    print(f"Respaldo verificado: {backup_verificado('cargar-resumen-visa-galicia-20261001')}")
    cols = list(r["cargos"].keys())
    valores = [ID_TARJETA, r["codigo"], r["cierre"], r["vencimiento"], "Cargado", None, f"Importado desde PDF el {datetime.now():%Y-%m-%d}"] + [r["cargos"][c] for c in cols]
    sql = (f"INSERT INTO dbo.Tarjetas_Resumenes (IdTarjeta, ResumenCodigo, FechaCierre, FechaVencimiento, EstadoResumen, SoloCabecera, Observaciones, ArchivoOrigen, {', '.join(cols)}) "
           f"OUTPUT INSERTED.IdResumen VALUES (?, ?, ?, ?, ?, ?, ?, ?, {', '.join('?' for _ in cols)})")
    valores.insert(7, PDF)
    stmts: list = [(sql, tuple(valores))]
    for l in r["lineas"]:
        stmts.append(lambda res, l=l: (
            "INSERT INTO dbo.Tarjetas_Resumenes_Lineas (IdResumen, FechaCompra, Detalle, Importe, IdContacto, NroDocumento) VALUES (?, ?, ?, ?, ?, ?)",
            (res[0], l["fechaCompra"], l["detalle"], l["importe"], contacto_de(l), None)))
    execute_write_transaction(stmts)
    print("Resumen cargado.")


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
