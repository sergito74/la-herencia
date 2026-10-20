"""Alta autorizada de FC0020-00251611, con PDF y comprobaciones en WC."""
import hashlib
import json
import shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src.db.connection import _assert_target_is_wc, fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

NUMBER = "0020-00251611"
ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes\Baya Casal\20261019\FC_0020_00251611.pdf")
DEST = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2021 - 03 2022\20210615_BayaCasal_FC0020-00251611.pdf")


def candidates():
    return fetch_all("SELECT IdDeuda,[Nro Documento] FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento] LIKE ?", (226, "%251611%"))


def read_invoice(invoice_id):
    return {
        "cabecera": fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda=?", (invoice_id,)),
        "lineas": fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra=?", (invoice_id,)),
        "vencimientos": fetch_all("SELECT * FROM dbo.[Vencimiento Compras] WHERE IdCompra=?", (invoice_id,)),
        "total": fetch_all("SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?", (invoice_id,)),
    }


def verify(state):
    c = state["cabecera"][0]
    assert c["IdContacto"] == 226 and c["Nro Documento"] == NUMBER
    assert c["Moneda"] == "Dolares" and c["Tipo de Cambio"] == 95.5
    assert c["Fecha"].date() == date(2021, 6, 15) and c["Fecha Vto"].date() == date(2022, 4, 11)
    assert c["Documento Original"] == str(DEST)
    assert len(state["lineas"]) == 1
    r = state["lineas"][0]
    assert r["Cantidad"] == 5 and r["Precio Unitario"] == 23.76 and r["IVA"] == 21
    assert r["Unidad"] == "LITROS" and r["IdCampaña"] == 15
    assert round(state["total"][0]["ImporteDocumento"], 2) == 143.75
    assert len(state["vencimientos"]) == 1


def main():
    _assert_target_is_wc()
    assert SOURCE.is_file()
    if DEST.exists():
        assert hashlib.sha256(DEST.read_bytes()).digest() == hashlib.sha256(SOURCE.read_bytes()).digest()
    else:
        assert DEST.parent.is_dir()
        shutil.copy2(SOURCE, DEST)
    existing = candidates()
    if existing:
        assert len(existing) == 1
        verify(read_invoice(existing[0]["IdDeuda"]))
        print("Factura ya cargada:", existing[0]["IdDeuda"])
        return
    nc = read_invoice(2143513255)
    reference = nc["lineas"][0]
    assert len(nc["lineas"]) == 1 and reference["Cantidad"] == 5 and reference["IdCampaña"] == 15
    backup = backup_verificado("baya-fc251611-036")
    path = ROOT / "backups/baya-conciliacion-20261019" / f"fc251611-alta-{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    audit = {"autorizacion": "Sergio: cargala al sistema", "backup_verificado": backup,
             "pdf": str(DEST), "sha256": hashlib.sha256(DEST.read_bytes()).hexdigest(),
             "clasificacionOrigen": "NC78448 del mismo producto y cantidad; se conserva sin cambios", "notaCreditoAntes": nc}
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    with reconciliation_transaction():
        assert not candidates(), "Documento creado concurrentemente"
        before = fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"]
        invoice_id = compras.create_compra(
            {"idContacto": 226, "fecha": date(2021, 6, 15), "tipoDocumento": "Factura", "tipo": "A",
             "numeroDocumento": NUMBER, "moneda": "Dolares", "tipoDeCambio": 95.5, "documentoOriginal": str(DEST)},
            [{"productoServicio": "IMIDACLOPRID 35% X 5 L", "cantidad": 5, "unidad": "LITROS", "precioUnitario": 23.76, "iva": 21,
              "idCentroCosto": reference["IdCentroCostos"], "idDestino": reference["IdDestino"], "idRubro": reference["IdRubro"], "campaña": reference["Campaña"]}],
            [{"fechaVencimiento": date(2022, 4, 11)}],
        )
        execute_write_transaction([
            ("UPDATE dbo.Compras SET [Fecha Vto]=? WHERE IdDeuda=?", (datetime(2022, 4, 11), invoice_id)),
            ("UPDATE dbo.Det_Compras SET IdCampaña=? WHERE IdCompra=?", (reference["IdCampaña"], invoice_id)),
        ])
        state = read_invoice(invoice_id)
        verify(state)
        assert read_invoice(2143513255) == nc, "La nota de credito no debe modificarse"
        after = fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"]
        assert abs(Decimal(str(before)) - Decimal(str(after)) - Decimal(str(state["total"][0]["ImporteDocumento"]))) < Decimal("0.001")
        audit.update(idCompra=invoice_id, factura=state, saldoBaseAntes=before, saldoBaseDespues=after,
                     nota="El sistema calcula143.748 con precios originales; visualiza143.75. No se agrega ajuste artificial ni pago, ni se ejecutaFIFO.")
        path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    assert read_invoice(invoice_id) == state
    print("Factura creada:", invoice_id, "Total visible USD143,75. Respaldo:", backup)
    print("PDF:", DEST)
    print("Auditoria:", path)


if __name__ == "__main__":
    main()
