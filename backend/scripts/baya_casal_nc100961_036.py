"""NC100961: reducción proporcional de costos en pesos, sin modificar USD."""
import hashlib
import json
import shutil
from datetime import date, datetime
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

from src.db.connection import _assert_target_is_wc, fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.compras.repository import create_compra, agregar_documento_relacionado, get_documentos_relacionados
from src.features.auditoria_cuentas.bimonetaria import construir, cotizacion_bna
from src.features.vinculos.backup import backup_verificado

D = Decimal
ORIGIN = 2143513785
NET = D("75012.03")
SOURCE = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes\Baya Casal\20261019\NC_0020_00100961.pdf")
PDF = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2023 - 03 2024\20230503_BayaCasal_NC0020-00100961.pdf")
ROOT = Path(__file__).resolve().parents[2] / "backups/baya-conciliacion-20261019"


def origin():
    return {"cabecera": fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda=?", (ORIGIN,)),
            "lineas": fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra=? ORDER BY IdDetalleCompra", (ORIGIN,))}


def note(invoice_id):
    return {"cabecera": fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda=?", (invoice_id,)),
            "lineas": fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra=? ORDER BY IdDetalleCompra", (invoice_id,)),
            "vencimientos": fetch_all("SELECT * FROM dbo.[Vencimiento Compras] WHERE IdCompra=?", (invoice_id,)),
            "relaciones": get_documentos_relacionados(invoice_id),
            "total": fetch_all("SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?", (invoice_id,))}


def existing():
    return fetch_all("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento] LIKE ?", (226, "%100961%"))


def save(path, data):
    path.write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    _assert_target_is_wc()
    assert SOURCE.is_file() and PDF.parent.is_dir()
    if PDF.exists():
        assert hashlib.sha256(PDF.read_bytes()).digest() == hashlib.sha256(SOURCE.read_bytes()).digest()
    else:
        shutil.copy2(SOURCE, PDF)
    found = existing()
    if found:
        assert len(found) == 1
        state = note(found[0]["IdDeuda"])
        assert len(state["lineas"]) == 73 and state["cabecera"][0]["Ajusta Tipo Cambio"]
        assert round(state["total"][0]["ImporteDocumento"], 2) == -90764.56
        print("Nota ya cargada y distribuida:", found[0]["IdDeuda"])
        return
    before = origin()
    assert before["cabecera"][0]["Nro Documento"] == "0020-00316792" and before["cabecera"][0]["IdContacto"] == 226
    # Excluir redondeo financiero añadido al corregir la factura: no es producto.
    rows = [r for r in before["lineas"] if not r["Ajuste financiero"]]
    assert len(rows) == 73
    weights = [D(str(r["Cantidad"])) * D(str(r["Precio Unitario"])) for r in rows]
    assert all(w > 0 for w in weights)
    total = sum(weights)
    raw = [NET * w / total for w in weights]
    amounts = [v.quantize(D("0.01"), rounding=ROUND_FLOOR) for v in raw]
    extra = int((NET - sum(amounts)) * 100)
    for i in sorted(range(len(rows)), key=lambda i: (-(raw[i] - amounts[i]), rows[i]["IdDetalleCompra"]))[:extra]:
        amounts[i] += D("0.01")
    assert sum(amounts) == NET
    plan = []
    for r, w, amount, exact in zip(rows, weights, amounts, raw):
        assert amount > 0 and abs(amount - exact) < D("0.01") and r["IdCampaña"] and r["IdDestino"]
        plan.append({"origen": r, "netoBaseUSD": str(w), "porcentaje": str(w * 100 / total), "reduccionNetaPesos": str(amount)})
    backup = backup_verificado("baya-nc100961-distribucion-036")
    path = ROOT / f"nc100961-alta-distribucion-{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    audit = {"autorizacion": "Sergio: cargala e imputala", "respaldo": backup, "pdf": str(PDF),
             "sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(), "antes": before, "distribucion": plan,
             "criterio": "Reduccion75012,03 proporcional a netosUSD corregidos de73lineas; IVA21%; mayoresrestos; se excluye redondeo financiero de factura."}
    save(path, audit)
    with reconciliation_transaction():
        assert not existing() and origin() == before
        balance_before = fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"]
        lines = []
        for part in plan:
            r = part["origen"]
            lines.append({"productoServicio": r["Producto/Servicio"], "cantidad": 1, "unidad": "ARS", "precioUnitario": -float(D(part["reduccionNetaPesos"])),
                          "iva": 21, "idRubro": r["IdRubro"], "idCentroCosto": r["IdCentroCostos"], "idDestino": r["IdDestino"],
                          "campaña": r["Campaña"], "ajusteFinanciero": True})
        invoice_id = create_compra({"idContacto": 226, "fecha": date(2023, 5, 3), "tipoDocumento": "Nota de Crédito", "tipo": "A",
                                    "numeroDocumento": "0020-00100961", "moneda": "Pesos", "tipoDeCambio": 1,
                                    "ajustaTipoCambio": True, "documentoOriginal": str(PDF)}, lines,
                                   [{"fechaVencimiento": date(2023, 5, 3)}])
        created = note(invoice_id)["lineas"]
        assert len(created) == len(plan)
        operations = [("UPDATE dbo.Compras SET [Fecha Vto]=? WHERE IdDeuda=?", (datetime(2023, 5, 3), invoice_id))]
        for new, part in zip(created, plan):
            r = part["origen"]
            operations.append(("UPDATE dbo.Det_Compras SET IdCampaña=?,IdFormulado=? WHERE IdDetalleCompra=? AND IdCompra=?", (r["IdCampaña"], r["IdFormulado"], new["IdDetalleCompra"], invoice_id)))
            part["idLineaNC"] = new["IdDetalleCompra"]
        execute_write_transaction(operations)
        agregar_documento_relacionado(invoice_id, ORIGIN)
        after = note(invoice_id)
        assert origin() == before and after["cabecera"][0]["Ajusta Tipo Cambio"] and after["cabecera"][0]["Moneda"] == "Pesos"
        assert round(after["total"][0]["ImporteDocumento"], 2) == -90764.56
        assert [r["idCompra"] for r in after["relaciones"]] == [ORIGIN]
        for new, part in zip(after["lineas"], plan):
            r = part["origen"]
            for k in ("Producto/Servicio", "IdCentroCostos", "IdDestino", "IdRubro", "IdCampaña", "Campaña", "IdFormulado"):
                assert new[k] == r[k]
            assert new["Precio Unitario"] < 0 and new["Cantidad"] == 1 and new["IVA"] == 21 and new["Ajuste financiero"]
        costs = fetch_all("SELECT IdDetalleCompra,IdDestino,IdCampaña,Pesos,Dolares FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra=?", (invoice_id,))
        assert len(costs) == 73 and abs(sum(D(str(r["Pesos"])) for r in costs) + NET) < D("0.0001")
        assert all(r["Pesos"] < 0 and r["Dolares"] == 0 for r in costs)
        movements = fetch_all("SELECT Fecha,Documento,[Nro Documento],Deuda,Credito,Origen,IdOrigen FROM dbo.vw_MovimientosCuenta_Base WHERE Origen=? AND IdOrigen=?", ("Compras", invoice_id))
        usd = construir(movements, {invoice_id: {"moneda": "Pesos", "tc": 1, "ajusta": True}}, cotizacion_bna())
        assert usd["saldoDolares"] == 0 and usd["saldoPesos"] > 0
        balance_after = fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"]
        assert abs(D(str(balance_after)) - D(str(balance_before)) + D(str(after["total"][0]["ImporteDocumento"]))) < D("0.001")
        audit.update(idCompra=invoice_id, despues=after, costosVerificados=costs, efectoUSD=0, saldoBaseAntes=balance_before, saldoBaseDespues=balance_after)
        save(path, audit)
    assert note(invoice_id) == after and origin() == before
    print("NC creada:", invoice_id, "Total$90.764,56 a favor; reduccionneta$75.012,03 en73renglones;efectoUSD0.")
    print("Respaldo verificado:", backup)
    print("Auditoria:", path)


if __name__ == "__main__":
    main()
