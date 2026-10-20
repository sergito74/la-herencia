"""Distribución autorizada de financiación entre productos/cultivos/campañas.

Base: neto USD de cada renglón de FC320048/320049/336203 vigente al aplicar.
Reparte540,88 a centavos por mayores restos; conserva IVA21% y total de ND.
No modifica cantidades/precios de facturas ni agrega pagos.
"""
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

from src.db.connection import _assert_target_is_wc, fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

D = Decimal
ND = 2143523738
SOURCES = (2143514032, 2143514033, 2143514218)
ROOT = Path(__file__).resolve().parents[2] / "backups/baya-conciliacion-20261019"


def snapshot():
    return {
        "facturas": fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda IN (?,?,?) ORDER BY IdDeuda", SOURCES),
        "lineasOrigen": fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra IN (?,?,?) ORDER BY IdCompra,IdDetalleCompra", SOURCES),
        "cabeceraND": fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda=?", (ND,)),
        "lineasND": fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra=? ORDER BY IdDetalleCompra", (ND,)),
        "totalND": fetch_all("SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?", (ND,)),
        "relaciones": fetch_all("SELECT * FROM dbo.CompraDocumentosRelacionados WHERE IdCompra=? OR IdCompraRelacionada=? ORDER BY IdCompra,IdCompraRelacionada", (ND, ND)),
        "saldoBase": fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"],
    }


def allocate(rows, campaigns):
    assert len(rows) == 23 and all(not r["Ajuste financiero"] for r in rows)
    weights = [D(str(r["Cantidad"])) * D(str(r["Precio Unitario"])) for r in rows]
    assert all(w > 0 for w in weights)
    total = sum(weights)
    raw = [D("540.88") * w / total for w in weights]
    amounts = [v.quantize(D("0.01"), rounding=ROUND_FLOOR) for v in raw]
    extra = int((D("540.88") - sum(amounts)) * 100)
    order = sorted(range(len(rows)), key=lambda i: (-(raw[i] - amounts[i]), rows[i]["IdDetalleCompra"]))
    for i in order[:extra]:
        amounts[i] += D("0.01")
    assert sum(amounts) == D("540.88") and all(a > 0 for a in amounts)
    out = []
    for r, w, amount, exact in zip(rows, weights, amounts, raw):
        campaign = campaigns[r["Campaña"]]
        assert r["IdCampaña"] in (None, campaign)
        assert r["IdCentroCostos"] and r["IdDestino"] and r["IdRubro"]
        assert abs(amount - exact) < D("0.01")
        out.append({"idLineaOrigen": r["IdDetalleCompra"], "idFacturaOrigen": r["IdCompra"],
                    "producto": r["Producto/Servicio"], "netoBase": str(w), "porcentaje": str(w * 100 / total),
                    "financiacionNeta": str(amount), "idCentro": r["IdCentroCostos"], "idDestino": r["IdDestino"],
                    "idRubro": r["IdRubro"], "idFormulado": r["IdFormulado"], "idCampaña": campaign, "campaña": r["Campaña"]})
    return out, total


