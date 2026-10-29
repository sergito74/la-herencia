"""036 — grupo 3: redondeos verificados a mano que el automático (`grupo3_redondeo_036`) no toma.

Son cuentas donde varias facturas tienen centavos de signo distinto, y un paso del automático no acerca el saldo a cero.
Cada importe nuevo es la suma exacta de los pagos de esa factura (transferencia + retención); todas ≤0,10%
(regla 29/10/2026). Mismo método: escalar precios de renglones o ajustar "Gastos Varios". Idempotente.
Uso (desde backend/): python -m scripts.grupo3_redondeo_manual_036 [--aplicar]
"""

from __future__ import annotations

import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

NUEVOS = {
    -1575687583: 8924.01,      # Agronomía El Amanecer: BNA 8.410,11 + NC 513,90
    2143513533: 2244.00,       # PC Electro Tigre: pago 2.244,00
    2143514777: 36000.00,      # PC Electro Tigre: pago 36.000,00
    2143514062: 287617.00,     # Reynoso: 3.410,60 + 140.397,90 + 143.808,50
    2143513415: 232320.00,     # Reynoso: 5.760 + 20.160 + 90.240 + 116.160
    2143515150: 2320500.00,    # Sabattini: 37.520 + 2.282.980
    2143515258: 10690875.00,   # Sabattini: 192.156,60 + 10.498.718,40
    2143515332: 4143750.00,    # Sabattini: 73.656,60 + 4.070.093,40
    2143517482: 4596800.00,    # Sabattini: 81.856,60 + 4.514.943,40
}


def casos() -> list[dict]:
    filas = fetch_all(
        "SELECT v.IdDeuda AS i, v.ImporteDocumento AS v, t.GranTotal AS g, t.TotalDetalleCompra AS d "
        "FROM dbo.vw_Compras_ImporteDocumento v JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda = v.IdDeuda "
        f"WHERE v.IdDeuda IN ({','.join(map(str, NUEVOS))})", ())
    salida = []
    for f in filas:
        total, nuevo = float(f["v"]), NUEVOS[f["i"]]
        if abs(total - nuevo) >= 0.005:
            assert abs(total - nuevo) / nuevo <= 0.001, f["i"]
            salida.append({**f, "total": total, "nuevo": nuevo})
    return salida


if __name__ == "__main__":
    _assert_target_is_wc()
    filas = casos()
    for f in filas:
        print(f["i"], round(f["total"], 4), "->", f["nuevo"])
    if "--aplicar" not in sys.argv or not filas:
        raise SystemExit("Simulación: usar --aplicar para grabar." if filas else "Nada pendiente.")
    respaldo = backup_verificado("grupo3-redondeo-manual-036")
    stmts = []
    for f in filas:
        g, d = float(f["g"]), float(f["d"] or 0)
        if abs(d) > 1e-6:
            stmts.append(("UPDATE dbo.Det_Compras SET [Precio Unitario] = [Precio Unitario] * ? WHERE IdCompra = ?",
                          ((f["nuevo"] - (g - d)) / d, f["i"])))
        else:
            stmts.append(("UPDATE dbo.Compras SET [Gastos Varios] = ISNULL([Gastos Varios], 0) + ? WHERE IdDeuda = ?",
                          (f["nuevo"] - f["total"], f["i"])))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('grupo3-redondeo-manual-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({str(f["i"]): [f["total"], f["nuevo"]] for f in filas}), respaldo,
                   f"{len(filas)} facturas de cuentas chicas redondeadas a la suma de sus pagos (≤0,10%, regla 29/10/2026).")))
    execute_write_transaction(stmts)
    print("Aplicado. Respaldo:", respaldo, " quedan:", len(casos()))
