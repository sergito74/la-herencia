"""Semilla facturada por Yanquelen que nunca entró al stock (aprobado por Sergio 24/11/2026).

Yanquelen factura la semilla escondida en labores ("Disco", "Fertilización"); en el sistema esas facturas están desglosadas
en kg de semilla, pero no había remito de entrada ni semilla en la orden de siembra, así que el costo no llegaba al cultivo.
Para cada caso: remito «SIN REMITO» de Yanquelen (fecha = la siembra) vinculado al renglón de la factura, y la semilla en la
orden de siembra repartida por superficie entre los lotes de la orden.

  · Avena 2020: 4.800 kg CALEN INTA (genérico avena)  ↔ FC 0002-00000012     → orden 49 (heredada #51), 25/03/2020
  · Avena 2021: 4.370 kg CALEN INTA                    ↔ FC 00002-00000015    → orden 70 (#72), 24/03/2021 (lotes 3A, 8B)
  · Soja 1ª 2022/23: 6.200 kg DON MARIO 40R16          ↔ FC 00002-00000025    → orden 100 (#104), 21/11/2022
  · Maíz diferido 2022/23: 633 kg MAIZ BETITO          ↔ FC 00002-00000025 (resto de 900) → orden 105 (#109) pasa de 267 a 900 kg
  · Maíz diferido 2023/24: 880 kg MAIZ BETITO          ↔ FC 00002-00000028    → orden de siembra NUEVA, 23/11/2023, Yanquelen,
    lotes de maíz diferido de la fertilización 120 (#124): 10A1 24,3 ha + 9A1 10 ha
Una transacción, respaldo en backups/, saldos antes = después.
Uso (desde backend/): python -m scripts.semillas_yanquelen_sin_remito_20261124 [--aplicar]
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import as_sql_datetime, execute_write_transaction, fetch_all, fetch_one  # noqa: E402
from src.features.ordenes import distribucion, formulario_retiro  # noqa: E402
from scripts.aplicar_vinculos_remitos import BACKUPS, saldos  # noqa: E402

YANQUELEN = 278
CALEN, DM40R16, BETITO = 999999004, 100016407, 999999001
SIEMBRA = 3

# (fecha, producto, kg, IdDetalleCompra, cantidad en unidad de factura, orden destino, nota)
CASOS = [
    (date(2020, 3, 25), CALEN, 4800.0, 2141370545, 4800.0, 49, "Avena 2020 (FC 0002-00000012)"),
    (date(2021, 3, 24), CALEN, 4370.0, 2141372169, 4370.0, 70, "Avena 2021 lotes 3A y 8B (FC 00002-00000015)"),
    (date(2022, 11, 21), DM40R16, 6200.0, 2141375045, 6200.0, 100, "Soja 1ª 2022/23 (FC 00002-00000025)"),
    (date(2022, 12, 20), BETITO, 633.0, 2141375046, 633.0, 105, "Maíz diferido 2022/23, resto de los 900 kg (FC 00002-00000025)"),
    (date(2023, 11, 23), BETITO, 880.0, 2141376271, 880.0, None, "Maíz diferido 2023/24 (FC 00002-00000028)"),
]
OBS = "Semilla facturada por Yanquelen dentro de las labores; cargada en la auditoría de remitos del 24/11/2026"


def _lotes(id_orden: int, cultivo: str | None = None) -> list[dict]:
    """Lotes de la orden tomados del primer renglón de insumo (superficie, cultivo y campaña)."""
    filas = fetch_all(
        """SELECT d.IdLote idLote, d.IdCultivo idCultivo, d.IdCampania idCampania, d.Superficie superficie, cu.Cultivo cultivo
           FROM dbo.Ordenes_Trabajo_Distrib d JOIN dbo.Cultivos cu ON cu.IdCultivo = d.IdCultivo
           WHERE d.IdOrdenInsumo = (SELECT MIN(IdOrdenInsumo) FROM dbo.Ordenes_Trabajo_Insumos WHERE IdOrdenTrabajo = ?)""",
        (id_orden,))
    if cultivo:
        filas = [f for f in filas if f["cultivo"] == cultivo]
    return [{**f, "superficie": float(f["superficie"]), "dosisHa": 1.0, "aplicar": True} for f in filas]


def _reparto(total: float, lotes: list[dict]) -> list[dict]:
    sup = sum(l["superficie"] for l in lotes)
    rep = distribucion.repartir_total(total, lotes)
    return [{**d, "dosisHa": round(total / sup, 4)} for d in rep]


def main():
    aplicar = "--aplicar" in sys.argv
    for _, _, _, idc, q, _, nota in CASOS:
        f = fetch_one("SELECT dc.Cantidad q, c.IdContacto p, (SELECT ISNULL(SUM(CantidadRemitida),0) FROM dbo.tblRemitoCompra x "
                      "WHERE x.IdDetalleCompra = dc.IdDetalleCompra) v FROM dbo.Det_Compras dc JOIN dbo.Compras c ON c.IdDeuda = dc.IdCompra "
                      "WHERE dc.IdDetalleCompra = ?", (idc,))
        assert f and f["p"] == YANQUELEN, nota
        assert float(f["v"]) + q <= float(f["q"]) + 0.001, f"{nota}: el renglón quedaría vinculado de más ({f['v']} + {q} > {f['q']})"

    stmts: list = []
    resumen = []
    for fecha, prod, kg, idc, q, orden, nota in CASOS:
        i_rem = len(stmts)
        stmts.append(("INSERT INTO dbo.Remitos (Fecha, IdProveedor, NroRemito, IdContacto) OUTPUT INSERTED.IdRemito VALUES (?, ?, 'SIN REMITO', ?)",
                      (as_sql_datetime(fecha), YANQUELEN, YANQUELEN)))
        i_det = len(stmts)
        stmts.append(lambda r, i=i_rem, prod=prod, kg=kg: (
            "INSERT INTO dbo.Remitos_Detalles (IdRemito, IdFormulado, Cantidad, [Unidad Medida]) OUTPUT INSERTED.IdDetalleRemito VALUES (?, ?, ?, 'KGS')",
            (r[i], prod, kg)))
        stmts.append(lambda r, i=i_rem, nota=nota: (
            "INSERT INTO dbo.Remitos_Extra (IdRemito, Observaciones, RevisarDuplicado) VALUES (?, ?, 0)", (r[i], f"{OBS}. {nota}")))
        idcompra = fetch_one("SELECT IdCompra i, [Producto/Servicio] t FROM dbo.Det_Compras WHERE IdDetalleCompra = ?", (idc,))
        nombre = fetch_one("SELECT Producto p FROM dbo.vw_ProductosBase WHERE IdProducto = ?", (prod,))["p"]
        stmts.append(lambda r, i=i_det, idc=idc, q=q, ic=idcompra, nombre=nombre: (
            "INSERT INTO dbo.tblRemitoCompra (IdDeuda, IdDetalleRemito, IdDetalleCompra, CantidadRemitida, DescripFormuladoRemito, DescripProductoFactura) "
            "VALUES (?, ?, ?, ?, ?, ?)", (ic["i"], r[i], idc, q, nombre, ic["t"])))

        if orden == 105:  # Betito ya cargado 267 kg: el renglón pasa a 900 kg, mismo reparto por superficie
            ins = fetch_one("SELECT IdOrdenInsumo i, CantidadTotal q FROM dbo.Ordenes_Trabajo_Insumos WHERE IdOrdenTrabajo = 105 AND IdProducto = ?", (BETITO,))
            total = float(ins["q"]) + kg
            lotes = _lotes(105)
            rep = _reparto(total, lotes)
            stmts.append(("DELETE FROM dbo.Ordenes_Trabajo_Distrib WHERE IdOrdenInsumo = ?", (ins["i"],)))
            stmts.append(("UPDATE dbo.Ordenes_Trabajo_Insumos SET CantidadTotal = ? WHERE IdOrdenInsumo = ?", (total, ins["i"])))
            for d in rep:
                stmts.append(("INSERT INTO dbo.Ordenes_Trabajo_Distrib (IdOrdenInsumo, IdLote, IdCultivo, IdCampania, DosisHa, Superficie, CantidadAsignada, Aplicar) "
                              "VALUES (?, ?, ?, ?, ?, ?, ?, 1)", (ins["i"], d["idLote"], d["idCultivo"], d["idCampania"], d["dosisHa"], d["superficie"], d["cantidadAsignada"])))
            resumen.append((nota, f"orden 105: Betito {ins['q']:g} → {total:g} kg", rep))
            continue

        if orden is None:  # orden de siembra nueva, lotes de maíz diferido de la fertilización 120
            lotes = _lotes(120, "Maiz diferido")
            i_ot = len(stmts)
            stmts.append(("INSERT INTO dbo.Ordenes_Trabajo (FechaPedido, FechaEjecucion, IdTipoLabor, IdContratistaContacto, Estado, Observaciones) "
                          "OUTPUT INSERTED.IdOrdenTrabajo VALUES (?, ?, ?, ?, 'Ejecutada', ?)",
                          (as_sql_datetime(fecha), as_sql_datetime(fecha), SIEMBRA, YANQUELEN, f"Siembra maíz diferido 2023/24 (faltaba). {OBS}")))
            stmts.append(formulario_retiro.stmt_generar(i_ot))
            ref = lambda r, i=i_ot: r[i]  # noqa: E731
        else:
            lotes = _lotes(orden)
            ref = lambda r, o=orden: o  # noqa: E731
        rep = _reparto(kg, lotes)
        i_ins = len(stmts)
        stmts.append(lambda r, ref=ref, prod=prod, kg=kg: (
            "INSERT INTO dbo.Ordenes_Trabajo_Insumos (IdOrdenTrabajo, IdProducto, CantidadTotal, Unidad) OUTPUT INSERTED.IdOrdenInsumo VALUES (?, ?, ?, 'KGS')",
            (ref(r), prod, kg)))
        for d in rep:
            stmts.append(lambda r, i=i_ins, d=d: (
                "INSERT INTO dbo.Ordenes_Trabajo_Distrib (IdOrdenInsumo, IdLote, IdCultivo, IdCampania, DosisHa, Superficie, CantidadAsignada, Aplicar) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 1)", (r[i], d["idLote"], d["idCultivo"], d["idCampania"], d["dosisHa"], d["superficie"], d["cantidadAsignada"])))
        resumen.append((nota, f"orden {orden or 'NUEVA'}: + {nombre} {kg:g} kg", rep))

    for nota, que, rep in resumen:
        print(f"{nota}\n   {que}: " + ", ".join(f"lote {d['idLote']} {d['superficie']:g} ha → {d['cantidadAsignada']:g} kg ({d['dosisHa']:g}/ha)" for d in rep))
    print(f"Sentencias: {len(stmts)}")
    if not aplicar:
        print("Simulación (usar --aplicar para escribir)")
        return
    s0 = saldos()
    BACKUPS.mkdir(exist_ok=True)
    resp = BACKUPS / f"semillas-yanquelen-antes-{datetime.now():%Y%m%d-%H%M%S}.json"
    resp.write_text(json.dumps({"orden105": fetch_all(
        "SELECT oi.*, d.IdDistrib, d.IdLote, d.Superficie, d.DosisHa, d.CantidadAsignada FROM dbo.Ordenes_Trabajo_Insumos oi "
        "JOIN dbo.Ordenes_Trabajo_Distrib d ON d.IdOrdenInsumo = oi.IdOrdenInsumo WHERE oi.IdOrdenTrabajo = 105 AND oi.IdProducto = ?", (BETITO,))},
        default=str, ensure_ascii=False, indent=1), encoding="utf-8")
    res = execute_write_transaction(stmts)
    s1 = saldos()
    dif = {c: (s0.get(c), s1.get(c)) for c in set(s0) | set(s1) if s0.get(c) != s1.get(c)}
    print(f"Aplicado. Remitos nuevos: {[r for r in res if isinstance(r, int)][:12]}. Respaldo: {resp}. Saldos con cambio: {len(dif)} {dif or ''}")
    from src.features.imputacion import progresivo
    progresivo.recalcular_seguro(progresivo.recalcular_productos, {CALEN, DM40R16, BETITO})


if __name__ == "__main__":
    main()
