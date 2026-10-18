"""036 — Rehace las imputaciones de pagos a documentos de UNA cuenta en pesos (decisiones de Sergio, barrida 036).

Para cuentas donde las imputaciones automáticas (`automatica-exacta`, `fifo-032`, ...) aplican pagos a facturas muy viejas o a
facturas que la tarjeta ya cubre (criterios C4/C5 de la ficha). Criterio, como en Lartirigoyen/Movistar (18/10/2026):
1. Cada crédito (pago bancario, efectivo, retención, NC, venta de granos) cancela primero el documento pendiente del MISMO
   importe (±$0,05) más cercano en fecha (hasta 120 días); si no hay, los pendientes más viejos (orden cronológico).
2. Lo que un documento ya tiene cubierto por la tarjeta (Tarjetas_Resumenes_Lineas_Compras) no se vuelve a imputar.
3. Se anulan las imputaciones activas de la cuenta y se graban las nuevas con origen 'manual'.
Solo cuentas sin documentos en dólares (las mixtas usan su propio script, p. ej. aplicacion_lartirigoyen_036).

Uso (desde backend/): python -m scripts.reimputar_cuenta_pesos_036 <idContacto> [--aplicar]
"""

from __future__ import annotations

import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

U = "Sergio (barrida 036)"
MEDIO = {"Banco Nacion": "bna", "Galicia": "galicia", "Pagos efectivo": "efectivo", "Retenciones": "retenciones",
         "Venta Granos": "comp-venta-granos", "Compras": "comp-compra"}


def plan(c: int):
    if fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdContacto = ? AND Moneda = 'Dolares'", (c,)):
        raise SystemExit("La cuenta tiene documentos en dólares: usar un script de aplicación propio.")
    filas = fetch_all("SELECT Fecha, Origen, IdOrigen, Deuda, Credito, [Nro Documento] AS n FROM dbo.vw_MovimientosCuenta_Saldo "
                      "WHERE IdContacto = ? ORDER BY Fecha, Origen, IdOrigen", (c,))
    tarjeta = {}
    for r in fetch_all("SELECT t.IdCompra AS i, SUM(t.ImporteImputado) AS s FROM dbo.Tarjetas_Resumenes_Lineas_Compras t "
                       "JOIN dbo.Compras x ON x.IdDeuda = t.IdCompra WHERE x.IdContacto = ? GROUP BY t.IdCompra", (c,)):
        tarjeta[r["i"]] = float(r["s"])
    docs = [{"id": f["IdOrigen"], "fecha": f["Fecha"], "cap": round(float(f["Deuda"]) - tarjeta.get(f["IdOrigen"], 0.0), 2)}
            for f in filas if f["Origen"] == "Compras" and f["Deuda"]]
    docs = [d for d in docs if d["cap"] > 0.005]
    nuevas, sobrante = [], 0.0
    for f in filas:
        if not f["Credito"] or f["Origen"] not in MEDIO:
            continue
        resto = round(float(f["Credito"]), 2)
        exacto = sorted((d for d in docs if d["cap"] > 0.005 and abs(d["cap"] - resto) <= 0.05
                         and abs((d["fecha"] - f["Fecha"]).days) <= 120), key=lambda d: abs((d["fecha"] - f["Fecha"]).days))
        orden = exacto[:1] + [d for d in docs if d not in exacto[:1]]
        for d in orden:
            if resto < 0.01:
                break
            if d["cap"] < 0.01:
                continue
            x = round(min(resto, d["cap"]), 2)
            nuevas.append((MEDIO[f["Origen"]], f["IdOrigen"], d["id"], x))
            d["cap"] = round(d["cap"] - x, 2); resto = round(resto - x, 2)
        sobrante += resto
    pendientes = round(sum(d["cap"] for d in docs), 2)
    return nuevas, pendientes, round(sobrante, 2)


if __name__ == "__main__":
    _assert_target_is_wc()
    c = int(sys.argv[1])
    nuevas, pendientes, sobrante = plan(c)
    print(f"Imputaciones: {len(nuevas)}; documentos con saldo sin imputar: ${pendientes:,.2f}; créditos sin aplicar: ${sobrante:,.2f}")
    if "--aplicar" not in sys.argv:
        print("Simulación: usar --aplicar para grabar.")
        raise SystemExit
    print("Respaldo verificado:", backup_verificado(f"reimputar-{c}-036"))
    st = [("UPDATE a SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() "
           "FROM dbo.AplicacionesPago a JOIN dbo.Compras x ON x.IdDeuda = a.IdDocumentoAplicado "
           "WHERE x.IdContacto = ? AND a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0",
           ("Reemplazada por reimputar_cuenta_pesos_036 (mismo importe, luego cronológico)", U, c))]
    st += [("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, "
            "Fecha, Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, 'CompraDeuda', ?, ?, SYSDATETIME(), ?, 0, 'manual', ?)",
            (m, i, d, x, U, "Barrida 036: mismo importe, luego cronológico")) for m, i, d, x in nuevas]
    execute_write_transaction(st)
