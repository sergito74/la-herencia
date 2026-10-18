"""036 — Movistar (71), 18/10/2026: factura 2467-01359217 del 14/06/2025 ($148.353,77), la que faltaba.

Sergio consiguió la copia (Dropbox "Compras/04 2025 - 03 2026/20250614_Movistar.pdf"). Se carga con el formato de las demás
facturas de Movistar: neto $109.516 al 27% de IVA; percepciones IIBB ($219,03) + IVA ($3.285,48) en "Ingresos Brutos";
impuestos internos ($5.763,94) en "Conceptos no gravados". La paga el débito Galicia del 26/06/2025, que ya estaba cargado.
Idempotente.

Uso (desde backend/): python -m scripts.movistar_junio_2025_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

C, NRO, MODELO = 71, "2467-01359217", 2143515082
PDF = r"..\..\..\Dropbox\Giamigli de Bolivar SA\Compras\04 2025 - 03 2026\20250614_Movistar.pdf"

if __name__ == "__main__":
    _assert_target_is_wc()
    if not fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (C, NRO)):
        m = fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra = ?", (MODELO,))[0]
        print("Respaldo verificado:", backup_verificado("movistar-junio-2025-036"))
        execute_write_transaction([
            ("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], "
             "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], "
             "[Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio], [Documento Original]) OUTPUT INSERTED.IdDeuda "
             "VALUES ('2025-06-14', ?, 'A', 'Factura', ?, 'Pesos', 1, 3504.51, 0, 5763.94, 0, 0, 0, 0, 0, 0, 0, ?)", (C, NRO, PDF + "#" + PDF + "#")),
            lambda r: ("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, IdRubro, "
                       "IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) VALUES (?, 1, 'Servicio Telefonia', 0, ?, ?, ?, ?, ?, 109516, 27, 0)",
                       (r[0], m["IdCentroCostos"], m["IdDestino"], m["IdRubro"], m["IdCampaña"], m["Campaña"])),
        ])
    print(fetch_all("SELECT v.ImporteDocumento t FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda WHERE c.IdContacto = ? AND c.[Nro Documento] = ?", (C, NRO)))
    print("Saldo:", fetch_all("SELECT SUM(Credito - Deuda) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,)))
