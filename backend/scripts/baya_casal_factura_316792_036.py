"""Corrección autorizada de FC316792, contra PDF original. Solo WC.

Conserva cantidades y repartos. Registra explícitamente el redondeo fiscal
del total, sin cambiar precios originales ni introducir ajustes de cuenta.
Guarda antes/después y respaldo verificado fuera de Git.
"""
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from src.db.connection import (
    _assert_target_is_wc, fetch_all, execute_write_transaction,
    reconciliation_transaction,
)
from src.features.vinculos.backup import backup_verificado

ID = 2143513785
ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "backups/baya-conciliacion-20261019"
LABEL = "Redondeo IVA segun comprobante FC 0020-00316792"
D = Decimal
PRICES = {
    "2,4 D 89% CASTER baja volatilidad X 20 L": (D("7.0171"), D(180)),
    "ATRAZINA 90% TRAC X 10 KG": (D("10.8446"), D(260)),
    "CARFENTRAZONE 40% AURORA X 1 L": (D("143.5320"), D(6)),
    "COADY METILADO SILICONADO ACTION X 10 L": (D("12.7584"), D(20)),
    "CRIPTON (trifloxistrobina 15% protioconazol 17,5%)": (D("36.1488"), D(35)),
    "DIFLUFENICAN 50% FLUSAN X 10 L": (D("48.6946"), D(20)),
    "DIFLUFENICAN 50% TUKEN X 5 KG": (D("48.6946"), D(5)),
    "FIERCE RM (piroxasulfona 34,5% flumioxazin 15%) X": (D("94.6248"), D(40)),
    "GLIFOSATO 54% FULL II SIGMA X 20 L": (D("11.6952"), D(1000)),
    "LAMBDA CIALOTRINA 25% KARATE ZEON": (D("37.2120"), D(10)),
    "PICLORAM 24% X 5 L": (D("16.7986"), D(20)),
    "S-METOLACLORO 96% STRIM X 20 L": (D("15.3101"), D(20)),
    "SULFATO DE AMONIO X 20 L": (D("1.4885"), D(200)),
}


def snapshot():
    return {
        "cabecera": fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda=?", (ID,)),
        "lineas": fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra=? ORDER BY IdDetalleCompra", (ID,)),
        "total": fetch_all("SELECT * FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?", (ID,)),
    }


def validate(state):
    c = state["cabecera"]
    assert len(c) == 1 and c[0]["IdContacto"] == 226
    assert c[0]["Nro Documento"] == "0020-00316792" and c[0]["Moneda"] == "Dolares"
    lines = [r for r in state["lineas"] if r["Producto/Servicio"] != LABEL]
    assert len(lines) == 73
    assert {r["Producto/Servicio"].strip() for r in lines} == set(PRICES)
    for name, (_, qty) in PRICES.items():
        selected = [r for r in lines if r["Producto/Servicio"].strip() == name]
        assert abs(sum(D(str(r["Cantidad"])) for r in selected) - qty) < D("0.001")
        assert all(r["IVA"] == 21 and not r["Ajuste financiero"] for r in selected)
    return lines


def save(path, value):
    path.write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    _assert_target_is_wc()
    pdf = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes\Baya Casal\20261019\FC_0020_00316792.pdf")
    assert pdf.is_file()
    before = snapshot()
    lines = validate(before)
    if (all(abs(r["Precio Unitario"] - float(PRICES[r["Producto/Servicio"].strip()][0])) < 1e-10 for r in lines)
            and before["cabecera"][0]["Tipo de Cambio"] == 230
            and abs(before["total"][0]["ImporteDocumento"] - 29613.30) < .0001):
        print("Factura ya corregida; no se repiten escrituras.")
        return
    assert not any(r["Producto/Servicio"] == LABEL for r in before["lineas"])
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    result_path = EVIDENCE / f"fc316792-correccion-{stamp}.json"
    backup = backup_verificado("baya-fc316792-036")
    audit = {"autorizacion": "Sergio: revisar y corregir para reflejar documento original",
             "pdf": str(pdf), "backup_verificado": backup, "antes": before}
    save(result_path, audit)
    with reconciliation_transaction():
        assert snapshot() == before, "La factura cambió desde la lectura; no sobrescribir"
        statements = []
        for r in lines:
            price = PRICES[r["Producto/Servicio"].strip()][0]
            statements.append(("UPDATE dbo.Det_Compras SET [Precio Unitario]=? WHERE IdDetalleCompra=? AND IdCompra=?",
                               (float(price), r["IdDetalleCompra"], ID)))
        statements.append(("UPDATE dbo.Compras SET [Tipo de Cambio]=?,[Fecha Vto]=? WHERE IdDeuda=? AND IdContacto=?",
                           (230, datetime(2023, 5, 30), ID, 226)))
        counts = execute_write_transaction(statements)
        # La sesión usa NOCOUNT: el driver puede informar -1. La relectura
        # dentro de la transacción verifica cada precio y todos los repartos.
        assert all(x in (-1, 1) for x in counts)
        subtotal = snapshot()
        adjustment = (D("29613.30") - D(str(subtotal["total"][0]["ImporteDocumento"]))).quantize(D("0.0001"), rounding=ROUND_HALF_UP)
        assert D(0) < adjustment < D("0.02"), "Residual distinto al redondeo fiscal esperado"
        execute_write_transaction([(
            "INSERT INTO dbo.Det_Compras (IdCompra,Cantidad,Unidad,[Producto/Servicio],[Precio Unitario],IVA,[Ajuste financiero]) "
            "VALUES (?,1,?,?,?,?,1)",
            (ID, "USD", LABEL, float(adjustment), 0),
        )])
        after = snapshot()
        corrected = validate(after)
        assert len(after["lineas"]) == 74
        for old, new in zip(lines, corrected):
            assert all(old[k] == new[k] for k in old if k not in ("Precio Unitario", "SSMA_TimeStamp"))
            assert abs(new["Precio Unitario"] - float(PRICES[new["Producto/Servicio"].strip()][0])) < 1e-10
        assert abs(after["total"][0]["ImporteDocumento"] - 29613.30) < .0001
        assert after["cabecera"][0]["Tipo de Cambio"] == 230
        audit.update(despues=after, redondeo_iva=str(adjustment))
        save(result_path, audit)
    persisted = snapshot()
    assert persisted == audit["despues"], "La relectura no coincide con el cambio confirmado"
    print("Respaldo verificado:", backup)
    print("Factura corregida; 73 repartos conservados, TC230, vencimiento30/05/2023.")
    print("Redondeo IVA identificado:", adjustment)
    print("Total persistido:", persisted["total"][0]["ImporteDocumento"])
    print("Auditoria:", result_path)


if __name__ == "__main__":
    main()
