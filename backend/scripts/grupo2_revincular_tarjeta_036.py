"""036 — grupo 2: 4 consumos de tarjeta vinculados a la factura equivocada (aprobado por Sergio 29/10/2026).

Cada uno estaba colgado de la factura anterior del mismo proveedor y su factura había quedado sin vínculo:
- Corredores Viales: consumo 01/06/2025 $2.516,76 (línea 651) → 0104-09326292 (28/05/2025), no 0104-09001678.
- Grupo Concesionario del Oeste: consumo 20/03/2024 $1.100 (línea 463) → 0629-04979992 (17/03/2024), no 0629-04791492.
- Autopistas del Sol: consumo 25/10/2019 $534,10 (línea 1391) → 0711-00499234 (15/10/2019), no 0711-00445358.
- Autopistas del Sol: consumo 21/04/2022 $1.060 (línea 108) → 0711-02863496 (18/04/2022), no 0711-02807114.
Uso (desde backend/): python -m scripts.grupo2_revincular_tarjeta_036 [--aplicar]
"""

from __future__ import annotations

import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

# IdVinculo: (IdCompra actual, IdCompra correcta)
CAMBIOS = {615: (2143515051, 2143515087), 434: (2143514389, 2143514476), 1013: (2143512386, 2143512432), 99: (2143513622, 2143513621)}

if __name__ == "__main__":
    _assert_target_is_wc()
    actual = {r["v"]: r["c"] for r in fetch_all(
        f"SELECT IdVinculo AS v, IdCompra AS c FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdVinculo IN ({','.join(map(str, CAMBIOS))})", ())}
    pendientes = {v: (a, b) for v, (a, b) in CAMBIOS.items() if actual.get(v) == a}
    assert all(actual.get(v) in (a, b) for v, (a, b) in CAMBIOS.items()), actual
    print("a cambiar:", pendientes)
    if "--aplicar" not in sys.argv or not pendientes:
        raise SystemExit("Simulación: usar --aplicar para grabar." if pendientes else "Nada pendiente.")
    respaldo = backup_verificado("grupo2-revincular-tarjeta-036")
    execute_write_transaction(
        [("UPDATE dbo.Tarjetas_Resumenes_Lineas_Compras SET IdCompra = ? WHERE IdVinculo = ? AND IdCompra = ?", (b, v, a))
         for v, (a, b) in pendientes.items()]
        + [("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
            "VALUES ('grupo2-revincular-tarjeta-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
            (json.dumps(pendientes), respaldo, "4 consumos de tarjeta pasados a su factura (estaban en la anterior)."))])
    print("Aplicado. Respaldo:", respaldo)
