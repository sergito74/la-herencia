"""036 — repara las facturas que `jym_centavo_exacto_036` (29/10/2026) llevó a un total equivocado.

El script tomaba como objetivo `vw_Compras_ImporteDocumento` pero escalaba los renglones para que `GranTotal` diera
ese número; donde las dos vistas difieren, cambió el total real de la factura (verificado contra LaHerencia y el PDF):
- Madelan (444): PDF $567.845,69 y $2.271.382,75 (70.000 por cabeza). Con eso la cuenta vuelve a cero.
- Ferias del Centro (39): PDF escaneado; vuelve al precio original de LaHerencia (15.200 y 18.000), el del cierre del 09/10.
- Catalpa (400): se llevó al PDF ($2.647.372,61) y se revirtió el mismo día a $2.647.371,85, el total con que se cerró
  la ficha el 17/10 (excepción $21.955,35); Sergio 30/10: la cuenta cierra en cero con el ajuste 163 de la retención 0000-2024-000005.
Uso (desde backend/): python -m scripts.reparar_centavo_exacto_036 [--aplicar]
"""

from __future__ import annotations

import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

TOTAL_PDF = {2143513150: 567845.69, 2143513151: 2271382.75}
PRECIO_ORIGINAL = {2143510825: 15200.0, 2143510826: 18000.0}
CUENTAS = (444, 39)

if __name__ == "__main__":
    _assert_target_is_wc()
    tot = {r["i"]: r for r in fetch_all(
        f"SELECT IdDeuda AS i, GranTotal AS g, TotalDetalleCompra AS d FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda IN ({','.join(map(str, TOTAL_PDF))})", ())}
    stmts = []
    for i, nuevo in TOTAL_PDF.items():
        g, d = float(tot[i]["g"]), float(tot[i]["d"])
        print(i, round(g, 2), "->", nuevo)
        stmts.append(("UPDATE dbo.Det_Compras SET [Precio Unitario] = [Precio Unitario] * ? WHERE IdCompra = ?", ((nuevo - (g - d)) / d, i)))
    for i, precio in PRECIO_ORIGINAL.items():
        print(i, "precio ->", precio)
        stmts.append(("UPDATE dbo.Det_Compras SET [Precio Unitario] = ? WHERE IdCompra = ?", (precio, i)))
    antes = {c: bimonetaria.cargar_cuenta(c, refrescar=True) for c in CUENTAS}
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    respaldo = backup_verificado("reparar-centavo-exacto-036")
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('reparar-centavo-exacto-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({"totalPdf": TOTAL_PDF, "precioOriginal": PRECIO_ORIGINAL}), respaldo,
                   "Repara jym-centavo-exacto-036 (29/10): Madelan y Catalpa al total del PDF, Ferias del Centro al precio original.")))
    execute_write_transaction(stmts)
    bimonetaria.invalidar()
    for c in CUENTAS:
        d = bimonetaria.cargar_cuenta(c, refrescar=True)
        print(c, "antes", antes[c]["saldoPesos"], antes[c]["saldoDolares"], " después", d["saldoPesos"], d["saldoDolares"])
