"""036 — grupo 4 (cuentas corrientes con más de 5 facturas): centavos, pares ≤0,10% y FIFO estricto (estrategia 29/10/2026).

Por cuenta de `grupo4_diagnostico_036.cuentas()`:
1. facturas llevadas a su GranTotal al centavo (`jym_centavo_exacto_036`, ya corregido);
2. pares factura-pago con diferencia ≤0,10% redondeados a lo pagado (`jym_redondeo_pares_036`), solo si el ajuste
   acerca el saldo de la cuenta a cero (mismo criterio que `grupo3_redondeo_036`);
3. FIFO estricto (`ejecuciones.simular/aplicar`), que respeta las imputaciones manuales vigentes.
Un respaldo para los redondeos y otro del FIFO. Control: el saldo de cada cuenta cambia solo por los redondeos.
Uso (desde backend/): python -m scripts.grupo4_cierre_036 [--aplicar]
"""

from __future__ import annotations

import json
import sys

from scripts import jym_centavo_exacto_036 as centavo, jym_redondeo_pares_036 as pares
from scripts.grupo4_diagnostico_036 import cuentas
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.recalculo_fifo import ejecuciones
from src.features.vinculos.backup import backup_verificado

U = "Sergio (barrida 036)"


def _escalar(i: int, nuevo: float, total: float, tot: dict) -> tuple:
    g, d = float(tot["g"]), float(tot["d"] or 0)
    if abs(d) > 1e-6:
        return ("UPDATE dbo.Det_Compras SET [Precio Unitario] = [Precio Unitario] * ? WHERE IdCompra = ?", ((nuevo - (g - d)) / d, i))
    return ("UPDATE dbo.Compras SET [Gastos Varios] = ISNULL([Gastos Varios], 0) + ? WHERE IdDeuda = ?", (nuevo - total, i))


def plan(ct: int, saldo: float) -> tuple[list, dict]:
    centavo.C = pares.C = ct
    cambios = {f["i"]: (float(f["g"]), f["nuevo"]) for f in centavo.casos()}
    par = {i: (total, nuevo) for i, _, total, nuevo in pares.pares()}
    ajuste_par = sum(n - t for t, n in par.values())
    if par and abs(saldo - ajuste_par) <= abs(saldo) + 0.005:  # deuda +x ⇒ saldo −x
        cambios.update(par)
    if not cambios:
        return [], {}
    tot = {r["i"]: r for r in fetch_all(
        f"SELECT IdDeuda AS i, GranTotal AS g, TotalDetalleCompra AS d FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda IN ({','.join(map(str, cambios))})", ())}
    return [_escalar(i, n, t, tot[i]) for i, (t, n) in cambios.items()], {str(i): [round(t, 4), n] for i, (t, n) in cambios.items()}


if __name__ == "__main__":
    _assert_target_is_wc()
    lista = [c for c, _, _ in cuentas()]
    antes = {c: bimonetaria.cargar_cuenta(c, refrescar=True) for c in lista}
    stmts, detalle = [], {}
    for c in lista:
        s, d = plan(c, float(antes[c]["saldoPesos"]))
        stmts += s
        if d:
            detalle[str(c)] = d
            print(c, len(d), "facturas, ajuste", round(sum(n - t for t, n in d.values()), 2))
    print(len(lista), "cuentas;", sum(len(d) for d in detalle.values()), "facturas a redondear")
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    if stmts:
        respaldo = backup_verificado("grupo4-redondeos-036")
        stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                      "VALUES ('grupo4-redondeos-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                      (json.dumps(detalle), respaldo, f"Grupo 4: {sum(len(d) for d in detalle.values())} facturas al centavo o "
                       f"redondeadas a su pago 1 a 1 (≤0,10%) en {len(detalle)} cuentas.")))
        execute_write_transaction(stmts)
    sim = ejecuciones.simular(lista, U)
    print("FIFO:", sim["resumen"])
    print(ejecuciones.aplicar(sim["idEjecucion"], lista, False, U))
    bimonetaria.invalidar()
    for c in lista:
        d = bimonetaria.cargar_cuenta(c, refrescar=True)
        esperado = float(antes[c]["saldoPesos"]) - sum(n - t for t, n in detalle.get(str(c), {}).values())
        if abs(float(d["saldoPesos"]) - esperado) > 0.01:
            print("CONTROL", c, "antes", antes[c]["saldoPesos"], "esperado", round(esperado, 2), "después", d["saldoPesos"])
    print("Control de saldos terminado.")
