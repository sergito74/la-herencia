"""Compra de una yegua a Julio Cabrera (09/10/2024), sin factura, pagada en efectivo de la caja de Giamigli.

Sergio, 19/11/2026: "La compra se hizo sin factura y se pagó en efectivo. El contacto es Julio Cabrera pero no sé el CUIT."
En la caja (planilla migrada) ya estaban "Compra Yegua" −$ 1.000.000 (mov. 1059) y "Flete Yegua" −$ 50.000 (mov. 1060),
fondeadas ese día con dos retiros de Galicia y un aporte en efectivo. Se carga el contacto, la compra sin documento con
sus dos renglones y un pago en efectivo por cada movimiento de caja, aplicado a la compra. No cambia el saldo de la caja.

Idempotente; respaldo verificado antes de escribir.  Uso (desde backend/): python -m scripts.compra_yegua_cabrera
"""
from src.db.connection import _assert_target_is_wc, execute_insert_returning_id, execute_write, fetch_one
from src.features.vinculos.backup import backup_verificado

USUARIO = "Sergio (vía Claude)"


def main() -> None:
    _assert_target_is_wc()
    if fetch_one("SELECT IdPagoEfectivo AS p FROM dbo.MovimientosCajaEfectivo WHERE IdMovimiento = 1059")["p"]:
        print("Ya cargada.")
        return
    print("Respaldo:", backup_verificado("compra-yegua-cabrera"))
    c = fetch_one("SELECT IdContacto AS i FROM dbo.Contactos WHERE [Razon Social] = 'Julio Cabrera'")
    id_contacto = c["i"] if c else execute_insert_returning_id(
        "INSERT INTO dbo.Contactos ([Razon Social], [Tipo Contacto], [CUIT/CUIL], EsContratistaLabores) "
        "OUTPUT INSERTED.IdContacto VALUES ('Julio Cabrera', 'Proveedor', NULL, 0)", ())
    id_compra = execute_insert_returning_id(
        "INSERT INTO dbo.Compras (Fecha, IdContacto, [Tipo documento], Tipo, [Nro Documento], Moneda, [Tipo de Cambio], "
        "[Ingresos Brutos], [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], [Ley de Sellos], "
        "[Res gral 4169/96], [Ajusta Tipo Cambio], Suspendida, PercepcionIVA) OUTPUT INSERTED.IdDeuda "
        "VALUES ('2024-10-09', ?, 'Factura', 'X', 'SIN DOCUMENTO', 'Pesos', 1, 0,0,0,0,0,0,0,0, 0, 0, 0)", (id_contacto,))
    for producto, rubro, precio in (("Yegua (compra sin factura, pagada en efectivo)", 23, 1000000.0),
                                    ("Flete yegua", 2047893480, 50000.0)):
        execute_write(
            "INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, IdRubro, "
            "[IdCampaña], [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) VALUES (?, 1, ?, 0, 2, 1, ?, 20, 'No Aplica', ?, 0, 0)",
            (id_compra, producto, rubro, precio))
    for mov, importe in ((1059, 1000000.0), (1060, 50000.0)):
        id_pago = execute_insert_returning_id(
            "INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, [Importe imputado]) "
            "OUTPUT INSERTED.IdPagoEfectivo VALUES (?, 1, 3, '2024-10-09', 'Blue', 'GiamigliSA', ?)", (id_contacto, importe))
        execute_write("UPDATE dbo.MovimientosCajaEfectivo SET IdPagoEfectivo = ?, IdContactoRelacionado = ? WHERE IdMovimiento = ?",
                      (id_pago, id_contacto, mov))
        execute_write(
            "INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, "
            "Usuario, Origen, NotaConciliacion) VALUES ('efectivo', ?, 'CompraDeuda', ?, ?, ?, 'manual', 'Compra yegua Julio Cabrera 09/10/2024')",
            (id_pago, id_compra, importe, USUARIO))
    print(f"Contacto {id_contacto}, compra {id_compra}: yegua $ 1.000.000 + flete $ 50.000, pagadas en efectivo.")


if __name__ == "__main__":
    main()
