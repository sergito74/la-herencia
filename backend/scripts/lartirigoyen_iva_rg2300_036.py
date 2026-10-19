"""036 — Lartirigoyen (61), 19/10/2026: IVA RG 2300/2007 de la liquidación de maíz COE 330215602055 (Venta Granos 112).

La liquidación (PDF Ventas/04 2020 - 03 2021/20200530_Lartirigoyen.pdf) tiene como deducciones solo el sellado ($136,05) y
la comisión ($197 + IVA); el "IVA RG 2300/2007" ($530,91) no es una deducción: es la parte del IVA que el comprador paga
aparte ("Pago según condiciones" $9.516,79 + IVA RG 2300 = neto a pagar $10.047,70). Estaba cargado como deducción
"Percepcion IVA" y el pago completo (OP 0012-00188537, BNA $10.047,70) se había compensado con el AjusteCuentaCorriente 24
($530,90). Se borra la deducción y el ajuste. El ingreso del maíz no cambia (es IVA). Idempotente.
(El mismo patrón está en la VG 110 de Lartirigoyen y en liquidaciones de Cargill y Baya Casal: se revisa con cada cuenta.)

Uso (desde backend/): python -m scripts.lartirigoyen_iva_rg2300_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("lartirigoyen-iva-rg2300-036"))
    execute_write_transaction([
        ("DELETE FROM dbo.[Venta Granos_Deducciones] WHERE IdDeduccion = 227 AND IdVenta = 112 AND Detalle = 'Percepcion IVA'", ()),
        ("DELETE FROM dbo.RevisionPagosSinFactura WHERE IdContacto = 61 AND Medio = 'ajuste-interno' AND IdMovimiento = 24", ()),
        ("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = 61 AND Origen = 'Ajuste Interno' AND IdOrigen = 24", ()),
        ("DELETE FROM dbo.AjustesCuentaCorriente WHERE IdAjuste = 24 AND IdContacto = 61", ()),
    ])
    print(fetch_all("SELECT Credito FROM dbo.vw_MovimientosCuenta_Saldo WHERE Origen = 'Venta Granos' AND IdOrigen = 112", ()))
