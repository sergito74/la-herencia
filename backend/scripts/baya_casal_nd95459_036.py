"""Alta de diferencia de cambio y reparto por factura/producto/cultivo/campaña.

Respeta importes identificados en el PDF para cada factura, y luego prorratea
cada uno por netos de sus líneas. Todo en pesos, sin efecto en dólares.
"""
import hashlib
import json
import shutil
import re
from datetime import date, datetime
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

from src.db.connection import _assert_target_is_wc, fetch_all, execute_write_transaction, reconciliation_transaction, _reconciliation_connection
from src.features.compras.repository import create_compra, agregar_documento_relacionado, get_documentos_relacionados
from src.features.auditoria_cuentas.bimonetaria import construir, cotizacion_bna
from src.features.vinculos.backup import backup_verificado

D = Decimal
TARGETS = {2143513786: D("36030.87"), 2143514123: D("-7059.16")}
NUMBER = "0020-00095459"
SOURCE = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes\Baya Casal\20261019\ND_0020_00095459.pdf")
PDF = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2023 - 03 2024\20230802_BayaCasal_ND0020-00095459.pdf")
ROOT = Path(__file__).resolve().parents[2] / "backups/baya-conciliacion-20261019"


def origins():
    return {"cabeceras": fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda IN (?,?) ORDER BY IdDeuda", tuple(TARGETS)),
            "lineas": fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra IN (?,?) ORDER BY IdCompra,IdDetalleCompra", tuple(TARGETS))}


def existing():
    return fetch_all("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento] LIKE ?", (226, "%95459%"))


def allocate(rows, targets=TARGETS):
    plan = []
    for invoice_id, amount in targets.items():
        sign = -1 if amount < 0 else 1
        amount = abs(amount)
        selected = [r for r in rows if r["IdCompra"] == invoice_id]
        assert selected
        weights = [D(str(r["Cantidad"])) * D(str(r["Precio Unitario"])) for r in selected]
        assert all(w > 0 for w in weights)
        total = sum(weights)
        raw = [amount * w / total for w in weights]
        rounded = [v.quantize(D("0.01"), rounding=ROUND_FLOOR) for v in raw]
        extra = int((amount - sum(rounded)) * 100)
        for i in sorted(range(len(selected)), key=lambda i: (-(raw[i] - rounded[i]), selected[i]["IdDetalleCompra"]))[:extra]:
            rounded[i] += D("0.01")
        assert sum(rounded) == amount
        for r, w, allocated, exact in zip(selected, weights, rounded, raw):
            assert allocated > 0 and abs(allocated - exact) < D("0.01")
            assert r["IdCampaña"] and r["IdCentroCostos"] and r["IdDestino"] and r["IdRubro"]
            plan.append({"origen": r, "baseNetaUSD": str(w), "porcentajeFactura": str(w * 100 / total), "netoPesos": str(allocated * sign)})
    assert len(plan) == len(rows) and sum(D(p["netoPesos"]) for p in plan) == D("28971.71")
    return plan


def note_state(invoice_id):
    return {"cabecera": fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda=?", (invoice_id,)),
            "lineas": fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra=? ORDER BY IdDetalleCompra", (invoice_id,)),
            "vencimientos": fetch_all("SELECT * FROM dbo.[Vencimiento Compras] WHERE IdCompra=?", (invoice_id,)),
            "relaciones": get_documentos_relacionados(invoice_id),
            "total": fetch_all("SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?", (invoice_id,))}


def save(path, data):
    path.write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def signed_financial_debits(definition):
    """Mantener reducciones de costo dentro de ND financieras; NC conserva su signo."""
    sign_pattern = (r"CASE\s+WHEN CP\.\[Tipo documento\] COLLATE Latin1_General_CI_AI = 'Nota de Credito' THEN -1"
                    r"\s+ELSE 1\s+END AS Signo")
    signed_case = ("CASE WHEN CP.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Credito' THEN -1 "
                   "WHEN ISNULL(DC.[Ajuste financiero],0)=1 AND CP.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Debito' "
                   "AND ISNULL(DC.Cantidad,0)*ISNULL(DC.[Precio Unitario],0)<0 THEN -1 ELSE 1 END AS Signo")
    definition = re.sub(sign_pattern, signed_case, definition, count=1)
    token = "ABS(ISNULL(DC.Cantidad, 0) * ISNULL(DC.[Precio Unitario], 0))"
    marker = "/* signo ND financiera 036 */"
    if marker in definition:
        return re.sub(r"^CREATE\s+VIEW", "ALTER VIEW", definition, count=1, flags=re.IGNORECASE)
    assert definition.count(token) == 4
    expression = (marker + " CASE WHEN ISNULL(DC.[Ajuste financiero],0)=1 "
                  "AND CP.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Debito' "
                  "THEN ISNULL(DC.Cantidad,0)*ISNULL(DC.[Precio Unitario],0) ELSE " + token + " END")
    result = definition.replace(token, expression)
    return re.sub(r"^CREATE\s+VIEW", "ALTER VIEW", result, count=1, flags=re.IGNORECASE)


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
        state = note_state(found[0]["IdDeuda"])
        assert state["cabecera"][0]["Ajusta Tipo Cambio"] and len(state["lineas"]) == 57
        assert round(state["total"][0]["ImporteDocumento"], 2) == 35055.77
        print("ND ya cargada y distribuida:", found[0]["IdDeuda"])
        return
    before = origins()
    assert len(before["cabeceras"]) == 2 and len(before["lineas"]) == 57
    assert all(c["IdContacto"] == 226 and c["Moneda"] == "Dolares" for c in before["cabeceras"])
    plan = allocate(before["lineas"])
    campaigns = {r["Campaña"]: r["IdCampaña"] for r in fetch_all("SELECT IdCampaña,Campaña FROM dbo.Campañas", ())}
    for part in plan:
        part["idCampañaAsignada"] = campaigns[part["origen"]["Campaña"]]
    view_before = fetch_all("SELECT OBJECT_DEFINITION(OBJECT_ID(?)) AS d", ("dbo.vw_ResultadosCultivo_CostosBase",))[0]["d"]
    view_after = signed_financial_debits(view_before)
    if view_after != view_before:
        assert fetch_all("SELECT COUNT(*) AS n FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda=d.IdCompra WHERE d.[Ajuste financiero]=1 AND c.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Debito' AND d.Cantidad*d.[Precio Unitario]<0", ())[0]["n"] == 0

    backup = backup_verificado("baya-nd95459-distribucion-036")
    path = ROOT / f"nd95459-alta-distribucion-{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    audit = {"autorizacion": "Sergio: mismo procedimiento de carga y distribucion proporcional", "respaldo": backup, "pdf": str(PDF),
             "sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(), "antes": before, "distribucion": plan, "vistaAntes": view_before, "vistaDespues": view_after,
             "criterio": "Diferencias expresas delPDF:415303.17-379272.30=36030.87;135206.09-142265.25=-7059.16. Dentro de cadafactura: proporcionalalneto, sinIVA, mayoresrestos. Se respeta reducciondeprecios enND."}
    save(path, audit)
    with reconciliation_transaction():
        assert not existing() and origins() == before
        if view_after != view_before:
            cursor = _reconciliation_connection.get().cursor()
            assert cursor.execute("SELECT DB_NAME()").fetchone()[0] == "WC"
            current = cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID(?))", ("dbo.vw_ResultadosCultivo_CostosBase",)).fetchone()[0]
            assert current == view_before
            cursor.execute(view_after)
        previous_balance = fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"]
        lines = []
        for part in plan:
            r = part["origen"]
            lines.append({"productoServicio": r["Producto/Servicio"], "cantidad": 1, "unidad": "ARS", "precioUnitario": float(D(part["netoPesos"])),
                          "iva": 21, "idRubro": r["IdRubro"], "idCentroCosto": r["IdCentroCostos"], "idDestino": r["IdDestino"],
                          "campaña": r["Campaña"], "ajusteFinanciero": True})
        invoice_id = create_compra({"idContacto": 226, "fecha": date(2023, 8, 2), "tipoDocumento": "Nota de Débito", "tipo": "A",
                                    "numeroDocumento": NUMBER, "moneda": "Pesos", "tipoDeCambio": 1,
                                    "ajustaTipoCambio": True, "documentoOriginal": str(PDF)}, lines,
                                   [{"fechaVencimiento": date(2023, 8, 2)}])
        rows = note_state(invoice_id)["lineas"]
        assert len(rows) == len(plan)
        updates = [("UPDATE dbo.Compras SET [Fecha Vto]=? WHERE IdDeuda=?", (datetime(2023, 8, 2), invoice_id))]
        for new, part in zip(rows, plan):
            r = part["origen"]
            updates.append(("UPDATE dbo.Det_Compras SET IdCampaña=?,IdFormulado=? WHERE IdDetalleCompra=? AND IdCompra=?", (part["idCampañaAsignada"], r["IdFormulado"], new["IdDetalleCompra"], invoice_id)))
            part["idLineaND"] = new["IdDetalleCompra"]
        execute_write_transaction(updates)
        for original in TARGETS:
            agregar_documento_relacionado(invoice_id, original)
        after = note_state(invoice_id)
        assert origins() == before
        assert after["cabecera"][0]["Moneda"] == "Pesos" and after["cabecera"][0]["Ajusta Tipo Cambio"]
        assert sorted(r["idCompra"] for r in after["relaciones"]) == sorted(TARGETS)
        assert round(after["total"][0]["ImporteDocumento"], 2) == 35055.77
        for new, part in zip(after["lineas"], plan):
            r = part["origen"]
            for key in ("Producto/Servicio", "IdCentroCostos", "IdDestino", "IdRubro", "Campaña", "IdFormulado"):
                assert new[key] == r[key]
            assert new["IdCampaña"] == part["idCampañaAsignada"]
            assert new["Cantidad"] == 1 and new["Unidad"] == "ARS" and new["IVA"] == 21 and new["Ajuste financiero"]
            assert abs(D(str(new["Precio Unitario"])) - D(part["netoPesos"])) < D("0.000001")
        movements = fetch_all("SELECT Fecha,Documento,[Nro Documento],Deuda,Credito,Origen,IdOrigen FROM dbo.vw_MovimientosCuenta_Base WHERE Origen=? AND IdOrigen=?", ("Compras", invoice_id))
        note_usd = construir(movements, {invoice_id: {"moneda": "Pesos", "tc": 1, "ajusta": True}}, cotizacion_bna())
        assert note_usd["saldoDolares"] == 0
        costs = fetch_all("SELECT IdDetalleCompra,IdDestino,IdCampaña,Pesos,Dolares,Signo FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra=?", (invoice_id,))
        assert len(costs) == len(plan) and abs(sum(D(str(r["Pesos"])) for r in costs) - D("28971.71")) < D("0.0001")
        assert all(r["Dolares"] == 0 for r in costs)
        actual_costs = {r["IdDetalleCompra"]: r for r in costs}
        for part in plan:
            assert abs(D(str(actual_costs[part["idLineaND"]]["Pesos"])) - D(part["netoPesos"])) < D("0.0001")
            cost = actual_costs[part["idLineaND"]]
            assert abs(abs(D(str(cost["Pesos"]))) * cost["Signo"] - D(part["netoPesos"])) < D("0.0001")
        balance = fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"]
        assert abs(D(str(previous_balance)) - D(str(balance)) - D(str(after["total"][0]["ImporteDocumento"]))) < D("0.001")
        audit.update(idCompra=invoice_id, despues=after, costoCultivosVerificado=costs, efectoDolares=note_usd["saldoDolares"], saldoBaseAntes=previous_balance, saldoBaseDespues=balance)
        save(path, audit)
    assert note_state(invoice_id) == after and origins() == before
    print("ND registrada:", invoice_id, "Total$35.055,77;57renglones distribuidos;efectoUSD0.")
    print("Respaldo verificado:", backup)
    print("Auditoria:", path)


if __name__ == "__main__":
    main()
