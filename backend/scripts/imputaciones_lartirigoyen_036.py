"""036 — Lartirigoyen (61), 18/10/2026: imputaciones de pagos rehechas según la aplicación real de Lartirigoyen.

Las 116 imputaciones 'automatica-exacta' de la cuenta mezclaban dólares con pesos y aplicaban pagos de 2020-2023 a
facturas de 2016-2019 (bloqueaban el criterio C5). Se anulan y se rehacen en orden cronológico, como aplica
Lartirigoyen (resúmenes 2018-2026): cada crédito en pesos cancela los documentos pendientes más viejos (las facturas en
dólares por su valor al TC de la factura); lo que ya cubre la tarjeta no se vuelve a imputar. Se graban las
imputaciones de pagos bancarios, liquidaciones de granos, retenciones y NC; los ajustes de cuenta corriente consumen
documentos en el orden pero no generan imputación. Idempotente.

Uso (desde backend/): python -m scripts.imputaciones_lartirigoyen_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U = 61, "Sergio (barrida 036)"
NOTA = "Aplicación según resúmenes de Lartirigoyen (orden cronológico, TC de la factura) — barrida 036 18/10/2026"
MEDIO = {"Banco Nacion": "bna", "Galicia": "galicia", "Venta Granos": "comp-venta-granos", "Retenciones": "retenciones", "Compras": "comp-compra"}

if __name__ == "__main__":
    _assert_target_is_wc()
    filas = bimonetaria.cargar_cuenta(C, refrescar=True)["filas"]
    tarjeta = {r["i"]: float(r["s"]) for r in fetch_all(
        "SELECT t.IdCompra AS i, SUM(t.ImporteImputado) AS s FROM dbo.Tarjetas_Resumenes_Lineas_Compras t "
        "JOIN dbo.Compras c ON c.IdDeuda = t.IdCompra WHERE c.IdContacto = ? GROUP BY t.IdCompra", (C,))}
    abiertos: list[list] = []   # [IdDeuda, pesos pendientes]
    lotes: list[list] = []      # [medio o None, IdMovimiento, pesos sin aplicar]
    nuevas: list[tuple] = []

    def aplicar():
        while abiertos and lotes:
            doc, lote = abiertos[0], lotes[0]
            x = round(min(doc[1], lote[2]), 2)
            if lote[0] and x >= 0.01:
                nuevas.append((lote[0], lote[1], doc[0], x))
            doc[1] -= x; lote[2] -= x
            if doc[1] <= 0.005: abiertos.pop(0)
            if lote[2] <= 0.005: lotes.pop(0)

    for f in filas:
        if f["origenTipo"] in ("Tarjetas", "Tarjeta sin imputar"):
            continue  # la tarjeta ya está imputada a sus facturas
        if f["origenTipo"] == "Compras" and f["deudaPesos"]:
            resto = round(f["deudaPesos"] - tarjeta.get(f["idOrigen"], 0.0), 2)
            if resto > 0.005: abiertos.append([f["idOrigen"], resto])
        elif f["creditoPesos"]:
            lotes.append([MEDIO.get(f["origenTipo"]), f["idOrigen"], f["creditoPesos"]])
        elif f["deudaPesos"]:
            continue  # débitos bancarios (pagos de Lartirigoyen a nosotros) y ajustes Deuda: subcuenta en pesos
        aplicar()
    print("Documentos sin cubrir:", [(d, round(p, 2)) for d, p in abiertos][:10], " créditos sin aplicar:", round(sum(l[2] for l in lotes), 2))
    print("Imputaciones nuevas:", len(nuevas))
    print("Respaldo verificado:", backup_verificado("imputaciones-lartirigoyen-036"))
    stmts = [("UPDATE a SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() "
              "FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
              "WHERE c.IdContacto = ? AND a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0",
              ("Reemplazada por la aplicación según resúmenes de Lartirigoyen (barrida 036)", U, C))]
    stmts += [("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, "
               "ImporteAplicado, Fecha, Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, 'CompraDeuda', ?, ?, SYSDATETIME(), ?, 0, 'manual', ?)",
               (m, i, d, x, U, NOTA)) for m, i, d, x in nuevas]
    execute_write_transaction(stmts)
