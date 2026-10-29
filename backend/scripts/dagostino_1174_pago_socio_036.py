"""D'Agostino (212): F-A 00002-00001174 del 28/08/2019 ($3.200), pagada por Sergio en efectivo el 16/08/2019.

El pago ya está en su cuenta de socio (MovimientosCuentaSocio 1936, Devolución, "Escribania Buira – Certificaciones
Aval Rural"); se vincula como pago por socio, igual que Pablo Car. Renglones según el PDF (sellos no gravados + honorarios
21%), mismo rubro y centro de costo que las otras facturas de la escribana. Idempotente; saldo de la 212 queda igual.

Uso (desde backend/): python -m scripts.dagostino_1174_pago_socio_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

C, NRO, MOV_SOCIO = 212, "00002-00001174", 1936
PDF = r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2019 - 03 2020\20190828_AlejandraDAgostino.pdf"
LINEAS = [("Sellos certificacion de firmas (2)", 190.00, 0), ("Honorarios certif. firmas (Acta 121 L-102)", 2487.60, 21)]


def saldo():
    return fetch_all("SELECT ROUND(SUM(Credito - Deuda), 2) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,))[0]["s"]


if __name__ == "__main__":
    _assert_target_is_wc()
    antes = saldo()
    if not fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (C, NRO)):
        assert not fetch_all("SELECT 1 AS x FROM dbo.PagosSocioProveedor WHERE IdMovimientoSocio = ?", (MOV_SOCIO,))
        print("Respaldo verificado:", backup_verificado("dagostino-1174-pago-socio"))
        execute_write_transaction([
            ("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], "
             "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], "
             "[Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio], [Documento Original]) OUTPUT INSERTED.IdDeuda "
             "VALUES ('2019-08-28', ?, 'A', 'Factura', ?, 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?)", (C, NRO, PDF)),
            *[(lambda texto, imp, iva: (lambda r: ("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, "
                                                   "IdCentroCostos, IdDestino, IdRubro, IdCampaña, [Campaña], [Precio Unitario], IVA, "
                                                   "[Ajuste financiero]) VALUES (?, 1, ?, 0, 3, 1, 14, 20, 'No Aplica', ?, ?, 0)",
                                                   (r[0], texto, imp, iva))))(t, i, v) for t, i, v in LINEAS],
            ("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio, IdContacto, Criterio) VALUES (?, ?, 'manual')", (MOV_SOCIO, C)),
        ])
    print(fetch_all("SELECT v.ImporteDocumento t FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda "
                    "WHERE c.IdContacto = ? AND c.[Nro Documento] = ?", (C, NRO)))
    print("Saldo D'Agostino antes/después:", antes, saldo())
