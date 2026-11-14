"""Simulación histórica: motor nuevo (tamiz + imputación progresiva) contra la imputación manual (050).

No escribe nada en la base. Recorre todas las compras desde el 01/09/2015 y, para cada renglón, compara:
  · Manual: lo cargado en el renglón (destino → cultivo, campaña, centro de costos).
  · Motor:  - renglones de una sola vez: la clasificación del tamiz (destino, cultivo, campaña);
            - insumos de stock: el reparto por uso de las órdenes (FIFO por remito vinculado) más lo que
              queda en stock, comparado en pesos contra el cultivo/campaña cargado a mano.
Resultado: Excel en specs/050-tamizado-imputacion-cultivos/ con resumen y detalle de diferencias.

Uso (desde backend/):  python -m scripts.simulacion_historica_050
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from src.db.connection import fetch_all
from src.features.imputacion import aprendizaje, motor, tamiz
from src.features.remitos import stock_datos

SALIDA = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos"
DESDE = "2015-09-01"
NO_APLICA = 20
CENTRO = {1: "Agricultura", 2: "Ganaderia", 3: "Adm. General", 4: "Maquinaria", 5: "SIP"}

# calcular_stock por producto es caro y el motor lo pide por renglón: se memoriza (solo lectura).
_stock_original = stock_datos.calcular_stock
motor.calcular_stock = lru_cache(maxsize=None)(lambda pid=None, excluir_remito=None: _stock_original(pid, excluir_remito))


def _manual(r: dict) -> dict:
    cultivo = r["idCultivoDestino"]
    campania = r["idCampania"] if r["idCampania"] not in (None, NO_APLICA) else None
    centro = r["idCentro"]
    if cultivo and campania:
        cat = "Cultivo"
    elif centro == 2:
        cat = "Ganaderia"
    elif cultivo or (r["destino"] or "").startswith(("Cultivo", "Verdeo")):
        cat = "Cultivo sin campaña" if cultivo else "Cultivo genérico"
    else:
        cat = "Estructura"
    return {"cat": cat, "cultivo": cultivo, "campania": campania}


def _motor_cat(destino: str | None) -> str:
    return {"Cultivo": "Cultivo", "Ganaderia": "Ganaderia", "Estructura": "Estructura", "Financiero": "Financiero",
            "NoImputa": "No se imputa", "CultivoStock": "Stock/uso"}.get(destino, "Para revisar")


def main() -> None:
    renglones = fetch_all(
        """
        SELECT d.IdDetalleCompra AS id, d.IdCompra AS idCompra, c.Fecha AS fecha, co.[Razon Social] AS proveedor,
               c.[Tipo documento] AS tipo, c.[Nro Documento] AS nro, d.[Producto/Servicio] AS producto,
               r.Rubro AS rubro, d.IdRubro AS idRubro, de.Destino AS destino, de.IdCultivo AS idCultivoDestino, d.[IdCampaña] AS idCampania,
               d.IdCentroCostos AS idCentro, ISNULL(d.Cantidad, 0) * ISNULL(d.[Precio Unitario], 0) *
               CASE WHEN c.Moneda = 'Dolares' THEN ISNULL(c.[Tipo de Cambio], 0) ELSE 1 END AS pesos
        FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.Rubros r ON r.IdRubro = d.IdRubro
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        WHERE c.Fecha >= ?
        """,
        (DESDE,),
    )
    por_compra: dict[int, list[dict]] = defaultdict(list)
    for r in renglones:
        por_compra[r["idCompra"]].append(r)
    cultivos = {f["IdCultivo"]: f["Cultivo"] for f in fetch_all("SELECT IdCultivo, Cultivo FROM dbo.Cultivos")}
    campanias = {f["IdCampaña"]: f["Campaña"] for f in fetch_all("SELECT [IdCampaña], [Campaña] FROM dbo.[Campañas]")}
    con_remito = {f["id"] for f in fetch_all("SELECT DISTINCT IdDetalleCompra AS id FROM dbo.tblRemitoCompra")}

    resumen: Counter = Counter()
    pesos: Counter = Counter()
    detalle = []
    # Aprendizaje sin mirar el futuro: cada compra se predice con la historia anterior y después se aprende.
    modelo = aprendizaje.Modelo()
    orden = sorted(por_compra, key=lambda i: (por_compra[i][0]["fecha"], i))
    for id_compra in orden:
        filas = por_compra[id_compra]
        clasif = {c["idDetalleCompra"]: c for c in tamiz.tamizar_compra(id_compra, guardar=False, forzar=True, modelo=modelo)}
        for r in filas:
            modelo.observar(r["idRubro"], tamiz.normalizar(r["producto"]), r["idCultivoDestino"], r["idCampania"], r["idCentro"])
        for r in filas:
            m = _manual(r)
            t = clasif.get(r["id"], {})
            mc = _motor_cat(t.get("destino")) if t.get("estado") == "Aprobada" else "Para revisar"
            importe = round(float(r["pesos"] or 0), 2)
            if t.get("destino") == "CultivoStock" and t.get("estado") == "Aprobada":
                grupo = "Insumo de stock"
                if r["id"] not in con_remito:
                    res, nota = "Sin remito vinculado (no se puede simular el uso)", None
                else:
                    fr = motor.calcular_propuesta_insumo(r["id"])
                    mismo = sum(f["importe"] for f in fr if f.get("idCultivo") == m["cultivo"] and f.get("idCampania") == m["campania"])
                    otro = sum(f["importe"] for f in fr if f.get("idCultivo") and not (f.get("idCultivo") == m["cultivo"] and f.get("idCampania") == m["campania"]))
                    stock = sum(f["importe"] for f in fr if f.get("esStock"))
                    resto = sum(f["importe"] for f in fr) - mismo - otro - stock
                    if m["cat"] == "Cultivo" and abs(otro) + abs(stock) + abs(resto) < 0.01 and abs(mismo - importe) < 0.01:
                        res = "Igual"
                    elif m["cat"] == "Cultivo" and abs(otro) + abs(stock) + abs(resto) < 0.01:
                        res = "Mismo cultivo/campaña, distinto importe"
                    else:
                        res = "Distinto"
                    usos = defaultdict(float)
                    for f in fr:
                        clave = "en stock" if f.get("esStock") else (
                            f"{cultivos.get(f.get('idCultivo'), '?')} {campanias.get(f.get('idCampania'), '')}".strip()
                            if f.get("idCultivo") else ("Ganadería" if f.get("esGanaderia") else "otro destino"))
                        usos[clave] += f["importe"]
                    nota = " · ".join(f"{k}: {v:,.2f}" for k, v in usos.items()) or "sin consumo ni stock"
            else:
                grupo = "Una sola vez"
                nota = t.get("motivo")
                if mc == "Para revisar":
                    res = "Motor: para revisar"
                elif mc == "No se imputa":
                    res = "Igual" if m["cat"] == "Estructura" else "Distinto"
                elif mc == m["cat"] and (mc != "Cultivo" or (t.get("idCultivo") == m["cultivo"] and t.get("idCampania") == m["campania"])):
                    res = "Igual"
                elif mc == "Financiero" and m["cat"] == "Estructura":
                    res = "Financiero (manual: gasto general)"
                else:
                    res = "Distinto"
            resumen[(grupo, res)] += 1
            pesos[(grupo, res)] += importe
            if res != "Igual":
                detalle.append([grupo, res, r["fecha"], r["proveedor"], r["tipo"], r["nro"], r["producto"], r["rubro"],
                                m["cat"], cultivos.get(m["cultivo"]) or r["destino"], campanias.get(m["campania"]),
                                mc, cultivos.get(t.get("idCultivo")), campanias.get(t.get("idCampania")), importe, nota])

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Grupo", "Resultado", "Renglones", "Importe $"])
    for (g, res), n in sorted(resumen.items()):
        ws.append([g, res, n, round(pesos[(g, res)], 2)])
    ws2 = wb.create_sheet("Diferencias")
    ws2.append(["Grupo", "Resultado", "Fecha", "Proveedor", "Tipo", "Nro", "Renglón", "Rubro", "Manual", "Manual cultivo/destino",
                "Manual campaña", "Motor", "Motor cultivo", "Motor campaña", "Importe $", "Detalle / motivo"])
    for f in detalle:
        ws2.append(f)
    for w in (ws, ws2):
        for c in w[1]:
            c.font = Font(bold=True)
    destino = SALIDA / f"simulacion-historica-{date.today():%Y%m%d}.xlsx"
    wb.save(destino)
    for (g, res), n in sorted(resumen.items()):
        print(f"{g:16} {res:55} {n:6}  ${pesos[(g, res)]:>18,.2f}")
    print("Excel:", destino)


if __name__ == "__main__":
    main()
