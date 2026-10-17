"""036 — Cierre de Eduardo Santos (579), 17/10/2026 (Sergio).

La factura 00002-162 (siembra, $5.918.380,10) se pagó con retención $105.776,60 + transferencia Galicia $112.603,40 y el
eCheq de Cargill 80557827 por $5.700.000 (fecha de pago 20/01/2025), endosado a Santos el 21/01/2025
(PDF: Cuentas a pagar\\Cheques electronicos\\Santos, Eduardo\\E cheq 80557827 (Cargill).pdf). El endoso figuraba en
ChequesEntregados pero no en Valores Recibidos: se carga como los demás cheques de Cargill (BBVA, endoso a tercero),
lo que registra el cobro a Cargill (258) y el pago a Santos.

Uso (desde backend/): python -m scripts.cierre_santos_20261017
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.vinculos.backup import backup_verificado

if __name__ == "__main__":
    if fetch_all("SELECT 1 x FROM dbo.[Valores Recibidos] WHERE [Numero Valor] = 80557827"):
        raise SystemExit("El cheque 80557827 ya está cargado")
    print("Respaldo verificado:", backup_verificado("cierre-santos-036"))
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        nuevo = cur.execute("SELECT ISNULL(MAX(IdValor), 0) + 1 FROM dbo.[Valores Recibidos] WITH (UPDLOCK, HOLDLOCK)").fetchone()[0]
        cur.execute("INSERT INTO dbo.[Valores Recibidos] (IdValor, [Numero Valor], Banco, [Fecha Emision], [Fecha Vencimiento], "
                    "[Fecha Endoso], IdEmisor, IdReceptor, Importe, Destino, Imagen) "
                    "VALUES (?, 80557827, 'BBVA', '2025-01-20', '2025-01-20', '2025-01-21', 258, 579, 5700000.00, 'Endoso a tercero', ?)",
                    nuevo, r"Cuentas a pagar\Cheques electronicos\Santos, Eduardo\E cheq 80557827 (Cargill).pdf")
        conn.commit()
        print("Valores Recibidos IdValor", nuevo)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(fetch_all("SELECT SUM(ISNULL(Credito,0)-ISNULL(Deuda,0)) s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=579"))
