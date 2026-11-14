"""Activación del esquema nuevo de imputación (050 T032, research R-01).

--dry-run  (no escribe nada) arma el Excel de impacto en specs/050-tamizado-imputacion-cultivos/:
    · Candidatos: renglones de insumo ya cargados que entrarían como StockSinImputar (sin imputación útil,
      sin corrida aprobada y con saldo en stock en una capa vinculada a ese renglón).
    · Tamiz: cómo clasificaría el tamiz cada renglón de las compras desde el 01/07/2025.
    · Costos: costo por cultivo/campaña de hoy (2025/2026 en adelante) para comparar después de aplicar.
--aplicar  exige el OK de Sergio sobre ese Excel: backup verificado, fija IdDeudaCorte = MAX(IdDeuda) actual,
    marca los StockSinImputar, los tamiza y pone Activo = 1. Solo WC.

Uso (desde backend/):  python -m scripts.activar_alcance_050 --dry-run
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, fetch_one
from src.features.imputacion import tamiz
from src.features.remitos.stock_datos import calcular_stock
from src.features.resultado_cultivo import costos

SALIDA = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos"
CAMPANIA_NO_APLICA = 20
DESDE_TAMIZ = "2025-07-01"


def candidatos_stock_sin_imputar() -> list[dict]:
    filas = fetch_all(
        """
        SELECT d.IdDetalleCompra AS idDetalleCompra, d.IdCompra AS idCompra, c.Fecha AS fecha, co.[Razon Social] AS proveedor,
               c.[Nro Documento] AS nro, d.[Producto/Servicio] AS producto, d.IdFormulado AS idProducto,
               d.Cantidad AS cantidad, de.Destino AS destino, ca.[Campaña] AS campania
        FROM dbo.Det_Compras d
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.TamizRubroDestino tr ON tr.IdRubro = d.IdRubro AND tr.Destino = 'CultivoStock' AND tr.ReglaDepende IS NULL
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        LEFT JOIN dbo.[Campañas] ca ON ca.[IdCampaña] = d.[IdCampaña]
        WHERE NULLIF(d.IdFormulado, 0) IS NOT NULL AND c.Fecha >= '2015-09-01'
          AND (de.IdCultivo IS NULL OR d.[IdCampaña] IS NULL OR d.[IdCampaña] = ?)
          AND NOT EXISTS (SELECT 1 FROM dbo.ImputacionPropuestas p WHERE p.IdDetalleCompra = d.IdDetalleCompra
                          AND p.Origen <> 'Contratista' AND p.Estado = 'Aprobada' AND p.IdCultivo IS NOT NULL)
          AND EXISTS (SELECT 1 FROM dbo.tblRemitoCompra t WHERE t.IdDetalleCompra = d.IdDetalleCompra)
        """,
        (CAMPANIA_NO_APLICA,),
    )
    vinculos: dict[int, list[dict]] = {}
    for v in fetch_all("SELECT IdDetalleCompra AS dc, IdDetalleRemito AS dr, CantidadRemitida AS cant FROM dbo.tblRemitoCompra"):
        vinculos.setdefault(v["dc"], []).append(v)
    stock_cache: dict[int, dict] = {}
    out = []
    for f in filas:
        pid = f["idProducto"]
        if pid not in stock_cache:
            stock_cache[pid] = {c["id"]: c for c in calcular_stock(pid).get(pid, {}).get("capas", [])}
        capas = stock_cache[pid]
        restante = valor = 0.0
        for v in vinculos.get(f["idDetalleCompra"], []):
            capa = capas.get(f"R{v['dr']}")
            if not capa or not capa["cantidad"]:
                continue
            peso = float(v["cant"] or 0) / float(capa["cantidad"])
            r = float(capa["restante"] or 0) * peso
            restante += r
            valor += r * float(capa["costoUnitario"] or 0)
        if restante > 1e-6:
            out.append({**f, "enStock": round(restante, 3), "valorStock": round(valor, 2)})
    return out


def _hoja(wb, titulo, columnas, filas):
    ws = wb.create_sheet(titulo)
    ws.append(columnas)
    for c in ws[1]:
        c.font = Font(bold=True)
    for f in filas:
        ws.append(f)
    return ws


def dry_run() -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    cand = candidatos_stock_sin_imputar()
    _hoja(wb, "Candidatos stock sin imputar",
          ["Fecha", "Proveedor", "Nro documento", "Producto", "Cantidad", "Destino cargado", "Campaña cargada",
           "Queda en stock", "Valor en stock $"],
          [[f["fecha"], f["proveedor"], f["nro"], f["producto"], f["cantidad"], f["destino"], f["campania"],
            f["enStock"], f["valorStock"]] for f in cand])

    etiquetas = tamiz.ETIQUETAS
    filas_tamiz = []
    for c in fetch_all(
        "SELECT c.IdDeuda AS id, c.Fecha AS fecha, co.[Razon Social] AS proveedor, c.[Nro Documento] AS nro "
        "FROM dbo.Compras c LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto WHERE c.Fecha >= ? ORDER BY c.Fecha",
        (DESDE_TAMIZ,),
    ):
        renglones = {r["idDetalleCompra"]: r for r in tamiz.repo.renglones_de_compra(c["id"])}
        for k in tamiz.tamizar_compra(c["id"], guardar=False, forzar=True):
            r = renglones.get(k["idDetalleCompra"], {})
            filas_tamiz.append([c["fecha"], c["proveedor"], c["nro"], r.get("producto"),
                                etiquetas.get(k["destino"], "Para revisar") if k["estado"] == "Aprobada" else "Para revisar",
                                k["estado"], k["motivo"]])
    _hoja(wb, "Tamiz desde 2025-26", ["Fecha", "Proveedor", "Nro documento", "Renglón", "Destino", "Estado", "Motivo"], filas_tamiz)

    filas_costos = []
    for cc in fetch_all(
        "SELECT DISTINCT d.IdCultivo AS cu, d.IdCampania AS ca, cu.Cultivo AS cultivo, ca.[Campaña] AS campania "
        "FROM dbo.Ordenes_Trabajo_Distrib d JOIN dbo.Cultivos cu ON cu.IdCultivo = d.IdCultivo "
        "JOIN dbo.[Campañas] ca ON ca.[IdCampaña] = d.IdCampania WHERE ca.[Campaña] >= '2025/2026' AND ca.[Campaña] LIKE '%/%'"
    ):
        t = costos.costo_total(cc["cu"], cc["ca"])
        filas_costos.append([cc["campania"], cc["cultivo"], t["pesos"], t["dolares"]])
    _hoja(wb, "Costos hoy", ["Campaña", "Cultivo", "Costo $ (hoy)", "Costo US$ (hoy)"], sorted(filas_costos))

    destino = SALIDA / f"impacto-activacion-{date.today():%Y%m%d}.xlsx"
    wb.save(destino)
    print(f"Candidatos: {len(cand)} (valor en stock ${sum(f['valorStock'] for f in cand):,.2f}) · "
          f"renglones tamizados: {len(filas_tamiz)} · cultivos/campaña: {len(filas_costos)}")
    print("Excel:", destino)
    return destino


def aplicar() -> None:
    from src.features.vinculos.backup import backup_verificado

    _assert_target_is_wc()
    if fetch_one("SELECT Activo AS a FROM dbo.ImputacionConfig WHERE Id = 1")["a"]:
        raise SystemExit("El esquema ya está activo.")
    print("Backup:", backup_verificado("pre_activar_050"))
    corte = fetch_one("SELECT MAX(IdDeuda) AS m FROM dbo.Compras")["m"]
    cand = candidatos_stock_sin_imputar()
    stmts = [("UPDATE dbo.ImputacionConfig SET IdDeudaCorte = ?, FechaActivacion = SYSDATETIME() WHERE Id = 1", (corte,))]
    stmts += [("IF NOT EXISTS (SELECT 1 FROM dbo.ImputacionAlcance WHERE IdDetalleCompra = ?) "
               "INSERT dbo.ImputacionAlcance (IdDetalleCompra, Motivo) VALUES (?, 'StockSinImputar')",
               (f["idDetalleCompra"], f["idDetalleCompra"])) for f in cand]
    execute_write_transaction(stmts)
    for id_compra in sorted({f["idCompra"] for f in cand}):
        tamiz.tamizar_al_guardar(id_compra)
    execute_write_transaction([("UPDATE dbo.ImputacionConfig SET Activo = 1 WHERE Id = 1", ())])
    print(f"Activado: corte IdDeuda {corte}, {len(cand)} renglones StockSinImputar.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    dry_run() if a.dry_run else aplicar()
