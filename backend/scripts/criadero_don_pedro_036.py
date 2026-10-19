"""036 — Criadero y Semillero Don Pedro (391), 19/10/2026: el pago BNA 18543 ($18.204,45, 30/09/2019) canceló la FC 0004-3502
(US$308,55, sorgo Hulk) y su ND en pesos de dif. de cambio ($154,28, ajuste de TC). Se valúa el pago en los US$308,55 de la
factura (el motor daba US$9,65 por usar el BNA del día). Idempotente.

Uso (desde backend/): python -m scripts.criadero_don_pedro_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U = 391, "Sergio (barrida 036)"

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("criadero-don-pedro-036"))
    execute_write_transaction([
        ("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", (C,)),
        ("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) VALUES "
         "('Banco Nacion', 18543, ?, 308.55, 'Pago de la FC 0004-3502 (US$308,55) y su ND de dif. de cambio', NULL, ?, SYSDATETIME())", (C, U)),
    ])
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo: pesos", r["saldoPesos"], " US$", r["saldoDolares"], r["gobierna"])
