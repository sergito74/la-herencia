"""036 — Juan Franco Rodríguez (379) y Martín Silva Rossi (228), 19/10/2026.

1. Rodríguez: la remuneración de abril 2025 ($64.500) se pagó en efectivo desde la Caja Efectivo Pesos de Giamigli el 23/04/2025
   ("Vacunacion y destete", MovimientosCajaEfectivo 1088); la Planilla de trabajos eventuales dice "22/04/2025 Juan Franco
   Rodriguez, Vacunacion y destete, 51.500 + 13.000 = 64.500, Pagado". Se carga el pago en efectivo y se vincula la caja.
2. Silva Rossi: la FC 00002-00006422 ($49.200, 08/09/2026) se pagó el 05/10/2026 por Galicia Office Banking (operación
   LRA5DR3858, concepto "Factura 6422"; comprobante enviado por mail a eagronomico.com.ar). Es posterior al corte: al
   30/09/2026 queda pendiente justificado hasta cargar el extracto de octubre. Sin cambios de datos.
Idempotente.

Uso (desde backend/): python -m scripts.rodriguez_silva_rossi_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

if __name__ == "__main__":
    _assert_target_is_wc()
    if fetch_all("SELECT 1 AS x FROM dbo.[Pagos efectivo] WHERE IdContacto = 379 AND Fecha = '2025-04-23' AND [Importe imputado] = 64500", ()):
        raise SystemExit("Ya cargado.")
    print("Respaldo verificado:", backup_verificado("rodriguez-silva-rossi-036"))
    execute_write_transaction([
        ("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, [Importe imputado]) "
         "VALUES (379, 1, 3, '2025-04-23', 'Blue', 'GiamigliSA', 64500)", ()),
        ("UPDATE dbo.MovimientosCajaEfectivo SET IdContactoRelacionado = 379 WHERE IdMovimiento = 1088 AND IdContactoRelacionado IS NULL", ()),
    ])
    print(fetch_all("SELECT SUM(Deuda - Credito) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = 379", ()))