def save(path, data):
    path.write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    _assert_target_is_wc()
    before = snapshot()
    assert len(before["lineasND"]) == 1, "La ND ya tiene distribución o cambió: revisar antes de repetir"
    old = before["lineasND"][0]
    assert old["Precio Unitario"] == 540.88 and old["Cantidad"] == 1 and old["IVA"] == 21
    assert old["IdRubro"] == 2047893443 and old["Ajuste financiero"]
    assert before["cabeceraND"][0]["Nro Documento"] == "0020-00096827"
    campaigns = {r["Campaña"]: r["IdCampaña"] for r in fetch_all("SELECT IdCampaña,Campaña FROM dbo.Campañas", ())}
    plan, base = allocate(before["lineasOrigen"], campaigns)
    # Heredar rubro de producto hace visible el costo en vistas de cultivo:
    # Financiamiento tiene clase5 y allí queda excluido. La marca financiera
    # conserva su naturaleza; cantidad1/USD no agrega litros ni kilos.
    rubros = fetch_all("SELECT IdRubro,IdClasifCostoCultivo FROM dbo.Rubros WHERE IdRubro IN (?,?)", (2, 2047893449))
    assert all(1 <= r["IdClasifCostoCultivo"] <= 4 for r in rubros)
    backup = backup_verificado("baya-nd96827-prorrateo-036")
    path = ROOT / f"nd96827-prorrateo-{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    audit = {"autorizacion": "Sergio: imputar financiacion proporcionalmente a productos,cultivos,campañas de las facturas afectadas",
             "respaldo": backup, "baseNetaUSD": str(base), "criterio": "Neto sinIVA de las23lineas vigentes; mayoresrestos a centavos; IVA21% de laND sin alteracion",
             "antes": before, "distribucion": plan}
    save(path, audit)
    with reconciliation_transaction():
        assert snapshot() == before, "Cambio concurrente: no sobrescribir"
        operations = []
        for i, part in enumerate(plan):
            args = (part["producto"], float(D(part["financiacionNeta"])), part["idCentro"], part["idDestino"],
                    part["idRubro"], part["idFormulado"], part["idCampaña"], part["campaña"])
            if i == 0:
                operations.append(("UPDATE dbo.Det_Compras SET [Producto/Servicio]=?,Cantidad=1,[Precio Unitario]=?,IVA=21,Unidad='USD',IdCentroCostos=?,IdDestino=?,IdRubro=?,IdFormulado=?,IdCampaña=?,Campaña=?,[Ajuste financiero]=1 WHERE IdDetalleCompra=? AND IdCompra=?", (*args, old["IdDetalleCompra"], ND)))
            else:
                operations.append(("INSERT INTO dbo.Det_Compras ([Producto/Servicio],Cantidad,[Precio Unitario],IVA,Unidad,IdCentroCostos,IdDestino,IdRubro,IdFormulado,IdCampaña,Campaña,[Ajuste financiero],IdCompra) VALUES (?,1,?,21,'USD',?,?,?,?,?,?,1,?)", (*args, ND)))
        execute_write_transaction(operations)
        after = snapshot()
        assert len(after["lineasND"]) == len(plan)
        for r, part in zip(after["lineasND"], plan):
            assert r["Producto/Servicio"] == part["producto"] and r["Cantidad"] == 1 and r["Unidad"] == "USD" and r["IVA"] == 21 and r["Ajuste financiero"]
            assert abs(D(str(r["Precio Unitario"])) - D(part["financiacionNeta"])) < D("0.000001")
            assert (r["IdCentroCostos"], r["IdDestino"], r["IdRubro"], r["IdCampaña"]) == (part["idCentro"], part["idDestino"], part["idRubro"], part["idCampaña"])
            part["idLineaND"] = r["IdDetalleCompra"]
        for key in ("facturas", "lineasOrigen", "cabeceraND", "relaciones"):
            assert after[key] == before[key], f"Cambio inesperado:{key}"
        assert abs(D(str(after["totalND"][0]["ImporteDocumento"])) - D(str(before["totalND"][0]["ImporteDocumento"]))) < D("0.0001")
        assert abs(D(str(after["saldoBase"])) - D(str(before["saldoBase"]))) < D("0.0001")
        costs = fetch_all("SELECT IdDetalleCompra,IdDestino,IdCampaña,IdRubro,Dolares FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra=?", (ND,))
        assert len(costs) == len(plan) and abs(sum(D(str(r["Dolares"])) for r in costs) - D("540.88")) < D("0.0001")
        audit.update(despues=after, costosCultivoVerificados=costs)
        save(path, audit)
    assert snapshot() == after
    summary = defaultdict(Decimal)
    for p in plan:
        summary[p["campaña"]] += D(p["financiacionNeta"])
    print("Distribucion aplicada:", len(plan), "renglones; netoUSD540,88; totalNDsin cambios.")
    print("Por campaña:", dict(summary))
    print("Respaldo verificado:", backup)
    print("Auditoria:", path)


if __name__ == "__main__":
    main()
