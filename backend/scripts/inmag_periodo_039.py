"""039: tabla del INMAG oficial por período y reliquidación de octubre 2026 (id 2, sin factura) como borrador."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import _assert_target_is_wc, get_connection  # noqa: E402
from src.features.pastaje import repository as repo, service  # noqa: E402
from src.features.vinculos.backup import backup_verificado  # noqa: E402

_assert_target_is_wc()
print("backup", backup_verificado("pastaje_inmag_periodo"))
with get_connection(readonly=False) as conn:
    cursor = conn.cursor()
    cursor.execute("""IF OBJECT_ID('dbo.IndiceINMAGPeriodo') IS NULL
        CREATE TABLE dbo.IndiceINMAGPeriodo (Desde date NOT NULL, Hasta date NOT NULL, Promedio decimal(18,3) NOT NULL,
        Fuente nvarchar(300) NOT NULL, ObtenidoEn datetime2 NOT NULL DEFAULT SYSDATETIME(),
        CONSTRAINT PK_IndiceINMAGPeriodo PRIMARY KEY (Desde, Hasta))""")
    conn.commit()
liq = repo.liquidacion(2)
if liq["estado"] == "confirmada":
    service.anular_liquidacion(2, liq["version"], "Claude (pedido de Sergio 02/11/2026)")
nueva = service.crear_borrador(liq["idContrato"], date(2026, 10, 1), "Claude (pedido de Sergio 02/11/2026)")
print({k: nueva[k] for k in ("id", "estado", "precioPromedio", "kg", "neto", "iva", "total")})
print("anulada:", repo.liquidacion(2)["estado"], "| septiembre:", service.diferencia(1))
