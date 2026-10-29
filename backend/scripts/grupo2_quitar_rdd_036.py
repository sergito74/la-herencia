"""036 — grupo 2: elimina las ND internas de redondeo del 30/09/2026 de Autopistas del Sol (RDD276, $1,01) y Grupo
Concesionario del Oeste (RDD306, $0,29). Compensaban centavos de facturas pagadas con tarjeta que el 29/10/2026 se
redondearon en la propia factura (grupo2_redondeo_tarjeta_036); con las dos cosas los centavos quedaban contados dos
veces. Después de quitarlas, el saldo de cada cuenta = sus facturas de octubre aún sin resumen de tarjeta.
Uso (desde backend/): python -m scripts.grupo2_quitar_rdd_036 [--aplicar]
"""

from __future__ import annotations

import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

DOCS = {2143523815: "RDD276-260930", 2143523816: "RDD306-260930"}

if __name__ == "__main__":
    _assert_target_is_wc()
    hay = fetch_all(f"SELECT IdDeuda AS i, [Nro Documento] AS n FROM dbo.Compras WHERE IdDeuda IN ({','.join(map(str, DOCS))})", ())
    assert all(DOCS[h["i"]] == h["n"] for h in hay), hay
    assert not fetch_all(f"SELECT 1 AS x FROM dbo.AplicacionesPago WHERE Anulada = 0 AND TipoDocumento = 'CompraDeuda' "
                         f"AND IdDocumentoAplicado IN ({','.join(map(str, DOCS))})", ())
    print("a eliminar:", hay)
    if "--aplicar" not in sys.argv or not hay:
        raise SystemExit("Simulación: usar --aplicar para grabar." if hay else "Nada pendiente.")
    respaldo = backup_verificado("grupo2-quitar-rdd-036")
    stmts = []
    for h in hay:
        stmts += [(f"DELETE FROM dbo.{t} WHERE IdCompra = ?", (h["i"],)) for t in ("Det_Compras", "[Vencimiento Compras]")]
        stmts.append(("DELETE FROM dbo.Compras WHERE IdDeuda = ?", (h["i"],)))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('grupo2-quitar-rdd-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({str(h["i"]): h["n"] for h in hay}), respaldo,
                   "ND internas de redondeo 30/09 eliminadas: los centavos quedaron redondeados en las facturas (29/10/2026).")))
    execute_write_transaction(stmts)
    print("Aplicado. Respaldo:", respaldo)
