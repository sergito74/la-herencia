"""036 — lleva cada factura de una cuenta a su total redondeado al centavo (Jáuregui y Morales 48 por defecto).

La vista calcula el total como cantidad × precio × (1 + IVA) sin redondear (p. ej. $180,0049), y los medios
centavos de cada factura se arrastran a la siguiente en el FIFO. Un comprobante siempre cierra al centavo.
Método `grupo3_redondeo_036`: escalar renglones o ajustar Gastos Varios. Idempotente.
Redondea GranTotal (el total que se escala); hasta el 30/10/2026 usaba vw_Compras_ImporteDocumento y cambió
totales reales donde las vistas difieren (reparado por `reparar_centavo_exacto_036`).
Uso (desde backend/): python -m scripts.jym_centavo_exacto_036 [idContacto] [--aplicar]
"""

from __future__ import annotations

import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

C = next((int(a) for a in sys.argv[1:] if a.isdigit()), 48)


def casos() -> list[dict]:
    filas = fetch_all(
        "SELECT t.IdDeuda AS i, t.GranTotal AS v, t.GranTotal AS g, t.TotalDetalleCompra AS d FROM dbo.Compras c "
        "JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda = c.IdDeuda "
        "WHERE c.IdContacto = ? AND c.Moneda = 'Pesos'", (C,))
    return [{**f, "total": float(f["v"]), "nuevo": round(float(f["v"]), 2)} for f in filas
            if f["v"] and abs(float(f["v"]) - round(float(f["v"]), 2)) > 0.00005]


if __name__ == "__main__":
    _assert_target_is_wc()
    filas = casos()
    print(len(filas), "facturas con fracción de centavo; ajuste", round(sum(f["nuevo"] - f["total"] for f in filas), 4))
    if "--aplicar" not in sys.argv or not filas:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    respaldo = backup_verificado(f"centavo-exacto-{C}-036")
    stmts = []
    for f in filas:
        g, d = float(f["g"]), float(f["d"] or 0)
        stmts.append(("UPDATE dbo.Det_Compras SET [Precio Unitario] = [Precio Unitario] * ? WHERE IdCompra = ?", ((f["nuevo"] - (g - d)) / d, f["i"]))
                     if abs(d) > 1e-6 else
                     ("UPDATE dbo.Compras SET [Gastos Varios] = ISNULL([Gastos Varios], 0) + ? WHERE IdDeuda = ?", (f["nuevo"] - f["total"], f["i"])))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('jym-centavo-exacto-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({str(f["i"]): [f["total"], f["nuevo"]] for f in filas}), respaldo,
                   f"Cuenta {C}: {len(filas)} facturas llevadas a su total al centavo.")))
    execute_write_transaction(stmts)
    print("Aplicado. Respaldo:", respaldo, " quedan:", len(casos()))
