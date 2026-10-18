"""Movistar (71): factura 2467-01676367 del 14/10/2026 ($243.640,80), bajada del mail del 18/10/2026.

PDF armado con factura + cuadro resumen + anexos de las 4 líneas: Dropbox "Compras/04 2026 - 03 2027/20261014_Movistar.pdf".
Mismo formato que sep-2026: un renglón por línea al 80% del cuadro resumen (bonificación; suma $187.416 = neto de la factura),
IVA 27% y percepción de IVA $5.622,48 en su campo. Idempotente.

Uso (desde backend/): python -m scripts.movistar_octubre_2026_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

C, NRO = 71, "2467-01676367"
PDF = r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2026 - 03 2027\20261014_Movistar.pdf"
LINEAS = [("1141564524", 54392.00), ("2314610470", 24240.00), ("1150644900", 54392.00), ("1128618159", 54392.00)]

if __name__ == "__main__":
    _assert_target_is_wc()
    if not fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (C, NRO)):
        print("Respaldo verificado:", backup_verificado("movistar-oct-2026"))
        execute_write_transaction([
            ("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], "
             "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], "
             "[Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio], [Documento Original]) OUTPUT INSERTED.IdDeuda "
             "VALUES ('2026-10-14', ?, 'A', 'Factura', ?, 'Pesos', 1, 0, 5622.48, 0, 0, 0, 0, 0, 0, 0, 0, ?)", (C, NRO, PDF)),
            *[(lambda linea, imp: (lambda r: ("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, "
                                              "IdDestino, IdRubro, IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) "
                                              "VALUES (?, 1, ?, 0, 3, 1, 21, 20, 'No Aplica', ?, 27, 0)",
                                              (r[0], f"Tel. movil {linea} - 14/10 al 13/11/2026", imp))))(l, i) for l, i in LINEAS],
        ])
    print(fetch_all("SELECT v.ImporteDocumento t FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda "
                    "WHERE c.IdContacto = ? AND c.[Nro Documento] = ?", (C, NRO)))
    print("Saldo Movistar:", fetch_all("SELECT SUM(Credito - Deuda) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,)))
