"""036 — grupo 2: redondeo de facturas pagadas con tarjeta cuya diferencia con la línea vinculada es ≤0,10%.

Regla aprobada por Sergio el 29/10/2026 (estrategia-imputaciones-20261029.md, punto 4): hasta 0,10% la factura se
redondea a lo pagado. Método `cargill_fracciones_036`: escalar los precios de los renglones (o, sin renglones, ajustar
"Gastos Varios"). Solo facturas en pesos de cuentas pagadas exclusivamente con tarjeta. Idempotente.
Uso (desde backend/): python -m scripts.grupo2_redondeo_tarjeta_036 [--aplicar]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

LIMITE = 0.001


def casos() -> list[dict]:
    cuentas = [r["ct"] for r in fetch_all(
        "SELECT IdContacto AS ct FROM dbo.vw_MovimientosCuenta_Base GROUP BY IdContacto "
        "HAVING SUM(CASE WHEN Origen IN ('Tarjetas','Tarjeta sin imputar') THEN 1 ELSE 0 END) > 0 "
        "AND SUM(CASE WHEN Origen IN ('Banco Nacion','Galicia','Pagos efectivo','Pagos Valores Recibidos') AND Credito > 0 THEN 1 ELSE 0 END) = 0 "
        "AND SUM(CASE WHEN Origen = 'Compras' AND Deuda > 0 THEN 1 ELSE 0 END) > 0", ())]
    vinc = defaultdict(float)
    for r in fetch_all("SELECT IdCompra AS i, ImporteImputado AS x FROM dbo.Tarjetas_Resumenes_Lineas_Compras", ()):
        vinc[r["i"]] += float(r["x"] or 0)
    docs = fetch_all(
        "SELECT c.IdContacto AS ct, c.IdDeuda AS i, c.[Nro Documento] AS n, c.[Tipo documento] AS td, c.Moneda AS m, "
        "v.ImporteDocumento AS v, t.GranTotal AS g, t.TotalDetalleCompra AS d FROM dbo.Compras c "
        "JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda = c.IdDeuda "
        f"WHERE c.IdContacto IN ({','.join(map(str, cuentas))})", ())
    salida = []
    for d in docs:
        total, pagado = float(d["v"] or 0), round(vinc.get(d["i"], 0.0), 2)
        if d["m"] != "Pesos" or (d["td"] and "Cr" in d["td"]) or total <= 0 or pagado <= 0:
            continue
        if 0.005 <= abs(total - pagado) and abs(total - pagado) / total <= LIMITE:
            salida.append({**d, "total": total, "pagado": pagado})
    return salida


if __name__ == "__main__":
    _assert_target_is_wc()
    filas = casos()
    print(len(filas), "facturas; ajuste total", round(sum(f["pagado"] - f["total"] for f in filas), 2))
    if "--aplicar" not in sys.argv or not filas:
        raise SystemExit("Simulación: usar --aplicar para grabar." if filas else "Nada pendiente.")
    respaldo = backup_verificado("grupo2-redondeo-tarjeta-036")
    stmts = []
    for f in filas:
        g, d = float(f["g"]), float(f["d"] or 0)
        if abs(d) > 1e-6:
            stmts.append(("UPDATE dbo.Det_Compras SET [Precio Unitario] = [Precio Unitario] * ? WHERE IdCompra = ?",
                          ((f["pagado"] - (g - d)) / d, f["i"])))
        else:
            stmts.append(("UPDATE dbo.Compras SET [Gastos Varios] = ISNULL([Gastos Varios], 0) + ? WHERE IdDeuda = ?",
                          (f["pagado"] - f["total"], f["i"])))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('grupo2-redondeo-tarjeta-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({str(f["i"]): [f["total"], f["pagado"]] for f in filas}), respaldo,
                   f"{len(filas)} facturas pagadas con tarjeta redondeadas a lo cobrado (≤0,10%, regla 29/10/2026).")))
    execute_write_transaction(stmts)
    quedan = casos()
    print("Aplicado. Respaldo:", respaldo, " quedan:", len(quedan))
