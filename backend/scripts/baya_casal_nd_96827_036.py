"""Alta autorizada de ND96827, financiaciónNERA, sin registrar otro pago."""
import hashlib
import json
import shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src.db.connection import _assert_target_is_wc, fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.compras.repository import create_compra, agregar_documento_relacionado, get_documentos_relacionados
from src.features.vinculos.backup import backup_verificado

NUMBER = "0020-00096827"
RELATED = [2143514032, 2143514033, 2143514218]
SOURCE = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes\Baya Casal\20261019\ND_0020_00096827.pdf")
PDF = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2023 - 03 2024\20230828_BayaCasal_ND0020-00096827.pdf")
ROOT = Path(__file__).resolve().parents[2] / "backups/baya-conciliacion-20261019"


def existing():
    return fetch_all("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento] LIKE ?", (226, "%96827%"))


def read(invoice_id):
    return {"cabecera": fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda=?", (invoice_id,)),
            "lineas": fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra=?", (invoice_id,)),
            "total": fetch_all("SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?", (invoice_id,)),
            "vencimientos": fetch_all("SELECT * FROM dbo.[Vencimiento Compras] WHERE IdCompra=?", (invoice_id,)),
            "relaciones": get_documentos_relacionados(invoice_id)}


def verify(state):
    c = state["cabecera"][0]
    assert c["IdContacto"] == 226 and c["Nro Documento"] == NUMBER and c["Tipo documento"] == "Nota de Débito"
    assert c["Moneda"] == "Dolares" and c["Tipo de Cambio"] == 349.95 and not c["Ajusta Tipo Cambio"]
    assert c["Fecha"].date() == date(2023, 8, 28) and c["Fecha Vto"].date() == date(2023, 8, 29)
    assert c["Documento Original"] == str(PDF) and len(state["lineas"]) == 1
    line = state["lineas"][0]
    assert line["Cantidad"] == 1 and line["Precio Unitario"] == 540.88 and line["IVA"] == 21
    assert line["IdRubro"] == 2047893443 and line["Ajuste financiero"]
    assert round(state["total"][0]["ImporteDocumento"], 2) == 654.46
    assert sorted(r["idCompra"] for r in state["relaciones"]) == RELATED
    assert len(state["vencimientos"]) == 1


def save(path, data):
    path.write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    _assert_target_is_wc()
    assert SOURCE.is_file() and PDF.parent.is_dir()
    if PDF.exists():
        assert hashlib.sha256(PDF.read_bytes()).digest() == hashlib.sha256(SOURCE.read_bytes()).digest()
    else:
        shutil.copy2(SOURCE, PDF)
    rows = existing()
    if rows:
        assert len(rows) == 1
        verify(read(rows[0]["IdDeuda"]))
        print("Nota ya cargada:", rows[0]["IdDeuda"])
        return
    documents = fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda IN (?,?,?) ORDER BY IdDeuda", tuple(RELATED))
    assert len(documents) == 3 and all(r["IdContacto"] == 226 for r in documents)
    payment = fetch_all("SELECT * FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?", (1375,))
    backup = backup_verificado("baya-nd96827-036")
    path = ROOT / f"nd96827-alta-{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    audit = {"autorizacion": "Sergio: registrala en el sistema", "respaldo": backup, "pdf": str(PDF),
             "sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(), "facturasRelacionadasAntes": documents, "pagoAntes": payment,
             "criterio": "RI33178 incluye FC320048/320049/336203 y ND96827; relacion documental sin nuevo pago ni FIFO"}
    save(path, audit)
    with reconciliation_transaction():
        assert not existing()
        before = fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"]
        invoice_id = create_compra(
            {"idContacto": 226, "fecha": date(2023, 8, 28), "tipoDocumento": "Nota de Débito", "tipo": "A", "numeroDocumento": NUMBER,
             "moneda": "Dolares", "tipoDeCambio": 349.95, "documentoOriginal": str(PDF), "ajustaTipoCambio": False},
            [{"productoServicio": "Gastos financiacion tarjeta NERA - 2%", "cantidad": 1, "unidad": "USD",
              "precioUnitario": 540.88, "iva": 21, "idRubro": 2047893443, "idCentroCosto": 3, "idDestino": 1,
              "campaña": "No Aplica", "ajusteFinanciero": True}],
            [{"fechaVencimiento": date(2023, 8, 29)}],
        )
        execute_write_transaction([
            ("UPDATE dbo.Compras SET [Fecha Vto]=? WHERE IdDeuda=?", (datetime(2023, 8, 29), invoice_id)),
            ("UPDATE dbo.Det_Compras SET IdCampaña=? WHERE IdCompra=?", (20, invoice_id)),
        ])
        for related in RELATED:
            agregar_documento_relacionado(invoice_id, related)
        state = read(invoice_id)
        verify(state)
        assert fetch_all("SELECT * FROM dbo.Compras WHERE IdDeuda IN (?,?,?) ORDER BY IdDeuda", tuple(RELATED)) == documents
        assert fetch_all("SELECT * FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?", (1375,)) == payment
        after = fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (226,))[0]["saldo"]
        assert abs(Decimal(str(before)) - Decimal(str(after)) - Decimal(str(state["total"][0]["ImporteDocumento"]))) < Decimal("0.001")
        audit.update(idCompra=invoice_id, despues=state, saldoBaseAntes=before, saldoBaseDespues=after)
        save(path, audit)
    assert read(invoice_id) == state
    print("Nota creada:", invoice_id, "Total USD654,46. Respaldo verificado:", backup)
    print("Relacionada con tres facturas; pago original sin cambios. Auditoria:", path)


if __name__ == "__main__":
    main()
