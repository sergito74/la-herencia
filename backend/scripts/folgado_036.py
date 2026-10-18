"""036 — Folgado, Martín (420), 18/10/2026.

- FC 00011-00001105 (30/12/2025, semilla de sorgo Hulk): el PDF es en dólares, US$847 (neto 700 + IVA 147); estaba cargada en
  pesos ($847). Se pagó con 4 cuotas de $308.519,75 (= US$847 x 1.457).
- ND 00011-00000140 ($16.871,33, 24/01/2025) y ND "FALTA COPIA" ($1.688,77, 30/12/2020): diferencias de cambio en pesos de
  facturas en dólares (se pagaron junto con ellas) → ajuste de tipo de cambio (no mueven dólares): la cuenta gobierna en dólares.
- Valuación en dólares: Folgado cobra al TC de su factura (cuotas exactas), así que cada pago vale los US$ de la factura que
  paga (pesos / TC de la factura); las ND en pesos y la venta de hacienda con sus dos cobros no mueven dólares.
Idempotente.

Uso (desde backend/): python -m scripts.folgado_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C = 420

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("folgado-036"))
    execute_write_transaction([
        ("UPDATE dbo.Compras SET Moneda = 'Dolares' WHERE IdDeuda = 2143515347 AND IdContacto = ?", (C,)),
        ("UPDATE dbo.Compras SET [Ajusta Tipo Cambio] = 1 WHERE IdDeuda IN (2143514955, 2143514469) AND IdContacto = ?", (C,)),
    ])
    bloques = [  # (TC de la factura, US$ del bloque, [(Origen, IdOrigen, pesos aplicados a la factura)])
        (74.25, 355.50, [("Banco Nacion", 18564, 355.50 * 74.25)]),
        (98.46, 312.79, [("Galicia", 202, None)]), (99.86, 369.66, [("Galicia", 272, None)]),
        (156.91, 1034.55, [("Galicia", 1165, None)]),
        (350.0, 1225.13, [("Retenciones", 110, None), ("Galicia", 1575, None)]),
        (962.0, 471.90, [("Retenciones", 172, None), ("Galicia", 2170, None), ("Galicia", 2235, None), ("Galicia", 2277, None),
                          ("Galicia", 2336, None), ("Galicia", 2397, None), ("Galicia", 2459, None)]),
        (1047.0, 11247.56, [("Retenciones", 189, None), ("Galicia", 2373, None), ("Galicia", 2413, None), ("Galicia", 2473, None),
                             ("Galicia", 2526, None)]),
        (1457.0, 847.00, [("Retenciones", 225, None), ("Galicia", 2998, None), ("Galicia", 3021, None), ("Galicia", 3077, None),
                          ("Galicia", 3119, None)]),
    ]
    filas = {(f["origenTipo"], f["idOrigen"]): f for f in bimonetaria.cargar_cuenta(C, refrescar=True)["filas"]}
    val = {}
    for tc, usd, pagos in bloques:
        for o, i, pesos in pagos:
            val[(o, i)] = round((pesos if pesos is not None else filas[(o, i)]["creditoOriginal"]) / tc, 4)
        ultimo = (pagos[-1][0], pagos[-1][1])
        val[ultimo] = round(val[ultimo] + usd - sum(val[(o, i)] for o, i, _ in pagos), 4)   # lo que excede es la ND en pesos
    # Imputaciones por bloque (criterio C5): cada pago a la factura de su bloque; el excedente de pesos, a la ND del bloque
    medio = {"Banco Nacion": "bna", "Galicia": "galicia", "Retenciones": "retenciones"}
    docs = {74.25: [(2143512875, 26395.73), (2143514469, 1688.77)], 98.46: [(2143513351, None)], 99.86: [(2143513402, None)],
            156.91: [(2143513817, None)], 350.0: [(2143514353, None)], 962.0: [(2143514797, None)],
            1047.0: [(2143514944, None), (2143514945, None), (2143514955, 16871.33)], 1457.0: [(2143515347, None)]}
    imput = []
    for tc, usd, pagos in bloques:
        cap = [[d, imp if imp is not None else None] for d, imp in docs[tc]]
        for d in cap:
            if d[1] is None:
                d[1] = round(fetch_all("SELECT ImporteDocumento * [Tipo de Cambio] t FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda = ?", (d[0],))[0]["t"], 2)
        for o, i, _ in pagos:
            resto = filas[(o, i)]["creditoOriginal"]
            for d in cap:
                x = round(min(resto, d[1]), 2)
                if x >= 0.01:
                    imput.append((medio[o], i, d[0], x)); d[1] -= x; resto -= x
            # sobrante de centavos: queda sin imputar
    st_imp = [("UPDATE a SET Anulada = 1, MotivoAnulacion = 'Reemplazada por imputación por bloques (barrida 036)', UsuarioAnulacion = 'Sergio (barrida 036)', "
               "FechaAnulacion = SYSDATETIME() FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
               "WHERE c.IdContacto = ? AND a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0", (C,))]
    st_imp += [("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, Fecha, "
                "Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, 'CompraDeuda', ?, ?, SYSDATETIME(), 'Sergio (barrida 036)', 0, 'manual', "
                "'Barrida 036: pago a la factura de su bloque (cuotas al TC de la factura)')", x) for x in imput]
    execute_write_transaction(st_imp)
    print("Imputaciones:", len(imput))
    for k in [("Venta Hacienda", 146), ("Galicia", 3002), ("Galicia", 3055)]:
        val[k] = 0.0
    st = [("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", (C,))]
    st += [("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) VALUES "
            "(?, ?, ?, ?, 'Pago al TC de la factura de Folgado (cuotas exactas), Sergio 18/10/2026', NULL, 'Sergio (barrida 036)', SYSDATETIME())",
            (o, i, C, d)) for (o, i), d in val.items()]
    execute_write_transaction(st)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("pesos", r["saldoPesos"], " US$", r["saldoDolares"], r["gobierna"])
    for f in r["filas"]:
        if abs(f["saldoDolares"]) > 0.5 and f["fecha"].year >= 2025:
            print(" ", f["fecha"], f["numeroDocumento"], f["moneda"][:3], round(f["deudaOriginal"], 2), round(f["creditoOriginal"], 2), f["saldoPesos"], f["saldoDolares"])
