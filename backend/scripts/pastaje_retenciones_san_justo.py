r"""Certificados SICORE de Ganancias de Ganadera San Justo (5671) sobre las facturas de pastaje, 11/11/2026: cargados en
[Retenciones Ventas Hacienda] (retenciones recibidas en ventas) con su PDF, e imputados a la factura que los origina.
Fuente: Dropbox\Giamigli de Bolivar SA\Ventas\Retenciones 04 2026 - 03 2027. Idempotente."""
from src.db.connection import _assert_target_is_wc, execute_insert_returning_id, execute_write, fetch_one
from src.features.pastaje.repository import cobrado, saldo_documento
from src.features.aplicaciones_pago import repository as ap

CARPETA = r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\Retenciones 04 2026 - 03 2027"
CERTS = [("0000-2026-000056", "2026-10-07", 4473.63, "0-2026-0056 GIAMIGLI DE BOLIVAR S.A.  07 10 2026.pdf", 1),
         ("0000-2026-000062", "2026-11-04", 27510.87, "0-2026-0062 GIAMIGLI DE BOLIVAR S.A.  04 11 2026.pdf", 2)]


def main():
    _assert_target_is_wc()
    for nro, fecha, imp, archivo, id_fac in CERTS:
        r = fetch_one("SELECT Id FROM dbo.[Retenciones Ventas Hacienda] WHERE IdContacto=5671 AND [Nro Documento]=?", (nro,))
        i = r["Id"] if r else execute_insert_returning_id(
            "INSERT INTO dbo.[Retenciones Ventas Hacienda] (Id,Fecha,IdContacto,Documento,[Nro Documento],Importe,Imagen) "
            "OUTPUT INSERTED.Id SELECT ISNULL(MAX(Id),0)+1,?,5671,'Cert. Retencion Ganancias',?,?,? FROM dbo.[Retenciones Ventas Hacienda]",
            (fecha, nro, imp, CARPETA + "\\" + archivo))
        if not ap.aplicaciones_vigentes_de_movimiento("ret-ventas-hacienda", i):
            saldo = float(saldo_documento(id_fac)["total"] - cobrado([id_fac])[id_fac])
            if round(imp - saldo, 2) > 0.01:  # el certificado de septiembre trae 1 centavo más que el saldo
                raise SystemExit(f"{nro}: {imp} supera el saldo de la factura {saldo}")
            execute_write("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,"
                          "ImporteAplicado,Usuario) VALUES ('ret-ventas-hacienda',?,'Pastaje',?,?,'Claude (11/11/2026)')", (i, id_fac, imp))
        print(nro, "id", i)


if __name__ == "__main__":
    main()
