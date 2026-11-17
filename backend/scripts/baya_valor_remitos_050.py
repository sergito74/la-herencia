"""050 (17/11/2026): trae de la extranet de Bayá Casal (Insumos → remitida pendiente de facturar) el precio en US$ y el
TC de cada artículo de los remitos sin factura y lo guarda en dbo.RemitoValorProveedor, para valorizar el remito
hasta que llegue la factura. Quita los precios de remitos que ya no están pendientes (llegó la factura).
Solo lectura en el portal (autorización permanente del 20/10/2026, portal 5). Re-corrible.
Uso (desde backend/): python -m scripts.baya_valor_remitos_050 [--sin-portal <merpenfac.json>]
"""
from __future__ import annotations

import difflib
import json
import sys
from datetime import date

from src.db.connection import execute_write_transaction, fetch_all

PORTAL = 5
FUENTE = "Bayá Casal portal"


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", ".")) if s else 0.0


def bajar_pendientes() -> list[list[str]]:
    from playwright.sync_api import sync_playwright

    from scripts.baya_remitos_bajar_050 import bajar
    from src.features.boveda import repository, servicio
    from src.features.boveda.conectores.baya_casal import ConectorBayaCasal

    if repository.autorizacion_vigente(PORTAL) is None:
        raise SystemExit("Sin autorización vigente para Bayá Casal.")
    cred = servicio.credencial_de(fetch_all("SELECT IdCredencial AS c FROM dbo.Portales WHERE IdPortal = ?", (PORTAL,))[0]["c"])
    with sync_playwright() as pw:
        s = ConectorBayaCasal().ingresar(pw, cred)
        try:
            # lo pendiente de facturar no depende de la fecha: una sola consulta
            return bajar(s.pagina, "merpenfac", f"{date.today().year - 3}-01-01", f"{date.today():%Y-%m-%d}")
        finally:
            s.browser.close()


def emparejar(filas: list[list[str]]) -> tuple[list[tuple], list[str]]:
    """Cada artículo del portal con su renglón de remito: mismo remito, misma cantidad y el nombre más parecido."""
    asignados, avisos, usados = [], [], set()
    for f in filas:
        if len(f) < 9 or not f[0].isdigit():
            continue
        remito, articulo, cantidad, tc, precio = f[0], f[3], _num(f[4]), _num(f[6]), _num(f[7])
        cands = fetch_all(
            "SELECT rd.IdDetalleRemito AS id, rd.Cantidad AS q, p.Producto AS producto FROM dbo.Remitos r "
            "JOIN dbo.Remitos_Detalles rd ON rd.IdRemito = r.IdRemito LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = rd.IdFormulado "
            "WHERE r.IdProveedor = 226 AND r.NroRemito LIKE ?", (f"%{int(remito):08d}",))
        if not cands:
            avisos.append(f"Remito 0043-{int(remito):08d} ({articulo}, {cantidad:g}) no está cargado en el sistema")
            continue
        mismos = [c for c in cands if abs(float(c["q"] or 0) - cantidad) <= 0.01 and c["id"] not in usados]
        if len(mismos) > 1:
            mismos.sort(key=lambda c: -difflib.SequenceMatcher(None, (c["producto"] or "").upper(), articulo.upper()).ratio())
        if not mismos:
            avisos.append(f"Remito 0043-{int(remito):08d}: no encontré el renglón de {articulo} ({cantidad:g})")
            continue
        usados.add(mismos[0]["id"])
        asignados.append((mismos[0]["id"], articulo, cantidad, precio, tc))
    return asignados, avisos


def guardar(asignados: list[tuple]) -> None:
    ids = [a[0] for a in asignados]
    stmts = [("DELETE FROM dbo.RemitoValorProveedor WHERE Fuente = ?" + (f" AND IdDetalleRemito NOT IN ({','.join('?' * len(ids))})" if ids else ""),
              (FUENTE, *ids))]
    for a in asignados:
        stmts.append(("UPDATE dbo.RemitoValorProveedor SET Articulo = ?, Cantidad = ?, PrecioUSD = ?, TipoCambio = ?, FechaConsulta = SYSDATETIME() "
                      "WHERE IdDetalleRemito = ?", (a[1], a[2], a[3], a[4], a[0])))
        stmts.append(("INSERT INTO dbo.RemitoValorProveedor (IdDetalleRemito, Fuente, Articulo, Cantidad, PrecioUSD, TipoCambio) "
                      "SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM dbo.RemitoValorProveedor WHERE IdDetalleRemito = ?)",
                      (a[0], FUENTE, a[1], a[2], a[3], a[4], a[0])))
    execute_write_transaction(stmts)


def main() -> dict:
    filas = json.load(open(sys.argv[2], encoding="utf-8")) if "--sin-portal" in sys.argv else bajar_pendientes()
    asignados, avisos = emparejar(filas)
    guardar(asignados)
    return {"valorizados": len(asignados), "avisos": avisos}


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=1))
